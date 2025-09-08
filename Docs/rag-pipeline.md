# RAG Pipeline Architecture & Failure Modes

## Overview

The ZenGlow RAG (Retrieval-Augmented Generation) pipeline is a hardened, production-ready system for ingesting, processing, and storing child wellness data with vector embeddings. This document describes the architecture, components, failure modes, and operational considerations.

## Architecture Components

### 1. Data Ingestion Layer

**Endpoint**: `POST /api/ingest`

**Components**:
- **Input Validation**: Pydantic schemas with strict validation rules
- **Rate Limiting**: Flask-Limiter (10 requests/minute per IP)
- **Sanitization**: HTML/script tag removal, content length limits
- **Idempotency**: Key generation using `child_id + timestamp`

**Flow**:
```
HTTP Request → Rate Limiter → Input Validation → Database Storage → Background Task Queue
```

### 2. Background Processing Layer

**Components**:
- **Celery**: Task queue with Redis backend
- **Embedding Generation**: BGE-large-en-v1.5 model (1024 dimensions)
- **Vector Storage**: Weaviate with versioned schema
- **Retry Logic**: Up to 3 retries with exponential backoff

**Flow**:
```
Task Queue → Model Loading → Text Processing → Embedding Generation → Vector Storage
```

### 3. Vector Storage Layer

**Components**:
- **Weaviate**: Vector database with custom schema
- **Schema Versioning**: `WellnessContext_v1`, `WellnessContext_v2`, etc.
- **Consistency Checks**: Embedding dimension validation
- **Idempotency**: Duplicate prevention at storage level

### 4. Observability Layer

**Endpoints**:
- `/health` - Comprehensive health check
- `/health/ready` - Kubernetes readiness probe
- `/health/live` - Kubernetes liveness probe
- `/metrics` - Prometheus metrics

**Metrics**:
- Request counts and latencies
- Embedding generation times
- Queue depth and worker status
- Error rates by component

## Data Flow

### Successful Ingestion

1. **Request Validation**:
   ```json
   {
     "child_id": "child_123",
     "timestamp": 1640995200,
     "wellness_metrics": {
       "hr": 80.0,
       "stress": 0.3,
       "sleep_duration": 28800,
       "sleep_state": "deep"
     },
     "context": {
       "user_profile": {"age": 8},
       "school_events": "Math test today"
     },
     "interaction": {
       "event": "Child played with puzzle game"
     }
   }
   ```

2. **Database Storage**: Store in TimescaleDB
3. **Task Queuing**: Submit to Celery worker
4. **Response**: Return task ID and idempotency key

### Background Processing

1. **Duplicate Check**: Query Weaviate for existing idempotency key
2. **Text Generation**: Create rich context string
3. **Embedding**: Generate 1024-dim vector using BGE model
4. **Validation**: Verify embedding dimensions
5. **Storage**: Store in `WellnessContext_v1` class

## Failure Modes & Handling

### 1. Input Validation Failures

**Symptoms**:
- HTTP 400 responses
- Validation error messages
- High rejection rate

**Causes**:
- Invalid field values (HR > 200, stress > 1.0)
- Missing required fields
- Malformed timestamps
- Oversized content

**Detection**:
- Metrics: `ingest_requests_total{status="validation_error"}`
- Logs: Validation error details

**Recovery**:
- Client-side fixes required
- No automatic recovery needed

### 2. Rate Limiting

**Symptoms**:
- HTTP 429 responses
- Blocked requests from specific IPs

**Causes**:
- Abuse or misconfigured clients
- Legitimate traffic spikes

**Detection**:
- Metrics: `http_requests_total{status="429"}`
- Rate limiter logs

**Recovery**:
- Automatic: Rate limits reset over time
- Manual: Whitelist legitimate high-volume clients

### 3. Database Connection Failures

**Symptoms**:
- HTTP 500 responses
- TimescaleDB connection errors
- Transaction rollbacks

**Causes**:
- Database server down
- Network connectivity issues
- Connection pool exhaustion

**Detection**:
- Health check: `/health` returns unhealthy
- Metrics: Increased error rates
- Database connection metrics

**Recovery**:
- Automatic: Connection retries
- Manual: Database server restart
- Scaling: Increase connection pool size

### 4. Background Task Failures

**Symptoms**:
- Tasks stuck in PENDING state
- Celery worker errors
- Queue depth increases

**Causes**:
- Model loading failures
- Weaviate connection issues
- Out of memory errors
- Embedding dimension mismatches

**Detection**:
- Metrics: `embedding_tasks_total{status="error"}`
- Celery monitoring: Task states
- Health check: Celery worker status

**Recovery**:
- Automatic: Task retries (up to 3 attempts)
- Manual: Worker restart
- Model reloading if GPU/memory issues

### 5. Vector Database Failures

**Symptoms**:
- Embedding storage failures
- Schema inconsistencies
- Query timeouts

**Causes**:
- Weaviate server down
- Schema version conflicts
- Storage capacity limits
- Network partitions

