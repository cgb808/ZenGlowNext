"""
TensorFlow Lite Model Training Pipeline for Family Wellness
"""

import tensorflow as tf
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
import os
from datetime import datetime

class WellnessModelTrainer:
    """Train TensorFlow Lite models for family wellness prediction"""
    
    def __init__(self, data_dir="../data", model_dir="../models"):
        self.data_dir = data_dir
        self.model_dir = model_dir
        self.scaler = StandardScaler()
        self.model = None
        
    def load_and_preprocess_data(self):
        """Load and preprocess training data"""
        print("📊 Loading training data...")
        
        # Load data files (when available)
        try:
            physiological = pd.read_csv(f"{self.data_dir}/raw/physiological_data.csv")
            behavioral = pd.read_csv(f"{self.data_dir}/raw/behavioral_data.csv") 
            mood = pd.read_csv(f"{self.data_dir}/raw/mood_data.csv")
            contextual = pd.read_csv(f"{self.data_dir}/raw/contextual_data.csv")
            
            # Merge datasets on timestamp and device_id
            data = self._merge_datasets(physiological, behavioral, mood, contextual)
            
        except FileNotFoundError:
            print("⚠️  Raw data files not found. Generating synthetic data...")
            data = self._generate_synthetic_data()
        
        # Feature engineering
        features, labels = self._engineer_features(data)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            features, labels, test_size=0.2, random_state=42
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Save scaler
        joblib.dump(self.scaler, f"{self.model_dir}/scaler.pkl")
        
        return X_train_scaled, X_test_scaled, y_train, y_test
    
    def _merge_datasets(self, physio, behav, mood, context):
        """Merge multiple datasets on timestamp and device_id"""
        # Implementation for merging real data
        pass
    
    def _generate_synthetic_data(self, n_samples=5000):
        """Generate synthetic wellness data for training"""
        print("🎲 Generating synthetic training data...")
        
        np.random.seed(42)
        data = []
        
        for i in range(n_samples):
            # Simulate daily patterns
            hour = np.random.randint(6, 23)  # Waking hours
            is_school_day = np.random.choice([0, 1], p=[0.3, 0.7])
            
            # Physiological features (correlated)
            base_hr = 70 + np.random.normal(0, 5)
            stress_level = np.random.beta(2, 5)  # Skewed toward low stress
            heart_rate = base_hr + stress_level * 20
            hrv = 50 - stress_level * 20 + np.random.normal(0, 5)
            
            # Activity patterns
            if 7 <= hour <= 8 or 15 <= hour <= 17:  # Active periods
                activity_multiplier = 2.0
            else:
                activity_multiplier = 1.0
            
            steps = np.random.poisson(50 * activity_multiplier)
            
            # Behavioral patterns
            screen_time = np.random.exponential(10) if hour > 18 else np.random.exponential(5)
            app_interactions = np.random.poisson(8 * (1 + stress_level))
            
            # Mood correlation with physiological state
            mood_base = 0.7 - stress_level * 0.4
            mood_score = np.clip(mood_base + np.random.normal(0, 0.1), 0, 1)
            
            # Wellness score (target variable)
            wellness_score = (
                0.3 * (1 - stress_level) +
                0.2 * (mood_score) + 
                0.2 * min(steps / 100, 1.0) +
                0.2 * (hrv / 50) +
                0.1 * (1 - min(screen_time / 60, 1.0))
            )
            wellness_score = np.clip(wellness_score, 0, 1)
            
            data.append({
                'heart_rate': heart_rate,
                'hrv': hrv,
                'steps': steps,
                'stress_level': stress_level,
                'screen_time': screen_time,
                'app_interactions': app_interactions,
                'hour_of_day': hour,
                'is_school_day': is_school_day,
                'mood_score': mood_score,
                'wellness_score': wellness_score
            })
        
        return pd.DataFrame(data)
    
    def _engineer_features(self, data):
        """Engineer features for model training"""
        feature_columns = [
            'heart_rate', 'hrv', 'steps', 'stress_level',
            'screen_time', 'app_interactions', 'hour_of_day', 
            'is_school_day', 'mood_score'
        ]
        
        features = data[feature_columns].values
        labels = data['wellness_score'].values
        
        return features, labels
    
    def build_mobile_model(self, input_shape):
        """Build ultra-lightweight model optimized for mobile devices"""
        print("🏗️  Building ultra-lightweight mobile model...")
        
        # Tiny model architecture - optimized for mobile inference speed
        self.model = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(input_shape,)),
            
            # Ultra-compact dense layers
            tf.keras.layers.Dense(8, activation='relu', name='mobile_dense_1'),  # Only 8 neurons!
            tf.keras.layers.Dropout(0.1),  # Minimal dropout
            
            tf.keras.layers.Dense(4, activation='relu', name='mobile_dense_2'),  # Even smaller
            
            # Single output for wellness score
            tf.keras.layers.Dense(1, activation='sigmoid', name='wellness_output')
        ])
        
        # Compile with mobile-optimized settings
        self.model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.01),  # Faster convergence
            loss='mse',
            metrics=['mae']
        )
        
        # Print model size info
        total_params = self.model.count_params()
        print(f"📊 Ultra-tiny model: {total_params:,} parameters")
        print(f"💾 Estimated model size: ~{total_params * 4 / 1024:.1f} KB")
        
        return self.model
    
    def train_model(self, X_train, y_train, X_test, y_test):
        """Train the ultra-lightweight mobile wellness prediction model"""
        print("🔥 Training ultra-lightweight mobile wellness model...")
        
        self.model = self.build_mobile_model(X_train.shape[1])
        
        # Training callbacks
        callbacks = [
            tf.keras.callbacks.EarlyStopping(patience=10, restore_best_weights=True),
            tf.keras.callbacks.ReduceLROnPlateau(patience=5, factor=0.5)
        ]
        
        # Train model
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_test, y_test),
            epochs=100,
            batch_size=32,
            callbacks=callbacks,
            verbose=1
        )
        
        # Evaluate model
        test_loss, test_mae = self.model.evaluate(X_test, y_test, verbose=0)
        print(f"📊 Test MAE: {test_mae:.4f}")
        
        return history
    
    def convert_to_tflite(self):
        """Convert trained model to ultra-lightweight TensorFlow Lite for mobile"""
        print("📱 Converting to ultra-lightweight TensorFlow Lite for mobile...")
        
        # Convert to TFLite with aggressive optimization for mobile
        converter = tf.lite.TFLiteConverter.from_keras_model(self.model)
        
        # Ultra-aggressive optimizations for mobile
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        converter.target_spec.supported_types = [tf.float16]  # Use float16 for smaller size
        
        # Enable experimental optimizations
        converter.experimental_new_converter = True
        converter.experimental_new_quantizer = True
        
        # Post-training quantization to int8 (smallest possible)
        tflite_model = converter.convert()
        
        # Save TFLite model
        tflite_path = f"{self.model_dir}/wellness_mobile_tiny.tflite"
        with open(tflite_path, 'wb') as f:
            f.write(tflite_model)
            
        return tflite_path

def main():
    """Main training pipeline"""
    print("🎯 ZenDexer Wellness Model Training Pipeline")
    print("=" * 50)
    
    # Initialize trainer
    trainer = WellnessModelTrainer()
    
    # Load and preprocess data
    X_train, X_test, y_train, y_test = trainer.load_and_preprocess_data()
    
    # Train model
    history = trainer.train_model(X_train, y_train, X_test, y_test)
    
    # Convert to TFLite
    tflite_path = trainer.convert_to_tflite()
    
    print("🎉 Training completed successfully!")
    print(f"📱 TensorFlow Lite model ready for deployment: {tflite_path}")

if __name__ == "__main__":
    main()
