"""
Distributed Logging Configuration

Centralized configuration for all logging microservice components.
"""
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class LoggingConfig:
    # Redis Configuration
    redis_url: str = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    redis_stream_key: str = os.getenv('LOG_STREAM_KEY', 'log_frames_stream')
    redis_channel: str = os.getenv('LOG_NOTIFICATION_CHANNEL', 'log_segments_sealed')
    redis_consumer_group: str = os.getenv('LOG_CONSUMER_GROUP', 'log_writers')
    
    # Local Storage Configuration
    log_dir: str = os.getenv('LOG_DIR', 'data/append_logs')
    max_file_size: int = int(os.getenv('LOG_MAX_SIZE', str(64 * 1024 * 1024)))  # 64MB
    max_file_age: int = int(os.getenv('LOG_MAX_AGE', '600'))  # 10 minutes
    
    # Performance Configuration
    fsync_interval: int = int(os.getenv('LOG_FSYNC_INTERVAL', '100'))
    batch_size: int = int(os.getenv('LOG_BATCH_SIZE', '10'))
    lock_timeout: float = float(os.getenv('LOG_LOCK_TIMEOUT', '5.0'))
    
    # Compression Configuration
    compression_method: Optional[str] = os.getenv('LOG_COMPRESSION', 'zstd')
    compression_level: int = int(os.getenv('LOG_COMPRESSION_LEVEL', '3'))
    remove_after_compression: bool = os.getenv('LOG_REMOVE_ORIGINAL', 'true').lower() == 'true'
    
    # Cloud Storage Configuration
    storage_bucket: str = os.getenv('SUPABASE_BUCKET_NAME', 'log-segments')
    storage_endpoint: str = os.getenv('SUPABASE_URL', '')
    storage_key: str = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
    
    # Worker Configuration
    worker_poll_interval: float = float(os.getenv('WORKER_POLL_INTERVAL', '0.1'))
    worker_retry_delay: float = float(os.getenv('WORKER_RETRY_DELAY', '5.0'))

# Global configuration instance
config = LoggingConfig()