#!/usr/bin/env python3
"""
Enhanced ZenGlow Data Intake System with Sidecar Metadata Support
Processes data sources with configurable weights and metadata enrichment.
"""
import argparse
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import redis  # type: ignore
import msgpack  # type: ignore
import yaml  # type: ignore

# Default configuration
REDIS_HOST_DEFAULT = "localhost"
REDIS_PORT_DEFAULT = 6379
CHUNK_SENTENCES_DEFAULT = 3
CONFIG_FILE_DEFAULT = "data_sources/data_source_config.yaml"
SIDECAR_SUFFIX = ".meta.json"  # Sidecar file extension

class DataSourceConfig:
    """Manages data source configuration and weights"""
    
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_file, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"⚠️  Config file not found: {self.config_file}, using defaults")
            return self._default_config()
        except yaml.YAMLError as e:
            print(f"⚠️  Error parsing config file: {e}, using defaults")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            'data_sources': {},
            'global_settings': {
                'default_chunk_sentences': 3,
                'default_weight': 0.5,
                'supported_extensions': ['.txt', '.md', '.json']
            }
        }
    
    def get_source_config(self, source_path: Path) -> Dict[str, Any]:
        """Get configuration for a specific data source path"""
        # Try to match path segments to configured data sources
        path_parts = [p.lower() for p in source_path.parts]
        
        for source_name, source_config in self.config.get('data_sources', {}).items():
            if source_name.lower() in path_parts:
                return source_config
        
        # Return default configuration
        global_settings = self.config.get('global_settings', {})
        return {
            'weight': global_settings.get('default_weight', 0.5),
            'category': 'general',
            'chunk_sentences': global_settings.get('default_chunk_sentences', 3),
            'priority': 'medium',
            'description': 'General data source'
        }

