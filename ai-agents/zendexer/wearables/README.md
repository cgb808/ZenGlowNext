# 🎯 ZenDexer Wearables Model

## Overview

Lightweight AI model designed for wearable devices that feeds wellness metrics to the SmolLM2 parental predictor system.

## Model Options for Wearables

### Option 1: TinyBERT (Recommended)

- **Size**: ~17MB
- **Parameters**: 14.5M
- **Use Case**: Text sentiment analysis, mood detection
- **Battery Impact**: Very low
- **Latency**: <50ms

### Option 2: MobileBERT

- **Size**: ~25MB
- **Parameters**: 25M
- **Use Case**: Better accuracy for complex text analysis
- **Battery Impact**: Low
- **Latency**: <100ms

### Option 3: DistilBERT (Quantized)

- **Size**: ~32MB (int8 quantized)
- **Parameters**: 66M
- **Use Case**: High accuracy mood/wellness analysis
- **Battery Impact**: Medium
- **Latency**: <150ms

## Metrics Collection

### Physiological Metrics

- Heart rate variability
- Step count and activity patterns
- Sleep quality indicators
- Stress level detection

### Behavioral Metrics

- App usage patterns
- Response time to notifications
- Interaction frequency
- Mood self-reports

### Environmental Context

- Location context (home/school/outdoors)
- Time of day patterns
- Social interaction indicators

## Architecture

```
[Wearable Device] → [Edge Model] → [Metrics API] → [SmolLM2 Predictor] → [Parental Dashboard]
```

## Next Steps

1. Set up local development environment
2. Test model selection
3. Implement metrics collection
4. Build API integration with SmolLM2
