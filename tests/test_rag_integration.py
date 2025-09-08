"""
Integration tests for ZenGlow RAG pipeline
"""
import pytest
import json
import time
import requests
from unittest.mock import Mock, patch
from flask import Flask
from flask.testing import FlaskClient

# Import the main app for testing
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRAGPipelineIntegration:
    """Integration tests for the complete RAG pipeline"""
    
    @pytest.fixture
    def app(self):
        """Create a test Flask app"""
        from src.app import app, db
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # In-memory DB for testing
        app.config['CELERY_TASK_ALWAYS_EAGER'] = True  # Run tasks synchronously
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture
    def client(self, app):
        """Create a test client"""
        return app.test_client()
    
    def test_valid_ingest_request_success(self, client):
        """Test that a valid ingest request succeeds"""
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
        
        # Mock the background task
        with patch('src.app.generate_embeddings_task') as mock_task:
            mock_task.delay.return_value.id = "test_task_id"
            
            response = client.post('/api/ingest', 
                                 json=valid_payload,
                                 content_type='application/json')
            
            assert response.status_code == 201
            data = json.loads(response.data)
            assert data['status'] == 'success'
            assert 'task_id' in data
            assert 'idempotency_key' in data
            mock_task.delay.assert_called_once()
    
    def test_invalid_payload_rejected(self, client):
        """Test that invalid payloads are rejected"""
        invalid_payload = {
            "child_id": "",  # Invalid empty child_id
            "timestamp": time.time(),
            "wellness_metrics": {
                "hr": 300.0,  # Invalid high heart rate
                "stress": 1.5   # Invalid high stress
            }
        }
        
        response = client.post('/api/ingest', 
                             json=invalid_payload,
                             content_type='application/json')
        
        assert response.status_code == 400
        assert 'Validation error' in response.get_json()['description']
    
    def test_missing_required_fields_rejected(self, client):
        """Test that requests missing required fields are rejected"""
        incomplete_payload = {
            "child_id": "test_child",
            # Missing timestamp and wellness_metrics
        }
        
        response = client.post('/api/ingest', 
                             json=incomplete_payload,
                             content_type='application/json')
        
        assert response.status_code == 400
    
    def test_rate_limiting_works(self, client):
        """Test that rate limiting prevents abuse"""
        valid_payload = {
            "child_id": "test_child",
            "timestamp": time.time(),
            "wellness_metrics": {"hr": 80.0, "stress": 0.3}
        }
        
        with patch('src.app.generate_embeddings_task') as mock_task:
            mock_task.delay.return_value.id = "test_task_id"
            
            # Make many requests rapidly (more than rate limit)
            responses = []
            for i in range(15):  # Rate limit is 10 per minute
                response = client.post('/api/ingest', 
                                     json=valid_payload,
                                     content_type='application/json')
                responses.append(response.status_code)
            
            # At least some requests should be rate limited
            assert 429 in responses
    
    def test_task_status_endpoint(self, client):
        """Test the task status endpoint"""
        # First create a task
        valid_payload = {
            "child_id": "test_child",
            "timestamp": time.time(),
            "wellness_metrics": {"hr": 80.0, "stress": 0.3}
        }
        
        with patch('src.app.generate_embeddings_task') as mock_task:
            mock_result = Mock()
            mock_result.id = "test_task_id"
            mock_result.status = "SUCCESS"
            mock_result.ready.return_value = True
            mock_result.successful.return_value = True
            mock_result.result = {"status": "success", "duration": 0.5}
            
            mock_task.delay.return_value = mock_result
            mock_task.AsyncResult.return_value = mock_result
            
            # Submit task
            response = client.post('/api/ingest', 
                                 json=valid_payload,
                                 content_type='application/json')
            
            assert response.status_code == 201
            task_id = json.loads(response.data)['task_id']
            
            # Check task status
            status_response = client.get(f'/api/ingest/status/{task_id}')
            assert status_response.status_code == 200
            
            status_data = json.loads(status_response.data)
            assert status_data['task_id'] == task_id
            assert status_data['status'] == 'SUCCESS'
            assert status_data['ready'] is True
    
    def test_health_endpoint_accessible(self, client):
        """Test that health endpoint is accessible"""
        with patch('src.observability.check_weaviate_health') as mock_weaviate, \
             patch('src.observability.check_redis_health') as mock_redis, \
             patch('src.observability.check_celery_health') as mock_celery:
            
            mock_weaviate.return_value = {"status": "healthy"}
            mock_redis.return_value = {"status": "healthy"}
            mock_celery.return_value = {"status": "healthy"}
            
            response = client.get('/health')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['status'] == 'healthy'
            assert 'services' in data
    
    def test_metrics_endpoint_accessible(self, client):
        """Test that metrics endpoint is accessible"""
        response = client.get('/metrics')
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'text/plain; version=0.0.4; charset=utf-8'
    
    def test_sanitization_works_end_to_end(self, client):
        """Test that input sanitization works in the full pipeline"""
        malicious_payload = {
            "child_id": "test_child",
            "timestamp": time.time(),
            "wellness_metrics": {"hr": 80.0, "stress": 0.3},
            "interaction": {
                "event": "<script>alert('xss')</script><img src=x onerror=alert(1)>Safe text"
            },
            "context": {
                "school_events": "<svg onload=alert(1)>Math test</svg>"
            }
        }
        
        with patch('src.app.generate_embeddings_task') as mock_task:
            mock_task.delay.return_value.id = "test_task_id"
            
            response = client.post('/api/ingest', 
                                 json=malicious_payload,
                                 content_type='application/json')
            
            assert response.status_code == 201
            
            # Check that sanitized data was passed to the task
            called_args = mock_task.delay.call_args[1]
            sanitized_data = called_args['data']
            
            # Verify malicious content was removed
            assert '<script>' not in sanitized_data['interaction']['event']
            assert 'onerror=' not in sanitized_data['interaction']['event']
            assert '<svg' not in sanitized_data['context']['school_events']
            
            # Verify safe content was preserved
            assert 'Safe text' in sanitized_data['interaction']['event']
            assert 'Math test' in sanitized_data['context']['school_events']
    
    def test_duplicate_prevention_integration(self, client):
        """Test duplicate prevention works in integration"""
        payload = {
            "child_id": "test_child",
            "timestamp": 1234567890,  # Fixed timestamp for reproducible test
            "wellness_metrics": {"hr": 80.0, "stress": 0.3}
        }
        
        with patch('src.app.generate_embeddings_task') as mock_task:
            mock_task.delay.return_value.id = "test_task_id"
            
            # Submit the same payload twice
            response1 = client.post('/api/ingest', json=payload, content_type='application/json')
            response2 = client.post('/api/ingest', json=payload, content_type='application/json')
            
            assert response1.status_code == 201
            assert response2.status_code == 201
            
            # Both should succeed at API level, but should have same idempotency key
            data1 = json.loads(response1.data)
            data2 = json.loads(response2.data)
            
            assert data1['idempotency_key'] == data2['idempotency_key']
            # Both should queue tasks (idempotency handled at task level)
            assert mock_task.delay.call_count == 2


