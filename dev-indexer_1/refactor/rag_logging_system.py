#!/usr/bin/env python3
"""
Multi-Database RAG Logging System

A streamlined, cloud-native logging system optimized for RAG applications
with support for multiple specialized databases:
- Local: PII, family health, history, conversational data
- Remote: AI model interactions, fine-tuning data
- Cloud: Domain-specific data for specialized AI models
"""
from __future__ import annotations
import os
import sys
import json
import uuid
import asyncio
import time
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import msgpack
    import redis.asyncio as aioredis
    from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request
    from fastapi.middleware.cors import CORSMiddleware
    import fcntl
except ImportError as e:
    print(f"Missing required dependency: {e}", file=sys.stderr)
    raise

# === ENUMS AND TYPES ===

class DatabaseTarget(str, Enum):
    LOCAL = "local"      # PII, family health, conversational data
    REMOTE = "remote"    # AI interactions, fine-tuning data  
    CLOUD = "cloud"      # Domain-specific specialized model data

class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ContentType(str, Enum):
    CONVERSATION = "conversation"
    MODEL_INTERACTION = "model_interaction"
    RAG_CONTEXT = "rag_context"
    FINE_TUNING = "fine_tuning"
    DOMAIN_SPECIFIC = "domain_specific"
    HEALTH_DATA = "health_data"
    PII_DATA = "pii_data"

# === CONFIGURATION ===

@dataclass
class DatabaseConfig:
    url: str
    bucket_name: str
    service_key: str
    compression: str = "zstd"
    max_file_size: int = 64 * 1024 * 1024
    max_file_age: int = 600

@dataclass
class LoggingConfig:
    # Redis Configuration
    redis_url: str = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    redis_stream_key: str = os.getenv('LOG_STREAM_KEY', 'rag_log_stream')
    redis_channel: str = os.getenv('LOG_NOTIFICATION_CHANNEL', 'rag_segments_sealed')
    redis_consumer_group: str = os.getenv('LOG_CONSUMER_GROUP', 'rag_writers')
    
    # Local Storage
    log_dir: str = os.getenv('LOG_DIR', 'data/rag_logs')
    batch_size: int = int(os.getenv('LOG_BATCH_SIZE', '50'))
    
    # Database Configurations
    databases: Dict[DatabaseTarget, DatabaseConfig] = None
    
    def __post_init__(self):
        if self.databases is None:
            self.databases = {
                DatabaseTarget.LOCAL: DatabaseConfig(
                    url=os.getenv('LOCAL_SUPABASE_URL', ''),
                    bucket_name=os.getenv('LOCAL_BUCKET_NAME', 'local-rag-logs'),
                    service_key=os.getenv('LOCAL_SERVICE_KEY', '')
                ),
                DatabaseTarget.REMOTE: DatabaseConfig(
                    url=os.getenv('REMOTE_SUPABASE_URL', ''),
                    bucket_name=os.getenv('REMOTE_BUCKET_NAME', 'remote-rag-logs'),
                    service_key=os.getenv('REMOTE_SERVICE_KEY', '')
                ),
                DatabaseTarget.CLOUD: DatabaseConfig(
                    url=os.getenv('CLOUD_SUPABASE_URL', ''),
                    bucket_name=os.getenv('CLOUD_BUCKET_NAME', 'cloud-rag-logs'),
                    service_key=os.getenv('CLOUD_SERVICE_KEY', '')
                )
            }

# === CORE LOGGING FRAME ===

@dataclass
class RAGLogFrame:
    session_id: str
    user_id: str
    content_type: ContentType
    content: str
    database_targets: List[DatabaseTarget]
    
    # Optional fields
    model_name: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    response_time_ms: Optional[int] = None
    rag_sources: Optional[List[str]] = None
    domain: Optional[str] = None
    level: LogLevel = LogLevel.INFO
    metadata: Optional[Dict[str, Any]] = None
    
    # System fields (auto-populated)
    timestamp: Optional[str] = None
    seq: Optional[int] = None
    version: int = 2  # Updated version for RAG system
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(UTC).isoformat()
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RAGLogFrame':
        return cls(**data)

# === DATABASE ROUTER ===

class DatabaseRouter:
    """Routes log frames to appropriate databases based on content type and targets"""
    
    CONTENT_TYPE_ROUTING = {
        ContentType.CONVERSATION: [DatabaseTarget.LOCAL, DatabaseTarget.REMOTE],
        ContentType.PII_DATA: [DatabaseTarget.LOCAL],
        ContentType.HEALTH_DATA: [DatabaseTarget.LOCAL],
        ContentType.MODEL_INTERACTION: [DatabaseTarget.REMOTE],
        ContentType.RAG_CONTEXT: [DatabaseTarget.REMOTE],
        ContentType.FINE_TUNING: [DatabaseTarget.REMOTE],
        ContentType.DOMAIN_SPECIFIC: [DatabaseTarget.CLOUD]
    }
    
    @classmethod
    def get_targets(cls, frame: RAGLogFrame) -> List[DatabaseTarget]:
        """Determine which databases should receive this log frame"""
        # Use explicit targets if provided, otherwise use content-based routing
        if frame.database_targets:
            return frame.database_targets
        return cls.CONTENT_TYPE_ROUTING.get(frame.content_type, [DatabaseTarget.REMOTE])
    
    @classmethod
    def should_encrypt(cls, target: DatabaseTarget, content_type: ContentType) -> bool:
        """Determine if content should be encrypted for this target"""
        if target == DatabaseTarget.LOCAL and content_type in [ContentType.PII_DATA, ContentType.HEALTH_DATA]:
            return True
        return False

