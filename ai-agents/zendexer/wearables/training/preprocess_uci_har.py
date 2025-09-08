"""
UCI HAR Dataset Preprocessor for ZenGlow Wellness Prediction
Converts UCI Human Activity Recognition data to ZenGlow wellness features

Citation Required:
Davide Anguita, Alessandro Ghio, Luca Oneto, Xavier Parra and Jorge L. Reyes-Ortiz. 
Human Activity Recognition on Smartphones using a Multiclass Hardware-Friendly Support Vector Machine. 
International Workshop of Ambient Assisted Living (IWAAL 2012). Vitoria-Gasteiz, Spain. Dec 2012
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler, LabelEncoder
import warnings
warnings.filterwarnings('ignore')

class UCIHARPreprocessor:
    """Convert UCI HAR dataset to ZenGlow wellness features"""
    
    def __init__(self):
        # UCI HAR activity mapping (child-friendly adaptation)
        self.activity_mapping = {
            1: 'walking',           # WALKING -> walking
            2: 'walking_upstairs',  # WALKING_UPSTAIRS -> walking_upstairs  
            3: 'walking_downstairs', # WALKING_DOWNSTAIRS -> walking_downstairs
            4: 'sitting',           # SITTING -> sitting
            5: 'standing',          # STANDING -> standing  
            6: 'lying_down'         # LAYING -> lying_down
        }
        
        # Wellness level mapping (child wellness context)
        self.wellness_mapping = {
            'walking': 0.8,         # High wellness - active movement
            'walking_upstairs': 0.9, # Very high wellness - vigorous activity  
            'walking_downstairs': 0.7, # Good wellness - moderate activity
            'sitting': 0.4,         # Low wellness - sedentary
            'standing': 0.5,        # Moderate wellness - stationary but upright
            'lying_down': 0.3       # Low wellness - resting/inactive
        }
        
        # Stress level mapping (inverted activity intensity)
        self.stress_mapping = {
            'walking': 0.2,         # Low stress - natural movement
            'walking_upstairs': 0.3, # Moderate stress - physical exertion
            'walking_downstairs': 0.2, # Low stress - controlled movement  
            'sitting': 0.6,         # High stress - prolonged sitting
            'standing': 0.4,        # Moderate stress - standing fatigue
            'lying_down': 0.1       # Very low stress - resting
        }
    
    def load_uci_har_data(self, data_path):
        """Load UCI HAR dataset from the extracted directory"""
        print(f"📁 Loading UCI HAR dataset from {data_path}")
        
        uci_path = Path(data_path) / "UCI HAR Dataset"
        
        # Load training data
        print("Loading training data...")
        X_train = pd.read_csv(uci_path / "train" / "X_train.txt", sep=r'\s+', header=None)
        y_train = pd.read_csv(uci_path / "train" / "y_train.txt", header=None, names=['activity'])
        subject_train = pd.read_csv(uci_path / "train" / "subject_train.txt", header=None, names=['subject'])
        
        # Load test data  
        print("Loading test data...")
        X_test = pd.read_csv(uci_path / "test" / "X_test.txt", sep=r'\s+', header=None)
        y_test = pd.read_csv(uci_path / "test" / "y_test.txt", header=None, names=['activity'])
        subject_test = pd.read_csv(uci_path / "test" / "subject_test.txt", header=None, names=['subject'])
        
        # Load feature names
        features = pd.read_csv(uci_path / "features.txt", sep=r'\s+', header=None, names=['index', 'feature'])
        feature_names = features['feature'].tolist()
        
        # Load activity labels
        activity_labels = pd.read_csv(uci_path / "activity_labels.txt", sep=r'\s+', header=None, names=['id', 'activity'])
        
        print(f"✅ Loaded {len(X_train)} training samples and {len(X_test)} test samples")
        print(f"✅ {len(feature_names)} features per sample")
        print(f"✅ {len(activity_labels)} activity types")
        
        return {
            'X_train': X_train, 'y_train': y_train, 'subject_train': subject_train,
            'X_test': X_test, 'y_test': y_test, 'subject_test': subject_test,
            'feature_names': feature_names, 'activity_labels': activity_labels
        }
    
    def extract_wellness_features(self, uci_data, output_path="../data/processed"):
        """Extract wellness features from UCI HAR data"""
        print("🔄 Extracting wellness features...")
        
        # Combine train and test data for comprehensive feature extraction
        X_combined = pd.concat([uci_data['X_train'], uci_data['X_test']], ignore_index=True)
        y_combined = pd.concat([uci_data['y_train'], uci_data['y_test']], ignore_index=True)
        subject_combined = pd.concat([uci_data['subject_train'], uci_data['subject_test']], ignore_index=True)
        
        # Set feature names
        X_combined.columns = uci_data['feature_names']
        
        wellness_features = []
        
        for i in range(len(X_combined)):
            if i % 1000 == 0:
                print(f"Processing sample {i}/{len(X_combined)}")
            
            # Get current sample data
            features = X_combined.iloc[i]
            activity_id = y_combined.iloc[i]['activity']
            subject_id = subject_combined.iloc[i]['subject']
            activity_name = self.activity_mapping[activity_id]
            
            # Generate realistic timestamp (simulating child's day)
            base_time = datetime(2025, 8, 13, 7, 0, 0)  # Start at 7 AM
            timestamp = base_time + timedelta(minutes=i * 2.56)  # ~2.56 min intervals
            
            # Extract key wellness indicators from 561 features
            wellness_feature = self._calculate_wellness_features(features, activity_name, subject_id, timestamp, activity_id)
            wellness_features.append(wellness_feature)
        
        # Convert to DataFrame
        wellness_df = pd.DataFrame(wellness_features)
        
        # Save processed data
        Path(output_path).mkdir(parents=True, exist_ok=True)
        output_file = Path(output_path) / "uci_har_wellness_features.csv"
        wellness_df.to_csv(output_file, index=False)
        
        print(f"✅ Wellness features saved to {output_file}")
        print(f"📊 Generated {len(wellness_df)} wellness samples")
        
        return wellness_df
    
    def _calculate_wellness_features(self, features, activity_name, subject_id, timestamp, activity_id):
        """Calculate wellness features from UCI HAR 561-feature vector"""
        
        # Key feature indices (approximated from UCI HAR features)
        # Features are time and frequency domain features from accelerometer and gyroscope
        
        # Body acceleration magnitude features (approximate indices)
        body_acc_mean = features.iloc[0:3].mean()    # First 3 features: body acc X,Y,Z means
        body_acc_std = features.iloc[3:6].mean()     # Features 4-6: body acc X,Y,Z std
        
        # Gravity acceleration features  
        gravity_acc_mean = features.iloc[40:43].mean()  # Gravity acc features
        gravity_acc_std = features.iloc[43:46].mean()
        
        # Body gyroscope features
        body_gyro_mean = features.iloc[120:123].mean()  # Body gyro features
        body_gyro_std = features.iloc[123:126].mean()
        
        # Jerk signals (derived acceleration)
        body_acc_jerk_mean = features.iloc[80:83].mean()  # Body acc jerk features
        body_gyro_jerk_mean = features.iloc[160:163].mean() # Body gyro jerk features
        
        # Magnitude features
        body_acc_mag_mean = features.iloc[200]     # Body acc magnitude mean
        gravity_acc_mag_mean = features.iloc[213]  # Gravity acc magnitude mean
        body_gyro_mag_mean = features.iloc[226]    # Body gyro magnitude mean
        
        # Frequency domain features (FFT)
        fft_body_acc_mean = features.iloc[266:269].mean()  # FFT body acc
        fft_body_gyro_mean = features.iloc[345:348].mean() # FFT body gyro
        
        # Calculate wellness metrics
        activity_intensity = abs(body_acc_mean) + abs(body_gyro_mean)
        movement_stability = 1.0 / (1.0 + body_acc_std + body_gyro_std)
        posture_quality = 1.0 / (1.0 + abs(gravity_acc_std))
        
        # Derive physiological proxies
        estimated_heart_rate = 70 + (activity_intensity * 50)  # Base HR + activity boost
        estimated_steps = max(0, (body_acc_jerk_mean * 30)) if activity_name in ['walking', 'walking_upstairs', 'walking_downstairs'] else 0
        
        return {
            'timestamp': timestamp.isoformat(),
            'device_id': f'child_{subject_id:03d}',
            'subject_id': subject_id,
            
            # Core wellness features
            'wellness_score': self.wellness_mapping[activity_name],
            'stress_level': self.stress_mapping[activity_name],
            'activity_level': min(1.0, activity_intensity / 2.0),
            
            # Physiological proxies
            'heart_rate': min(180, max(60, estimated_heart_rate)),
            'heart_rate_variability': 20 + np.random.normal(0, 5),  # Simulated HRV
            'steps_per_minute': estimated_steps,
            'movement_variance': body_acc_std,
            
            # Behavioral indicators
            'activity_intensity': activity_intensity,
            'movement_consistency': movement_stability,
            'posture_stability': posture_quality,
            
            # Activity context
            'activity_type': activity_name,
            'is_active': 1 if activity_name.startswith('walking') else 0,
            'is_sedentary': 1 if activity_name in ['sitting', 'lying_down'] else 0,
            'is_upright': 1 if activity_name in ['walking', 'walking_upstairs', 'walking_downstairs', 'standing'] else 0,
            
            # Temporal context
            'hour_of_day': timestamp.hour,
            'is_school_hours': 1 if 8 <= timestamp.hour <= 15 else 0,
            'is_active_hours': 1 if 7 <= timestamp.hour <= 20 else 0,
            
            # Raw sensor proxies (normalized key features)
            'body_acc_magnitude': body_acc_mag_mean,
            'gravity_acc_magnitude': gravity_acc_mag_mean,
            'body_gyro_magnitude': body_gyro_mag_mean,
            'movement_jerk': (body_acc_jerk_mean + body_gyro_jerk_mean) / 2,
            'frequency_energy': (fft_body_acc_mean + fft_body_gyro_mean) / 2,
            
            # Original activity label (for validation)
            'original_activity_id': activity_id if isinstance(activity_id, int) else activity_name
        }
    
    def create_train_test_split(self, wellness_df, test_size=0.2):
        """Create train/test split maintaining subject separation"""
        print("📋 Creating train/test split...")
        
        # Split by subject to avoid data leakage
        unique_subjects = wellness_df['subject_id'].unique()
        n_test_subjects = max(1, int(len(unique_subjects) * test_size))
        
        np.random.seed(42)
        test_subjects = np.random.choice(unique_subjects, n_test_subjects, replace=False)
        
        train_df = wellness_df[~wellness_df['subject_id'].isin(test_subjects)].copy()
        test_df = wellness_df[wellness_df['subject_id'].isin(test_subjects)].copy()
        
        print(f"✅ Train: {len(train_df)} samples from {len(unique_subjects) - n_test_subjects} subjects")
        print(f"✅ Test: {len(test_df)} samples from {n_test_subjects} subjects")
        
        return train_df, test_df

def main():
    """Main preprocessing pipeline"""
    parser = argparse.ArgumentParser(description='Preprocess UCI HAR data for ZenGlow wellness prediction')
    parser.add_argument('--input', default='../data', help='Path to UCI HAR dataset directory')
    parser.add_argument('--output', default='../data/processed', help='Output directory for processed features')
    
    args = parser.parse_args()
    
    print("🎯 UCI HAR to ZenGlow Wellness Feature Extraction")
    print("=" * 50)
    
    # Initialize preprocessor
    preprocessor = UCIHARPreprocessor()
    
    # Load UCI HAR data
    uci_data = preprocessor.load_uci_har_data(args.input)
    
    # Extract wellness features
    wellness_df = preprocessor.extract_wellness_features(uci_data, args.output)
    
    # Create train/test split
    train_df, test_df = preprocessor.create_train_test_split(wellness_df)
    
    # Save splits
    output_path = Path(args.output)
    train_df.to_csv(output_path / "train_wellness_features.csv", index=False)
    test_df.to_csv(output_path / "test_wellness_features.csv", index=False)
    
    print("\n✅ Preprocessing complete!")
    print(f"📁 Training data: {output_path / 'train_wellness_features.csv'}")
    print(f"📁 Test data: {output_path / 'test_wellness_features.csv'}")
    print(f"📁 Combined data: {output_path / 'uci_har_wellness_features.csv'}")

if __name__ == "__main__":
    main()
