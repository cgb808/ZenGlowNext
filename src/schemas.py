"""
Pydantic schemas for input validation in the ZenGlow RAG pipeline
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, Any
from datetime import datetime
import re


class UserProfileSchema(BaseModel):
    """User profile data schema"""
    age: Optional[int] = Field(None, ge=6, le=12, description="Child's age between 6-12")


class ContextSchema(BaseModel):
    """Context data schema"""
    user_profile: Optional[UserProfileSchema] = None
    school_events: Optional[str] = Field(None, max_length=200, description="School events description")

    @field_validator('school_events')
    @classmethod
    def sanitize_school_events(cls, v):
        if v is None:
            return v
        # Remove HTML/XML tags and limit length
        sanitized = re.sub(r'<[^>]+>', '', str(v))
        return sanitized[:200] if len(sanitized) > 200 else sanitized


class InteractionSchema(BaseModel):
    """Interaction event schema"""
    event: Optional[str] = Field(None, max_length=500, description="Interaction event description")

    @field_validator('event')
    @classmethod
    def sanitize_event(cls, v):
        if v is None:
            return v
        # Remove HTML/XML tags and potentially harmful content
        sanitized = re.sub(r'<[^>]+>', '', str(v))
        # Remove script-like content
        sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'on\w+\s*=', '', sanitized, flags=re.IGNORECASE)
        return sanitized[:500] if len(sanitized) > 500 else sanitized


class WellnessMetricsSchema(BaseModel):
    """Wellness metrics schema with validation"""
    hr: float = Field(..., ge=30, le=200, description="Heart rate in BPM")
    stress: float = Field(..., ge=0.0, le=1.0, description="Stress level between 0-1")
    sleep_duration: Optional[float] = Field(0, ge=0, le=86400, description="Sleep duration in seconds")
    sleep_state: Optional[str] = Field('awake', pattern=r'^(awake|light|deep|REM)$', description="Sleep state")


class IngestDataSchema(BaseModel):
    """Main schema for data ingestion endpoint"""
    child_id: str = Field(..., min_length=1, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$', 
                         description="Child identifier")
    timestamp: float = Field(..., gt=0, description="Unix timestamp")
    wellness_metrics: WellnessMetricsSchema
    context: Optional[ContextSchema] = None
    interaction: Optional[InteractionSchema] = None

    @field_validator('child_id')
    @classmethod
    def sanitize_child_id(cls, v):
        # Remove any potential harmful characters
        return re.sub(r'[^a-zA-Z0-9_-]', '', v)

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v):
        # Ensure timestamp is reasonable (not too far in past/future)
        now = datetime.now().timestamp()
        # Allow timestamps within 1 year of current time
        if abs(now - v) > 365 * 24 * 3600:
            raise ValueError("Timestamp is too far from current time")
        return v

    @model_validator(mode='after')
    def validate_complete_data(self):
        """Ensure we have minimum required data for meaningful embedding"""
        if not self.child_id or not self.wellness_metrics:
            raise ValueError("child_id and wellness_metrics are required")
        
        return self

    def get_idempotency_key(self) -> str:
        """Generate idempotency key from child_id and timestamp"""
        return f"{self.child_id}_{int(self.timestamp)}"