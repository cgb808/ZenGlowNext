#!/usr/bin/env python3
"""
RAG Multi-Database Logging Client SDK

A comprehensive client SDK for integrating with the RAG logging system.
Provides easy-to-use interfaces for different types of logging scenarios.
"""
from __future__ import annotations
import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
from contextlib import asynccontextmanager

# === CONFIGURATION ===

@dataclass
class ClientConfig:
    base_url: str = "http://localhost:8000"
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    batch_size: int = 10
    flush_interval: float = 5.0
    auto_flush: bool = True
    
    # Authentication (if needed)
    api_key: Optional[str] = None
    
    def get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

# === LOGGING CONTEXTS ===

class LoggingContext:
    """Context manager for automatic session and user tracking"""
    
    def __init__(self, client: 'RAGLogClient', session_id: str = None, user_id: str = None):
        self.client = client
        self.session_id = session_id or str(uuid.uuid4())
        self.user_id = user_id
        self._original_session = None
        self._original_user = None
    
    def __enter__(self):
        self._original_session = getattr(self.client, '_current_session_id', None)
        self._original_user = getattr(self.client, '_current_user_id', None)
        self.client._current_session_id = self.session_id
        self.client._current_user_id = self.user_id
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client._current_session_id = self._original_session
        self.client._current_user_id = self._original_user

class ModelInteractionContext:
    """Context manager for tracking complete model interactions"""
    
    def __init__(self, client: 'RAGLogClient', model_name: str, session_id: str = None, user_id: str = None):
        self.client = client
        self.model_name = model_name
        self.session_id = session_id or getattr(client, '_current_session_id', None) or str(uuid.uuid4())
        self.user_id = user_id or getattr(client, '_current_user_id', None)
        self.start_time = None
        self.rag_sources = []
        self.metadata = {}
    
    async def __aenter__(self):
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:  # Only log successful interactions
            response_time_ms = int((time.time() - self.start_time) * 1000)
            await self.client.log_model_interaction(
                session_id=self.session_id,
                user_id=self.user_id,
                model_name=self.model_name,
                prompt=getattr(self, 'prompt', ''),
                response=getattr(self, 'response', ''),
                response_time_ms=response_time_ms,
                rag_sources=self.rag_sources,
                metadata=self.metadata
            )
    
    def add_rag_source(self, source: str, relevance_score: float = None):
        """Add a RAG source that was used in this interaction"""
        if relevance_score is not None:
            self.rag_sources.append({"source": source, "score": relevance_score})
        else:
            self.rag_sources.append(source)
    
    def set_prompt(self, prompt: str):
        """Set the prompt for this interaction"""
        self.prompt = prompt
    
    def set_response(self, response: str):
        """Set the response for this interaction"""
        self.response = response
    
    def add_metadata(self, key: str, value: Any):
        """Add metadata to this interaction"""
        self.metadata[key] = value

# === MAIN CLIENT ===

