"""
SmolLM2 Enhanced Predictor with Wearables Integration
Receives metrics from wearable devices and provides parental predictions
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from flask import Flask, request, jsonify
import numpy as np
from collections import defaultdict, deque

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class SmolLM2Predictor:
    """Enhanced SmolLM2 predictor with wearables integration"""
    
    def __init__(self):
        self.device_metrics = defaultdict(lambda: deque(maxlen=100))  # Store last 100 batches per device
        self.family_profiles = {}
        self.prediction_cache = {}
        
        logger.info("SmolLM2 Predictor initialized with wearables support")
    
    def ingest_metrics(self, device_id: str, metrics_batch: List[Dict]) -> bool:
        """Ingest metrics from wearable device"""
        try:
            for batch in metrics_batch:
                # Validate and store metrics
                if self._validate_metrics_batch(batch):
                    self.device_metrics[device_id].append(batch)
                    logger.debug(f"Stored metrics batch from {device_id}")
            
            # Trigger real-time analysis for immediate concerns
            self._check_immediate_concerns(device_id)
            
            return True
        except Exception as e:
            logger.error(f"Error ingesting metrics: {e}")
            return False
    
    def _validate_metrics_batch(self, batch: Dict) -> bool:
        """Validate metrics batch structure"""
        required_fields = ["batch_id", "device_id", "timestamp", "wellness_score"]
        return all(field in batch for field in required_fields)
    
    def _check_immediate_concerns(self, device_id: str):
        """Check for immediate wellness concerns"""
        recent_batches = list(self.device_metrics[device_id])[-3:]  # Last 3 batches
        
        if len(recent_batches) >= 3:
            wellness_scores = [batch["wellness_score"] for batch in recent_batches]
            avg_wellness = np.mean(wellness_scores)
            
            # Alert if wellness consistently low
            if avg_wellness < 0.3:
                self._trigger_alert(device_id, "low_wellness", avg_wellness)
            
            # Check for sudden drops
            if len(wellness_scores) >= 2 and wellness_scores[-1] < (wellness_scores[-2] - 0.4):
                self._trigger_alert(device_id, "wellness_drop", wellness_scores[-1])
    
    def _trigger_alert(self, device_id: str, alert_type: str, value: float):
        """Trigger alert for parental dashboard"""
        alert = {
            "device_id": device_id,
            "alert_type": alert_type,
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "severity": "high" if value < 0.2 else "medium"
        }
        logger.warning(f"ALERT: {alert}")
        # In real implementation, this would send to parental dashboard
    
    def predict_child_wellness(self, family_id: str, child_id: str, prediction_horizon: int = 24) -> Dict:
        """Predict child wellness for next N hours"""
        device_id = f"child_{child_id}"
        
        if device_id not in self.device_metrics:
            return {"error": "No metrics available for this child"}
        
        recent_metrics = list(self.device_metrics[device_id])[-20:]  # Last 20 batches
        
        if len(recent_metrics) < 5:
            return {"error": "Insufficient data for prediction"}
        
        # Extract features for prediction
        features = self._extract_prediction_features(recent_metrics)
        
        # Simple prediction model (would be more sophisticated in real implementation)
        predicted_wellness = self._generate_wellness_prediction(features, prediction_horizon)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(features, predicted_wellness)
        
        return {
            "family_id": family_id,
            "child_id": child_id,
            "prediction_horizon_hours": prediction_horizon,
            "current_wellness": features["current_wellness"],
            "predicted_wellness": predicted_wellness,
            "confidence": features["prediction_confidence"],
            "recommendations": recommendations,
            "last_updated": datetime.now().isoformat()
        }
    
    def _extract_prediction_features(self, metrics: List[Dict]) -> Dict:
        """Extract features from metrics for prediction"""
        wellness_scores = [m["wellness_score"] for m in metrics]
        
        # Time-based patterns
        hours = [(datetime.fromisoformat(m["timestamp"].replace('Z', '+00:00')).hour) for m in metrics]
        hour_wellness = defaultdict(list)
        for hour, wellness in zip(hours, wellness_scores):
            hour_wellness[hour].append(wellness)
        
        # Physiological trends
        stress_levels = []
        heart_rates = []
        for m in metrics:
            if "physiological" in m:
                stress_levels.append(m["physiological"].get("stress_level", 0.5))
                heart_rates.append(m["physiological"].get("heart_rate", 75))
        
        return {
            "current_wellness": wellness_scores[-1],
            "wellness_trend": np.mean(wellness_scores[-5:]) - np.mean(wellness_scores[-10:-5]) if len(wellness_scores) >= 10 else 0,
            "avg_stress": np.mean(stress_levels) if stress_levels else 0.5,
            "heart_rate_variability": np.std(heart_rates) if heart_rates else 0,
            "time_patterns": dict(hour_wellness),
            "prediction_confidence": min(len(metrics) / 20, 1.0)  # More data = higher confidence
        }
    
    def _generate_wellness_prediction(self, features: Dict, hours: int) -> List[Dict]:
        """Generate wellness prediction for next N hours"""
        predictions = []
        current_wellness = features["current_wellness"]
        trend = features["wellness_trend"]
        
        for hour in range(1, hours + 1):
            # Simple linear prediction with some randomness
            predicted = current_wellness + (trend * hour * 0.1)
            predicted = max(0, min(1, predicted + np.random.normal(0, 0.1)))
            
            predictions.append({
                "hour": hour,
                "predicted_wellness": round(predicted, 3),
                "confidence": features["prediction_confidence"]
            })
        
        return predictions
    
    def _generate_recommendations(self, features: Dict, predictions: List[Dict]) -> List[str]:
        """Generate recommendations based on features and predictions"""
        recommendations = []
        
        if features["current_wellness"] < 0.4:
            recommendations.append("Consider checking in with your child about their day")
        
        if features["avg_stress"] > 0.7:
            recommendations.append("Stress levels elevated - perhaps suggest a calming activity")
        
        if features["wellness_trend"] < -0.2:
            recommendations.append("Wellness trending down - extra attention may be helpful")
        
        # Check predicted low points
        low_predictions = [p for p in predictions[:12] if p["predicted_wellness"] < 0.3]
        if low_predictions:
            recommendations.append(f"Potential wellness dip predicted around hour {low_predictions[0]['hour']}")
        
        if not recommendations:
            recommendations.append("Wellness levels look stable - keep up the good routine!")
        
        return recommendations

# Flask API endpoints
predictor = SmolLM2Predictor()

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "connected_devices": len(predictor.device_metrics)
    })

@app.route("/metrics/ingest", methods=["POST"])
def ingest_metrics():
    """Ingest metrics from wearable devices"""
    try:
        data = request.get_json()
        device_id = data.get("device_id")
        metrics_batch = data.get("metrics_batch", [])
        
        if not device_id or not metrics_batch:
            return jsonify({"error": "Missing device_id or metrics_batch"}), 400
        
        success = predictor.ingest_metrics(device_id, metrics_batch)
        
        if success:
            return jsonify({
                "status": "success",
                "device_id": device_id,
                "batches_received": len(metrics_batch),
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({"error": "Failed to process metrics"}), 500
    
    except Exception as e:
        logger.error(f"Error in metrics ingestion: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/predict/child-wellness", methods=["POST"])
def predict_wellness():
    """Predict child wellness"""
    try:
        data = request.get_json()
        family_id = data.get("family_id")
        child_id = data.get("child_id")
        prediction_horizon = data.get("prediction_horizon", 24)
        
        if not family_id or not child_id:
            return jsonify({"error": "Missing family_id or child_id"}), 400
        
        prediction = predictor.predict_child_wellness(family_id, child_id, prediction_horizon)
        
        return jsonify(prediction)
    
    except Exception as e:
        logger.error(f"Error in wellness prediction: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/analytics/family/<family_id>", methods=["GET"])
def family_analytics(family_id):
    """Get family analytics"""
    try:
        # Get all devices for this family (simplified)
        family_devices = [device_id for device_id in predictor.device_metrics.keys() 
                         if f"family_{family_id}" in device_id or "child_" in device_id]
        
        analytics = {
            "family_id": family_id,
            "connected_devices": len(family_devices),
            "last_24h_summary": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Calculate summary stats
        for device_id in family_devices:
            recent_metrics = list(predictor.device_metrics[device_id])[-48:]  # Last 24h (30s intervals)
            if recent_metrics:
                wellness_scores = [m["wellness_score"] for m in recent_metrics]
                analytics["last_24h_summary"][device_id] = {
                    "avg_wellness": round(np.mean(wellness_scores), 3),
                    "min_wellness": round(min(wellness_scores), 3),
                    "max_wellness": round(max(wellness_scores), 3),
                    "data_points": len(wellness_scores)
                }
        
        return jsonify(analytics)
    
    except Exception as e:
        logger.error(f"Error in family analytics: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("🧠 SmolLM2 Predictor with Wearables Integration")
    print("=" * 50)
    app.run(host="0.0.0.0", port=8002, debug=True)
