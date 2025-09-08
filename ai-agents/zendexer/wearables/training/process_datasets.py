#!/usr/bin/env python3
"""
ZenGlow Multi-Dataset Processor
Process stress, demographic, and activity data for wellness model training
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path
import glob
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class ZenGlowDataProcessor:
    """Comprehensive processor for multiple wellness datasets"""
    
    def __init__(self, data_root="/mnt/DevBuilds/ZenGlow/ZenGlow/ai-agents/zendexer/wearables/data"):
        self.data_root = Path(data_root)
        self.stress_data_path = self.data_root / "stress_dataset" / "Data"
        self.demographics_path = self.data_root / "demographics" / "data_subjects_info.csv"
        self.uci_path = self.data_root / "UCI HAR Dataset"
        
        print("🎯 ZenGlow Multi-Dataset Processor")
        print("=" * 50)
        
    def load_demographics_data(self):
        """Load subject demographic information"""
        print("📊 Loading demographic data...")
        
        if self.demographics_path.exists():
            demographics = pd.read_csv(self.demographics_path)
            print(f"   • Found {len(demographics)} subjects")
            print(f"   • Columns: {list(demographics.columns)}")
            
            # Decode gender (assuming 1=male, 0=female)
            demographics['gender_label'] = demographics['gender'].map({1: 'Male', 0: 'Female'})
            
            # Calculate BMI
            demographics['bmi'] = demographics['weight'] / (demographics['height']/100)**2
            demographics['bmi_category'] = pd.cut(demographics['bmi'], 
                                                bins=[0, 18.5, 25, 30, 100],
                                                labels=['Underweight', 'Normal', 'Overweight', 'Obese'])
            
            print(f"   • Age range: {demographics['age'].min()}-{demographics['age'].max()}")
            print(f"   • Gender distribution: {demographics['gender_label'].value_counts().to_dict()}")
            print(f"   • BMI categories: {demographics['bmi_category'].value_counts().to_dict()}")
            
            return demographics
        else:
            print("   ⚠️  Demographics file not found")
            return None
    
    def load_stress_sensor_data(self, subject_limit=3):
        """Load stress sensor data from wearable devices"""
        print("🔋 Loading stress sensor data...")
        
        if not self.stress_data_path.exists():
            print("   ⚠️  Stress dataset not found")
            return None
            
        stress_data = []
        subjects = list(self.stress_data_path.glob("S*"))[:subject_limit]  # Limit for demo
        
        for subject_dir in subjects:
            subject_id = subject_dir.name
            print(f"   • Processing {subject_id}...")
            
            # Find exam sessions
            sessions = list(subject_dir.glob("*"))
            
            for session_dir in sessions:
                session_name = session_dir.name
                
                # Look for sensor files
                acc_file = session_dir / "ACC.csv"
                hr_file = session_dir / "HR.csv"
                temp_file = session_dir / "TEMP.csv"
                
                if acc_file.exists() and hr_file.exists():
                    try:
                        # Load accelerometer data
                        acc_data = pd.read_csv(acc_file, header=None)
                        if len(acc_data) > 2:
                            # Skip header rows
                            acc_values = acc_data.iloc[2:, :3].values.astype(float)
                            
                            # Load heart rate data
                            hr_data = pd.read_csv(hr_file, header=None)
                            if len(hr_data) > 2:
                                hr_values = hr_data.iloc[2:].values.astype(float).flatten()
                                
                                # Create wellness features
                                wellness_features = self.extract_stress_wellness_features(
                                    acc_values, hr_values, subject_id, session_name
                                )
                                stress_data.append(wellness_features)
                                
                    except Exception as e:
                        print(f"     ⚠️  Error processing {subject_id}/{session_name}: {e}")
        
        if stress_data:
            stress_df = pd.DataFrame(stress_data)
            print(f"   • Processed {len(stress_df)} stress sessions")
            return stress_df
        else:
            print("   ⚠️  No stress data processed")
            return None
    
    def extract_stress_wellness_features(self, acc_data, hr_data, subject_id, session):
        """Extract wellness features from stress sensor data"""
        
        # Accelerometer features
        acc_magnitude = np.sqrt(np.sum(acc_data**2, axis=1))
        acc_mean = np.mean(acc_magnitude)
        acc_std = np.std(acc_magnitude)
        movement_intensity = np.percentile(acc_magnitude, 95)
        
        # Heart rate features
        hr_mean = np.mean(hr_data) if len(hr_data) > 0 else 70
        hr_std = np.std(hr_data) if len(hr_data) > 1 else 5
        hr_max = np.max(hr_data) if len(hr_data) > 0 else 80
        
        # Stress indicators
        stress_level = 'High' if 'Midterm' in session or 'Final' in session else 'Low'
        stress_score = 0.8 if stress_level == 'High' else 0.3
        
        # Wellness score (inverse of stress)
        wellness_score = 1.0 - stress_score
        
        return {
            'subject_id': subject_id,
            'session': session,
            'acc_mean': acc_mean,
            'acc_std': acc_std,
            'movement_intensity': movement_intensity,
            'hr_mean': hr_mean,
            'hr_std': hr_std,
            'hr_max': hr_max,
            'stress_level': stress_level,
            'stress_score': stress_score,
            'wellness_score': wellness_score
        }
    
    def load_uci_activity_data(self):
        """Load UCI HAR activity recognition data"""
        print("🏃 Loading UCI activity data...")
        
        try:
            # Load features
            features_file = self.uci_path / "features.txt"
            if features_file.exists():
                features = pd.read_csv(features_file, header=None, sep=' ', names=['id', 'feature'])
                feature_names = features['feature'].tolist()
            else:
                feature_names = [f'feature_{i}' for i in range(561)]
            
            # Load training data
            X_train_file = self.uci_path / "train" / "X_train.txt"
            y_train_file = self.uci_path / "train" / "y_train.txt"
            
            if X_train_file.exists() and y_train_file.exists():
                X_train = pd.read_csv(X_train_file, sep='\s+', header=None, names=feature_names)
                y_train = pd.read_csv(y_train_file, header=None, names=['activity'])
                
                # Load test data
                X_test_file = self.uci_path / "test" / "X_test.txt"
                y_test_file = self.uci_path / "test" / "y_test.txt"
                
                if X_test_file.exists() and y_test_file.exists():
                    X_test = pd.read_csv(X_test_file, sep='\s+', header=None, names=feature_names)
                    y_test = pd.read_csv(y_test_file, header=None, names=['activity'])
                    
                    # Combine train and test
                    X_combined = pd.concat([X_train, X_test], ignore_index=True)
                    y_combined = pd.concat([y_train, y_test], ignore_index=True)
                    
                    print(f"   • Total samples: {len(X_combined)}")
                    print(f"   • Features: {len(feature_names)}")
                    print(f"   • Activity distribution: {y_combined['activity'].value_counts().to_dict()}")
                    
                    return X_combined, y_combined, feature_names
            
        except Exception as e:
            print(f"   ⚠️  Error loading UCI data: {e}")
        
        return None, None, None
    
    def create_unified_wellness_dataset(self):
        """Create a unified wellness dataset from all sources"""
        print("\n🔄 Creating unified wellness dataset...")
        
        # Load all data sources
        demographics = self.load_demographics_data()
        stress_data = self.load_stress_sensor_data()
        X_uci, y_uci, feature_names = self.load_uci_activity_data()
        
        unified_data = []
        
        # Process stress data with demographics
        if stress_data is not None and demographics is not None:
            print("   • Merging stress and demographic data...")
            
            for _, row in stress_data.iterrows():
                # Extract subject number from subject_id (e.g., "S5" -> 5)
                subject_num = int(row['subject_id'].replace('S', ''))
                
                # Find matching demographic data
                demo_row = demographics[demographics['code'] == subject_num]
                
                if not demo_row.empty:
                    demo_data = demo_row.iloc[0]
                    
                    # Create unified record
                    unified_record = {
                        'subject_id': subject_num,
                        'age': demo_data['age'],
                        'gender': demo_data['gender'],
                        'weight': demo_data['weight'],
                        'height': demo_data['height'],
                        'bmi': demo_data['bmi'],
                        'session_type': row['session'],
                        'movement_level': min(row['acc_mean'] / 10, 1.0),  # Normalize
                        'heart_rate_avg': row['hr_mean'],
                        'heart_rate_variability': row['hr_std'],
                        'stress_level': row['stress_score'],
                        'wellness_score': row['wellness_score'],
                        'data_source': 'stress_sensor'
                    }
                    unified_data.append(unified_record)
        
        # Add synthetic UCI-based wellness data
        if X_uci is not None and y_uci is not None:
            print("   • Adding UCI activity-based wellness data...")
            
            # Sample a subset for processing
            sample_size = min(1000, len(X_uci))
            sample_indices = np.random.choice(len(X_uci), sample_size, replace=False)
            
            for idx in sample_indices:
                # Extract key features for wellness
                acc_features = [col for col in feature_names if 'Acc' in col and 'mean' in col]
                gyro_features = [col for col in feature_names if 'Gyro' in col and 'mean' in col]
                
                if acc_features and gyro_features:
                    acc_mean = X_uci.iloc[idx][acc_features].mean()
                    gyro_mean = X_uci.iloc[idx][gyro_features].mean()
                    activity = y_uci.iloc[idx]['activity']
                    
                    # Map activities to wellness scores
                    activity_wellness_map = {
                        1: 0.8,  # WALKING
                        2: 0.9,  # WALKING_UPSTAIRS  
                        3: 0.7,  # WALKING_DOWNSTAIRS
                        4: 0.3,  # SITTING
                        5: 0.4,  # STANDING
                        6: 0.2   # LAYING
                    }
                    
                    # Generate synthetic demographics
                    age = np.random.randint(20, 60)
                    gender = np.random.choice([0, 1])
                    weight = np.random.normal(70 if gender else 60, 10)
                    height = np.random.normal(175 if gender else 165, 8)
                    bmi = weight / (height/100)**2
                    
                    unified_record = {
                        'subject_id': f'uci_{idx}',
                        'age': age,
                        'gender': gender,
                        'weight': weight,
                        'height': height,
                        'bmi': bmi,
                        'session_type': f'activity_{activity}',
                        'movement_level': min(abs(acc_mean), 1.0),
                        'heart_rate_avg': np.random.normal(75, 10),
                        'heart_rate_variability': np.random.normal(5, 2),
                        'stress_level': 1.0 - activity_wellness_map.get(activity, 0.5),
                        'wellness_score': activity_wellness_map.get(activity, 0.5),
                        'data_source': 'uci_activity'
                    }
                    unified_data.append(unified_record)
        
        if unified_data:
            unified_df = pd.DataFrame(unified_data)
            print(f"   • Created unified dataset with {len(unified_df)} records")
            print(f"   • Data sources: {unified_df['data_source'].value_counts().to_dict()}")
            
            # Save the unified dataset
            output_path = self.data_root / "processed" / "unified_wellness_dataset.csv"
            output_path.parent.mkdir(exist_ok=True)
            unified_df.to_csv(output_path, index=False)
            print(f"   • Saved to: {output_path}")
            
            return unified_df
        else:
            print("   ⚠️  No unified data created")
            return None
    
    def generate_training_features(self, unified_df):
        """Generate features for mobile model training"""
        print("\n🎯 Generating mobile training features...")
        
        if unified_df is None:
            return None, None
        
        # Select features for mobile model
        feature_columns = [
            'age', 'gender', 'bmi', 'movement_level', 
            'heart_rate_avg', 'heart_rate_variability', 'stress_level'
        ]
        
        target_column = 'wellness_score'
        
        # Prepare features and target
        X = unified_df[feature_columns].copy()
        y = unified_df[target_column].copy()
        
        # Handle missing values
        X = X.fillna(X.mean())
        y = y.fillna(y.mean())
        
        # Normalize features for mobile model
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        print(f"   • Training features shape: {X_scaled.shape}")
        print(f"   • Target range: {y.min():.3f} - {y.max():.3f}")
        print(f"   • Feature columns: {feature_columns}")
        
        # Save for training
        training_path = self.data_root / "processed" / "mobile_training_data.csv"
        training_df = pd.DataFrame(X_scaled, columns=feature_columns)
        training_df[target_column] = y.values
        training_df.to_csv(training_path, index=False)
        print(f"   • Saved training data to: {training_path}")
        
        return X_scaled, y.values
    
    def process_all_datasets(self):
        """Process all available datasets"""
        print("\n🚀 Processing all datasets for ZenGlow...")
        
        # Create unified dataset
        unified_df = self.create_unified_wellness_dataset()
        
        # Generate training features
        X, y = self.generate_training_features(unified_df)
        
        print("\n✅ Dataset processing complete!")
        print(f"📊 Summary:")
        if unified_df is not None:
            print(f"   • Total records: {len(unified_df)}")
            print(f"   • Wellness score avg: {unified_df['wellness_score'].mean():.3f}")
            print(f"   • Data sources: {len(unified_df['data_source'].unique())}")
        if X is not None:
            print(f"   • Training samples: {X.shape[0]}")
            print(f"   • Features: {X.shape[1]}")
        
        return unified_df, X, y

def main():
    """Main processing pipeline"""
    processor = ZenGlowDataProcessor()
    unified_df, X, y = processor.process_all_datasets()
    
    if unified_df is not None:
        print(f"\n📋 Dataset Sample:")
        print(unified_df.head())
        
        print(f"\n📈 Wellness Statistics:")
        print(unified_df[['age', 'bmi', 'wellness_score', 'stress_level']].describe())

if __name__ == "__main__":
    main()
