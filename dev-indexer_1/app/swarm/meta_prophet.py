from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional


def _utc_ts(ts: Optional[float] = None) -> float:
    if ts is None:
        return datetime.now(tz=timezone.utc).timestamp()
    return float(ts)


@dataclass
class SeasonalEWMAState:
    level: float = 0.0
    season: Dict[int, float] = field(default_factory=lambda: {i: 0.0 for i in range(7)})
    count: int = 0
    alpha_level: float = 0.2
    alpha_season: float = 0.2
    period: int = 7  # day-of-week
    last_ts: Optional[float] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(s: str) -> "SeasonalEWMAState":
        d = json.loads(s)
        st = SeasonalEWMAState()
        st.level = float(d.get("level", 0.0))
        st.season = {int(k): float(v) for k, v in (d.get("season") or {}).items()}
        st.count = int(d.get("count", 0))
        st.alpha_level = float(d.get("alpha_level", 0.2))
        st.alpha_season = float(d.get("alpha_season", 0.2))
        st.period = int(d.get("period", 7))
        st.last_ts = float(d["last_ts"]) if d.get("last_ts") is not None else None
        for i in range(st.period):
            st.season.setdefault(i, 0.0)
        return st


class SeasonalEWMA:
    """Tiny, online-trainable seasonal EWMA forecaster (period=7 by default).

    y_t = level + season[dow]
    Updates are online; state is small and JSON-serializable for Redis.
    """

    def __init__(self, state: Optional[SeasonalEWMAState] = None):
        self.state = state or SeasonalEWMAState()

    def update(self, y: float, ts: Optional[float] = None) -> SeasonalEWMAState:
        s = self.state
        ts = _utc_ts(ts)
        dow = datetime.fromtimestamp(ts, tz=timezone.utc).weekday()

        if s.count == 0:
            s.level = y
            s.season[dow] = 0.0
            s.count = 1
            s.last_ts = ts
            return s

        # One-step prediction error using current components
        y_hat = s.level + s.season.get(dow, 0.0)
        err = y - y_hat

        # Update seasonal first using new error influence
        s.season[dow] = (1.0 - s.alpha_season) * s.season.get(dow, 0.0) + s.alpha_season * err

        # Update level using de-seasonalized observation
        s.level = (1.0 - s.alpha_level) * s.level + s.alpha_level * (y - s.season[dow])

        s.count += 1
        s.last_ts = ts
        return s

    def forecast(self, h: int, start_ts: Optional[float] = None) -> List[float]:
        s = self.state
        if h <= 0:
            return []
        base_ts = _utc_ts(start_ts or s.last_ts)
        if s.count == 0:
            return [0.0] * h
        out: List[float] = []
        level = s.level
        for i in range(1, h + 1):
            t = datetime.fromtimestamp(base_ts, tz=timezone.utc) + timedelta(minutes=i)
            dow = t.weekday()
            y_hat = level + s.season.get(dow, 0.0)
            out.append(float(y_hat))
        return out

    def to_json(self) -> str:
        return self.state.to_json()

    @staticmethod
    def from_json(s: str) -> "SeasonalEWMA":
        return SeasonalEWMA(SeasonalEWMAState.from_json(s))


def default_state(alpha_level: float = 0.2, alpha_season: float = 0.2, period: int = 7) -> SeasonalEWMAState:
    st = SeasonalEWMAState(alpha_level=alpha_level, alpha_season=alpha_season, period=period)
    return st
