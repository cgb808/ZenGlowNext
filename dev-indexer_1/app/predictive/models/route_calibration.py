from __future__ import annotations
from typing import Dict, Any
from ..features import extract_route_features

# Simple logistic weights (hand-tuned placeholder)
WEIGHTS = {
    'bias': -0.4,
    'len_log': 0.05,
    'len_gt_60': 0.6,
    'len_lt_12': -0.3,
    'question_mark': -0.05,
    'recent_fallback_high': -0.8,
    'ts_mod_minute': 0.0,
}

class RouteCalibrationPredictor:
    name = 'route_calibration'
    def predict(self, context: Dict[str, Any]) -> Dict[str, Any]:
        feats = extract_route_features(context)
        z = 0.0
        used = {}
        for k, w in WEIGHTS.items():
            v = feats.get(k, 0.0)
            z += w * v
            used[k] = v
        # logistic
        import math
        score = 1.0 / (1.0 + math.exp(-z))
        return {
            'score': float(score),
            'adjustment': (score - 0.5) * 0.1,  # small delta suggestion
            'features_used': used,
            'raw_z': z,
        }
