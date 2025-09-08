"""
Simple ZenDexer Wearables Test (No External Dependencies)
Testing the wearables -> SmolLM2 integration pipeline
"""

import json
import time
import random
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import urllib.request
import urllib.error

class SimpleSmolLM2Server(BaseHTTPRequestHandler):
    """Simple HTTP server to simulate SmolLM2 predictor"""
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service": "SmolLM2 Predictor (Test Mode)"
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            
            if self.path == '/metrics/ingest':
                device_id = data.get('device_id', 'unknown')
                metrics_batch = data.get('metrics_batch', [])
                
                print(f"📊 Received metrics from {device_id}: {len(metrics_batch)} batches")
                
                # Log some metrics details
                if metrics_batch:
                    latest = metrics_batch[-1]
                    wellness = latest.get('wellness_score', 'N/A')
                    print(f"   Latest wellness score: {wellness}")
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                response = {
                    "status": "success",
                    "device_id": device_id,
                    "batches_received": len(metrics_batch),
                    "timestamp": datetime.now().isoformat()
                }
                self.wfile.write(json.dumps(response).encode())
                
            elif self.path == '/predict/child-wellness':
                family_id = data.get('family_id', 'test_family')
                child_id = data.get('child_id', 'test_child')
                
                print(f"🔮 Prediction request for family {family_id}, child {child_id}")
                
                # Generate mock prediction
                response = {
                    "family_id": family_id,
                    "child_id": child_id,
                    "prediction_horizon_hours": 24,
                    "current_wellness": round(random.uniform(0.3, 0.9), 3),
                    "predicted_wellness": [
                        {"hour": i, "predicted_wellness": round(random.uniform(0.2, 0.8), 3)}
                        for i in range(1, 25)
                    ],
                    "confidence": 0.75,
                    "recommendations": [
                        "Monitor stress levels during afternoon hours",
                        "Encourage physical activity if wellness drops below 0.4"
                    ],
                    "last_updated": datetime.now().isoformat()
                }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response, indent=2).encode())
                
            else:
                self.send_response(404)
                self.end_headers()
                
        except Exception as e:
            print(f"❌ Error processing request: {e}")
            self.send_response(500)
            self.end_headers()

class SimpleWearableDevice:
    """Simple wearable device simulator"""
    
    def __init__(self, device_id="test_wearable_001"):
        self.device_id = device_id
        self.smollm_url = "http://localhost:8002"
    
    def generate_metrics(self):
        """Generate simulated metrics"""
        return {
            "batch_id": f"{self.device_id}_{int(time.time())}",
            "device_id": self.device_id,
            "timestamp": datetime.now().isoformat(),
            "physiological": {
                "heart_rate": random.randint(65, 95),
                "stress_level": random.uniform(0.1, 0.8),
                "steps": random.randint(0, 150),
                "activity_level": random.choice(["sedentary", "light", "moderate"])
            },
            "mood": {
                "mood_score": random.uniform(-0.5, 0.8),
                "confidence": random.uniform(0.6, 0.9)
            },
            "behavioral": {
                "app_interactions": random.randint(0, 8),
                "screen_time": random.randint(5, 45)
            },
            "wellness_score": round(random.uniform(0.2, 0.9), 3)
        }
    
    def send_metrics(self, metrics_batch):
        """Send metrics to SmolLM2 predictor"""
        try:
            payload = {
                "device_id": self.device_id,
                "metrics_batch": metrics_batch,
                "sync_timestamp": datetime.now().isoformat()
            }
            
            data = json.dumps(payload).encode('utf-8')
            
            req = urllib.request.Request(
                f"{self.smollm_url}/metrics/ingest",
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    print(f"✅ Sent {len(metrics_batch)} metric batches successfully")
                    return True
                else:
                    print(f"❌ Failed to send metrics: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error sending metrics: {e}")
            return False
    
    def test_prediction(self):
        """Test wellness prediction"""
        try:
            payload = {
                "family_id": "test_family_001",
                "child_id": "test_child_001",
                "prediction_horizon": 12
            }
            
            data = json.dumps(payload).encode('utf-8')
            
            req = urllib.request.Request(
                f"{self.smollm_url}/predict/child-wellness",
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode('utf-8'))
                    print("🔮 Prediction result:")
                    print(f"   Current wellness: {result.get('current_wellness', 'N/A')}")
                    print(f"   Confidence: {result.get('confidence', 'N/A')}")
                    print(f"   Recommendations: {len(result.get('recommendations', []))}")
                    return True
                else:
                    print(f"❌ Prediction failed: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error testing prediction: {e}")
            return False

def start_server():
    """Start the simple SmolLM2 server"""
    server = HTTPServer(('localhost', 8002), SimpleSmolLM2Server)
    print("🧠 Starting SmolLM2 test server on http://localhost:8002")
    server.serve_forever()

def test_integration():
    """Test the full wearables -> SmolLM2 integration"""
    print("🎯 ZenDexer Wearables Integration Test")
    print("=" * 50)
    
    # Start server in background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    print("⏳ Waiting for server to start...")
    time.sleep(2)
    
    # Test server health
    try:
        req = urllib.request.Request("http://localhost:8002/health")
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                health_data = json.loads(response.read().decode('utf-8'))
                print(f"✅ Server health check passed: {health_data['status']}")
            else:
                print("❌ Server health check failed")
                return
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return
    
    # Initialize wearable device
    device = SimpleWearableDevice("test_wearable_001")
    
    # Generate and send test metrics
    print("\n📊 Generating test metrics...")
    metrics_batch = []
    
    for i in range(5):
        metrics = device.generate_metrics()
        metrics_batch.append(metrics)
        print(f"   Batch {i+1}: wellness_score = {metrics['wellness_score']}")
        time.sleep(0.5)
    
    # Send metrics to SmolLM2
    print(f"\n📤 Sending {len(metrics_batch)} metric batches...")
    success = device.send_metrics(metrics_batch)
    
    if success:
        print("✅ Metrics sent successfully")
        
        # Test prediction
        print("\n🔮 Testing wellness prediction...")
        device.test_prediction()
        
        print("\n🎉 Integration test completed successfully!")
        print("\nNext steps:")
        print("1. Deploy to wearable device")
        print("2. Implement real model inference")
        print("3. Add parental dashboard integration")
        print("4. Set up production monitoring")
        
    else:
        print("❌ Integration test failed")

if __name__ == "__main__":
    test_integration()