# === CLOUD STORAGE CLIENT ===

class MultiDatabaseStorageClient:
    """Handles uploads to multiple Supabase instances"""
    
    def __init__(self, config: LoggingConfig):
        self.config = config
        self.clients = {}
        # In production, initialize actual Supabase clients here
        for target, db_config in config.databases.items():
            print(f"[Storage] Initialized {target.value} client for bucket: {db_config.bucket_name}")
    
    async def upload(self, local_path: Path, target: DatabaseTarget, frame_metadata: Dict) -> str:
        """Upload file to specific database target"""
        db_config = self.config.databases[target]
        
        # Generate intelligent remote path based on content type and metadata
        remote_path = self._generate_remote_path(local_path, target, frame_metadata)
        
        print(f"[Storage] UPLOADING {local_path} to {target.value}://{db_config.bucket_name}/{remote_path}")
        
        # Simulate upload (replace with actual Supabase client)
        await asyncio.sleep(0.1)
        
        # Clean up local file after successful upload
        local_path.unlink(missing_ok=True)
        
        uri = f"{target.value}://{db_config.bucket_name}/{remote_path}"
        print(f"[Storage] UPLOAD complete: {uri}")
        return uri
    
    def _generate_remote_path(self, local_path: Path, target: DatabaseTarget, metadata: Dict) -> str:
        """Generate intelligent remote paths for better organization"""
        content_type = metadata.get('content_type', 'unknown')
        domain = metadata.get('domain', 'general')
        date_prefix = datetime.now(UTC).strftime('%Y/%m/%d')
        
        if target == DatabaseTarget.LOCAL:
            return f"local/{date_prefix}/{content_type}/{local_path.name}"
        elif target == DatabaseTarget.REMOTE:
            model_name = metadata.get('model_name', 'unknown_model')
            return f"remote/{date_prefix}/{model_name}/{content_type}/{local_path.name}"
        else:  # CLOUD
            return f"cloud/{date_prefix}/{domain}/{content_type}/{local_path.name}"

# === NOTIFICATION SYSTEM ===

async def notify_segment_ready(
    segment_uris: Dict[DatabaseTarget, str],
    redis_channel: str,
    batch_metadata: Dict,
    config: LoggingConfig
) -> bool:
    """Publish notification about completed log segment to all relevant targets"""
    if not redis_channel:
        for target, uri in segment_uris.items():
            print(f"[segment] sealed {target.value}: {uri}")
        return True
    
    try:
        redis_client = aioredis.from_url(config.redis_url)
        
        event_payload = {
            "eventType": "rag_log_segment_sealed",
            "segment_uris": segment_uris,
            "batch_metadata": batch_metadata,
            "timestamp": datetime.now(UTC).isoformat(),
            "producer": "rag_log_writer_v2"
        }
        
        await redis_client.publish(redis_channel, json.dumps(event_payload))
        await redis_client.close()
        
        print(f"[notify] Published multi-target event to channel '{redis_channel}'")
        return True
        
    except Exception as e:
        print(f"[notify] Redis publish failed: {e}")
        return False

# === FASTAPI INGESTION GATEWAY ===

