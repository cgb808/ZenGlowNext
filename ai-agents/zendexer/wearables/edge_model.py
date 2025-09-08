"""
ZenDexer Wearables Edge Model
Lightweight AI model for wearable devices that processes wellness metrics
"""

import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WearablesEdgeModel:
    """Lightweight model for wearable devices"""
    
    def __init__(self, model_type: str = "tinybert", device_id: str = "wearable_001"):
        self.model_type = model_type
        self.device_id = device_id
        self.metrics_buffer = []
        self.last_sync = datetime.now()
        self.smollm_endpoint = "http://localhost:8002"  # SmolLM2 predictor endpoint
        
        logger.info(f"Initialized {model_type} model on device {device_id}")
    
    def collect_physiological_metrics(self) -> Dict:
        """Simulate physiological metric collection"""
        # In real implementation, this would read from sensors
        return {
            "timestamp": datetime.now().isoformat(),
            "heart_rate": random.randint(60, 100),
            "heart_rate_variability": random.uniform(20, 80),
            "steps": random.randint(0, 200),  # Steps in last 5 minutes
            "activity_level": random.choice(["sedentary", "light", "moderate", "vigorous"]),
            "stress_level": random.uniform(0, 1),  # 0 = calm, 1 = highly stressed
            "device_id": self.device_id
        }
    
    def analyze_mood_indicators(self, text_input: Optional[str] = None) -> Dict:
        """Analyze mood from various inputs"""
        # Simulate lightweight NLP processing
        if text_input:
            # In real implementation, this would use TinyBERT/MobileBERT
            mood_score = random.uniform(-1, 1)  # -1 = negative, 1 = positive
            confidence = random.uniform(0.6, 0.95)
        else:
            # Infer from behavioral patterns
            mood_score = random.uniform(-0.5, 0.5)
            confidence = random.uniform(0.4, 0.7)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "mood_score": mood_score,
            "confidence": confidence,
            "input_type": "text" if text_input else "behavioral",
            "device_id": self.device_id
        }
    
    def collect_behavioral_metrics(self) -> Dict:
        """Collect behavioral interaction metrics"""
        return {
            "timestamp": datetime.now().isoformat(),
            "app_interactions": random.randint(0, 10),
            "notification_responses": random.randint(0, 5),
            "response_time_avg": random.uniform(1, 10),  # seconds
            "screen_time": random.randint(0, 30),  # minutes in last hour
            "device_id": self.device_id
        }
    
    def process_metrics_batch(self) -> Dict:
        """Process a batch of collected metrics"""
        physio = self.collect_physiological_metrics()
        mood = self.analyze_mood_indicators()
        behavioral = self.collect_behavioral_metrics()
        
        # Combine metrics with edge processing
        wellness_score = self._calculate_wellness_score(physio, mood, behavioral)
        
        batch = {
            "batch_id": f"{self.device_id}_{int(time.time())}",
            "device_id": self.device_id,
            "timestamp": datetime.now().isoformat(),
            "physiological": physio,
            "mood": mood,
            "behavioral": behavioral,
            "wellness_score": wellness_score,
            "model_type": self.model_type
        }
        
        self.metrics_buffer.append(batch)
        return batch
    
    def _calculate_wellness_score(self, physio: Dict, mood: Dict, behavioral: Dict) -> float:
        """Calculate composite wellness score on device"""
        # Simple weighted scoring (would be more sophisticated in real implementation)
        stress_factor = 1 - physio["stress_level"]
        mood_factor = (mood["mood_score"] + 1) / 2  # Normalize to 0-1
        activity_factor = min(physio["steps"] / 100, 1.0)  # Steps per 5 min
        
        wellness_score = (stress_factor * 0.4 + mood_factor * 0.4 + activity_factor * 0.2)
        return round(wellness_score, 3)
    
    def sync_to_smollm(self) -> bool:
        """Sync metrics to SmolLM2 predictor"""
        if not self.metrics_buffer:
            return True
        
        try:
            payload = {
                "device_id": self.device_id,
                "metrics_batch": self.metrics_buffer,
                "sync_timestamp": datetime.now().isoformat()
            }
            
            response = requests.post(
                f"{self.smollm_endpoint}/metrics/ingest",
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info(f"Synced {len(self.metrics_buffer)} metric batches to SmolLM2")
                self.metrics_buffer.clear()
                self.last_sync = datetime.now()
                return True
            else:
                logger.error(f"Sync failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Sync error: {e}")
            return False
    
    def run_collection_cycle(self, duration_minutes: int = 5):
        """Run continuous metrics collection cycle"""
        logger.info(f"Starting collection cycle for {duration_minutes} minutes")
        
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        
        while datetime.now() < end_time:
            # Collect metrics every 30 seconds
            batch = self.process_metrics_batch()
            logger.info(f"Collected batch: wellness_score={batch['wellness_score']}")
            
            # Sync every 2 minutes or when buffer gets large
            if (len(self.metrics_buffer) >= 4 or 
                (datetime.now() - self.last_sync).seconds >= 120):
                self.sync_to_smollm()
            
            time.sleep(30)  # Wait 30 seconds
        
        # Final sync
        if self.metrics_buffer:
            self.sync_to_smollm()
        
        logger.info("Collection cycle completed")

def main():
    """Test the wearables model locally"""
    print("🎯 ZenDexer Wearables Edge Model - Local Test")
    print("=" * 50)
    
    # Initialize model
    model = WearablesEdgeModel(model_type="tinybert", device_id="test_device_001")
    
    # Test single metric collection
    print("\n📊 Testing single metric collection:")
    batch = model.process_metrics_batch()
    print(json.dumps(batch, indent=2))
    
    # Test short collection cycle
    print(f"\n🔄 Starting 1-minute test collection cycle...")
    model.run_collection_cycle(duration_minutes=1)
    
    print("\n✅ Local test completed!")

if __name__ == "__main__":
    main()
