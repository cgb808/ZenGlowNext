from flask import Flask, request, jsonify, abort
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import weaviate
# from darts import TimeSeries  # Temporarily disabled
# from transformers import AutoModelForCausalLM, AutoTokenizer  # Temporarily disabled
# from FlagEmbedding import BGEM3FlagModel  # Temporarily disabled
from datetime import datetime
# import pandas as pd  # Temporarily disabled
import requests # For calling forecast endpoint from insights
import re
import logging
import time
import signal
import sys
from pydantic import ValidationError

# Import our new modules
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from schemas import IngestDataSchema
from tasks import make_celery, create_embedding_task
from observability import observability_bp, record_ingest_request, record_weaviate_error
from weaviate_schema import WeaviateSchemaManager

app = Flask(__name__)
CORS(app)  # Enable CORS for mobile apps

# Configurations
# Update this to connect to your local timescaledb-local service
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://zenglow:examplepassword@timescaledb-local:5432/zenglow'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Rate limiting configuration
app.config['RATELIMIT_STORAGE_URL'] = 'redis://localhost:6379'

db = SQLAlchemy(app)

# Rate limiting setup
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["1000 per hour"]
)

# Register observability blueprint
app.register_blueprint(observability_bp)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery for background tasks
celery = make_celery(app)
generate_embeddings_task = create_embedding_task(celery)

# Initialize models (lazy-load on first use)
bge_model = None
darts_model = None
llm_model = None
llm_tokenizer = None
vector_client = None
schema_manager = None

# Graceful shutdown handling
shutdown_flag = False

# Database Models (TimescaleDB)
class Child(db.Model):
    __tablename__ = 'children'
    id = db.Column(db.String(50), primary_key=True)  # child_123
    age = db.Column(db.Integer)
    baseline_stress = db.Column(db.Float)
    school_events = db.Column(db.JSON)  # {"math_test": "2023-08-15"}

class WellnessMetric(db.Model):
    __tablename__ = 'wellness_metrics'
    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.String(50), db.ForeignKey('children.id'))
    timestamp = db.Column(db.DateTime, index=True)
    heart_rate = db.Column(db.Float)
    stress_level = db.Column(db.Float)
    activity_intensity = db.Column(db.Float)
    sleep_duration = db.Column(db.Float)  # Seconds
    sleep_state = db.Column(db.String(20))  # "light"/"deep"/"REM"

# Helper Functions
def init_models():
    global bge_model, vector_client, darts_model, llm_model, llm_tokenizer, schema_manager

    # BGE Embedding Model
    # bge_model = BGEM3FlagModel("BAAI/bge-large-en-v1.5", use_fp16=True) # Commented out for now, as it requires GPU or specific setup

    # Weaviate Client
    vector_client = weaviate.Client("http://weaviate:8080")
    schema_manager = WeaviateSchemaManager(vector_client)
    
    # Ensure WellnessContext_v1 class exists with proper schema
    schema_manager.create_class_if_not_exists(version="v1", expected_vector_dimension=1024)

    # Darts Model (lazy-loaded in forecast endpoint)

    # LLM Model (lazy-loaded in insights endpoint)

