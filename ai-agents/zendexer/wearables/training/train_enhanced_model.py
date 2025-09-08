#!/usr/bin/env python3
"""
ZenGlow Enhanced Mobile Model Training
Train ultra-lightweight model with unified wellness dataset
"""

import pandas as pd
import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import os
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class EnhancedWellnessTrainer:
    """Enhanced trainer for unified wellness datasets"""
    
    def __init__(self, model_dir="../models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        self.model = None
        self.scaler = StandardScaler()
        
        print("🎯 ZenGlow Enhanced Mobile Wellness Trainer")
        print("=" * 50)
    
    def load_unified_dataset(self):
        """Load the unified wellness dataset"""
        print("📊 Loading unified wellness dataset...")
        
        # Try multiple data sources
        data_paths = [
            "../data/processed/unified_wellness_dataset.csv",
            "../data/processed/mobile_training_data.csv",
            "./processed/unified_wellness_dataset.csv"
        ]
        
        for path in data_paths:
            full_path = Path(path)
            if full_path.exists():
                print(f"   • Found dataset: {full_path}")
                data = pd.read_csv(full_path)
                print(f"   • Records: {len(data)}")
                print(f"   • Columns: {list(data.columns)}")
                return data
        
        print("   ⚠️  No unified dataset found, generating synthetic data...")
        return self.generate_enhanced_synthetic_data()
    
    def generate_enhanced_synthetic_data(self):
        """Generate enhanced synthetic wellness data"""
        print("🎲 Generating enhanced synthetic wellness data...")
        
        np.random.seed(42)
        n_samples = 2000
        
        # Demographics
        ages = np.random.randint(18, 65, n_samples)
        genders = np.random.choice([0, 1], n_samples)  # 0=female, 1=male
        heights = np.where(genders == 1, 
                          np.random.normal(175, 8, n_samples),  # Male heights
                          np.random.normal(165, 7, n_samples))  # Female heights
        weights = np.where(genders == 1,
                          np.random.normal(75, 12, n_samples),  # Male weights
                          np.random.normal(62, 10, n_samples))  # Female weights
        bmis = weights / (heights/100)**2
        
        # Activity patterns
        movement_levels = np.random.beta(2, 3, n_samples)  # Skewed toward lower activity
        heart_rates = np.random.normal(72, 12, n_samples)
        hr_variability = np.random.exponential(8, n_samples)
        
        # Stress modeling based on multiple factors
        stress_base = 0.3  # Base stress level
        
        # Age factor (higher stress in middle age)
        age_stress = 0.2 * np.sin((ages - 25) / 20 * np.pi)
        
        # Activity factor (lower activity = higher stress)
        activity_stress = 0.3 * (1 - movement_levels)
        
        # Heart rate variability factor (higher HRV = lower stress)
        hrv_stress = 0.2 * np.exp(-hr_variability / 10)
        
        # BMI factor (extreme BMIs = higher stress)
        bmi_stress = 0.1 * np.abs(bmis - 22) / 5
        
        # Combine stress factors
        stress_levels = np.clip(
            stress_base + age_stress + activity_stress + hrv_stress + bmi_stress,
            0, 1
        )
        
        # Wellness score (inverse relationship with stress)
        wellness_scores = 1.0 - stress_levels + np.random.normal(0, 0.05, n_samples)
        wellness_scores = np.clip(wellness_scores, 0, 1)
        
        # Session types
        session_types = np.random.choice([
            'morning_routine', 'work_break', 'evening_wind_down', 
            'exercise_recovery', 'stress_relief', 'sleep_prep'
        ], n_samples)
        
        data = pd.DataFrame({
            'subject_id': [f'synth_{i}' for i in range(n_samples)],
            'age': ages,
            'gender': genders,
            'weight': weights,
            'height': heights,
            'bmi': bmis,
            'session_type': session_types,
            'movement_level': movement_levels,
            'heart_rate_avg': heart_rates,
            'heart_rate_variability': hr_variability,
            'stress_level': stress_levels,
            'wellness_score': wellness_scores,
            'data_source': 'enhanced_synthetic'
        })
        
        print(f"   • Generated {len(data)} synthetic samples")
        print(f"   • Wellness score range: {wellness_scores.min():.3f} - {wellness_scores.max():.3f}")
        
        return data
    
    def prepare_training_data(self, data):
        """Prepare data for mobile model training"""
        print("🔧 Preparing training data...")
        
        # Feature selection for mobile model
        feature_columns = [
            'age', 'gender', 'bmi', 'movement_level',
            'heart_rate_avg', 'heart_rate_variability', 'stress_level'
        ]
        
        target_column = 'wellness_score'
        
        # Extract features and target
        X = data[feature_columns].copy()
        y = data[target_column].copy()
        
        # Handle missing values
        X = X.fillna(X.mean())
        y = y.fillna(y.mean())
        
        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=None
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        print(f"   • Training samples: {X_train_scaled.shape[0]}")
        print(f"   • Test samples: {X_test_scaled.shape[0]}")
        print(f"   • Features: {X_train_scaled.shape[1]}")
        print(f"   • Target range: {y.min():.3f} - {y.max():.3f}")
        
        return X_train_scaled, X_test_scaled, y_train.values, y_test.values
    
    def build_ultra_mobile_model(self, input_shape):
        """Build ultra-lightweight model for mobile deployment"""
        print("🏗️  Building ultra-lightweight mobile model...")
        
        model = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(input_shape,)),
            
            # Ultra-compact architecture
            tf.keras.layers.Dense(8, activation='relu', name='dense_1'),
            tf.keras.layers.Dropout(0.1),
            
            tf.keras.layers.Dense(4, activation='relu', name='dense_2'),
            tf.keras.layers.Dropout(0.1),
            
            tf.keras.layers.Dense(1, activation='sigmoid', name='output')
        ])
        
        # Compile with optimized settings for mobile
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.01),
            loss='mse',
            metrics=['mae']
        )
        
        # Count parameters
        total_params = model.count_params()
        model_size_kb = (total_params * 4) / 1024  # Approximate size in KB
        
        print(f"📊 Ultra-mobile model: {total_params} parameters")
        print(f"💾 Estimated model size: ~{model_size_kb:.1f} KB")
        
        return model
    
    def train_enhanced_model(self, X_train, X_test, y_train, y_test):
        """Train the enhanced mobile wellness model"""
        print("🔥 Training enhanced mobile wellness model...")
        
        self.model = self.build_ultra_mobile_model(X_train.shape[1])
        
        # Enhanced training callbacks
        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor='val_loss', patience=10, restore_best_weights=True
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss', factor=0.5, patience=5, min_lr=0.0001
            ),
            tf.keras.callbacks.ModelCheckpoint(
                f"{self.model_dir}/best_mobile_model.keras",
                monitor='val_loss', save_best_only=True
            )
        ]
        
        # Train the model
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_test, y_test),
            epochs=100,
            batch_size=32,
            callbacks=callbacks,
            verbose=1
        )
        
        # Evaluate
        test_loss, test_mae = self.model.evaluate(X_test, y_test, verbose=0)
        print(f"📊 Test MAE: {test_mae:.4f}")
        print(f"📊 Test RMSE: {np.sqrt(test_loss):.4f}")
        
        return history
    
    def convert_to_ultra_tflite(self):
        """Convert to ultra-optimized TensorFlow Lite"""
        print("📱 Converting to ultra-optimized TensorFlow Lite...")
        
        # Convert with maximum optimization
        converter = tf.lite.TFLiteConverter.from_keras_model(self.model)
        
        # Maximum optimization for mobile
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        converter.target_spec.supported_types = [tf.float16]
        
        # Post-training quantization
        converter.representative_dataset = self.representative_dataset_gen
        converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
        converter.inference_input_type = tf.uint8
        converter.inference_output_type = tf.uint8
        
        tflite_model = converter.convert()
        
        # Save ultra-optimized model
        tflite_path = f"{self.model_dir}/wellness_ultra_mobile.tflite"
        with open(tflite_path, 'wb') as f:
            f.write(tflite_model)
        
        # Check final size
        file_size_kb = len(tflite_model) / 1024
        print(f"📱 Final TFLite size: {file_size_kb:.1f} KB")
        
        return tflite_path
    
    def representative_dataset_gen(self):
        """Generate representative dataset for quantization"""
        # Use a sample of training data for quantization
        for i in range(100):
            yield [np.random.random((1, 7)).astype(np.float32)]
    
    def validate_mobile_model(self, X_test, y_test, tflite_path):
        """Validate the mobile TensorFlow Lite model"""
        print("🔍 Validating mobile model...")
        
        # Load TFLite model
        interpreter = tf.lite.Interpreter(model_path=tflite_path)
        interpreter.allocate_tensors()
        
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        
        predictions = []
        for i in range(len(X_test)):
            # Set input
            input_data = X_test[i:i+1].astype(np.float32)
            interpreter.set_tensor(input_details[0]['index'], input_data)
            
            # Run inference
            interpreter.invoke()
            
            # Get output
            output_data = interpreter.get_tensor(output_details[0]['index'])
            predictions.append(output_data[0][0])
        
        # Calculate metrics
        mae = mean_absolute_error(y_test, predictions)
        rmse = np.sqrt(mean_squared_error(y_test, predictions))
        
        print(f"📊 Mobile model validation:")
        print(f"   • MAE: {mae:.4f}")
        print(f"   • RMSE: {rmse:.4f}")
        print(f"   • Model size: {os.path.getsize(tflite_path) / 1024:.1f} KB")
        
        return predictions
    
    def run_enhanced_training(self):
        """Run the complete enhanced training pipeline"""
        print("\n🚀 Starting enhanced training pipeline...")
        
        # Load unified dataset
        data = self.load_unified_dataset()
        
        # Prepare training data
        X_train, X_test, y_train, y_test = self.prepare_training_data(data)
        
        # Train model
        history = self.train_enhanced_model(X_train, X_test, y_train, y_test)
        
        # Convert to TensorFlow Lite
        try:
            tflite_path = self.convert_to_ultra_tflite()
            
            # Validate mobile model
            predictions = self.validate_mobile_model(X_test, y_test, tflite_path)
            
            print(f"\n🎉 Enhanced training completed successfully!")
            print(f"📱 Ultra-mobile model ready: {tflite_path}")
            
        except Exception as e:
            print(f"⚠️  TensorFlow Lite conversion failed: {e}")
            print("💾 Saving Keras model instead...")
            keras_path = f"{self.model_dir}/wellness_enhanced_mobile.keras"
            self.model.save(keras_path)
            print(f"📱 Keras model saved: {keras_path}")
        
        return self.model

def main():
    """Main enhanced training pipeline"""
    trainer = EnhancedWellnessTrainer()
    model = trainer.run_enhanced_training()

if __name__ == "__main__":
    main()
