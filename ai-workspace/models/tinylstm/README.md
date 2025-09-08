# TinyLSTM Mobile Training & Verification

This directory contains standalone scripts for training and verifying TinyLSTM models optimized for mobile deployment. The models are designed to predict wellness trends and alerts from physiological and behavioral data on mobile devices.

## 🎯 Quick Start

```bash
# 1. Install dependencies
pip install tensorflow>=2.10.0 numpy

# 2. Train the model
python train_tinylstm.py

# 3. Verify the model
python verify_tflite.py mobile_lstm.tflite
```

## 📁 Files

- **`train_tinylstm.py`** - Main training script that generates synthetic data, trains the model, and exports quantized TFLite
- **`verify_tflite.py`** - Verification script that loads the TFLite model and runs sample inference
- **`README.md`** - This documentation file

## 🛠️ Prerequisites

### Python Environment
- **Python 3.8+** (recommended: 3.9 or 3.10)
- **TensorFlow 2.10.0+** for training and TFLite conversion
- **NumPy** for data handling

### Installation Options

#### Option 1: Minimal Installation
```bash
pip install tensorflow>=2.10.0 numpy
```

#### Option 2: Full AI Workspace (Recommended)
```bash
cd ai-workspace
pip install -r requirements.txt
```

#### Option 3: Virtual Environment
```bash
python3 -m venv tflite_env
source tflite_env/bin/activate  # On Windows: tflite_env\Scripts\activate
pip install tensorflow>=2.10.0 numpy
```

## 🚀 Training the Model

### Basic Usage
```bash
python train_tinylstm.py
```

### Advanced Options
```bash
python train_tinylstm.py \
    --lstm-units 32 \
    --epochs 30 \
    --samples 2000 \
    --output-dir ./models \
    --verbose 1
```

### Parameters
- `--lstm-units`: Number of LSTM units (default: 16, range: 8-64)
- `--epochs`: Training epochs (default: 20)
- `--samples`: Synthetic training samples (default: 1000)
- `--output-dir`: Output directory (default: current directory)
- `--verbose`: Training verbosity (0=silent, 1=progress, 2=epoch details)

### Output Files
- **`mobile_lstm.tflite`** - Quantized TensorFlow Lite model (< 200KB)
- **`model_info.txt`** - Model metadata and training summary

## 🔍 Verifying the Model

### Basic Usage
```bash
python verify_tflite.py mobile_lstm.tflite
```

### Advanced Options
```bash
python verify_tflite.py mobile_lstm.tflite \
    --num-tests 5 \
    --benchmark \
    --benchmark-iterations 200
```

### Parameters
- `model_path`: Path to .tflite file (default: mobile_lstm.tflite)
- `--num-tests`: Number of test cases (default: 3)
- `--benchmark`: Run performance benchmark
- `--benchmark-iterations`: Benchmark iterations (default: 100)

### Verification Output
The script will display:
- 📋 Model information (size, input/output shapes)
- 🧪 Test case results with sample predictions
- 📊 Performance metrics (inference time, mobile suitability)

## 📊 Model Architecture

### Input Format
- **Shape**: `(1, 20, 4)` - Batch of 1, 20 timesteps, 4 features
- **Type**: `float32`
- **Features**: 
  1. Heart rate (normalized 0-1)
  2. Movement level (0-1)
  3. Stress indicator (0-1)
  4. Sleep quality (0-1)

### Output Format
- **Shape**: `(1, 2)` - Batch of 1, 2 predictions
- **Type**: `float32`
- **Values**:
  1. Wellness trend (0-1, higher = better)
  2. Alert level (0-1, higher = more concerning)

### Model Size
- **Target**: < 200KB for mobile deployment
- **Typical**: 50-150KB with quantization
- **Parameters**: ~5,000-15,000 (depending on LSTM units)

## 🎲 Synthetic Data Generation

The training script generates realistic synthetic wellness data that simulates:
- **Daily patterns**: Heart rate and activity variations throughout the day
- **Individual differences**: Baseline variations between simulated users
- **Temporal correlations**: Realistic time-series patterns
- **Noise**: Natural measurement variations

