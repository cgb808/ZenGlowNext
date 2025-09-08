#!/usr/bin/env python3
"""
ZenGlow RAG Manifest Generator
Creates a searchable index of all data sources for RAG retrieval system.
Integrates with sidecar metadata and weighted categorization.
"""
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
import hashlib

# --- Configuration ---

# Define the root directory to scan
SOURCE_DIRECTORY = "./data_sources" 

# Define the output file for the RAG manifest
OUTPUT_MANIFEST_FILE = "rag_manifest.jsonl"

# Define sidecar file extension
SIDECAR_SUFFIX = ".meta.json"

# Define the mapping of ZenGlow path keywords to RAG categories
# Order matters - first match wins
ZENGLOW_CATEGORY_KEYWORDS = {
    'physiological_data': ['wearables', 'sensors', 'biometric', 'heart_rate', 'sleep'],
    'behavioral_feedback': ['ai_pet', 'pet_feedback', 'behavior', 'interaction'],
    'parental_insights': ['parent_dashboard', 'medication', 'supplements', 'food_intake'],
    'child_self_report': ['child_app', 'mood', 'feelings', 'self_report'],
    'environmental_context': ['environmental', 'ambient', 'weather', 'noise'],
    'development_knowledge': ['development', 'code', 'best_practices', 'ui_implementations'],
    'operational_knowledge': ['operational', 'deployment', 'monitoring', 'infrastructure'],
    'professional_knowledge': ['professional', 'research', 'clinical', 'guidelines'],
    'wellness_analytics': ['wellness', 'mhealth', 'analytics', 'study'],
    'healthcare_ai': ['healthcare', 'medical_ai', 'diagnosis'],
    'zenglow_vision': ['vision', 'ecosystem', 'architecture', 'philosophy']
}

# RAG-specific weight mappings for different content types
RAG_WEIGHT_MODIFIERS = {
    'production-ready': 1.5,
    'reviewed': 1.3,
    'analyzed': 1.2,
    'draft': 0.8,
    'deprecated': 0.3,
    'experimental': 0.7
}

# --- Utility Functions ---

def load_sidecar_metadata(file_path: Path) -> Optional[Dict[str, Any]]:
    """Load sidecar metadata if it exists"""
    sidecar_path = file_path.with_suffix(file_path.suffix + SIDECAR_SUFFIX)
    
    if not sidecar_path.exists():
        return None
    
    try:
        with open(sidecar_path, 'r') as f:
            content = json.load(f)
            return content if isinstance(content, dict) else None
    except Exception as e:
        print(f"⚠️  Error reading sidecar {sidecar_path}: {e}")
        return None

def calculate_content_hash(file_path: Path) -> str:
    """Generate content hash for deduplication"""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except (OSError, FileNotFoundError):
        return ""

