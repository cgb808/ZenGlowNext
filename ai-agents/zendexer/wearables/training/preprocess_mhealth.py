"""
MHEALTH Dataset Preprocessor for ZenGlow Wellness Prediction
Converts MHEALTH sensor data to ZenGlow wellness features

Citation Required:
Banos, O., et al. "mHealthDroid: a novel framework for agile development of mobile health applications." 
IWAAL 2014, Belfast, Northern Ireland, December 2-5, (2014).

Banos, O., et al. "Design, implementation and validation of a novel open framework for agile development 
of mobile health applications." BioMedical Engineering OnLine, vol. 14, no. S2:S6, pp. 1-20 (2015).
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

class MHEALTHPreprocessor:
    """Convert MHEALTH dataset to ZenGlow wellness features"""
    
    def __init__(self):
        # MHEALTH sensor column mapping
        self.sensor_columns = {
            # Chest sensors (1-9)
            'chest_acc_x': 1, 'chest_acc_y': 2, 'chest_acc_z': 3,
            'chest_ecg1': 4, 'chest_ecg2': 5,
            'chest_gyro_x': 6, 'chest_gyro_y': 7, 'chest_gyro_z': 8,
            'chest_mag_x': 9, 'chest_mag_y': 10, 'chest_mag_z': 11,
            
            # Left ankle sensors (10-17)
            'ankle_acc_x': 12, 'ankle_acc_y': 13, 'ankle_acc_z': 14,
            'ankle_gyro_x': 15, 'ankle_gyro_y': 16, 'ankle_gyro_z': 17,
            'ankle_mag_x': 18, 'ankle_mag_y': 19, 'ankle_mag_z': 20,
            
            # Right arm sensors (18-23)
            'arm_acc_x': 21, 'arm_acc_y': 22, 'arm_acc_z': 23,
            
            # Activity label
            'activity': 24
        }
        
        self.activity_mapping = {
            0: 'null',
            1: 'standing_still',
            2: 'sitting_relaxing', 
            3: 'lying_down',
            4: 'walking',
            5: 'climbing_stairs',
            6: 'waist_bends_forward',
            7: 'frontal_elevation_arms',
            8: 'knees_bending',
            9: 'cycling',
            10: 'jogging',
            11: 'running',
            12: 'jump_front_back'
        }
    
    def load_mhealth_file(self, file_path):
        """Load a single MHEALTH subject file"""
        print(f"Loading {file_path}")
        
        # MHEALTH files are space-separated with 24 columns
        try:
            data = pd.read_csv(file_path, sep='\t', header=None)
            if data.shape[1] != 24:
                # Try space separator
                data = pd.read_csv(file_path, sep=' ', header=None)
            
            print(f"Loaded {len(data)} samples with {data.shape[1]} features")
            return data
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return None
    
    def extract_wellness_features(self, mhealth_data, subject_id='unknown'):
        """Extract wellness features from MHEALTH sensor data"""
        if mhealth_data is None:
            return None
        
        features = []
        
        # Process in 30-second windows (assuming 50Hz sampling rate = 1500 samples per window)
        window_size = 1500  # 30 seconds at 50Hz
        
        for i in range(0, len(mhealth_data) - window_size, window_size // 2):  # 50% overlap
            window = mhealth_data.iloc[i:i + window_size]
            
            if len(window) < window_size:
                continue
            
            # Calculate wellness features for this window
            feature_vector = self._calculate_window_features(window, subject_id, i)
            features.append(feature_vector)
        
        return pd.DataFrame(features)
    
    def _calculate_window_features(self, window, subject_id, window_idx):
        """Calculate wellness features for a single time window"""
        
        # Chest accelerometer (activity level)
        chest_acc_mag = np.sqrt(
            window.iloc[:, self.sensor_columns['chest_acc_x']-1]**2 + 
            window.iloc[:, self.sensor_columns['chest_acc_y']-1]**2 + 
            window.iloc[:, self.sensor_columns['chest_acc_z']-1]**2
        )
        
        # Ankle accelerometer (step detection)
        ankle_acc_mag = np.sqrt(
            window.iloc[:, self.sensor_columns['ankle_acc_x']-1]**2 + 
            window.iloc[:, self.sensor_columns['ankle_acc_y']-1]**2 + 
            window.iloc[:, self.sensor_columns['ankle_acc_z']-1]**2
        )
        
        # ECG for heart rate estimation (simplified)
        ecg_signal = window.iloc[:, self.sensor_columns['chest_ecg1']-1]
        
        # Activity classification
        activity_mode = window.iloc[:, self.sensor_columns['activity']-1].mode()
        activity_label = activity_mode.iloc[0] if len(activity_mode) > 0 else 0
        
        # Generate timestamp (simulate real-time data)
        timestamp = datetime.now() + timedelta(seconds=window_idx * 15)  # 15-second intervals
        
        # Calculate wellness features
        features = {
            'timestamp': timestamp.isoformat(),
            'device_id': f'mhealth_subject_{subject_id}',
            
            # Physiological features
            'heart_rate': self._estimate_heart_rate(ecg_signal),
            'heart_rate_variability': self._calculate_hrv(ecg_signal),
            'activity_level': self._classify_activity_level(chest_acc_mag.std()),
            'steps_per_minute': self._estimate_steps(ankle_acc_mag),
            'movement_variance': chest_acc_mag.var(),
            
            # Behavioral proxies (derived from activity patterns)
            'activity_intensity': chest_acc_mag.mean(),
            'movement_consistency': 1.0 / (1.0 + chest_acc_mag.var()),  # Inverse of variance
            'posture_stability': 1.0 / (1.0 + window.iloc[:, self.sensor_columns['chest_gyro_x']-1].std()),
            
            # Contextual features
            'activity_type': self.activity_mapping.get(activity_label, 'unknown'),
            'is_active': 1 if activity_label >= 4 else 0,  # Walking or higher intensity
            'is_sedentary': 1 if activity_label <= 3 else 0,  # Sitting, lying, standing
            
            # Derived wellness indicators
            'stress_indicator': self._estimate_stress(ecg_signal, chest_acc_mag),
            'wellness_score': self._calculate_wellness_score(chest_acc_mag, ecg_signal, activity_label)
        }
        
        return features
    
    def _estimate_heart_rate(self, ecg_signal, sampling_rate=50):
        """Estimate heart rate from ECG signal"""
        if len(ecg_signal) == 0:
            return 75  # Default resting HR
        
        # Simple peak detection (in real implementation would use proper ECG analysis)
        signal_std = ecg_signal.std()
        if signal_std > 0:
            # Estimate based on signal variability
            estimated_hr = 60 + (signal_std * 20)  # Rough approximation
            return max(50, min(150, estimated_hr))  # Clamp to reasonable range
        return 75
    
    def _calculate_hrv(self, ecg_signal):
        """Calculate heart rate variability approximation"""
        if len(ecg_signal) == 0:
            return 40
        
        # Simplified HRV based on ECG signal variance
        hrv = ecg_signal.std() * 100  # Scale factor
        return max(20, min(80, hrv))  # Clamp to reasonable HRV range
    
    def _classify_activity_level(self, acceleration_std):
        """Classify activity level from acceleration variance"""
        if acceleration_std < 0.5:
            return 'sedentary'
        elif acceleration_std < 1.5:
            return 'light'
        elif acceleration_std < 3.0:
            return 'moderate'
        else:
            return 'vigorous'
    
    def _estimate_steps(self, ankle_acc_mag, sampling_rate=50):
        """Estimate steps per minute from ankle accelerometer"""
        # Simple step detection based on acceleration peaks
        threshold = ankle_acc_mag.mean() + ankle_acc_mag.std()
        peaks = (ankle_acc_mag > threshold).sum()
        
        # Convert to steps per minute (30-second window)
        steps_per_30sec = peaks / 4  # Rough step estimation
        steps_per_minute = steps_per_30sec * 2
        
        return max(0, min(200, steps_per_minute))  # Reasonable range
    
    def _estimate_stress(self, ecg_signal, chest_acc_mag):
        """Estimate stress level from physiological signals"""
        if len(ecg_signal) == 0:
            return 0.3
        
        # Stress correlates with HRV and movement patterns
        ecg_variability = ecg_signal.std()
        movement_chaos = chest_acc_mag.std()
        
        # Normalized stress indicator (0-1)
        stress = (ecg_variability * 0.6 + movement_chaos * 0.4) / 5.0
        return max(0.0, min(1.0, stress))
    
    def _calculate_wellness_score(self, chest_acc_mag, ecg_signal, activity_label):
        """Calculate overall wellness score (0-1)"""
        # Activity score
        activity_score = 0.8 if 4 <= activity_label <= 11 else 0.4  # Active vs sedentary
        
        # Physiological stability
        movement_score = 1.0 / (1.0 + chest_acc_mag.var())
        ecg_score = 1.0 / (1.0 + ecg_signal.var()) if len(ecg_signal) > 0 else 0.5
        
        # Combined wellness score
        wellness = (activity_score * 0.4 + movement_score * 0.3 + ecg_score * 0.3)
        return max(0.1, min(1.0, wellness))
    
    def process_dataset(self, input_dir, output_file):
        """Process entire MHEALTH dataset"""
        input_path = Path(input_dir)
        all_features = []
        
        # Find all MHEALTH data files (typically named mHealth_subject*.log)
        mhealth_files = list(input_path.glob("*subject*.log")) + list(input_path.glob("*subject*.txt"))
        
        if not mhealth_files:
            print(f"No MHEALTH files found in {input_dir}")
            print("Expected files: mHealth_subject1.log, mHealth_subject2.log, etc.")
            return
        
        print(f"Found {len(mhealth_files)} MHEALTH files")
        
        for file_path in mhealth_files:
            # Extract subject ID from filename
            subject_id = file_path.stem.split('subject')[-1].split('.')[0]
            
            # Load and process
            mhealth_data = self.load_mhealth_file(file_path)
            if mhealth_data is not None:
                features = self.extract_wellness_features(mhealth_data, subject_id)
                if features is not None:
                    all_features.append(features)
                    print(f"Extracted {len(features)} feature windows from subject {subject_id}")
        
        if all_features:
            # Combine all features
            combined_features = pd.concat(all_features, ignore_index=True)
            
            # Save processed data
            combined_features.to_csv(output_file, index=False)
            print(f"Saved {len(combined_features)} wellness feature vectors to {output_file}")
            
            # Print summary statistics
            print("\nDataset Summary:")
            print(f"Total samples: {len(combined_features)}")
            print(f"Subjects: {combined_features['device_id'].nunique()}")
            print(f"Average wellness score: {combined_features['wellness_score'].mean():.3f}")
            print(f"Activity distribution:")
            print(combined_features['activity_type'].value_counts())
            
        else:
            print("No valid data processed")

def main():
    parser = argparse.ArgumentParser(description='Convert MHEALTH dataset to ZenGlow wellness features')
    parser.add_argument('--input', required=True, help='Path to MHEALTH dataset directory')
    parser.add_argument('--output', required=True, help='Output CSV file for wellness features')
    
    args = parser.parse_args()
    
    print("🏥 MHEALTH to ZenGlow Wellness Feature Converter")
    print("=" * 50)
    print(f"Input directory: {args.input}")
    print(f"Output file: {args.output}")
    print()
    
    # Create output directory if needed
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Process dataset
    preprocessor = MHEALTHPreprocessor()
    preprocessor.process_dataset(args.input, args.output)
    
    print("\n✅ MHEALTH preprocessing completed!")
    print("\nCitation reminder:")
    print("Please cite the MHEALTH dataset authors in any publications:")
    print("- Banos, O., et al. IWAAL 2014")
    print("- Banos, O., et al. BioMedical Engineering OnLine, 2015")

if __name__ == "__main__":
    main()
