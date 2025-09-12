from __future__ import annotations
import math, time
from typing import Dict, Any

def extract_route_features(ctx: Dict[str, Any]) -> Dict[str, float]:
    text = ctx.get('text','')
    words = text.split()
    length = len(words)
    now = time.time()
    recent_fallback_rate = float(ctx.get('recent_fallback_rate', 0.0))
    feats = {
        'bias': 1.0,
        'len_log': math.log(max(1, length)),
        'len_gt_60': 1.0 if length > 60 else 0.0,
        'len_lt_12': 1.0 if length < 12 else 0.0,
        'question_mark': 1.0 if '?' in text else 0.0,
        'recent_fallback_high': 1.0 if recent_fallback_rate > 0.25 else 0.0,
        'ts_mod_minute': (now % 60.0) / 60.0,
    }
    return feats