### Data Features
```python
# Example sequence for one timestep
features = [
    0.65,  # Heart rate (normalized)
    0.45,  # Movement level
    0.30,  # Stress indicator
    0.75   # Sleep quality
]
```

### Labels Generation
Labels are derived from feature patterns:
- **Wellness trend**: Combination of low stress, good movement, good sleep
- **Alert level**: Based on high stress or very low movement

## 🏥 Integration with Real Data

To use your own data instead of synthetic data:

1. **Prepare your data** in the expected format:
   ```python
   X_real = np.array(your_sequences)  # Shape: (samples, 20, 4)
   y_real = np.array(your_labels)     # Shape: (samples, 2)
   ```

2. **Modify the training script**:
   ```python
   # Replace the synthetic data generation with:
   X_train, y_train = load_your_data()
   ```

3. **Feature preprocessing** (normalize all features to 0-1 range):
   ```python
   from sklearn.preprocessing import MinMaxScaler
   scaler = MinMaxScaler()
   X_normalized = scaler.fit_transform(X_reshaped)
   ```

## 📱 Mobile Deployment

### Android Integration
1. Copy `mobile_lstm.tflite` to `app/src/main/assets/`
2. Add TensorFlow Lite dependency to `build.gradle`:
   ```gradle
   implementation 'org.tensorflow:tensorflow-lite:2.8.0'
   ```
3. Use the model in your app (see main documentation for Kotlin examples)

### iOS Integration
1. Add `mobile_lstm.tflite` to your Xcode project
2. Add TensorFlow Lite dependency via CocoaPods:
   ```ruby
   pod 'TensorFlowLiteSwift'
   ```
3. Load and run the model in Swift

## 🚨 Troubleshooting

### Common Issues

#### 1. TensorFlow Import Error
```bash
# Error: No module named 'tensorflow'
pip install tensorflow>=2.10.0

# For Apple Silicon Macs:
pip install tensorflow-macos tensorflow-metal
```

#### 2. Model Size Too Large
```bash
# Try reducing LSTM units
python train_tinylstm.py --lstm-units 8

# Or reduce training samples
python train_tinylstm.py --samples 500
```

#### 3. Memory Issues During Training
```bash
# Reduce batch size or samples
python train_tinylstm.py --samples 500
```

#### 4. Verification Fails
```bash
# Check model path
ls -la *.tflite

# Verify TensorFlow installation
python -c "import tensorflow as tf; print(tf.__version__)"
```

### Performance Optimization

#### For Smaller Models
- Reduce `--lstm-units` (8-16 for ultra-light)
- Use fewer training samples for faster iteration
- Implement progressive training (start small, grow as needed)

#### For Better Accuracy
- Increase `--lstm-units` (24-32, but watch size)
- Use more training samples
- Add regularization (modify script to add dropout)

## 📚 Additional Resources

### Documentation
- [Main TinyLSTM Documentation](../../../Docs/TINYLSTM_TRAINING_AND_MOBILE_INTEGRATION.md)
- [TensorFlow Lite Guide](https://www.tensorflow.org/lite)
- [Model Optimization](https://www.tensorflow.org/model_optimization)

### Related Scripts
- `ai-agents/zendexer/wearables/training/` - Full training pipeline
- `ai-workspace/` - General AI workspace setup

### Example Commands

```bash
# Quick test run (fast training)
python train_tinylstm.py --epochs 5 --samples 200

# Production training (better accuracy)
python train_tinylstm.py --lstm-units 24 --epochs 50 --samples 5000

# Ultra-light model (< 50KB)
python train_tinylstm.py --lstm-units 8 --samples 500

# Verification with benchmark
python verify_tflite.py --benchmark --num-tests 10
```

## 📝 License & Contributing

This code is part of the ZenGlow project. See the main repository for license and contribution guidelines.

---

**Need Help?** Check the troubleshooting section above or refer to the main project documentation.