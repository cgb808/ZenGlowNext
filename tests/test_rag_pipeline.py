"""
Unit tests for ZenGlow RAG pipeline hardening
"""
import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Test the Pydantic schemas
from src.schemas import IngestDataSchema, WellnessMetricsSchema, ContextSchema, InteractionSchema
from pydantic import ValidationError


class TestInputValidation:
    """Test input validation with Pydantic schemas"""
    
    def test_valid_ingest_data(self):
        """Test valid input data passes validation"""
        valid_data = {
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
        
        schema = IngestDataSchema(**valid_data)
        assert schema.child_id == "test_child_123"
        assert schema.wellness_metrics.hr == 80.0
        assert schema.wellness_metrics.stress == 0.3
        assert schema.context.user_profile.age == 8
    
    def test_invalid_child_id(self):
        """Test invalid child_id is rejected"""
        invalid_data = {
            "child_id": "",  # Empty child_id
            "timestamp": time.time(),
            "wellness_metrics": {"hr": 80.0, "stress": 0.3}
        }
        
        with pytest.raises(ValidationError):
            IngestDataSchema(**invalid_data)
    
    def test_invalid_heart_rate(self):
        """Test invalid heart rate values are rejected"""
        invalid_data = {
            "child_id": "test_child",
            "timestamp": time.time(),
            "wellness_metrics": {"hr": 300.0, "stress": 0.3}  # Too high HR
        }
        
        with pytest.raises(ValidationError):
            IngestDataSchema(**invalid_data)
    
    def test_invalid_stress_level(self):
        """Test invalid stress level is rejected"""
        invalid_data = {
            "child_id": "test_child",
            "timestamp": time.time(),
            "wellness_metrics": {"hr": 80.0, "stress": 1.5}  # > 1.0
        }
        
        with pytest.raises(ValidationError):
            IngestDataSchema(**invalid_data)
    
    def test_sanitization_removes_html_tags(self):
        """Test that HTML tags are removed from input"""
        data = {
            "child_id": "test_child",
            "timestamp": time.time(),
            "wellness_metrics": {"hr": 80.0, "stress": 0.3},
            "interaction": {
                "event": "<script>alert('xss')</script>Normal text"
            }
        }
        
        schema = IngestDataSchema(**data)
        assert "<script>" not in schema.interaction.event
        assert "Normal text" in schema.interaction.event
    
    def test_idempotency_key_generation(self):
        """Test idempotency key generation"""
        timestamp = 1234567890.123
        data = {
            "child_id": "test_child",
            "timestamp": timestamp,
            "wellness_metrics": {"hr": 80.0, "stress": 0.3}
        }
        
        schema = IngestDataSchema(**data)
        expected_key = f"test_child_{int(timestamp)}"
        assert schema.get_idempotency_key() == expected_key
    
    def test_invalid_timestamp(self):
        """Test that invalid timestamps are rejected"""
        # Timestamp from year 1900 should be rejected
        invalid_timestamp = datetime(1900, 1, 1).timestamp()
        
        invalid_data = {
            "child_id": "test_child",
            "timestamp": invalid_timestamp,
            "wellness_metrics": {"hr": 80.0, "stress": 0.3}
        }
        
        with pytest.raises(ValidationError):
            IngestDataSchema(**invalid_data)


class TestWeaviateSchemaManager:
    """Test Weaviate schema management"""
    
    @patch('src.weaviate_schema.weaviate.Client')
    def test_create_class_if_not_exists_new_class(self, mock_client):
        """Test creating a new Weaviate class"""
        from src.weaviate_schema import WeaviateSchemaManager
        
        # Mock that class doesn't exist
        mock_client.schema.get.return_value = {"classes": []}
        mock_client.schema.create_class = Mock()
        
        manager = WeaviateSchemaManager(mock_client)
        result = manager.create_class_if_not_exists(version="v1")
        
        assert result is True
        mock_client.schema.create_class.assert_called_once()
    
    @patch('src.weaviate_schema.weaviate.Client')
    def test_create_class_if_not_exists_existing_class(self, mock_client):
        """Test handling existing Weaviate class"""
        from src.weaviate_schema import WeaviateSchemaManager
        
        # Mock that class already exists
        mock_client.schema.get.return_value = {
            "classes": [{"class": "WellnessContext_v1"}]
        }
        mock_client.query.get.return_value.with_additional.return_value.with_limit.return_value.do.return_value = {
            "data": {"Get": {"WellnessContext_v1": []}}
        }
        
        manager = WeaviateSchemaManager(mock_client)
        result = manager.create_class_if_not_exists(version="v1")
        
        assert result is True
        # Should not create class since it exists
        mock_client.schema.create_class.assert_not_called()


@patch('src.tasks.weaviate.Client')
@patch('src.tasks.BGEM3FlagModel')
class TestBackgroundTasks:
    """Test background embedding generation tasks"""
    
    def test_successful_embedding_generation(self, mock_bge, mock_client):
        """Test successful embedding generation"""
        from src.tasks import create_embedding_task
        from celery import Celery
        
        # Create mock Celery app
        celery_app = Celery('test')
        celery_app.conf.task_always_eager = True  # Run tasks synchronously for testing
        
        # Mock embedding model
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1] * 1024]  # Mock 1024-dim embedding
        mock_bge.return_value = mock_model
        
        # Mock Weaviate client
        mock_weaviate = Mock()
        mock_weaviate.query.get.return_value.with_where.return_value.do.return_value = {
            "data": {"Get": {"WellnessContext_v1": []}}
        }
        mock_weaviate.data_object.create.return_value = "test_object_id"
        mock_client.return_value = mock_weaviate
        
        # Create task
        task = create_embedding_task(celery_app)
        
        # Test data
        test_data = {
            "child_id": "test_child",
            "timestamp": time.time(),
            "wellness_metrics": {"hr": 80.0, "stress": 0.3, "sleep_duration": 28800, "sleep_state": "deep"}
        }
        
        # Execute task
        result = task(test_data, "test_key", "v1")
        
        assert result['status'] == 'success'
        assert result['idempotency_key'] == 'test_key'
        mock_weaviate.data_object.create.assert_called_once()
    
    def test_duplicate_prevention(self, mock_bge, mock_client):
        """Test that duplicate embeddings are prevented"""
        from src.tasks import create_embedding_task
        from celery import Celery
        
        celery_app = Celery('test')
        celery_app.conf.task_always_eager = True
        
        # Mock that object already exists
        mock_weaviate = Mock()
        mock_weaviate.query.get.return_value.with_where.return_value.do.return_value = {
            "data": {"Get": {"WellnessContext_v1": [{"id": "existing_object"}]}}
        }
        mock_client.return_value = mock_weaviate
        
        task = create_embedding_task(celery_app)
        
        test_data = {
            "child_id": "test_child",
            "timestamp": time.time(),
            "wellness_metrics": {"hr": 80.0, "stress": 0.3}
        }
        
        result = task(test_data, "test_key", "v1")
        
        assert result['status'] == 'duplicate'
        # Should not create new object
        mock_weaviate.data_object.create.assert_not_called()
    
    def test_embedding_dimension_validation(self, mock_bge, mock_client):
        """Test that embedding dimension is validated"""
        from src.tasks import create_embedding_task
        from celery import Celery
        
        celery_app = Celery('test')
        celery_app.conf.task_always_eager = True
        
        # Mock wrong dimension embedding
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1] * 512]  # Wrong dimension
        mock_bge.return_value = mock_model
        
        mock_weaviate = Mock()
        mock_weaviate.query.get.return_value.with_where.return_value.do.return_value = {
            "data": {"Get": {"WellnessContext_v1": []}}
        }
        mock_client.return_value = mock_weaviate
        
        task = create_embedding_task(celery_app)
        
        test_data = {
            "child_id": "test_child",
            "timestamp": time.time(),
            "wellness_metrics": {"hr": 80.0, "stress": 0.3}
        }
        
        result = task(test_data, "test_key", "v1")
        
        assert result['status'] == 'failed'
        assert 'dimension mismatch' in result['error'].lower()