**Detection**:
- Metrics: `weaviate_errors_total{operation="create"}`
- Health check: Weaviate status
- Schema validation errors

**Recovery**:
- Automatic: Connection retries
- Schema: Auto-recreation with consistency flag
- Manual: Weaviate server restart

### 6. Model Loading Failures

**Symptoms**:
- Long task execution times
- Model initialization errors
- GPU/memory errors

**Causes**:
- Insufficient GPU memory
- Model file corruption
- Network issues downloading models

**Detection**:
- Task duration metrics exceed thresholds
- Model loading error logs
- GPU memory monitoring

**Recovery**:
- Automatic: Model reloading on worker restart
- Manual: GPU memory cleanup
- Configuration: Reduce model precision (fp16 → fp32)

## Performance Characteristics

### Latency Targets

- **Ingestion Response**: < 200ms median (local)
- **Background Processing**: < 5 seconds per embedding
- **Health Checks**: < 1 second
- **Metrics Collection**: < 500ms

### Throughput Capacity

- **Ingestion**: 10 requests/minute per IP (configurable)
- **Background Tasks**: Depends on worker count and GPU availability
- **Storage**: Limited by Weaviate instance capacity

### Resource Requirements

- **CPU**: 2+ cores for Flask app
- **Memory**: 4GB+ for embedding model
- **GPU**: Optional but recommended for embedding generation
- **Storage**: Depends on data retention requirements

## Operational Procedures

### Deployment

1. **Prerequisites**:
   - Redis server for Celery backend
   - Weaviate instance with proper configuration
   - TimescaleDB for metric storage

2. **Environment Variables**:
   ```bash
   DATABASE_URL=postgresql://user:pass@timescale:5432/db
   REDIS_URL=redis://localhost:6379/0
   WEAVIATE_URL=http://weaviate:8080
   ```

3. **Service Startup**:
   ```bash
   # Start Celery worker
   celery -A src.app.celery worker --loglevel=info
   
   # Start Flask app
   python src/app.py
   ```

### Monitoring

1. **Health Checks**:
   - Kubernetes: Use `/health/ready` and `/health/live`
   - Load balancer: Use `/health`

2. **Metrics Collection**:
   - Prometheus: Scrape `/metrics` endpoint
   - Grafana: Create dashboards for key metrics

3. **Alerting Rules**:
   ```yaml
   - alert: HighIngestionErrorRate
     expr: rate(ingest_requests_total{status="error"}[5m]) > 0.1
     
   - alert: EmbeddingQueueBacklog
     expr: embedding_queue_size > 100
     
   - alert: WeaviateDown
     expr: up{job="weaviate"} == 0
   ```

### Scaling Considerations

1. **Horizontal Scaling**:
   - Multiple Flask app instances behind load balancer
   - Multiple Celery workers across machines
   - Weaviate clustering for high availability

2. **Vertical Scaling**:
   - Increase worker memory for larger models
   - GPU upgrades for faster embedding generation
   - Database scaling for higher ingestion rates

### Troubleshooting

1. **High Error Rates**:
   - Check `/health` endpoint for service status
   - Review application logs for error patterns
   - Monitor resource utilization

2. **Slow Performance**:
   - Check embedding generation latency metrics
   - Monitor GPU utilization if available
   - Review database query performance

3. **Queue Backlog**:
   - Scale up Celery workers
   - Check for stuck tasks
   - Monitor memory usage on workers

## Security Considerations

### Input Sanitization

- HTML/XML tag removal
- Script injection prevention
- Content length limits
- Character set validation

### Rate Limiting

- Per-IP request limits
- Configurable time windows
- Bypass mechanisms for trusted clients

### Data Protection

- Child data encryption at rest
- Secure API communication (HTTPS)
- Access logging and audit trails

## Schema Evolution

### Version Management

- New schema versions: `WellnessContext_v2`, etc.
- Backward compatibility maintenance
- Migration procedures for existing data

### Breaking Changes

- Embedding dimension changes
- Field type modifications
- Required field additions

## Disaster Recovery

### Backup Procedures

1. **Database Backups**: Regular TimescaleDB snapshots
2. **Vector Backups**: Weaviate data export procedures
3. **Configuration Backups**: Environment and schema definitions

### Recovery Procedures

1. **Service Restart**: Graceful shutdown and restart procedures
2. **Data Recovery**: Restore from backups with minimal downtime
3. **Schema Recovery**: Auto-recreation with consistency checks

## Future Enhancements

### Planned Improvements

1. **Advanced Validation**: ML-based content safety validation
2. **Smart Retry**: Context-aware retry strategies
3. **Multi-Model Support**: Multiple embedding models for A/B testing
4. **Advanced Metrics**: Custom business metrics and SLAs

### Performance Optimizations

1. **Caching**: Embedding result caching for similar content
2. **Batching**: Batch processing for multiple embeddings
3. **Compression**: Vector compression for storage efficiency