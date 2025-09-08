# ai_service/main.py
"""
ZenDexer AI Service v4.0
Advanced RAG-compatible content processing service with vector embeddings.
"""

import os
import logging
import asyncio
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
import uvicorn

# Vector and AI libraries
try:
    import openai
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    print("Warning: sentence-transformers not installed. Using fallback embeddings.")

try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False
    print("Warning: chromadb not installed. Using in-memory vector store.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === CONFIGURATION ===
class Config:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.vector_db_path = os.getenv("VECTOR_DB_PATH", "./vector_db")
        self.max_chunk_size = int(os.getenv("MAX_CHUNK_SIZE", "8000"))
        self.similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.8"))
        self.batch_size = int(os.getenv("BATCH_SIZE", "10"))
        
config = Config()

# ...existing code...
