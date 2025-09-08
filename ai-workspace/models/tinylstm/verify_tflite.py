#!/usr/bin/env python3
"""
TinyLSTM TensorFlow Lite Model Verification Script

This script loads a TensorFlow Lite model and runs sample inference
to verify the model is working correctly for mobile deployment.

Requirements:
- TensorFlow >= 2.10.0 (for tf.lite.Interpreter)
- NumPy

Usage:
    python verify_tflite.py [model_path]
    python verify_tflite.py mobile_lstm.tflite
"""

import os
import sys
import numpy as np
import argparse
from typing import Tuple, List

try:
    import tensorflow as tf
except ImportError:
    print("❌ TensorFlow not found. Please install: pip install tensorflow")
    sys.exit(1)


class TinyLSTMVerifier:
    """Verifier for TinyLSTM TensorFlow Lite models"""
    
    def __init__(self, model_path: str):
        """
        Initialize verifier with TFLite model
        
        Args:
            model_path (str): Path to the .tflite model file
        """
        self.model_path = model_path
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        
        self._load_model()
    
    def _load_model(self):
        """Load the TensorFlow Lite model"""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        
        try:
            # Load TFLite model
            self.interpreter = tf.lite.Interpreter(model_path=self.model_path)
            self.interpreter.allocate_tensors()
            
            # Get input and output details
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            
            print(f"✅ Model loaded successfully: {self.model_path}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load TFLite model: {str(e)}")
    
    def print_model_info(self):
        """Print detailed model information"""
        print("\n📋 Model Information:")
        print("=" * 50)
        
        # File info
        file_size = os.path.getsize(self.model_path)
        print(f"File: {os.path.basename(self.model_path)}")
        print(f"Size: {file_size / 1024:.1f} KB")
        print(f"Mobile Ready: {'✅ Yes' if file_size / 1024 < 200 else '⚠️  No (>200KB)'}")
        
        # Input details
        print(f"\n📥 Input Details:")
        for i, input_detail in enumerate(self.input_details):
            print(f"  Input {i}:")
            print(f"    Name: {input_detail['name']}")
            print(f"    Shape: {input_detail['shape']}")
            print(f"    Type: {input_detail['dtype']}")
            print(f"    Quantization: {input_detail.get('quantization', 'None')}")
        
        # Output details
        print(f"\n📤 Output Details:")
        for i, output_detail in enumerate(self.output_details):
            print(f"  Output {i}:")
            print(f"    Name: {output_detail['name']}")
            print(f"    Shape: {output_detail['shape']}")
            print(f"    Type: {output_detail['dtype']}")
            print(f"    Quantization: {output_detail.get('quantization', 'None')}")
    
    def generate_sample_input(self) -> np.ndarray:
        """
        Generate realistic sample input data for testing
        
        Returns:
            np.ndarray: Sample input matching the model's expected format
        """
        input_shape = self.input_details[0]['shape']
        batch_size, sequence_length, feature_count = input_shape
        
        print(f"\n🎲 Generating sample input: {input_shape}")
        
        # Generate realistic physiological/behavioral data
        # Features: [heart_rate_normalized, movement_level, stress_indicator, sleep_quality]
        sample_data = []
        
        # Simulate a day's worth of data with realistic patterns
        for t in range(sequence_length):
            # Time-based patterns (e.g., heart rate variations throughout day)
            time_factor = t / sequence_length
            
            # Heart rate (normalized): higher during day, lower at night
            heart_rate = 0.6 + 0.2 * np.sin(time_factor * 2 * np.pi) + np.random.normal(0, 0.05)
            heart_rate = np.clip(heart_rate, 0, 1)
            
            # Movement level: active during day, low at night
            movement = 0.4 + 0.3 * np.sin(time_factor * 2 * np.pi) + np.random.normal(0, 0.1)
            movement = np.clip(movement, 0, 1)
            
            # Stress indicator: varies throughout day
            stress = 0.3 + 0.2 * np.random.random() + np.random.normal(0, 0.05)
            stress = np.clip(stress, 0, 1)
            
            # Sleep quality: consistent but with some noise
            sleep_quality = 0.7 + np.random.normal(0, 0.1)
            sleep_quality = np.clip(sleep_quality, 0, 1)
            
            sample_data.append([heart_rate, movement, stress, sleep_quality])
        
        # Reshape to match expected input format
        input_data = np.array(sample_data, dtype=np.float32).reshape(input_shape)
        
        print("📊 Sample input statistics:")
        feature_names = ["Heart Rate", "Movement", "Stress", "Sleep Quality"]
        for i, name in enumerate(feature_names):
            values = input_data[0, :, i]
            print(f"  {name}: mean={values.mean():.3f}, std={values.std():.3f}, range=[{values.min():.3f}, {values.max():.3f}]")
        
        return input_data
    
    def run_inference(self, input_data: np.ndarray) -> np.ndarray:
        """
        Run inference on the model
        
        Args:
            input_data (np.ndarray): Input data for inference
            
        Returns:
            np.ndarray: Model predictions
        """
        # Set input tensor
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        
        # Run inference
        self.interpreter.invoke()
        
        # Get output tensor
        output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
        
        return output_data
    
    def interpret_predictions(self, predictions: np.ndarray):
        """
        Interpret and display model predictions
        
        Args:
            predictions (np.ndarray): Raw model predictions
        """
        print("\n🔮 Prediction Results:")
        print("=" * 30)
        
        # Assuming 2 outputs: [wellness_trend, alert_level]
        if predictions.shape[-1] >= 2:
            wellness_trend = predictions[0, 0]
            alert_level = predictions[0, 1]
            
            print(f"🌟 Wellness Trend: {wellness_trend:.3f}")
            print(f"   Interpretation: {'😊 Good' if wellness_trend > 0.6 else '😐 Moderate' if wellness_trend > 0.3 else '😟 Concerning'}")
            
            print(f"🚨 Alert Level: {alert_level:.3f}")
            print(f"   Interpretation: {'🔴 High Alert' if alert_level > 0.7 else '🟡 Medium Alert' if alert_level > 0.4 else '🟢 Low Alert'}")
            
            # Overall assessment
            if wellness_trend > 0.6 and alert_level < 0.4:
                overall = "😊 Good overall wellness"
            elif wellness_trend < 0.4 or alert_level > 0.7:
                overall = "😟 Wellness concerns detected"
            else:
                overall = "😐 Moderate wellness status"
            
            print(f"\n📊 Overall Assessment: {overall}")
        else:
            print(f"Raw predictions: {predictions}")
    
    def run_verification(self, num_tests: int = 3):
        """
        Run complete verification with multiple test cases
        
        Args:
            num_tests (int): Number of test cases to run
        """
        print(f"\n🧪 Running {num_tests} verification tests...")
        
        for test_num in range(num_tests):
            print(f"\n--- Test Case {test_num + 1} ---")
            
            # Generate sample input
            input_data = self.generate_sample_input()
            
            # Run inference
            try:
                predictions = self.run_inference(input_data)
                print(f"✅ Inference successful")
                print(f"📐 Output shape: {predictions.shape}")
                print(f"📊 Output values: {predictions.flatten()}")
                
                # Interpret results
                self.interpret_predictions(predictions)
                
            except Exception as e:
                print(f"❌ Inference failed: {str(e)}")
                return False
        
        return True
    
    def benchmark_performance(self, num_iterations: int = 100):
        """
        Benchmark inference performance
        
        Args:
            num_iterations (int): Number of inference iterations
        """
        print(f"\n⚡ Performance Benchmark ({num_iterations} iterations)...")
        
        # Generate test input
        input_data = self.generate_sample_input()
        
        # Warm up
        for _ in range(5):
            self.run_inference(input_data)
        
        # Benchmark
        import time
        start_time = time.time()
        
        for _ in range(num_iterations):
            self.run_inference(input_data)
        
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time = (total_time / num_iterations) * 1000  # Convert to milliseconds
        
        print(f"📊 Performance Results:")
        print(f"  Total time: {total_time:.3f} seconds")
        print(f"  Average inference time: {avg_time:.2f} ms")
        print(f"  Inferences per second: {num_iterations / total_time:.1f}")
        
        # Mobile performance assessment
        if avg_time < 10:
            perf_assessment = "🚀 Excellent for mobile"
        elif avg_time < 50:
            perf_assessment = "✅ Good for mobile"
        elif avg_time < 100:
            perf_assessment = "⚠️  Acceptable for mobile"
        else:
            perf_assessment = "❌ Too slow for mobile"
        
        print(f"  Mobile suitability: {perf_assessment}")


