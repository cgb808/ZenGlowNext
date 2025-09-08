"""
Health and metrics endpoints for ZenGlow RAG pipeline observability
"""
from flask import Blueprint, jsonify, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import weaviate
import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Create blueprint for observability endpoints
observability_bp = Blueprint('observability', __name__)

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
INGEST_REQUESTS = Counter('ingest_requests_total', 'Total ingest requests', ['status'])
WEAVIATE_ERRORS = Counter('weaviate_errors_total', 'Total Weaviate errors', ['operation'])
ACTIVE_TASKS = Gauge('active_embedding_tasks', 'Number of active embedding tasks')

def check_weaviate_health() -> Dict[str, Any]:
    """Check Weaviate connection and health"""
    try:
        client = weaviate.Client("http://weaviate:8080")
        # Simple health check - get schema
        schema = client.schema.get()
        return {
            "status": "healthy",
            "response_time": "fast",
            "schema_classes": len(schema.get('classes', []))
        }
    except Exception as e:
        logger.error(f"Weaviate health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def check_redis_health() -> Dict[str, Any]:
    """Check Redis connection for Celery backend"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, socket_timeout=2)
        r.ping()
        return {
            "status": "healthy",
            "response_time": "fast"
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def check_celery_health() -> Dict[str, Any]:
    """Check Celery worker status"""
    try:
        from celery import current_app
        
        # Get active tasks
        inspect = current_app.control.inspect()
        active_tasks = inspect.active()
        
        if active_tasks is None:
            return {
                "status": "unhealthy", 
                "error": "No workers available"
            }
        
        total_active = sum(len(tasks) for tasks in active_tasks.values())
        
        return {
            "status": "healthy",
            "active_workers": len(active_tasks),
            "active_tasks": total_active
        }
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@observability_bp.route('/health', methods=['GET'])
def health_check():
    """
    Comprehensive health check endpoint
    Returns 200 if all systems are healthy, 503 if any critical system is down
    """
    start_time = time.time()
    
    health_status = {
        "timestamp": time.time(),
        "status": "healthy",
        "version": "1.0.0",
        "services": {
            "weaviate": check_weaviate_health(),
            "redis": check_redis_health(),
            "celery": check_celery_health()
        }
    }
    
    # Determine overall health
    unhealthy_services = [
        name for name, service in health_status["services"].items() 
        if service.get("status") != "healthy"
    ]
    
    if unhealthy_services:
        health_status["status"] = "unhealthy"
        health_status["unhealthy_services"] = unhealthy_services
        status_code = 503
    else:
        status_code = 200
    
    health_status["response_time"] = time.time() - start_time
    
    REQUEST_COUNT.labels(method='GET', endpoint='/health', status=status_code).inc()
    
    return jsonify(health_status), status_code


@observability_bp.route('/health/ready', methods=['GET'])
def readiness_check():
    """
    Readiness check - simpler check for container orchestrators
    Returns 200 if service is ready to accept requests
    """
    try:
        # Just check if we can connect to Weaviate
        weaviate_health = check_weaviate_health()
        
        if weaviate_health.get("status") == "healthy":
            REQUEST_COUNT.labels(method='GET', endpoint='/health/ready', status=200).inc()
            return jsonify({"status": "ready"}), 200
        else:
            REQUEST_COUNT.labels(method='GET', endpoint='/health/ready', status=503).inc()
            return jsonify({"status": "not ready", "reason": "weaviate unavailable"}), 503
            
    except Exception as e:
        REQUEST_COUNT.labels(method='GET', endpoint='/health/ready', status=503).inc()
        return jsonify({"status": "not ready", "error": str(e)}), 503


@observability_bp.route('/health/live', methods=['GET'])
def liveness_check():
    """
    Liveness check - basic check that the service is alive
    Returns 200 if the Flask app is running
    """
    REQUEST_COUNT.labels(method='GET', endpoint='/health/live', status=200).inc()
    return jsonify({
        "status": "alive",
        "timestamp": time.time()
    }), 200


@observability_bp.route('/metrics', methods=['GET'])
def metrics():
    """
    Prometheus metrics endpoint
    Returns metrics in Prometheus exposition format
    """
    try:
        REQUEST_COUNT.labels(method='GET', endpoint='/metrics', status=200).inc()
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
    except Exception as e:
        logger.error(f"Metrics generation failed: {e}")
        REQUEST_COUNT.labels(method='GET', endpoint='/metrics', status=500).inc()
        return jsonify({"error": "Failed to generate metrics"}), 500


def record_ingest_request(status: str):
    """Record ingest request metrics"""
    INGEST_REQUESTS.labels(status=status).inc()


def record_weaviate_error(operation: str):
    """Record Weaviate operation errors"""
    WEAVIATE_ERRORS.labels(operation=operation).inc()


def update_active_tasks(count: int):
    """Update active tasks gauge"""
    ACTIVE_TASKS.set(count)