class TestObservabilityEndpoints:
    """Test health and metrics endpoints"""
    
    @patch('src.observability.weaviate.Client')
    @patch('src.observability.redis.Redis')
    def test_health_endpoint_all_healthy(self, mock_redis, mock_weaviate):
        """Test health endpoint when all services are healthy"""
        from src.observability import health_check
        
        # Mock healthy services
        mock_weaviate.return_value.schema.get.return_value = {"classes": []}
        mock_redis.return_value.ping.return_value = True
        
        with patch('src.observability.current_app') as mock_celery:
            mock_celery.control.inspect.return_value.active.return_value = {"worker1": []}
            
            # This would need to be tested in Flask app context
            # For now, test the underlying function logic
            from src.observability import check_weaviate_health, check_redis_health
            
            weaviate_health = check_weaviate_health()
            redis_health = check_redis_health()
            
            assert weaviate_health['status'] == 'healthy'
            assert redis_health['status'] == 'healthy'
    
    @patch('src.observability.weaviate.Client')
    def test_health_endpoint_weaviate_unhealthy(self, mock_weaviate):
        """Test health endpoint when Weaviate is unhealthy"""
        from src.observability import check_weaviate_health
        
        # Mock Weaviate failure
        mock_weaviate.side_effect = Exception("Connection failed")
        
        health = check_weaviate_health()
        assert health['status'] == 'unhealthy'
        assert 'Connection failed' in health['error']


if __name__ == '__main__':
    pytest.main([__file__])