def main():
    """Main verification pipeline"""
    parser = argparse.ArgumentParser(description='Verify TinyLSTM TensorFlow Lite model')
    parser.add_argument('model_path', nargs='?', default='mobile_lstm.tflite',
                       help='Path to the .tflite model file (default: mobile_lstm.tflite)')
    parser.add_argument('--num-tests', type=int, default=3,
                       help='Number of test cases to run (default: 3)')
    parser.add_argument('--benchmark', action='store_true',
                       help='Run performance benchmark')
    parser.add_argument('--benchmark-iterations', type=int, default=100,
                       help='Number of benchmark iterations (default: 100)')
    
    args = parser.parse_args()
    
    print("🔍 TinyLSTM TensorFlow Lite Verification")
    print("=" * 45)
    
    try:
        # Initialize verifier
        verifier = TinyLSTMVerifier(args.model_path)
        
        # Print model information
        verifier.print_model_info()
        
        # Run verification tests
        success = verifier.run_verification(args.num_tests)
        
        if not success:
            print("❌ Verification failed!")
            sys.exit(1)
        
        # Run benchmark if requested
        if args.benchmark:
            verifier.benchmark_performance(args.benchmark_iterations)
        
        print("\n🎉 Model verification completed successfully!")
        print("✅ Model is ready for mobile deployment")
        
    except Exception as e:
        print(f"❌ Verification failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()