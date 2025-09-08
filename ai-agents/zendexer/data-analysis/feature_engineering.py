#!/usr/bin/env python3
"""
Feature Engineering Module for ZenGlow Clustering Pipeline
Transforms raw sensor + mood data into features for clustering analysis
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


class WellnessFeatureEngineer:
    """Feature engineering for wellness sensor and mood data"""
    
    def __init__(self):
        self.feature_definitions = {
            'rolling_stats': ['mean', 'std', 'min', 'max', 'median'],
            'circadian_buckets': ['morning', 'afternoon', 'evening', 'night'],
            'temporal_features': ['hour_of_day', 'day_of_week', 'is_weekend'],
        }
        
    def create_temporal_features(self, df: pd.DataFrame, timestamp_col: str = 'timestamp') -> pd.DataFrame:
        """Create temporal and circadian rhythm features"""
        print("🕐 Creating temporal features...")
        
        # Ensure timestamp is datetime
        df[timestamp_col] = pd.to_datetime(df[timestamp_col])
        
        # Basic temporal features
        df['hour_of_day'] = df[timestamp_col].dt.hour
        df['day_of_week'] = df[timestamp_col].dt.dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        df['month'] = df[timestamp_col].dt.month
        df['day_of_month'] = df[timestamp_col].dt.day
        
        # Circadian buckets (based on typical sleep/wake patterns)
        df['circadian_bucket'] = df['hour_of_day'].apply(self._get_circadian_bucket)
        
        # One-hot encode circadian buckets
        for bucket in self.feature_definitions['circadian_buckets']:
            df[f'is_{bucket}'] = (df['circadian_bucket'] == bucket).astype(int)
        
        # Time-based cyclical encoding (preserves temporal relationships)
        df['hour_sin'] = np.sin(2 * np.pi * df['hour_of_day'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour_of_day'] / 24)
        df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        
        print(f"   • Added {8 + len(self.feature_definitions['circadian_buckets'])} temporal features")
        return df
    
    def _get_circadian_bucket(self, hour: int) -> str:
        """Map hour to circadian rhythm bucket"""
        if 6 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 17:
            return 'afternoon'
        elif 17 <= hour < 22:
            return 'evening'
        else:
            return 'night'
    
    def create_rolling_features(self, df: pd.DataFrame, 
                              numeric_cols: List[str],
                              device_id_col: str = 'device_id',
                              timestamp_col: str = 'timestamp',
                              windows: List[int] = [3, 6, 12]) -> pd.DataFrame:
        """Create rolling statistical features over different time windows (using row counts)"""
        print("📊 Creating rolling statistical features...")
        
        # Ensure timestamp is datetime and sort
        df[timestamp_col] = pd.to_datetime(df[timestamp_col])
        df = df.sort_values([device_id_col, timestamp_col])
        
        # Group by device to calculate rolling stats per individual
        grouped = df.groupby(device_id_col)
        
        for window in windows:
            for col in numeric_cols:
                if col in df.columns:
                    for stat in self.feature_definitions['rolling_stats']:
                        feature_name = f'{col}_rolling_{window}_{stat}'
                        
                        if stat == 'mean':
                            df[feature_name] = grouped[col].transform(
                                lambda x: x.rolling(window, min_periods=1).mean()
                            )
                        elif stat == 'std':
                            df[feature_name] = grouped[col].transform(
                                lambda x: x.rolling(window, min_periods=1).std().fillna(0)
                            )
                        elif stat == 'min':
                            df[feature_name] = grouped[col].transform(
                                lambda x: x.rolling(window, min_periods=1).min()
                            )
                        elif stat == 'max':
                            df[feature_name] = grouped[col].transform(
                                lambda x: x.rolling(window, min_periods=1).max()
                            )
                        elif stat == 'median':
                            df[feature_name] = grouped[col].transform(
                                lambda x: x.rolling(window, min_periods=1).median()
                            )
        
        feature_count = len(windows) * len(numeric_cols) * len(self.feature_definitions['rolling_stats'])
        print(f"   • Added {feature_count} rolling statistical features")
        return df
    
    def create_mood_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create mood-specific features and transformations"""
        print("😊 Creating mood-specific features...")
        
        mood_features = []
        
        # Mood score features
        if 'mood_score' in df.columns:
            # Normalize mood score to 0-1 if not already
            df['mood_score_normalized'] = df['mood_score'].clip(0, 1)
            
            # Mood categories
            df['mood_category'] = pd.cut(df['mood_score_normalized'], 
                                       bins=[0, 0.3, 0.7, 1.0],
                                       labels=['low', 'medium', 'high'])
            
            # Mood volatility (rolling standard deviation)
            df['mood_volatility_6h'] = df.groupby('device_id')['mood_score'].transform(
                lambda x: x.rolling(6, min_periods=1).std().fillna(0)
            )
            
            mood_features.extend(['mood_score_normalized', 'mood_volatility_6h'])
        
        # Wellness self-report features
        if 'wellness_self_report' in df.columns:
            df['wellness_report_normalized'] = df['wellness_self_report'] / 10.0  # Assuming 1-10 scale
            mood_features.append('wellness_report_normalized')
        
        # Confidence features
        if 'confidence' in df.columns:
            df['confidence_normalized'] = df['confidence'].clip(0, 1)
            mood_features.append('confidence_normalized')
        
        # One-hot encode mood categories
        if 'mood_category' in df.columns:
            mood_dummies = pd.get_dummies(df['mood_category'], prefix='mood')
            df = pd.concat([df, mood_dummies], axis=1)
            mood_features.extend(mood_dummies.columns.tolist())
        
        print(f"   • Added {len(mood_features)} mood-specific features")
        return df
    
    def create_physiological_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create physiological sensor features"""
        print("❤️ Creating physiological features...")
        
        physio_features = []
        
        # Heart rate features
        if 'heart_rate' in df.columns:
            # Heart rate zones (based on age-adjusted zones)
            df['hr_resting_zone'] = (df['heart_rate'] < 100).astype(int)
            df['hr_moderate_zone'] = ((df['heart_rate'] >= 100) & (df['heart_rate'] < 150)).astype(int)
            df['hr_vigorous_zone'] = (df['heart_rate'] >= 150).astype(int)
            
            physio_features.extend(['hr_resting_zone', 'hr_moderate_zone', 'hr_vigorous_zone'])
        
        # Activity level features
        if 'activity_level' in df.columns:
            # Encode activity levels
            activity_mapping = {'sedentary': 0, 'light': 1, 'moderate': 2, 'vigorous': 3}
            df['activity_level_encoded'] = df['activity_level'].map(activity_mapping).fillna(1)
            physio_features.append('activity_level_encoded')
        
        # Steps features
        if 'steps' in df.columns:
            # Daily step goals
            df['steps_goal_met'] = (df['steps'] >= 10000).astype(int)
            df['steps_per_1000'] = df['steps'] / 1000  # Scale for better clustering
            physio_features.extend(['steps_goal_met', 'steps_per_1000'])
        
        # Stress indicator features
        if 'stress_indicator' in df.columns:
            df['stress_level'] = df['stress_indicator'].clip(0, 1)
            df['high_stress'] = (df['stress_indicator'] > 0.7).astype(int)
            physio_features.extend(['stress_level', 'high_stress'])
        
        # HRV features
        if 'hrv' in df.columns:
            df['hrv_normalized'] = df['hrv'] / 100  # Assuming typical HRV ranges
            physio_features.append('hrv_normalized')
        
        print(f"   • Added {len(physio_features)} physiological features")
        return df
    
    def create_behavioral_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create behavioral pattern features"""
        print("📱 Creating behavioral features...")
        
        behavioral_features = []
        
        # Screen time features
        if 'screen_time' in df.columns:
            # Screen time categories (minutes)
            df['screen_time_low'] = (df['screen_time'] < 30).astype(int)
            df['screen_time_moderate'] = ((df['screen_time'] >= 30) & (df['screen_time'] < 120)).astype(int)
            df['screen_time_high'] = (df['screen_time'] >= 120).astype(int)
            
            behavioral_features.extend(['screen_time_low', 'screen_time_moderate', 'screen_time_high'])
        
        # App interaction features
        if 'app_interactions' in df.columns:
            df['app_interactions_per_hour'] = df['app_interactions'] / max(df['app_interactions'].max() / 60, 1)
            behavioral_features.append('app_interactions_per_hour')
        
        # Response time features
        if 'response_time' in df.columns:
            df['response_time_fast'] = (df['response_time'] < 2.0).astype(int)
            df['response_time_slow'] = (df['response_time'] > 5.0).astype(int)
            behavioral_features.extend(['response_time_fast', 'response_time_slow'])
        
        print(f"   • Added {len(behavioral_features)} behavioral features")
        return df
    
    def engineer_all_features(self, df: pd.DataFrame, 
                            timestamp_col: str = 'timestamp',
                            device_id_col: str = 'device_id') -> pd.DataFrame:
        """Apply all feature engineering steps"""
        print("\n🔧 Starting comprehensive feature engineering...")
        print("=" * 60)
        
        original_shape = df.shape
        
        # Create temporal features
        df = self.create_temporal_features(df, timestamp_col)
        
        # Identify numeric columns for rolling features
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        # Remove ID and derived columns from rolling calculations
        numeric_cols = [col for col in numeric_cols if not any(x in col.lower() 
                       for x in ['id', '_sin', '_cos', 'is_', 'bucket', 'zone', 'goal', 'category'])]
        
        # Create rolling features for key metrics
        if len(numeric_cols) > 0:
            df = self.create_rolling_features(df, numeric_cols[:5], device_id_col, timestamp_col, windows=[3, 6, 12])  # Limit to prevent explosion
        
        # Create domain-specific features
        df = self.create_mood_features(df)
        df = self.create_physiological_features(df)
        df = self.create_behavioral_features(df)
        
        final_shape = df.shape
        new_features = final_shape[1] - original_shape[1]
        
        print("\n✅ Feature engineering complete!")
        print(f"   • Original shape: {original_shape}")
        print(f"   • Final shape: {final_shape}")
        print(f"   • New features created: {new_features}")
        
        return df
    
    def get_feature_importance_summary(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """Get summary of feature categories for documentation"""
        feature_categories = {
            'temporal': [],
            'rolling_stats': [],
            'mood': [],
            'physiological': [],
            'behavioral': [],
            'original': []
        }
        
        for col in df.columns:
            if any(x in col for x in ['hour', 'day', 'weekend', 'circadian', 'sin', 'cos']):
                feature_categories['temporal'].append(col)
            elif 'rolling' in col:
                feature_categories['rolling_stats'].append(col)
            elif any(x in col for x in ['mood', 'wellness', 'confidence']):
                feature_categories['mood'].append(col)
            elif any(x in col for x in ['heart', 'hr_', 'hrv', 'steps', 'stress', 'activity']):
                feature_categories['physiological'].append(col)
            elif any(x in col for x in ['screen', 'app', 'response']):
                feature_categories['behavioral'].append(col)
            else:
                feature_categories['original'].append(col)
        
        return feature_categories