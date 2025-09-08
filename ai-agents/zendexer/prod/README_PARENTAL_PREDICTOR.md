# 👨‍👩‍👧‍👦 ZenDexer Parental Prediction Model - Production Documentation

## 🎯 Overview

The **Parental Predictor** is a specialized Phi-2 based AI model designed for family wellness monitoring and parental dashboard functionality in the ZenGlow ecosystem. It operates in production mode with enhanced privacy, security, and child-focused analytics.

## 🏗️ Architecture

### Service Configuration

- **Service Name**: `smollm-predictor` (historical naming)
- **Port**: `8002`
- **Model**: Microsoft Phi-2 (2.7B parameters)
- **Image**: `zendexer/phi2-predictor:latest`
- **Network**: Dual-network (public AI network + secure encrypted network)

### Resource Allocation

```yaml
Resources:
  Limits:
    - CPUs: 2.0 cores
    - Memory: 3GB
  Reservations:
    - CPUs: 1.0 core
    - Memory: 1.5GB
  Replicas: 2 (High Availability)
```

## 🔐 Security & Privacy

### Deployment Constraints

- **Secure Nodes Only**: `node.labels.secure==true`
- **Encrypted Network**: `secure-local-network` with overlay encryption
- **Privacy Mode**: `PRIVACY_MODE=local_only`
- **Data Retention**: Local processing, no external data transmission

### Network Security

```yaml
Networks:
  - ai-network: Standard overlay for inter-service communication
  - secure-local-network: Encrypted overlay for sensitive data
```

## 👨‍👩‍👧‍👦 Parental Dashboard Features

### Core Capabilities

- **Child Wellness Tracking**: Real-time monitoring of child health metrics
- **Parental Insights**: Predictive analytics for family wellness patterns
- **Safety Alerts**: Proactive notifications for concerning patterns
- **Privacy Protection**: All processing occurs locally without cloud transmission

### Environment Variables

```bash
MODEL_TYPE=phi-2                    # Core AI model
TASK_FOCUS=parental_prediction      # Specialized for family monitoring
DEPLOYMENT_MODE=production          # Production stability settings
PRIVACY_MODE=local_only            # No external data sharing
PARENTAL_DASHBOARD=true            # Enable dashboard features
CHILD_WELLNESS_TRACKING=true       # Enable child-specific monitoring
USE_GPU=optional                   # GPU acceleration when available
GPU_BACKEND=opencl                 # Cross-platform GPU support
```

## 📊 Prediction Capabilities

### Primary Functions

#### 1. **Child Wellness Patterns**

- **Sleep Quality Assessment**: Analyzes sleep patterns and quality metrics
- **Activity Level Monitoring**: Tracks physical activity and sedentary periods
- **Mood Pattern Recognition**: Identifies emotional patterns and triggers
- **Learning Engagement**: Monitors attention spans and learning effectiveness

#### 2. **Family Dynamic Analysis**

- **Interaction Quality**: Assesses family interaction patterns
- **Stress Level Prediction**: Predicts family stress indicators
- **Routine Optimization**: Suggests optimal family routine adjustments
- **Health Trend Forecasting**: Predicts health trends for proactive intervention

#### 3. **Parental Insights**

- **Intervention Timing**: Recommends optimal times for parental guidance
- **Behavioral Predictions**: Forecasts potential behavioral challenges
- **Wellness Recommendations**: Suggests family wellness activities
- **Progress Tracking**: Monitors long-term wellness improvement

## 🔄 Integration Points

### Input Sources

```yaml
Data Inputs:
  - Wearable Device Metrics (heart rate, steps, sleep)
  - App Usage Patterns (screen time, app interactions)
  - Environmental Sensors (room temperature, air quality)
  - Manual Check-ins (mood ratings, energy levels)
  - Family Activity Logs (meals, activities, routines)
```

### Output Destinations

```yaml
Data Outputs:
  - Parental Dashboard (real-time insights)
  - Alert System (safety notifications)
  - Recommendation Engine (wellness suggestions)
  - Trend Reports (weekly/monthly summaries)
  - Local Storage (encrypted historical data)
```

### Service Communication

```bash
# Upstream Services (Data Sources)
- Local Data Manager: Health data collection
- Redis Cache: Real-time metric storage
- Vector Store: Historical pattern retrieval

# Downstream Services (Consumers)
- Mistral Interface: Complex reasoning requests
- Phi-2 Assistant: Technical analysis support
- Parental Dashboard UI: Real-time visualization
```