def find_and_load_sidecar(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Looks for a corresponding .meta.json sidecar file and loads it if it exists.
    
    Args:
        file_path: The Path object for the source file.
        
    Returns:
        A dictionary with the sidecar data, or None if no sidecar is found.
    """
    sidecar_path = file_path.with_suffix(file_path.suffix + SIDECAR_SUFFIX)
    
    if sidecar_path.is_file():
        try:
            with open(sidecar_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️  Warning: Could not decode JSON from sidecar: {sidecar_path}")
        except Exception as e:
            print(f"⚠️  Warning: Could not read sidecar file {sidecar_path}. Error: {e}")
    return None

def chunk_text(text: str, sentences_per_chunk: int = 3) -> List[str]:
    """Split text into chunks of approximately N sentences"""
    # Simple sentence splitting - could be enhanced with proper NLP
    import re
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    chunks = []
    for i in range(0, len(sentences), sentences_per_chunk):
        chunk = '. '.join(sentences[i:i + sentences_per_chunk])
        if chunk:
            chunks.append(chunk + '.')
    
    return chunks if chunks else [text]

def create_enhanced_payload(
    chunk_id: str,
    text: str,
    source_file: str,
    category: str,
    weight: float,
    source_config: Dict[str, Any],
    sidecar_metadata: Optional[Dict[str, Any]] = None,
    file_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create enriched payload with metadata and weights"""
    payload = {
        'chunk_id': chunk_id,
        'text': text,
        'source_file': source_file,
        'category': category,
        'weight': weight,
        'priority': source_config.get('priority', 'medium'),
        'description': source_config.get('description', ''),
        'timestamp': time.time(),
        'source_config': {
            'retention_days': source_config.get('retention_days', 90),
            'chunk_sentences': source_config.get('chunk_sentences', 3)
        }
    }
    
    # Add sidecar metadata if available
    if sidecar_metadata:
        payload['sidecar_metadata'] = sidecar_metadata
    
    # Add file metadata if available
    if file_metadata:
        payload['file_metadata'] = file_metadata
    
    return payload

def push_file_enhanced(
    path: Path,
    redis_client: redis.Redis,  # type: ignore[name-defined]
    queue_key: str,
    config: DataSourceConfig
) -> int:
    """Enhanced file processing with metadata and configuration support"""
    
    # Get source configuration
    source_config = config.get_source_config(path)
    chunk_sentences = source_config.get('chunk_sentences', CHUNK_SENTENCES_DEFAULT)
    weight = source_config.get('weight', 0.5)
    category = source_config.get('category', 'general')
    
    # Load sidecar metadata
    sidecar_metadata = find_and_load_sidecar(path)
    
    # Collect file metadata
    try:
        stat = path.stat()
        file_metadata = {
            'size_bytes': stat.st_size,
            'modified_time': stat.st_mtime,
            'file_extension': path.suffix,
            'full_path': str(path.absolute())
        }
    except (OSError, FileNotFoundError):
        file_metadata = {'full_path': str(path)}
    
    # Read and process file content
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (UnicodeDecodeError, OSError) as e:
        print(f"⚠️  Could not read {path.name}: {e}")
        return 0
    
    if not content.strip():
        return 0
    
    # Create chunks
    chunks = chunk_text(content, chunk_sentences)
    
    # Push chunks to Redis
    count = 0
    for i, chunk in enumerate(chunks):
        chunk_id = f"{path.stem}_{i+1}"
        
        payload = create_enhanced_payload(
            chunk_id=chunk_id,
            text=chunk,
            source_file=path.name,
            category=category,
            weight=weight,
            source_config=source_config,
            sidecar_metadata=sidecar_metadata,
            file_metadata=file_metadata
        )
        
        try:
            redis_client.rpush(queue_key, msgpack.packb(payload))
            count += 1
        except Exception as e:
            print(f"⚠️  Failed to push chunk {chunk_id}: {e}")
    
    return count

def process_data_source(
    source_path: Path,
    redis_client: redis.Redis,  # type: ignore[name-defined]
    config: DataSourceConfig,
    queue_prefix: str = "intake_queue"
) -> Dict[str, int]:
    """Process a data source directory or file"""
    
    results = {}
    
    if source_path.is_file():
        # Process single file
        source_config = config.get_source_config(source_path)
        category = source_config.get('category', 'general')
        queue_key = f"{queue_prefix}:{category}"
        
        print(f"  📄 Processing file: {source_path.name}")
        count = push_file_enhanced(source_path, redis_client, queue_key, config)
        results[category] = count
        
    elif source_path.is_dir():
        # Process directory
        supported_extensions = config.config.get('global_settings', {}).get(
            'supported_extensions', ['.txt', '.md', '.json']
        )
        
        for file_path in source_path.rglob('*'):
            # Skip sidecar files and unsupported files
            if (file_path.suffix == SIDECAR_SUFFIX or 
                file_path.suffix not in supported_extensions or
                not file_path.is_file()):
                continue
            
            source_config = config.get_source_config(file_path)
            category = source_config.get('category', 'general')
            queue_key = f"{queue_prefix}:{category}"
            
            print(f"  📄 Processing: {file_path.relative_to(source_path)}")
            count = push_file_enhanced(file_path, redis_client, queue_key, config)
            
            if category in results:
                results[category] += count
            else:
                results[category] = count
    
    return results

def main() -> None:
    parser = argparse.ArgumentParser(description='Enhanced ZenGlow data intake with metadata support')
    parser.add_argument("--source", default="data_sources", help="Source directory or file path")
    parser.add_argument("--config", default=CONFIG_FILE_DEFAULT, help="Configuration file path")
    parser.add_argument("--redis-host", default=REDIS_HOST_DEFAULT)
    parser.add_argument("--redis-port", type=int, default=REDIS_PORT_DEFAULT)
    parser.add_argument("--queue-prefix", default="intake_queue", help="Queue name prefix")
    
    args = parser.parse_args()
    
    # Load configuration
    config = DataSourceConfig(args.config)
    
    # Validate source path
    source_path = Path(args.source)
    if not source_path.exists():
        print(f"❌ Source path not found: {source_path}")
        return
    
    # Connect to Redis
    print(f"→ Connecting to Redis {args.redis_host}:{args.redis_port} ...")
    try:
        r = redis.Redis(host=args.redis_host, port=args.redis_port, db=0, decode_responses=False)  # type: ignore[call-arg]
        r.ping()
    except Exception as e:  # pragma: no cover
        print(f"❌ Redis connection failed: {e}")
        return
    
    print(f"→ Processing data source: {source_path}")
    print(f"→ Using configuration: {args.config}")
    
    # Process the data source
    results = process_data_source(source_path, r, config, args.queue_prefix)
    
    # Report results
    total_chunks = sum(results.values())
    print(f"\n✅ Processing complete!")
    print(f"📊 Results by category:")
    for category, count in sorted(results.items()):
        queue_name = f"{args.queue_prefix}:{category}"
        print(f"  {category}: {count} chunks → {queue_name}")
    print(f"📈 Total chunks processed: {total_chunks}")

if __name__ == "__main__":  # pragma: no cover
    main()