def extract_text_preview(file_path: Path, max_chars: int = 500) -> str:
    """Extract text preview for RAG context"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read(max_chars)
            # Clean up the preview
            preview = content.replace('\n', ' ').replace('\r', ' ')
            preview = ' '.join(preview.split())  # Normalize whitespace
            return preview + "..." if len(content) >= max_chars else preview
    except (UnicodeDecodeError, OSError):
        return "[Binary or unreadable content]"

def categorize_file_for_rag(file_path: Path, sidecar_data: Optional[Dict[str, Any]] = None) -> str:
    """
    Assigns a RAG category to a file based on path and sidecar metadata
    """
    # First check sidecar for explicit category
    if sidecar_data and 'content_type' in sidecar_data:
        content_type = sidecar_data['content_type']
        # Map common content types to our categories
        content_type_mapping = {
            'development_guidelines': 'development_knowledge',
            'ui_implementation': 'development_knowledge',
            'sleep_analysis': 'physiological_data',
            'mood_tracking': 'child_self_report',
            'behavioral_observation': 'behavioral_feedback'
        }
        if content_type in content_type_mapping:
            return content_type_mapping[content_type]
    
    # Then check path components
    path_parts = {part.lower() for part in file_path.parts}
    
    for category, keywords in ZENGLOW_CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in path_parts or keyword in str(file_path).lower():
                return category
    
    # Fallback based on file extensions
    extension_mapping = {
        '.py': 'development_knowledge',
        '.tsx': 'development_knowledge', 
        '.jsx': 'development_knowledge',
        '.ts': 'development_knowledge',
        '.js': 'development_knowledge',
        '.md': 'development_knowledge',
        '.json': 'operational_knowledge',
        '.yaml': 'operational_knowledge',
        '.yml': 'operational_knowledge',
        '.txt': 'professional_knowledge',
        '.csv': 'wellness_analytics'
    }
    
    if file_path.suffix in extension_mapping:
        return extension_mapping[file_path.suffix]
    
    return "general"

def calculate_rag_weight(file_path: Path, sidecar_data: Optional[Dict[str, Any]], base_weight: float = 1.0) -> float:
    """Calculate RAG retrieval weight based on metadata and content type"""
    weight = base_weight
    
    if sidecar_data:
        # Apply weight modifier from sidecar
        if 'weight_modifier' in sidecar_data:
            try:
                weight *= float(sidecar_data['weight_modifier'])
            except (ValueError, TypeError):
                pass
        
        # Apply status-based modifiers
        status = sidecar_data.get('status', '').lower()
        if status in RAG_WEIGHT_MODIFIERS:
            weight *= RAG_WEIGHT_MODIFIERS[status]
        
        # Boost based on tags
        tags = sidecar_data.get('tags', [])
        if isinstance(tags, list):
            # Boost for important tags
            important_tags = {'production-ready', 'reviewed', 'critical', 'best-practices'}
            tag_boost = len([tag for tag in tags if tag.lower() in important_tags]) * 0.1
            weight += tag_boost
    
    # File type modifiers
    if file_path.suffix in ['.md', '.txt']:
        weight *= 1.1  # Boost for documentation
    elif file_path.suffix in ['.py', '.tsx', '.jsx']:
        weight *= 1.2  # Boost for code examples
    
    return round(weight, 3)

def extract_keywords_for_rag(file_path: Path, sidecar_data: Optional[Dict[str, Any]], content_preview: str) -> List[str]:
    """Extract searchable keywords for RAG retrieval"""
    keywords: set[str] = set()
    
    # Add path components
    keywords.update(part.lower() for part in file_path.parts)
    keywords.add(file_path.stem.lower())
    
    # Add sidecar tags
    if sidecar_data:
        if 'tags' in sidecar_data and isinstance(sidecar_data['tags'], list):
            keywords.update(str(tag).lower() for tag in sidecar_data['tags'])
        
        # Add other metadata fields as keywords
        for field in ['author', 'status', 'content_type', 'category']:
            if field in sidecar_data:
                value = str(sidecar_data[field]).lower()
                keywords.add(value)
    
    # Extract keywords from content preview (simple approach)
    import re
    content_words = re.findall(r'\b[a-zA-Z]{3,}\b', content_preview.lower())
    # Add frequent words as keywords (basic approach)
    word_counts: dict[str, int] = {}
    for word in content_words:
        word_counts[word] = word_counts.get(word, 0) + 1
    
    # Add words that appear more than once
    frequent_words = [word for word, count in word_counts.items() if count > 1]
    keywords.update(frequent_words[:10])  # Limit to top 10
    
    return sorted(list(keywords))

# --- Main Script Logic ---

def create_rag_manifest(root_dir: str, output_file: str) -> None:
    """
    Crawls ZenGlow data sources and creates a RAG-optimized manifest
    """
    print(f"🚀 Starting RAG manifest generation for: '{root_dir}'")
    file_count = 0
    processed_hashes = set()  # For deduplication
    
    # RAG-specific supported extensions
    supported_extensions = {
        '.txt', '.md', '.json', '.yaml', '.yml', '.csv',
        '.py', '.tsx', '.jsx', '.ts', '.js'
    }
    
    with open(output_file, 'w') as f:
        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filenames:
                full_path = Path(dirpath) / filename
                
                # Skip dotfiles and sidecar files
                if filename.startswith('.') or filename.endswith(SIDECAR_SUFFIX):
                    continue
                
                # Only process supported file types
                if full_path.suffix not in supported_extensions:
                    continue
                
                try:
                    # Get file metadata
                    file_stat = full_path.stat()
                    
                    # Load sidecar metadata
                    sidecar_data = load_sidecar_metadata(full_path)
                    
                    # Calculate content hash for deduplication
                    content_hash = calculate_content_hash(full_path)
                    if content_hash in processed_hashes:
                        print(f"⚠️ Skipping duplicate content: {full_path}")
                        continue
                    processed_hashes.add(content_hash)
                    
                    # Extract content preview
                    content_preview = extract_text_preview(full_path)
                    
                    # Create comprehensive RAG record
                    rag_record = {
                        # Core file information
                        "file_path": str(full_path),
                        "file_name": filename,
                        "relative_path": str(full_path.relative_to(Path(root_dir))),
                        "file_extension": full_path.suffix,
                        
                        # RAG categorization
                        "category": categorize_file_for_rag(full_path, sidecar_data),
                        "rag_weight": calculate_rag_weight(full_path, sidecar_data),
                        "keywords": extract_keywords_for_rag(full_path, sidecar_data, content_preview),
                        
                        # Content information
                        "content_preview": content_preview,
                        "content_hash": content_hash,
                        "size_kb": round(file_stat.st_size / 1024, 2),
                        "size_bytes": file_stat.st_size,
                        
                        # Temporal information
                        "modified_time": file_stat.st_mtime,
                        "modified_datetime": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                        "indexed_datetime": datetime.now().isoformat(),
                        
                        # Sidecar metadata (if available)
                        "sidecar_metadata": sidecar_data or {},
                        
                        # RAG-specific fields
                        "retrievable": True,
                        "chunk_ready": full_path.suffix in {'.txt', '.md'},
                        "code_content": full_path.suffix in {'.py', '.tsx', '.jsx', '.ts', '.js'},
                        "documentation": full_path.suffix in {'.md', '.txt'} and 'docs' in str(full_path).lower()
                    }
                    
                    # Write the RAG record
                    f.write(json.dumps(rag_record) + '\n')
                    file_count += 1
                    
                    if file_count % 10 == 0:
                        print(f"📊 Processed {file_count} files...")

                except (FileNotFoundError, PermissionError) as e:
                    print(f"⚠️ Could not access file {full_path}. Error: {e}")

    print(f"✅ RAG manifest complete. Indexed {file_count} files in '{output_file}'.")
    
    # Generate summary statistics
    generate_manifest_summary(output_file)

def generate_manifest_summary(manifest_file: str) -> None:
    """Generate summary statistics for the RAG manifest"""
    categories = {}
    total_weight = 0
    total_size = 0
    
    try:
        with open(manifest_file, 'r') as f:
            for line in f:
                record = json.loads(line.strip())
                category = record['category']
                weight = record['rag_weight']
                size = record['size_kb']
                
                if category not in categories:
                    categories[category] = {'count': 0, 'total_weight': 0, 'total_size': 0}
                
                categories[category]['count'] += 1
                categories[category]['total_weight'] += weight
                categories[category]['total_size'] += size
                
                total_weight += weight
                total_size += size
        
        print(f"\n📊 RAG Manifest Summary:")
        print(f"Total files: {sum(cat['count'] for cat in categories.values())}")
        print(f"Total weight: {total_weight:.2f}")
        print(f"Total size: {total_size:.2f} KB")
        print(f"\nBy category:")
        
        for category, stats in sorted(categories.items()):
            avg_weight = stats['total_weight'] / stats['count']
            print(f"  {category}: {stats['count']} files, avg weight: {avg_weight:.2f}")
            
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"⚠️ Could not generate summary: {e}")

if __name__ == "__main__":
    # Ensure the source directory exists
    if not Path(SOURCE_DIRECTORY).is_dir():
        print(f"❌ Error: Source directory '{SOURCE_DIRECTORY}' not found.")
        print("🔧 Please ensure ZenGlow data sources are properly set up.")
        exit(1)
        
    create_rag_manifest(SOURCE_DIRECTORY, OUTPUT_MANIFEST_FILE)