## 🚀 Deployment

### Prerequisites

```bash
# Node Requirements
- Docker Swarm cluster
- Nodes labeled with 'secure=true'
- GPU support (optional, OpenCL compatible)
- Minimum 4GB RAM per node
```

### Deployment Commands

```bash
# Deploy the full production stack
docker stack deploy -c prod/zendexer_Swarm_Prod.compose zendexer-prod

# Scale the parental predictor specifically
docker service scale zendexer-prod_smollm-predictor=3

# Check service status
docker service ps zendexer-prod_smollm-predictor
```

### Health Monitoring

```bash
# Service health endpoint
curl http://localhost:8002/health

# Check logs
docker service logs zendexer-prod_smollm-predictor

# Monitor resource usage
docker stats $(docker ps -q --filter "name=zendexer-prod_smollm-predictor")
```

## 📈 Performance Metrics

### Expected Performance

- **Prediction Latency**: < 100ms for real-time metrics
- **Throughput**: 1000+ predictions per minute
- **Memory Usage**: 1.5-3GB under normal load
- **CPU Usage**: 60-80% under typical family monitoring load

### Scaling Guidelines

```yaml
Family Size Scaling:
  - 1-2 children: 1 replica sufficient
  - 3-4 children: 2 replicas recommended
  - 5+ children: 3+ replicas for optimal performance
  - Multiple families: Scale horizontally with load balancer
```

## 🔧 Configuration Management

### Environment Customization

```bash
# Family-specific settings
FAMILY_SIZE=4                       # Number of family members
CHILD_AGE_RANGES="6-8,10-12,14-16" # Age groups for specialized tracking
ALERT_SENSITIVITY=medium            # low|medium|high alert frequency
PREDICTION_HORIZON=7d              # Prediction timeframe
PRIVACY_LEVEL=strict               # strict|moderate|basic
```

### Model Tuning

```bash
# Performance optimization
MODEL_QUANTIZATION=int8            # Memory optimization
BATCH_SIZE=16                      # Inference batch size
CACHE_SIZE=1000                    # Prediction cache size
PREDICTION_CONFIDENCE_THRESHOLD=0.7 # Minimum confidence for alerts
```

## 🛠️ Troubleshooting

### Common Issues

#### High Memory Usage

```bash
# Check for memory leaks
docker exec -it <container_id> ps aux --sort=-%mem

# Restart service if needed
docker service update --force zendexer-prod_smollm-predictor
```

#### Slow Predictions

```bash
# Check GPU utilization
nvidia-smi  # or rocm-smi for AMD

# Verify model cache
docker exec -it <container_id> ls -la /app/model_cache
```

#### Network Connectivity

```bash
# Test inter-service communication
docker exec -it <container_id> curl http://phi2-assistant:8001/health
docker exec -it <container_id> curl http://mistral-interface:8080/health
```

## 📚 API Reference

### Core Endpoints

#### Prediction API

```http
POST /predict/child-wellness
Content-Type: application/json

{
  "child_id": "child_001",
  "metrics": {
    "sleep_hours": 8.5,
    "activity_minutes": 45,
    "mood_rating": 7,
    "screen_time_minutes": 120
  },
  "prediction_type": "next_24h"
}
```

#### Family Analytics

```http
GET /analytics/family/{family_id}?timeframe=7d
Authorization: Bearer <family_token>
```

#### Parental Insights

```http
GET /insights/parental?child_id=child_001&focus=behavior
Authorization: Bearer <parent_token>
```

## 🔒 Privacy & Compliance

### Data Protection

- **COPPA Compliance**: Child data protection standards
- **GDPR Compliance**: European privacy regulations
- **Local Processing**: No cloud data transmission
- **Encrypted Storage**: All data encrypted at rest
- **Access Controls**: Role-based parental access

### Audit Logging

```bash
# Audit log location
/app/audit_logs/parental_predictions.log

# Log retention
30 days local retention (configurable)
```

## 🎯 Future Enhancements

### Roadmap

- **Multi-language Support**: Localized insights and recommendations
- **Advanced ML Models**: Integration with larger specialized models
- **Wearable Integration**: Direct API connections to popular devices
- **Predictive Alerts**: Machine learning-based early warning system
- **Family Coaching**: AI-powered family wellness coaching

---

**📞 Support**: For technical support, see the main ZenDexer documentation or contact the development team.

**🔄 Last Updated**: August 11, 2025 | **Version**: 4.0-prod