class TestRAGPipelineStressTest:
    """Stress tests for the RAG pipeline"""
    
    @pytest.fixture
    def app(self):
        """Create a test Flask app"""
        from src.app import app, db
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['CELERY_TASK_ALWAYS_EAGER'] = True
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture
    def client(self, app):
        """Create a test client"""
        return app.test_client()
    
    def test_concurrent_requests_handling(self, client):
        """Test handling of concurrent requests"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            payload = {
                "child_id": f"child_{threading.current_thread().ident}",
                "timestamp": time.time(),
                "wellness_metrics": {"hr": 80.0, "stress": 0.3}
            }
            
            with patch('src.app.generate_embeddings_task') as mock_task:
                mock_task.delay.return_value.id = f"task_{threading.current_thread().ident}"
                
                response = client.post('/api/ingest', json=payload, content_type='application/json')
                results.put(response.status_code)
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that all requests succeeded
        status_codes = []
        while not results.empty():
            status_codes.append(results.get())
        
        # Most requests should succeed (some might be rate limited)
        success_count = sum(1 for code in status_codes if code == 201)
        assert success_count >= 3  # At least 3 out of 5 should succeed
    
    def test_large_payload_handling(self, client):
        """Test handling of large payloads within limits"""
        large_payload = {
            "child_id": "test_child",
            "timestamp": time.time(),
            "wellness_metrics": {"hr": 80.0, "stress": 0.3},
            "interaction": {
                "event": "A" * 400  # Near the 500 character limit
            },
            "context": {
                "school_events": "B" * 150  # Near the 200 character limit
            }
        }
        
        with patch('src.app.generate_embeddings_task') as mock_task:
            mock_task.delay.return_value.id = "test_task_id"
            
            response = client.post('/api/ingest', json=large_payload, content_type='application/json')
            assert response.status_code == 201
    
    def test_oversized_payload_rejected(self, client):
        """Test that oversized payloads are rejected"""
        oversized_payload = {
            "child_id": "test_child",
            "timestamp": time.time(),
            "wellness_metrics": {"hr": 80.0, "stress": 0.3},
            "interaction": {
                "event": "A" * 600  # Over the 500 character limit
            }
        }
        
        response = client.post('/api/ingest', json=oversized_payload, content_type='application/json')
        assert response.status_code == 400


if __name__ == '__main__':
    pytest.main([__file__, '-v'])