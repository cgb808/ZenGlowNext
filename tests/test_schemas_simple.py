"""
Simple unit test for Pydantic schemas
"""
import pytest
import time
from pydantic import ValidationError

def test_schemas_import():
    """Test that schemas can be imported without errors"""
    from src.schemas import IngestDataSchema, WellnessMetricsSchema
    assert IngestDataSchema is not None
    assert WellnessMetricsSchema is not None

def test_valid_wellness_metrics():
    """Test valid wellness metrics validation"""
    from src.schemas import WellnessMetricsSchema
    
    valid_data = {
        "hr": 80.0,
        "stress": 0.3,
        "sleep_duration": 28800,
        "sleep_state": "deep"
    }
    
    schema = WellnessMetricsSchema(**valid_data)
    assert schema.hr == 80.0
    assert schema.stress == 0.3
    assert schema.sleep_state == "deep"

def test_invalid_heart_rate():
    """Test that invalid heart rate is rejected"""
    from src.schemas import WellnessMetricsSchema
    
    invalid_data = {
        "hr": 300.0,  # Too high
        "stress": 0.3
    }
    
    with pytest.raises(ValidationError):
        WellnessMetricsSchema(**invalid_data)

def test_valid_ingest_data():
    """Test complete valid ingest data"""
    from src.schemas import IngestDataSchema
    
    valid_data = {
        "child_id": "test_child_123",
        "timestamp": time.time(),
        "wellness_metrics": {
            "hr": 80.0,
            "stress": 0.3,
            "sleep_duration": 28800,
            "sleep_state": "deep"
        }
    }
    
    schema = IngestDataSchema(**valid_data)
    assert schema.child_id == "test_child_123"
    assert schema.wellness_metrics.hr == 80.0

def test_idempotency_key():
    """Test idempotency key generation"""
    from src.schemas import IngestDataSchema
    
    # Use current timestamp to avoid validation error
    timestamp = time.time()
    data = {
        "child_id": "test_child",
        "timestamp": timestamp,
        "wellness_metrics": {"hr": 80.0, "stress": 0.3}
    }
    
    schema = IngestDataSchema(**data)
    expected_key = f"test_child_{int(timestamp)}"
    assert schema.get_idempotency_key() == expected_key

if __name__ == '__main__':
    pytest.main([__file__, '-v'])