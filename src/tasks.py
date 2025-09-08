"""
Celery configuration and background tasks for ZenGlow RAG pipeline
"""
from celery import Celery
import weaviate
# from FlagEmbedding import BGEM3FlagModel  # Temporarily disabled
import time
import logging
import re
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# Prometheus metrics
EMBEDDING_COUNTER = Counter('embedding_tasks_total', 'Total embedding tasks', ['status'])
EMBEDDING_DURATION = Histogram('embedding_duration_seconds', 'Time spent generating embeddings')
EMBEDDING_QUEUE_SIZE = Gauge('embedding_queue_size', 'Number of tasks in embedding queue')

# Global model instances (lazy-loaded)
bge_model = None
vector_client = None

def make_celery(app):
    """Create Celery instance with Flask app context"""
    celery = Celery(
        app.import_name,
        backend='redis://localhost:6379/0',
        broker='redis://localhost:6379/0'
    )
    
    class ContextTask(celery.Task):
        """Make celery tasks work with Flask app context."""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery


def init_embedding_models():
    """Initialize embedding models for background tasks"""
    global bge_model, vector_client
    
    try:
        if vector_client is None:
            vector_client = weaviate.Client("http://weaviate:8080")
            logger.info("Weaviate client initialized")
        
        if bge_model is None:
            # Temporarily mock the model for testing
            # bge_model = BGEM3FlagModel("BAAI/bge-large-en-v1.5", use_fp16=True)
            logger.warning("BGE model disabled for testing - using mock")
            
    except Exception as e:
        logger.error(f"Failed to initialize embedding models: {e}")
        raise


def create_embedding_task(celery_app):
    """Create the embedding generation task"""
    
    @celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
    def generate_embeddings_task(self, data: Dict[str, Any], idempotency_key: str, version: str = "v1"):
        """
        Background task to generate embeddings and store in Weaviate
        
        Args:
            data: Validated ingestion data
            idempotency_key: Unique key to prevent duplicates
            version: Schema version for vector class
        """
        start_time = time.time()
        
        try:
            # Initialize models if needed
            init_embedding_models()
            
            # Check for existing object with same idempotency key
            class_name = f"WellnessContext_{version}"
            existing = vector_client.query.get(class_name).with_where({
                "path": ["idempotency_key"],
                "operator": "Equal",
                "valueString": idempotency_key
            }).do()
            
            if existing.get('data', {}).get('Get', {}).get(class_name):
                logger.info(f"Skipping duplicate embedding for key: {idempotency_key}")
                EMBEDDING_COUNTER.labels(status='duplicate').inc()
                return {'status': 'duplicate', 'idempotency_key': idempotency_key}
            
            # Create rich text for embedding
            interaction_event = data.get('interaction', {}).get('event', 'None')
            # Enhanced sanitization
            interaction_event = re.sub(r'<[^>]+>', '', str(interaction_event))
            interaction_event = re.sub(r'javascript:', '', interaction_event, flags=re.IGNORECASE)
            
            context_text = (
                f"Child {data['child_id']} at age {data.get('context', {}).get('user_profile', {}).get('age', 'unknown')}: "
                f"Stress level was {data['wellness_metrics']['stress']:.2f}. "
                f"Sleep state was {data['wellness_metrics'].get('sleep_state', 'unknown')}. "
                f"Sleep duration was {data['wellness_metrics'].get('sleep_duration', 0):.0f} seconds. "
                f"Heart rate was {data['wellness_metrics']['hr']:.0f} BPM. "
                f"School events: {data.get('context', {}).get('school_events', 'None')}. "
                f"Interaction: {interaction_event}."
            )
            
            # Generate embedding
            if bge_model is None:
                # Mock embedding for testing
                embedding = [0.1] * 1024  # Mock 1024-dim embedding
                logger.warning("Using mock embedding for testing")
            else:
                embedding = bge_model.encode([context_text])[0]
            
            # Verify embedding dimensionality
            expected_dim = 1024  # BGE-large-en-v1.5 dimension
            if len(embedding) != expected_dim:
                logger.error(f"Embedding dimension mismatch: got {len(embedding)}, expected {expected_dim}")
                EMBEDDING_COUNTER.labels(status='dimension_error').inc()
                raise ValueError(f"Embedding dimension mismatch: got {len(embedding)}, expected {expected_dim}")
            
            # Store in Weaviate with idempotency key
            result = vector_client.data_object.create(
                data_object={
                    "text": context_text,
                    "child_id": data['child_id'],
                    "timestamp": data['timestamp'],
                    "idempotency_key": idempotency_key,
                    "version": version,
                    "wellness_metrics": data['wellness_metrics'],
                    "context": data.get('context', {}),
                    "interaction": data.get('interaction', {})
                },
                class_name=class_name,
                vector=embedding.tolist()
            )
            
            duration = time.time() - start_time
            EMBEDDING_DURATION.observe(duration)
            EMBEDDING_COUNTER.labels(status='success').inc()
            
            logger.info(f"Successfully created embedding for {idempotency_key} in {duration:.2f}s")
            
            return {
                'status': 'success',
                'idempotency_key': idempotency_key,
                'duration': duration,
                'object_id': result,
                'class_name': class_name
            }
            
        except Exception as exc:
            duration = time.time() - start_time
            EMBEDDING_COUNTER.labels(status='error').inc()
            
            logger.error(f"Embedding generation failed for {idempotency_key}: {exc}")
            
            # Retry on certain errors
            if self.request.retries < self.max_retries:
                logger.info(f"Retrying embedding task for {idempotency_key} (attempt {self.request.retries + 1})")
                raise self.retry(exc=exc)
            else:
                logger.error(f"Max retries exceeded for {idempotency_key}")
                return {
                    'status': 'failed',
                    'idempotency_key': idempotency_key,
                    'error': str(exc),
                    'duration': duration
                }
    
    return generate_embeddings_task