def create_app(config: LoggingConfig = None) -> FastAPI:
    if config is None:
        config = LoggingConfig()
    
    app = FastAPI(
        title="RAG Multi-Database Logging System",
        description="High-performance logging for RAG applications with multi-database support",
        version="2.0.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Store config in app state
    app.state.config = config
    app.state.redis = None
    
    @app.on_event("startup")
    async def startup_event():
        app.state.redis = aioredis.from_url(config.redis_url)
        print("[App] Connected to Redis")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        if app.state.redis:
            await app.state.redis.close()
            print("[App] Disconnected from Redis")
    
    # Create router
    router = APIRouter(prefix="/api/v2/log", tags=["rag-logging"])
    
    async def get_redis_client(request: Request) -> aioredis.Redis:
        if hasattr(request.app.state, 'redis') and request.app.state.redis:
            return request.app.state.redis
        raise HTTPException(status_code=503, detail="Redis client not available")
    
    @router.post("/append", status_code=202)
    async def append_rag_log(
        payload: Dict[str, Any],
        redis: aioredis.Redis = Depends(get_redis_client)
    ):
        """Accept RAG log frame and route to appropriate databases"""
        try:
            # Create and validate RAG log frame
            frame = RAGLogFrame.from_dict(payload)
            
            # Determine target databases
            targets = DatabaseRouter.get_targets(frame)
            frame.database_targets = targets
            
            # Add routing metadata
            frame.metadata.update({
                'targets': [t.value for t in targets],
                'routing_timestamp': datetime.now(UTC).isoformat()
            })
            
            # Queue the frame
            packed_frame = msgpack.packb(frame.to_dict(), use_bin_type=True)
            await redis.xadd(config.redis_stream_key, {"frame": packed_frame})
            
            return {
                "status": "queued",
                "targets": [t.value for t in targets],
                "session_id": frame.session_id,
                "content_type": frame.content_type.value
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to queue RAG log: {e}")
    
    @router.get("/health")
    async def health_check():
        return {"status": "healthy", "version": "2.0.0"}
    
    @router.get("/stats")
    async def get_stats(redis: aioredis.Redis = Depends(get_redis_client)):
        """Get logging system statistics"""
        try:
            stream_info = await redis.xinfo_stream(config.redis_stream_key)
            return {
                "stream_length": stream_info.get("length", 0),
                "last_generated_id": stream_info.get("last-generated-id", "0-0"),
                "consumer_groups": stream_info.get("groups", 0)
            }
        except Exception as e:
            return {"error": str(e)}
    
    app.include_router(router)
    return app

# === WORKER PROCESSES ===

class RAGLogWorker:
    """Enhanced worker for processing RAG log frames"""
    
    def __init__(self, config: LoggingConfig):
        self.config = config
        self.consumer_name = f"rag_writer_{os.getpid()}"
        self.storage_client = MultiDatabaseStorageClient(config)
    
    async def process_messages(self):
        """Main worker loop for processing log frames"""
        redis_client = aioredis.from_url(self.config.redis_url)
        
        # Ensure consumer group exists
        try:
            await redis_client.xgroup_create(
                self.config.redis_stream_key, 
                self.config.redis_consumer_group, 
                id='0', 
                mkstream=True
            )
        except Exception as e:
            if "name already exists" not in str(e).lower():
                raise
        
        print(f"[{self.consumer_name}] Starting RAG log processing...")
        
        while True:
            try:
                response = await redis_client.xreadgroup(
                    self.config.redis_consumer_group,
                    self.consumer_name,
                    {self.config.redis_stream_key: '>'},
                    count=self.config.batch_size,
                    block=0
                )
                
                if not response:
                    continue
                
                for stream, messages in response:
                    batch_frames = []
                    message_ids = []
                    
                    for message_id, fields in messages:
                        frame_data = fields.get(b'frame')
                        if not frame_data:
                            continue
                        
                        frame_dict = msgpack.unpackb(frame_data, raw=False)
                        frame = RAGLogFrame.from_dict(frame_dict)
                        batch_frames.append(frame)
                        message_ids.append(message_id)
                    
                    # Process batch
                    if batch_frames:
                        await self._process_frame_batch(batch_frames)
                        
                        # Acknowledge all messages
                        for msg_id in message_ids:
                            await redis_client.xack(
                                self.config.redis_stream_key,
                                self.config.redis_consumer_group,
                                msg_id
                            )
                        
                        print(f"[{self.consumer_name}] Processed batch of {len(batch_frames)} frames")
            
            except Exception as e:
                print(f"[{self.consumer_name}] Error: {e}")
                await asyncio.sleep(5)
        
        await redis_client.close()
    
    async def _process_frame_batch(self, frames: List[RAGLogFrame]):
        """Process a batch of RAG log frames"""
        # Group frames by target databases for efficient processing
        target_groups = {}
        
        for frame in frames:
            for target in frame.database_targets:
                if target not in target_groups:
                    target_groups[target] = []
                target_groups[target].append(frame)
        
        # Process each target group
        for target, target_frames in target_groups.items():
            try:
                await self._write_frames_to_target(target, target_frames)
            except Exception as e:
                print(f"[{self.consumer_name}] Error writing to {target.value}: {e}")
    
    async def _write_frames_to_target(self, target: DatabaseTarget, frames: List[RAGLogFrame]):
        """Write frames to a specific database target"""
        # Create target-specific log file
        timestamp = int(time.time() * 1000)
        log_file = Path(self.config.log_dir) / f"{target.value}_batch_{timestamp}.jsonl"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write frames to file
        with log_file.open('w') as f:
            for frame in frames:
                json.dump(frame.to_dict(), f, default=str)
                f.write('\n')
        
        # Upload to appropriate storage
        try:
            metadata = {
                'target': target.value,
                'frame_count': len(frames),
                'content_types': list(set(f.content_type.value for f in frames))
            }
            
            uri = await self.storage_client.upload(log_file, target, metadata)
            print(f"[{self.consumer_name}] Uploaded {len(frames)} frames to {target.value}: {uri}")
            
        except Exception as e:
            print(f"[{self.consumer_name}] Upload failed for {target.value}: {e}")

# === MAIN EXECUTION ===

async def run_worker():
    """Run the RAG log worker"""
    config = LoggingConfig()
    worker = RAGLogWorker(config)
    await worker.process_messages()

def run_server():
    """Run the FastAPI server"""
    import uvicorn
    config = LoggingConfig()
    app = create_app(config)
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "worker":
        asyncio.run(run_worker())
    else:
        run_server()