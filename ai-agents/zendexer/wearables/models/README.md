# Models Directory

## Directory Structure

### `/models/trained/`

- Trained Keras models (.h5 files)
- Training checkpoints
- Model metadata

### `/models/tflite/`

- Converted TensorFlow Lite models (.tflite)
- Quantized versions
- Different optimization levels

### `/models/artifacts/`

- Preprocessing artifacts (scalers, encoders)
- Feature engineering pipelines
- Model validation reports

## Model Versions

### v1.0 - Baseline Model

- Simple feed-forward network
- Physiological + temporal features
- Binary wellness classification

### v2.0 - Enhanced Model

- Multi-output predictions
- Behavioral features added
- Regression for wellness scores

### v3.0 - Production Model

- Optimized for wearables
- Advanced feature engineering
- Real-time inference ready

## Model Naming Convention

```
wellness_model_v{version}_{optimization}.{extension}

Examples:
- wellness_model_v1.0_baseline.h5
- wellness_model_v2.0_quantized.tflite
- wellness_model_v3.0_optimized.tflite
```

## Size Targets

- **Keras Model**: <50MB
- **TFLite (FP32)**: <10MB
- **TFLite (INT8)**: <3MB
- **Ultra-optimized**: <1MB