class RAGLogClient:
    """
    Main client for the RAG Multi-Database Logging System
    
    Supports:
    - Synchronous and asynchronous logging
    - Batching and auto-flushing
    - Context managers for session tracking
    - Specialized logging methods for different content types
    - Automatic retry logic
    """
    
    def __init__(self, config: ClientConfig = None):
        self.config = config or ClientConfig()
        self.api_base = f"{self.config.base_url.rstrip('/')}/api/v2/log"
        
        # Internal state
        self._session = None
        self._batch = []
        self._last_flush = time.time()
        self._flush_task = None
        self._current_session_id = None
        self._current_user_id = None
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
    
    async def start(self):
        """Initialize the client"""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            headers=self.config.get_headers()
        )
        
        if self.config.auto_flush:
            self._start_auto_flush()
        
        self.logger.info("RAG Log Client started")
    
    async def stop(self):
        """Cleanup the client"""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        await self.flush()  # Final flush
        
        if self._session:
            await self._session.close()
        
        self.logger.info("RAG Log Client stopped")
    
    def _start_auto_flush(self):
        """Start the auto-flush background task"""
        async def auto_flush_loop():
            while True:
                try:
                    await asyncio.sleep(self.config.flush_interval)
                    if self._batch and time.time() - self._last_flush >= self.config.flush_interval:
                        await self.flush()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Auto-flush error: {e}")
        
        self._flush_task = asyncio.create_task(auto_flush_loop())
    
    # === CONTEXT MANAGERS ===
    
    def session(self, session_id: str = None, user_id: str = None) -> LoggingContext:
        """Create a logging context with session and user tracking"""
        return LoggingContext(self, session_id, user_id)
    
    def model_interaction(self, model_name: str, session_id: str = None, user_id: str = None) -> ModelInteractionContext:
        """Create a context for tracking a complete model interaction"""
        return ModelInteractionContext(self, model_name, session_id, user_id)
    
    # === CORE LOGGING METHODS ===
    
    async def log_conversation(
        self,
        content: str,
        session_id: str = None,
        user_id: str = None,
        metadata: Dict[str, Any] = None,
        immediate: bool = False
    ) -> Dict[str, Any]:
        """Log a conversation entry"""
        payload = {
            "session_id": session_id or self._current_session_id or str(uuid.uuid4()),
            "user_id": user_id or self._current_user_id or "anonymous",
            "content_type": "conversation",
            "content": content,
            "database_targets": ["local", "remote"],
            "metadata": metadata or {}
        }
        return await self._send_log(payload, immediate)
    
    async def log_model_interaction(
        self,
        model_name: str,
        prompt: str = "",
        response: str = "",
        session_id: str = None,
        user_id: str = None,
        prompt_tokens: int = None,
        completion_tokens: int = None,
        response_time_ms: int = None,
        rag_sources: List[Union[str, Dict]] = None,
        metadata: Dict[str, Any] = None,
        immediate: bool = False
    ) -> Dict[str, Any]:
        """Log an AI model interaction"""
        content_data = {}
        if prompt:
            content_data["prompt"] = prompt
        if response:
            content_data["response"] = response
        
        payload = {
            "session_id": session_id or self._current_session_id or str(uuid.uuid4()),
            "user_id": user_id or self._current_user_id or "anonymous",
            "content_type": "model_interaction",
            "content": json.dumps(content_data),
            "model_name": model_name,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "response_time_ms": response_time_ms,
            "rag_sources": rag_sources or [],
            "database_targets": ["remote"],
            "metadata": metadata or {}
        }
        return await self._send_log(payload, immediate)
    
    async def log_rag_context(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
        context_used: str = "",
        session_id: str = None,
        user_id: str = None,
        relevance_scores: List[float] = None,
        metadata: Dict[str, Any] = None,
        immediate: bool = False
    ) -> Dict[str, Any]:
        """Log RAG context retrieval and usage"""
        payload = {
            "session_id": session_id or self._current_session_id or str(uuid.uuid4()),
            "user_id": user_id or self._current_user_id or "anonymous",
            "content_type": "rag_context",
            "content": json.dumps({
                "query": query,
                "retrieved_docs": retrieved_docs,
                "context_used": context_used,
                "relevance_scores": relevance_scores or []
            }),
            "database_targets": ["remote"],
            "metadata": metadata or {}
        }
        return await self._send_log(payload, immediate)
    
    async def log_health_data(
        self,
        health_info: Dict[str, Any],
        session_id: str = None,
        user_id: str = None,
        metadata: Dict[str, Any] = None,
        immediate: bool = True  # Health data is sensitive, send immediately
    ) -> Dict[str, Any]:
        """Log sensitive health data (local database only)"""
        payload = {
            "session_id": session_id or self._current_session_id or str(uuid.uuid4()),
            "user_id": user_id or self._current_user_id or "anonymous",
            "content_type": "health_data",
            "content": json.dumps(health_info),
            "database_targets": ["local"],  # Only local database
            "level": "info",
            "metadata": metadata or {}
        }
        return await self._send_log(payload, immediate)
    
    async def log_pii_data(
        self,
        pii_info: Dict[str, Any],
        session_id: str = None,
        user_id: str = None,
        metadata: Dict[str, Any] = None,
        immediate: bool = True  # PII data is sensitive, send immediately
    ) -> Dict[str, Any]:
        """Log personally identifiable information (local database only)"""
        payload = {
            "session_id": session_id or self._current_session_id or str(uuid.uuid4()),
            "user_id": user_id or self._current_user_id or "anonymous",
            "content_type": "pii_data",
            "content": json.dumps(pii_info),
            "database_targets": ["local"],  # Only local database
            "level": "info",
            "metadata": metadata or {}
        }
        return await self._send_log(payload, immediate)
    
    async def log_domain_specific(
        self,
        domain: str,
        specialist_data: Dict[str, Any],
        session_id: str = None,
        user_id: str = None,
        metadata: Dict[str, Any] = None,
        immediate: bool = False
    ) -> Dict[str, Any]:
        """Log domain-specific data for specialized AI models"""
        payload = {
            "session_id": session_id or self._current_session_id or str(uuid.uuid4()),
            "user_id": user_id or self._current_user_id or "anonymous",
            "content_type": "domain_specific",
            "content": json.dumps(specialist_data),
            "domain": domain,
            "database_targets": ["cloud"],
            "metadata": {**(metadata or {}), "domain": domain}
        }
        return await self._send_log(payload, immediate)
    
    async def log_fine_tuning_data(
        self,
        training_example: Dict[str, Any],
        model_name: str = None,
        session_id: str = None,
        user_id: str = None,
        metadata: Dict[str, Any] = None,
        immediate: bool = False
    ) -> Dict[str, Any]:
        """Log data for model fine-tuning"""
        payload = {
            "session_id": session_id or self._current_session_id or str(uuid.uuid4()),
            "user_id": user_id or self._current_user_id or "anonymous",
            "content_type": "fine_tuning",
            "content": json.dumps(training_example),
            "model_name": model_name,
            "database_targets": ["remote"],
            "metadata": metadata or {}
        }
        return await self._send_log(payload, immediate)
    
    # === BATCH OPERATIONS ===
    
    async def _send_log(self, payload: Dict[str, Any], immediate: bool = False) -> Dict[str, Any]:
        """Internal method to send log payload"""
        if immediate:
            return await self._send_immediate(payload)
        else:
            return await self._add_to_batch(payload)
    
    async def _add_to_batch(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Add payload to batch for later sending"""
        self._batch.append(payload)
        
        # Auto-flush if batch is full
        if len(self._batch) >= self.config.batch_size:
            await self.flush()
        
        return {"status": "batched", "batch_size": len(self._batch)}
    
    async def _send_immediate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send payload immediately"""
        if not self._session:
            raise RuntimeError("Client not started. Call start() or use async context manager.")
        
        for attempt in range(self.config.retry_attempts):
            try:
                async with self._session.post(
                    f"{self.api_base}/append",
                    json=payload
                ) as response:
                    if response.status == 202:
                        result = await response.json()
                        self.logger.debug(f"Log sent successfully: {result}")
                        return result
                    else:
                        error_text = await response.text()
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=error_text
                        )
            except Exception as e:
                if attempt == self.config.retry_attempts - 1:
                    self.logger.error(f"Failed to send log after {self.config.retry_attempts} attempts: {e}")
                    raise
                else:
                    self.logger.warning(f"Attempt {attempt + 1} failed, retrying in {self.config.retry_delay}s: {e}")
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
    
    async def flush(self) -> List[Dict[str, Any]]:
        """Flush all batched logs"""
        if not self._batch:
            return []
        
        batch_to_send = self._batch[:]
        self._batch.clear()
        self._last_flush = time.time()
        
        results = []
        for payload in batch_to_send:
            try:
                result = await self._send_immediate(payload)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Failed to send batched payload: {e}")
                results.append({"status": "error", "error": str(e)})
        
        self.logger.info(f"Flushed {len(results)} log entries")
        return results
    
    # === UTILITY METHODS ===
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        if not self._session:
            raise RuntimeError("Client not started")
        
        async with self._session.get(f"{self.api_base}/stats") as response:
            return await response.json()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check system health"""
        if not self._session:
            raise RuntimeError("Client not started")
        
        async with self._session.get(f"{self.api_base}/health") as response:
            return await response.json()

# === SPECIALIZED CLIENTS ===

class HealthRAGClient(RAGLogClient):
    """Specialized client for healthcare RAG applications"""
    
    async def log_patient_interaction(
        self,
        patient_id: str,
        interaction_type: str,  # consultation, diagnosis, treatment, etc.
        content: str,
        severity: str = "normal",  # low, normal, high, critical
        session_id: str = None,
        metadata: Dict[str, Any] = None
    ):
        """Log patient interaction with automatic PHI handling"""
        # PHI data goes to local database only
        await self.log_health_data(
            health_info={
                "patient_id": patient_id,
                "interaction_type": interaction_type,
                "content": content,
                "severity": severity
            },
            session_id=session_id,
            user_id=patient_id,
            metadata=metadata,
            immediate=True
        )
    
    async def log_medical_rag_query(
        self,
        query: str,
        patient_context: Dict[str, Any],
        retrieved_guidelines: List[Dict[str, Any]],
        recommendation: str,
        confidence_score: float = None,
        session_id: str = None,
        metadata: Dict[str, Any] = None
    ):
        """Log medical RAG query with patient context"""
        # Store anonymized version for model improvement
        await self.log_rag_context(
            query=query,
            retrieved_docs=retrieved_guidelines,
            context_used=recommendation,
            session_id=session_id,
            metadata={
                **(metadata or {}),
                "domain": "medical",
                "confidence_score": confidence_score,
                "has_patient_context": bool(patient_context)
            }
        )

class LegalRAGClient(RAGLogClient):
    """Specialized client for legal RAG applications"""
    
    async def log_legal_consultation(
        self,
        case_type: str,
        jurisdiction: str,
        query: str,
        legal_analysis: str,
        precedent_cases: List[str] = None,
        session_id: str = None,
        user_id: str = None,
        metadata: Dict[str, Any] = None
    ):
        """Log legal consultation with domain-specific routing"""
        await self.log_domain_specific(
            domain="legal",
            specialist_data={
                "case_type": case_type,
                "jurisdiction": jurisdiction,
                "query": query,
                "legal_analysis": legal_analysis,
                "precedent_cases": precedent_cases or []
            },
            session_id=session_id,
            user_id=user_id,
            metadata=metadata
        )

class FinancialRAGClient(RAGLogClient):
    """Specialized client for financial RAG applications"""
    
    async def log_financial_advice(
        self,
        advice_type: str,  # investment, tax, planning, etc.
        user_profile: Dict[str, Any],
        market_data_used: List[str],
        recommendation: str,
        risk_level: str,
        session_id: str = None,
        user_id: str = None,
        metadata: Dict[str, Any] = None
    ):
        """Log financial advice with appropriate data routing"""
        # Personal financial data to local
        await self.log_pii_data(
            pii_info={
                "user_profile": user_profile,
                "advice_type": advice_type,
                "recommendation": recommendation,
                "risk_level": risk_level
            },
            session_id=session_id,
            user_id=user_id,
            metadata=metadata,
            immediate=True
        )
        
        # Anonymized market analysis to cloud for model improvement
        await self.log_domain_specific(
            domain="financial",
            specialist_data={
                "advice_type": advice_type,
                "market_data_sources": market_data_used,
                "risk_level": risk_level,
                "user_segment": user_profile.get("segment", "unknown")
            },
            session_id=session_id,
            user_id="anonymized",
            metadata=metadata
        )

# === USAGE EXAMPLES ===

async def example_basic_usage():
    """Basic usage example"""
    config = ClientConfig(
        base_url="http://localhost:8000",
        batch_size=5,
        auto_flush=True,
        flush_interval=2.0
    )
    
    async with RAGLogClient(config) as client:
        # Basic logging
        await client.log_conversation(
            content="User asked about their investment portfolio",
            session_id="session_123",
            user_id="user_456"
        )
        
        # Using context manager for session tracking
        with client.session(session_id="session_123", user_id="user_456"):
            await client.log_model_interaction(
                model_name="gpt-4-turbo",
                prompt="What should I invest in?",
                response="Based on your profile, consider diversified ETFs...",
                prompt_tokens=15,
                completion_tokens=87,
                response_time_ms=1200
            )

async def example_model_interaction_context():
    """Example using model interaction context"""
    async with RAGLogClient() as client:
        async with client.model_interaction("claude-3-sonnet") as interaction:
            interaction.set_prompt("Explain quantum computing")
            
            # Simulate RAG retrieval
            interaction.add_rag_source("quantum_physics_textbook", 0.95)
            interaction.add_rag_source("quantum_computing_paper_2023", 0.87)
            interaction.add_metadata("complexity_level", "intermediate")
            
            # Simulate model response
            interaction.set_response("Quantum computing leverages quantum mechanics...")

async def example_specialized_clients():
    """Example using specialized clients"""
    # Healthcare example
    health_client = HealthRAGClient()
    await health_client.start()
    
    await health_client.log_patient_interaction(
        patient_id="patient_789",
        interaction_type="consultation",
        content="Patient reports chest pain and shortness of breath",
        severity="high",
        metadata={"department": "cardiology"}
    )
    
    await health_client.stop()
    
    # Legal example
    legal_client = LegalRAGClient()
    await legal_client.start()
    
    await legal_client.log_legal_consultation(
        case_type="contract_dispute",
        jurisdiction="california",
        query="Can employer terminate for cause without notice?",
        legal_analysis="Under CA Labor Code Section 2922...",
        precedent_cases=["Martinez v. Corp 2019", "Smith v. LLC 2021"]
    )
    
    await legal_client.stop()

async def example_batch_processing():
    """Example of batch processing with manual flush control"""
    config = ClientConfig(auto_flush=False, batch_size=100)
    
    async with RAGLogClient(config) as client:
        # Log many entries that will be batched
        for i in range(50):
            await client.log_conversation(
                content=f"Batch message {i}",
                session_id=f"batch_session_{i // 10}",
                user_id=f"batch_user_{i % 5}"
            )
        
        # Manual flush
        results = await client.flush()
        print(f"Flushed {len(results)} entries")

# === MAIN DEMO ===

async def main_demo():
    """Comprehensive demo of the RAG logging client"""
    print("🚀 RAG Logging Client SDK Demo")
    
    # Basic usage
    print("\n1. Basic Usage:")
    await example_basic_usage()
    
    # Model interaction context
    print("\n2. Model Interaction Context:")
    await example_model_interaction_context()
    
    # Specialized clients
    print("\n3. Specialized Clients:")
    await example_specialized_clients()
    
    # Batch processing
    print("\n4. Batch Processing:")
    await example_batch_processing()
    
    print("\n✅ Demo completed successfully!")

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run demo
    asyncio.run(main_demo())