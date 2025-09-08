# RAG Ingestion Hardening Guide

This guide provides comprehensive patterns and best practices for implementing hardened RAG (Retrieval-Augmented Generation) data ingestion pipelines in ZenGlow. It addresses security, reliability, and scalability concerns for production-grade wellness data processing.

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Async Workflow Patterns](#async-workflow-patterns)
- [Deduplication Strategies](#deduplication-strategies)
- [Rate Limiting Implementation](#rate-limiting-implementation)
- [Input Validation & Sanitization](#input-validation--sanitization)
- [Metrics & Monitoring](#metrics--monitoring)
- [Retry Mechanisms](#retry-mechanisms)
- [Backpressure Handling](#backpressure-handling)
- [Security Checklist](#security-checklist)
- [Implementation Examples](#implementation-examples)

## Architecture Overview

The hardened RAG ingestion pipeline follows a multi-layer approach:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Source   │───▶│  Ingestion API  │───▶│  Validation     │
│  (Mobile/IoT)   │    │  (Rate Limited) │    │  & Sanitization │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐    ┌─────────▼─────────┐
│   Vector Store  │◀───│  Async Queue    │◀───│  Deduplication  │
│   (Weaviate)    │    │   (Celery)      │    │  & Processing   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Monitoring    │    │  Error Handling │    │  Metrics &      │
│   & Alerting    │    │  & Retries      │    │  Observability  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Async Workflow Patterns

### 1. Message Queue Architecture

Implement asynchronous processing using Celery with Redis/RabbitMQ:

```python
# tasks.py
from celery import Celery
from celery.exceptions import Retry
import time

celery_app = Celery('zenglow_ingestion')

@celery_app.task(bind=True, max_retries=3)
def process_wellness_data(self, data):
    """Asynchronously process wellness data with retries"""
    try:
        # Validate data structure
        validated_data = validate_wellness_data(data)
        
        # Store in TimescaleDB
        store_metrics(validated_data)
        
        # Generate embeddings
        generate_embeddings(validated_data)
        
        # Update metrics
        update_processing_metrics('success')
        
    except ValidationError as e:
        update_processing_metrics('validation_error')
        raise self.retry(countdown=60, exc=e)
    except DatabaseError as e:
        update_processing_metrics('db_error')
        raise self.retry(countdown=120, exc=e)
```

### 2. Event-Driven Processing

```python
# async_processor.py
import asyncio
import aioredis
from asyncio import Queue

class AsyncIngestionProcessor:
    def __init__(self):
        self.processing_queue = Queue(maxsize=1000)
        self.redis_client = None
        
    async def start(self):
        """Start async processing workers"""
        self.redis_client = await aioredis.create_redis_pool('redis://localhost')
        
        # Start multiple workers
        workers = [
            asyncio.create_task(self.worker(f"worker-{i}"))
            for i in range(4)
        ]
        await asyncio.gather(*workers)
    
    async def worker(self, worker_id):
        """Process items from queue"""
        while True:
            try:
                data = await self.processing_queue.get()
                await self.process_item(data, worker_id)
                self.processing_queue.task_done()
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)
```

## Deduplication Strategies

### 1. Content-Based Deduplication

```python
import hashlib
import redis
from datetime import timedelta

class DeduplicationManager:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.dedupe_ttl = timedelta(hours=24)
    
    def generate_content_hash(self, data):
        """Generate deterministic hash for content"""
        # Extract key fields for hashing
        key_content = {
            'child_id': data.get('child_id'),
            'timestamp': data.get('timestamp'),
            'wellness_metrics': data.get('wellness_metrics', {}),
            'interaction': data.get('interaction', {})
        }
        
        content_str = json.dumps(key_content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    def is_duplicate(self, data):
        """Check if data has been processed recently"""
        content_hash = self.generate_content_hash(data)
        key = f"dedupe:{content_hash}"
        
        if self.redis.exists(key):
            return True
        
        # Mark as seen
        self.redis.setex(key, self.dedupe_ttl, "1")
        return False
```

### 2. Temporal Deduplication

```python
def temporal_deduplication(data, window_minutes=5):
    """Prevent duplicate entries within time window"""
    child_id = data['child_id']
    timestamp = data['timestamp']
    
    # Check for recent entries
    time_window = timestamp - (window_minutes * 60)
    
    recent_entry = WellnessMetric.query.filter(
        WellnessMetric.child_id == child_id,
        WellnessMetric.timestamp >= datetime.fromtimestamp(time_window),
        WellnessMetric.timestamp <= datetime.fromtimestamp(timestamp)
    ).first()
    
    return recent_entry is not None
```

## Rate Limiting Implementation

### 1. Token Bucket Algorithm

```python
import time
import redis
from flask import request, abort

class TokenBucket:
    def __init__(self, redis_client, capacity=100, refill_rate=10):
        self.redis = redis_client
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second
    
    def consume(self, client_id, tokens=1):
        """Attempt to consume tokens from bucket"""
        key = f"rate_limit:{client_id}"
        
        with self.redis.pipeline() as pipe:
            pipe.multi()
            
            # Get current bucket state
            bucket_data = pipe.hgetall(key)
            current_time = time.time()
            
            if bucket_data:
                tokens_count = float(bucket_data.get('tokens', self.capacity))
                last_refill = float(bucket_data.get('last_refill', current_time))
            else:
                tokens_count = self.capacity
                last_refill = current_time
            
            # Calculate tokens to add
            time_passed = current_time - last_refill
            tokens_to_add = time_passed * self.refill_rate
            tokens_count = min(self.capacity, tokens_count + tokens_to_add)
            
            # Check if we can consume
            if tokens_count >= tokens:
                tokens_count -= tokens
                
                # Update bucket
                pipe.hset(key, mapping={
                    'tokens': tokens_count,
                    'last_refill': current_time
                })
                pipe.expire(key, 3600)  # 1 hour TTL
                pipe.execute()
                return True
            else:
                return False

# Flask decorator
def rate_limit(max_per_minute=60):
    def decorator(f):
        def decorated_function(*args, **kwargs):
            client_id = request.remote_addr
            bucket = TokenBucket(redis_client)
            
            if not bucket.consume(client_id):
                abort(429, description="Rate limit exceeded")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

### 2. Sliding Window Rate Limiting

```python
def sliding_window_rate_limit(client_id, window_seconds=60, max_requests=100):
    """Sliding window rate limiting"""
    current_time = time.time()
    window_start = current_time - window_seconds
    
    key = f"sliding_window:{client_id}"
    
    with redis_client.pipeline() as pipe:
        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current requests
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(current_time): current_time})
        
        # Set expiry
        pipe.expire(key, window_seconds)
        
        results = pipe.execute()
        current_count = results[1]
        
        return current_count < max_requests
```

## Input Validation & Sanitization

### 1. Schema Validation

```python
from marshmallow import Schema, fields, validate, ValidationError
import bleach

class WellnessDataSchema(Schema):
    child_id = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    timestamp = fields.Integer(required=True, validate=validate.Range(min=0))
    
    wellness_metrics = fields.Nested('WellnessMetricsSchema', required=True)
    interaction = fields.Nested('InteractionSchema', missing={})
    context = fields.Nested('ContextSchema', missing={})

class WellnessMetricsSchema(Schema):
    hr = fields.Float(validate=validate.Range(min=30, max=220))
    stress = fields.Float(validate=validate.Range(min=0, max=1))
    activity = fields.Float(validate=validate.Range(min=0, max=1), missing=0)
    sleep_duration = fields.Integer(validate=validate.Range(min=0, max=86400), missing=0)
    sleep_state = fields.Str(validate=validate.OneOf(['awake', 'light', 'deep', 'REM']), missing='awake')

class InteractionSchema(Schema):
    event = fields.Str(validate=validate.Length(max=200), missing='none')
    activity = fields.Str(validate=validate.Length(max=100), missing='none')

def validate_and_sanitize(data):
    """Validate and sanitize incoming data"""
    schema = WellnessDataSchema()
    
    try:
        # Validate structure
        validated_data = schema.load(data)
        
        # Sanitize text fields
        if 'interaction' in validated_data and 'event' in validated_data['interaction']:
            validated_data['interaction']['event'] = bleach.clean(
                validated_data['interaction']['event'],
                tags=[],  # No HTML tags allowed
                strip=True
            )
        
        return validated_data
        
    except ValidationError as e:
        raise ValueError(f"Validation failed: {e.messages}")
```

### 2. Advanced Sanitization

```python
import re
from html import escape

class DataSanitizer:
    def __init__(self):
        # Patterns for potentially malicious content
        self.sql_injection_pattern = re.compile(
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            re.IGNORECASE
        )
        self.script_pattern = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
        self.svg_pattern = re.compile(r"<svg[^>]*>.*?</svg>", re.IGNORECASE | re.DOTALL)
    
    def sanitize_text(self, text):
        """Comprehensive text sanitization"""
        if not isinstance(text, str):
            return text
        
        # Remove potentially dangerous patterns
        text = self.script_pattern.sub('', text)
        text = self.svg_pattern.sub('', text)
        
        # Check for SQL injection patterns
        if self.sql_injection_pattern.search(text):
            raise ValueError("Potentially malicious SQL pattern detected")
        
        # HTML escape
        text = escape(text)
        
        # Limit length
        return text[:1000]  # Reasonable limit
    
    def sanitize_numeric(self, value, min_val=None, max_val=None):
        """Sanitize numeric values"""
        try:
            num_val = float(value)
            
            if min_val is not None and num_val < min_val:
                raise ValueError(f"Value {num_val} below minimum {min_val}")
            if max_val is not None and num_val > max_val:
                raise ValueError(f"Value {num_val} above maximum {max_val}")
                
            return num_val
        except (ValueError, TypeError):
            raise ValueError(f"Invalid numeric value: {value}")
```

## Metrics & Monitoring

### 1. Application Metrics

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time

# Define metrics
ingestion_requests = Counter('zenglow_ingestion_requests_total', 
                           'Total ingestion requests', ['status', 'endpoint'])
ingestion_duration = Histogram('zenglow_ingestion_duration_seconds',
                              'Time spent processing ingestion requests')
active_connections = Gauge('zenglow_active_connections',
                          'Number of active connections')
queue_size = Gauge('zenglow_queue_size',
                   'Current size of processing queue')

class MetricsCollector:
    def __init__(self):
        self.start_time = time.time()
    
    def record_ingestion(self, status, duration):
        """Record ingestion metrics"""
        ingestion_requests.labels(status=status, endpoint='/api/ingest').inc()
        ingestion_duration.observe(duration)
    
    def update_queue_metrics(self, current_size):
        """Update queue size metrics"""
        queue_size.set(current_size)
    
    def update_connection_count(self, count):
        """Update active connection count"""
        active_connections.set(count)

# Middleware for metrics collection
def metrics_middleware():
    def decorator(f):
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            try:
                result = f(*args, **kwargs)
                metrics_collector.record_ingestion('success', time.time() - start_time)
                return result
            except Exception as e:
                metrics_collector.record_ingestion('error', time.time() - start_time)
                raise
        return decorated_function
    return decorator
```

### 2. Health Checks

```python
@app.route('/health')
def health_check():
    """Comprehensive health check endpoint"""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
        'checks': {}
    }
    
    # Check database connectivity
    try:
        db.session.execute('SELECT 1')
        health_status['checks']['database'] = 'healthy'
    except Exception as e:
        health_status['checks']['database'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'degraded'
    
    # Check Weaviate connectivity
    try:
        vector_client.schema.get()
        health_status['checks']['vector_store'] = 'healthy'
    except Exception as e:
        health_status['checks']['vector_store'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'degraded'
    
    # Check Redis connectivity
    try:
        redis_client.ping()
        health_status['checks']['redis'] = 'healthy'
    except Exception as e:
        health_status['checks']['redis'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'degraded'
    
    # Check queue health
    try:
        queue_size_val = get_queue_size()
        if queue_size_val > 10000:  # Alert threshold
            health_status['checks']['queue'] = 'degraded'
            health_status['status'] = 'degraded'
        else:
            health_status['checks']['queue'] = 'healthy'
    except Exception as e:
        health_status['checks']['queue'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return jsonify(health_status), status_code
```

## Retry Mechanisms

### 1. Exponential Backoff

```python
import random
import time
from functools import wraps

class ExponentialBackoff:
    def __init__(self, max_retries=3, base_delay=1, max_delay=60, jitter=True):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
    
    def calculate_delay(self, attempt):
        """Calculate delay for given attempt"""
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        
        if self.jitter:
            # Add jitter to prevent thundering herd
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay
    
    def retry(self, exceptions=(Exception,)):
        """Decorator for retry with exponential backoff"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(self.max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        
                        if attempt == self.max_retries:
                            break
                        
                        delay = self.calculate_delay(attempt)
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s")
                        time.sleep(delay)
                
                raise last_exception
            return wrapper
        return decorator

# Usage example
backoff = ExponentialBackoff(max_retries=3, base_delay=1, max_delay=30)

@backoff.retry(exceptions=(ConnectionError, TimeoutError))
def store_embeddings(data):
    """Store embeddings with retry logic"""
    try:
        vector_client.data_object.create(data)
    except weaviate.exceptions.WeaviateException as e:
        logger.error(f"Weaviate error: {e}")
        raise ConnectionError(f"Failed to store embeddings: {e}")
```

### 2. Circuit Breaker Pattern

```python
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60, expected_exception=Exception):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Reset circuit breaker on success"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """Handle failure"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

# Usage
vector_store_circuit = CircuitBreaker(failure_threshold=3, timeout=30)

def safe_vector_store(data):
    return vector_store_circuit.call(vector_client.data_object.create, data)
```

## Backpressure Handling

### 1. Queue-Based Backpressure

```python
import asyncio
from asyncio import Queue
import signal

class BackpressureManager:
    def __init__(self, max_queue_size=1000, warning_threshold=0.8):
        self.max_queue_size = max_queue_size
        self.warning_threshold = warning_threshold
        self.processing_queue = Queue(maxsize=max_queue_size)
        self.is_shutting_down = False
        
        # Setup graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        logger.info("Initiating graceful shutdown...")
        self.is_shutting_down = True
    
    async def enqueue_with_backpressure(self, item):
        """Add item to queue with backpressure handling"""
        current_size = self.processing_queue.qsize()
        
        # Check if we're approaching capacity
        if current_size > (self.max_queue_size * self.warning_threshold):
            logger.warning(f"Queue at {current_size}/{self.max_queue_size} capacity")
            
            # Implement backpressure strategies
            if current_size >= self.max_queue_size:
                # Option 1: Reject request
                raise Exception("System overloaded, please retry later")
                
                # Option 2: Drop oldest items (alternative)
                # try:
                #     self.processing_queue.get_nowait()
                #     logger.warning("Dropped oldest item due to backpressure")
                # except asyncio.QueueEmpty:
                #     pass
        
        # Add item to queue
        await self.processing_queue.put(item)
    
    async def graceful_shutdown(self):
        """Drain queue gracefully during shutdown"""
        logger.info(f"Draining {self.processing_queue.qsize()} remaining items...")
        
        while not self.processing_queue.empty():
            try:
                item = await asyncio.wait_for(
                    self.processing_queue.get(), 
                    timeout=5.0
                )
                # Process item
                await self.process_item(item)
                self.processing_queue.task_done()
            except asyncio.TimeoutError:
                logger.warning("Timeout during graceful shutdown")
                break
        
        logger.info("Graceful shutdown complete")
```

### 2. Load Shedding

```python
import random
from datetime import datetime, timedelta

class LoadShedder:
    def __init__(self):
        self.load_metrics = {
            'cpu_usage': 0,
            'memory_usage': 0,
            'queue_size': 0,
            'response_time': 0
        }
        self.thresholds = {
            'cpu_high': 80,
            'memory_high': 85,
            'queue_high': 1000,
            'response_time_high': 5.0
        }
    
    def should_shed_load(self):
        """Determine if we should shed load"""
        cpu_overload = self.load_metrics['cpu_usage'] > self.thresholds['cpu_high']
        memory_overload = self.load_metrics['memory_usage'] > self.thresholds['memory_high']
        queue_overload = self.load_metrics['queue_size'] > self.thresholds['queue_high']
        response_overload = self.load_metrics['response_time'] > self.thresholds['response_time_high']
        
        if cpu_overload or memory_overload:
            return True, "System resource exhaustion"
        elif queue_overload:
            return True, "Queue capacity exceeded"
        elif response_overload:
            return True, "Response time degradation"
        
        return False, None
    
    def shed_load(self, request_priority='normal'):
        """Implement load shedding strategy"""
        should_shed, reason = self.should_shed_load()
        
        if not should_shed:
            return False
        
        # Priority-based shedding
        if request_priority == 'low':
            drop_probability = 0.8
        elif request_priority == 'normal':
            drop_probability = 0.3
        else:  # high priority
            drop_probability = 0.1
        
        if random.random() < drop_probability:
            logger.warning(f"Load shedding: {reason}")
            return True
        
        return False

# Flask middleware for load shedding
def load_shedding_middleware():
    load_shedder = LoadShedder()
    
    def decorator(f):
        def decorated_function(*args, **kwargs):
            # Update current load metrics
            load_shedder.load_metrics.update(get_current_load_metrics())
            
            # Check if we should shed this request
            priority = request.headers.get('X-Priority', 'normal')
            if load_shedder.shed_load(priority):
                abort(503, description="Service temporarily overloaded")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

## Security Checklist

### ✅ Production Readiness Checklist

#### Input Validation & Sanitization
- [ ] **Schema validation** - All input data validated against strict schemas
- [ ] **Type checking** - Numeric ranges, string lengths, allowed values verified
- [ ] **HTML/Script sanitization** - All text input sanitized to prevent XSS
- [ ] **SQL injection prevention** - Parameterized queries and pattern detection
- [ ] **File upload validation** - If applicable, strict file type and size limits

#### Authentication & Authorization
- [ ] **API key validation** - All ingestion requests authenticated
- [ ] **Rate limiting per client** - Per-API-key or IP-based rate limiting
- [ ] **RBAC implementation** - Role-based access control for different data types
- [ ] **Token expiration** - JWT tokens with appropriate expiration times
- [ ] **Audit logging** - All authentication attempts logged

#### Rate Limiting & DoS Protection
- [ ] **Token bucket algorithm** - Implemented for smooth rate limiting
- [ ] **Sliding window limits** - Additional protection against burst attacks
- [ ] **Geographic rate limiting** - Different limits for different regions
- [ ] **User agent filtering** - Block known malicious user agents
- [ ] **Connection limiting** - Limit concurrent connections per client

#### Data Processing Security
- [ ] **Async processing** - Non-blocking ingestion pipeline implemented
- [ ] **Queue overflow protection** - Backpressure mechanisms in place
- [ ] **Circuit breakers** - Protection against cascading failures
- [ ] **Retry limits** - Exponential backoff with maximum retry limits
- [ ] **Dead letter queues** - Failed messages properly handled

#### Monitoring & Alerting
- [ ] **Real-time metrics** - Prometheus/Grafana monitoring setup
- [ ] **Error rate alerting** - Alerts for high error rates
- [ ] **Performance monitoring** - Response time and throughput tracking
- [ ] **Security event logging** - Failed auth attempts, suspicious patterns
- [ ] **Health check endpoints** - Comprehensive health monitoring

#### Data Protection
- [ ] **Encryption in transit** - TLS 1.3 for all communications
- [ ] **Encryption at rest** - Database and vector store encryption
- [ ] **PII handling** - Proper handling of personally identifiable information
- [ ] **Data retention policies** - Automated data cleanup procedures
- [ ] **Backup security** - Encrypted backups with access controls

#### Infrastructure Security
- [ ] **Network segmentation** - Proper firewall and VPC configuration
- [ ] **Container security** - Secure Docker images and runtime policies
- [ ] **Secrets management** - Proper secret rotation and storage
- [ ] **Resource limits** - CPU, memory, and disk usage limits
- [ ] **Log rotation** - Prevent disk space exhaustion from logs

## Implementation Examples

### Complete Hardened Ingestion Endpoint

```python
from flask import Flask, request, jsonify, abort
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# Initialize components
rate_limiter = TokenBucket(redis_client)
deduplicator = DeduplicationManager(redis_client)
sanitizer = DataSanitizer()
metrics_collector = MetricsCollector()
backpressure_manager = BackpressureManager()

@app.route('/api/ingest', methods=['POST'])
@rate_limit(max_per_minute=100)
@load_shedding_middleware()
@metrics_middleware()
def hardened_ingest():
    """Production-ready hardened ingestion endpoint"""
    start_time = time.time()
    
    try:
        # 1. Basic request validation
        if not request.is_json:
            abort(400, description="Content-Type must be application/json")
        
        data = request.get_json()
        if not data:
            abort(400, description="Empty request body")
        
        # 2. Schema validation and sanitization
        try:
            validated_data = validate_and_sanitize(data)
        except ValueError as e:
            logger.warning(f"Validation failed: {e}")
            abort(400, description=str(e))
        
        # 3. Deduplication check
        if deduplicator.is_duplicate(validated_data):
            logger.info("Duplicate data detected, skipping processing")
            return jsonify({"status": "duplicate", "message": "Data already processed"}), 200
        
        # 4. Enqueue for async processing
        try:
            asyncio.run(backpressure_manager.enqueue_with_backpressure(validated_data))
        except Exception as e:
            logger.error(f"Queue full: {e}")
            abort(503, description="System temporarily overloaded")
        
        # 5. Return success response
        processing_time = time.time() - start_time
        logger.info(f"Data queued successfully in {processing_time:.3f}s")
        
        return jsonify({
            "status": "accepted",
            "message": "Data queued for processing",
            "processing_time": processing_time
        }), 202
        
    except Exception as e:
        logger.error(f"Unexpected error in ingestion: {e}")
        abort(500, description="Internal server error")

if __name__ == '__main__':
    # Setup graceful shutdown
    import atexit
    atexit.register(lambda: asyncio.run(backpressure_manager.graceful_shutdown()))
    
    app.run(host='0.0.0.0', port=5000, threaded=True)
```

### Monitoring Dashboard Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'zenglow-ingestion'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
    scrape_interval: 5s

# alertmanager rules
groups:
  - name: zenglow_ingestion
    rules:
      - alert: HighErrorRate
        expr: rate(zenglow_ingestion_requests_total{status="error"}[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: High error rate in ZenGlow ingestion
          
      - alert: QueueBacklog
        expr: zenglow_queue_size > 1000
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: ZenGlow ingestion queue backlog
```

---

## Conclusion

This hardening guide provides comprehensive patterns for implementing production-grade RAG ingestion pipelines. Regular security audits, load testing, and monitoring are essential for maintaining system integrity and performance.

For implementation assistance or security questions, refer to the [Security Implementation Guide](../Security_Implementation_Guide.md) or consult the development team.