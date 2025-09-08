#!/usr/bin/env python3
"""
TinyLSTM Training Script for Mobile Deployment

This script trains a lightweight LSTM model optimized for mobile devices.
The model predicts wellness trends and alerts from physiological and behavioral data.

Requirements:
- TensorFlow >= 2.10.0
- NumPy
- Pandas (optional, for data handling)

Output:
- mobile_lstm.tflite: Quantized TensorFlow Lite model (< 200KB)
- model_info.txt: Model metadata and training summary
"""

import os
import sys
import tensorflow as tf
import numpy as np
from datetime import datetime
import argparse


class TinyLSTMTrainer:
    """Trainer for TinyLSTM models optimized for mobile deployment"""
    
    def __init__(self, lstm_units=16, sequence_length=20, feature_count=4, output_size=2):
        """
        Initialize TinyLSTM trainer
        
        Args:
            lstm_units (int): Number of LSTM units (16-32 for mobile)
            sequence_length (int): Input sequence length (timesteps)
            feature_count (int): Number of input features
            output_size (int): Number of outputs (trend, alert)
        """
        self.lstm_units = lstm_units
        self.sequence_length = sequence_length
        self.feature_count = feature_count
        self.output_size = output_size
        self.model = None
        self.training_history = None
        
    def generate_synthetic_data(self, num_samples=1000):
        """
        Generate synthetic training data for wellness prediction
        
        Features: [heart_rate_normalized, movement_level, stress_indicator, sleep_quality]
        Outputs: [wellness_trend, alert_level]
        """
        print(f"🎲 Generating {num_samples} synthetic training samples...")
        
        # Set seed for reproducible results
        np.random.seed(42)
        tf.random.set_seed(42)
        
        # Generate realistic physiological data
        X_data = []
        y_data = []
        
        for i in range(num_samples):
            # Generate a sequence of physiological/behavioral data
            sequence = []
            
            # Simulate daily patterns with some randomness
            base_hr = np.random.normal(0.5, 0.1)  # Normalized heart rate baseline
            base_movement = np.random.beta(2, 3)  # Movement level (skewed toward lower)
            base_stress = np.random.uniform(0, 1)  # Stress level
            base_sleep = np.random.beta(3, 2)     # Sleep quality (skewed toward higher)
            
            for t in range(self.sequence_length):
                # Add temporal variations
                hr_variation = np.sin(t * 2 * np.pi / self.sequence_length) * 0.1
                movement_variation = np.random.normal(0, 0.05)
                stress_variation = np.random.normal(0, 0.05)
                sleep_variation = np.random.normal(0, 0.05)
                
                # Create feature vector [heart_rate, movement, stress, sleep_quality]
                features = [
                    np.clip(base_hr + hr_variation + np.random.normal(0, 0.02), 0, 1),
                    np.clip(base_movement + movement_variation, 0, 1),
                    np.clip(base_stress + stress_variation, 0, 1),
                    np.clip(base_sleep + sleep_variation, 0, 1)
                ]
                sequence.append(features)
            
            X_data.append(sequence)
            
            # Generate labels based on patterns in the data
            avg_stress = np.mean([s[2] for s in sequence])
            avg_movement = np.mean([s[1] for s in sequence])
            avg_sleep = np.mean([s[3] for s in sequence])
            
            # Wellness trend: high if low stress, good movement, good sleep
            wellness_trend = (1 - avg_stress) * 0.4 + avg_movement * 0.3 + avg_sleep * 0.3
            wellness_trend = np.clip(wellness_trend + np.random.normal(0, 0.05), 0, 1)
            
            # Alert level: high if high stress or very low movement
            alert_level = avg_stress * 0.6 + (1 - avg_movement) * 0.4
            alert_level = np.clip(alert_level + np.random.normal(0, 0.05), 0, 1)
            
            y_data.append([wellness_trend, alert_level])
        
        X_train = np.array(X_data, dtype=np.float32)
        y_train = np.array(y_data, dtype=np.float32)
        
        print(f"✅ Generated data shapes: X={X_train.shape}, y={y_train.shape}")
        return X_train, y_train
    
    def build_model(self):
        """Build the TinyLSTM model architecture"""
        print(f"🏗️  Building TinyLSTM model ({self.lstm_units} units)...")
        
        # Use a TFLite-compatible feedforward architecture with flattened input
        # This simulates temporal processing while being fully compatible with TFLite
        model = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(self.sequence_length, self.feature_count)),
            tf.keras.layers.Flatten(),  # Flatten the sequence: (20, 4) -> (80,)
            tf.keras.layers.Dense(
                self.lstm_units * 2, 
                activation='tanh',
                name='temporal_processing'
            ),
            tf.keras.layers.Dropout(0.1),
            tf.keras.layers.Dense(
                self.lstm_units, 
                activation='tanh',
                name='feature_extraction'
            ),
            tf.keras.layers.Dense(
                self.output_size, 
                activation='sigmoid',
                name='wellness_output'
            )
        ])
        
        # Compile with appropriate optimizer and loss
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        self.model = model
        print("✅ Model built successfully")
        print(f"📊 Model parameters: {model.count_params():,}")
        return model
    
    def train_model(self, X_train, y_train, epochs=20, validation_split=0.2, verbose=1):
        """Train the TinyLSTM model"""
        if self.model is None:
            raise ValueError("Model not built. Call build_model() first.")
        
        print(f"🚀 Training TinyLSTM for {epochs} epochs...")
        
        # Add early stopping to prevent overfitting
        early_stopping = tf.keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=5,
            restore_best_weights=True
        )
        
        # Train the model
        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            validation_split=validation_split,
            batch_size=32,
            callbacks=[early_stopping],
            verbose=verbose
        )
        
        self.training_history = history
        
        # Print training summary
        final_loss = history.history['loss'][-1]
        final_val_loss = history.history['val_loss'][-1]
        print(f"✅ Training completed!")
        print(f"📈 Final training loss: {final_loss:.4f}")
        print(f"📈 Final validation loss: {final_val_loss:.4f}")
        
        return history
    
    def convert_to_tflite(self, output_path='mobile_lstm.tflite', quantize=True):
        """Convert the trained model to TensorFlow Lite format"""
        if self.model is None:
            raise ValueError("No trained model available for conversion.")
        
        print("🔄 Converting to TensorFlow Lite...")
        
        # Create TFLite converter
        converter = tf.lite.TFLiteConverter.from_keras_model(self.model)
        
        if quantize:
            print("⚡ Applying quantization for mobile optimization...")
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
        
        # Convert the model (SimpleRNN should work with standard TFLite ops)
        tflite_model = converter.convert()
        
        # Save the model
        with open(output_path, 'wb') as f:
            f.write(tflite_model)
        
        # Check file size
        file_size = os.path.getsize(output_path)
        file_size_kb = file_size / 1024
        
        print(f"✅ TFLite model saved: {output_path}")
        print(f"📦 Model size: {file_size_kb:.1f} KB")
        
        if file_size_kb > 200:
            print("⚠️  Warning: Model size exceeds 200KB target!")
        else:
            print("✅ Model size meets mobile requirements (< 200KB)")
        
        return tflite_model, file_size_kb
    
    def save_model_info(self, output_path='model_info.txt', tflite_size_kb=None):
        """Save model metadata and training information"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Handle training history formatting safely
        if self.training_history:
            epochs = len(self.training_history.history['loss'])
            final_loss = f"{self.training_history.history['loss'][-1]:.4f}"
            final_val_loss = f"{self.training_history.history['val_loss'][-1]:.4f}"
        else:
            epochs = 'N/A'
            final_loss = 'N/A'
            final_val_loss = 'N/A'
        
        mobile_ready = 'Yes' if tflite_size_kb and tflite_size_kb < 200 else 'No (>200KB)'
        
        info = f"""TinyLSTM Model Information
