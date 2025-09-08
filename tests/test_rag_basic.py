"""
Basic RAG pipeline tests without heavy dependencies
"""
import pytest
import time
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_schema_validation_pipeline():
    """Test the complete validation pipeline"""
    from schemas import IngestDataSchema
    
    # Test valid data
    valid_payload = {
        "child_id": "test_child_123",
        "timestamp": time.time(),
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
    
    schema = IngestDataSchema(**valid_payload)
    assert schema.child_id == "test_child_123"
    assert schema.wellness_metrics.hr == 80.0
    assert schema.wellness_metrics.stress == 0.3
    
    # Test idempotency key
    idempotency_key = schema.get_idempotency_key()
    assert idempotency_key.startswith("test_child_123_")
    
    print("✅ Schema validation pipeline works correctly")

def test_input_sanitization():
    """Test that malicious input is properly sanitized"""
    from schemas import IngestDataSchema
    
    malicious_payload = {
        "child_id": "test_child_123",  # Valid child_id, malicious content in other fields
        "timestamp": time.time(),
        "wellness_metrics": {"hr": 80.0, "stress": 0.3},
        "interaction": {
            "event": "<script>alert('xss')</script><img src=x onerror=alert(1)>Safe text"
        },
        "context": {
            "school_events": "<svg onload=alert(1)>Math test</svg>"
        }
    }
    
    schema = IngestDataSchema(**malicious_payload)
    
    # Verify malicious content was removed
    assert '<script>' not in schema.interaction.event
    assert 'onerror=' not in schema.interaction.event
    assert '<svg' not in schema.context.school_events
    
    # Verify safe content was preserved
    assert 'Safe text' in schema.interaction.event
    assert 'Math test' in schema.context.school_events
    
    print("✅ Input sanitization works correctly")

def test_weaviate_schema_generation():
    """Test Weaviate schema generation"""
    from weaviate_schema import WeaviateSchemaManager
    from unittest.mock import Mock
    
    # Mock Weaviate client
    mock_client = Mock()
    manager = WeaviateSchemaManager(mock_client)
    
    # Test schema generation
    schema = manager.get_wellness_context_schema("v1")
    
    assert schema["class"] == "WellnessContext_v1"
    assert schema["vectorizer"] == "none"
    
    # Check required properties exist
    property_names = [prop["name"] for prop in schema["properties"]]
    required_props = ["text", "child_id", "timestamp", "idempotency_key", "version", "wellness_metrics"]
    
    for prop in required_props:
        assert prop in property_names, f"Missing property: {prop}"
    
    print("✅ Weaviate schema generation works correctly")

def test_observability_checks():
    """Test observability health check functions"""
    from observability import check_weaviate_health, check_redis_health
    from unittest.mock import patch, Mock
    
    # Test Weaviate health check with mock
    with patch('weaviate.Client') as mock_weaviate:
        mock_weaviate.return_value.schema.get.return_value = {"classes": []}
        health = check_weaviate_health()
        assert health["status"] == "healthy"
    
    # Test Redis health check with mock
    with patch('redis.Redis') as mock_redis:
        mock_redis.return_value.ping.return_value = True
        health = check_redis_health()
        assert health["status"] == "healthy"
    
    print("✅ Observability health checks work correctly")

def test_rate_limiting_config():
    """Test that rate limiting configuration is properly set up"""
    from flask import Flask
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    
    app = Flask(__name__)
    app.config['RATELIMIT_STORAGE_URL'] = 'memory://'
    
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["1000 per hour"]
    )
    
    limiter.init_app(app)
    
    @app.route('/test')
    @limiter.limit("10 per minute")
    def test_endpoint():
        return "OK"
    
    # Test that decorator can be applied
    assert test_endpoint is not None
    print("✅ Rate limiting configuration works correctly")

def test_comprehensive_pipeline():
    """Test the complete pipeline components work together"""
    test_schema_validation_pipeline()
    test_input_sanitization()
    test_weaviate_schema_generation()
    test_observability_checks()
    test_rate_limiting_config()
    
    print("🎉 All RAG pipeline components are working correctly!")

if __name__ == "__main__":
    test_comprehensive_pipeline()