def signal_handler(sig, frame):
    """Handle graceful shutdown"""
    global shutdown_flag
    logger.info("Received shutdown signal, initiating graceful shutdown...")
    shutdown_flag = True
    
    # Give background tasks time to complete
    try:
        # Get active tasks count
        from celery import current_app
        inspect = current_app.control.inspect()
        active_tasks = inspect.active()
        
        if active_tasks:
            total_active = sum(len(tasks) for tasks in active_tasks.values())
            if total_active > 0:
                logger.info(f"Waiting for {total_active} active tasks to complete...")
                # In production, you might want to implement a more sophisticated shutdown
                time.sleep(5)  # Give tasks a moment to finish
        
    except Exception as e:
        logger.warning(f"Error during shutdown: {e}")
    
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@app.route('/api/ingest', methods=['POST'])
@limiter.limit("10 per minute")  # Rate limiting to prevent abuse
def ingest_data():
    """
    Enhanced data ingestion endpoint with validation, idempotency, and background processing
    """
    start_time = time.time()
    
    try:
        # Check for shutdown flag
        if shutdown_flag:
            abort(503, description="Service is shutting down")
        
        # Parse and validate input data
        raw_data = request.json
        if not raw_data:
            record_ingest_request('validation_error')
            abort(400, description="Missing request body")
        
        try:
            # Validate using Pydantic schema
            validated_data = IngestDataSchema(**raw_data)
        except ValidationError as e:
            logger.warning(f"Validation error: {e}")
            record_ingest_request('validation_error')
            abort(400, description=f"Validation error: {e}")
        
        # Generate idempotency key
        idempotency_key = validated_data.get_idempotency_key()
        
        # Store metric in TimescaleDB
        metric = WellnessMetric(
            child_id=validated_data.child_id,
            timestamp=datetime.fromtimestamp(validated_data.timestamp),
            heart_rate=validated_data.wellness_metrics.hr,
            stress_level=validated_data.wellness_metrics.stress,
            sleep_duration=validated_data.wellness_metrics.sleep_duration,
            sleep_state=validated_data.wellness_metrics.sleep_state
        )
        db.session.add(metric)
        db.session.commit()
        
        # Queue background embedding generation task
        task_result = generate_embeddings_task.delay(
            data=validated_data.dict(),
            idempotency_key=idempotency_key,
            version="v1"
        )
        
        duration = time.time() - start_time
        record_ingest_request('success')
        
        logger.info(f"Ingestion successful for {validated_data.child_id} in {duration:.3f}s, task_id: {task_result.id}")
        
        return jsonify({
            "status": "success",
            "task_id": task_result.id,
            "idempotency_key": idempotency_key,
            "processing_time": duration
        }), 201

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Ingestion error: {e}")
        record_ingest_request('error')
        
        if 'metric' in locals():
            db.session.rollback()
        
        abort(500, description="Failed to process request.")

@app.route('/api/ingest/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Get the status of a background embedding task"""
    try:
        result = generate_embeddings_task.AsyncResult(task_id)
        
        response = {
            "task_id": task_id,
            "status": result.status,
            "ready": result.ready()
        }
        
        if result.ready():
            if result.successful():
                response["result"] = result.result
            else:
                response["error"] = str(result.result)
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Failed to get task status for {task_id}: {e}")
        return jsonify({"error": "Failed to get task status"}), 500

# Legacy embedding function (kept for backward compatibility, but now deprecated)
def _generate_embeddings(data):
    """
    DEPRECATED: Use background task instead
    This function is kept for backward compatibility but should not be used
    """
    logger.warning("_generate_embeddings called directly - this is deprecated, use background tasks instead")
    
    # This should be run in a background task (e.g., Celery)
    global vector_client, bge_model
    if vector_client is None: # Lazy initialization
        vector_client = weaviate.Client("http://weaviate:8080")
    if bge_model is None:
        bge_model = BGEM3FlagModel("BAAI/bge-large-en-v1.5", use_fp16=True)

    # Create a rich text string for embedding
    interaction_event = data.get('interaction', {}).get('event', 'None')
    # Basic sanitization to remove potential HTML/XML tags (like SVG)
    interaction_event = re.sub(r'<[^>]+>', '', interaction_event)

    context_text = (
        f"Child {data['child_id']} at age {data.get('context', {}).get('user_profile', {}).get('age')}: "
        f"Stress level was {data['wellness_metrics']['stress']:.2f}. "
        f"Sleep state was {data['wellness_metrics'].get('sleep_state')}. "
        f"School events: {data.get('context', {}).get('school_events', 'None')}. "
        f"Interaction: {interaction_event}."
    )

    embedding = bge_model.encode([context_text])[0]

    vector_client.data_object.create(
        data_object={
            "text": context_text,
            "child_id": data['child_id'],
            "timestamp": data['timestamp']
        },
        class_name="WellnessContext",
        vector=embedding.tolist()
    )

# Run the Flask App
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create tables if they don't exist
        init_models()  # Initialize models and schema
    
    app.run(host='0.0.0.0', port=5000, debug=True)