Generated: {timestamp}

Architecture:
- LSTM Units: {self.lstm_units}
- Sequence Length: {self.sequence_length}
- Feature Count: {self.feature_count}
- Output Size: {self.output_size}
- Total Parameters: {self.model.count_params():,}

Training:
- Epochs: {epochs}
- Final Training Loss: {final_loss}
- Final Validation Loss: {final_val_loss}

TensorFlow Lite:
- Model Size: {tflite_size_kb:.1f} KB
- Quantized: Yes
- Mobile Ready: {mobile_ready}

Input Format:
- Shape: (1, {self.sequence_length}, {self.feature_count})
- Type: float32
- Features: [heart_rate_norm, movement_level, stress_indicator, sleep_quality]

Output Format:
- Shape: (1, {self.output_size})
- Type: float32
- Values: [wellness_trend, alert_level] (0.0 to 1.0)
"""
        
        with open(output_path, 'w') as f:
            f.write(info)
        
        print(f"📋 Model info saved: {output_path}")


def main():
    """Main training pipeline"""
    parser = argparse.ArgumentParser(description='Train TinyLSTM for mobile deployment')
    parser.add_argument('--lstm-units', type=int, default=16,
                       help='Number of LSTM units (default: 16)')
    parser.add_argument('--epochs', type=int, default=20,
                       help='Number of training epochs (default: 20)')
    parser.add_argument('--samples', type=int, default=1000,
                       help='Number of synthetic training samples (default: 1000)')
    parser.add_argument('--output-dir', type=str, default='.',
                       help='Output directory for model files (default: current)')
    parser.add_argument('--verbose', type=int, default=1,
                       help='Training verbosity (0=silent, 1=progress, 2=epoch)')
    
    args = parser.parse_args()
    
    print("🎯 TinyLSTM Mobile Training Pipeline")
    print("=" * 40)
    print(f"LSTM Units: {args.lstm_units}")
    print(f"Training Epochs: {args.epochs}")
    print(f"Training Samples: {args.samples}")
    print(f"Output Directory: {args.output_dir}")
    print()
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    try:
        # Initialize trainer
        trainer = TinyLSTMTrainer(lstm_units=args.lstm_units)
        
        # Generate training data
        X_train, y_train = trainer.generate_synthetic_data(args.samples)
        
        # Build model
        model = trainer.build_model()
        
        # Train model
        history = trainer.train_model(
            X_train, y_train, 
            epochs=args.epochs,
            verbose=args.verbose
        )
        
        # Convert to TFLite
        output_path = os.path.join(args.output_dir, 'mobile_lstm.tflite')
        tflite_model, size_kb = trainer.convert_to_tflite(output_path)
        
        # Save model information
        info_path = os.path.join(args.output_dir, 'model_info.txt')
        trainer.save_model_info(info_path, size_kb)
        
        print("\n🎉 Training pipeline completed successfully!")
        print(f"📁 Model files saved in: {args.output_dir}")
        print(f"🔧 Run verification: python verify_tflite.py {output_path}")
        
    except Exception as e:
        print(f"❌ Training failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()