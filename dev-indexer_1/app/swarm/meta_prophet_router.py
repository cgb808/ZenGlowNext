from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

try:  # optional import; router remains mountable without Redis
    import redis.asyncio as redis  # type: ignore
except ImportError:  # pragma: no cover
    try:
        import redis  # type: ignore
    except Exception:  # pragma: no cover
        redis = None  # type: ignore

from .meta_prophet import SeasonalEWMA, SeasonalEWMAState, default_state


router = APIRouter(prefix="/swarm/predict", tags=["swarm-predictor"])


def _redis_client():
    if redis is None:
        raise RuntimeError("redis client not installed")
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    return redis.Redis(host=host, port=port)


def _key(name: str) -> str:
    return f"swarm:forecaster:{name}" if name else "swarm:forecaster:default"


async def _load(name: str) -> SeasonalEWMA:
    r = _redis_client()
    raw = await r.get(_key(name))
    if not raw:
        return SeasonalEWMA(default_state())
    try:
        s = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)
        return SeasonalEWMA.from_json(s)
    except Exception:
        return SeasonalEWMA(default_state())


async def _save(name: str, model: SeasonalEWMA) -> None:
    r = _redis_client()
    await r.set(_key(name), model.to_json())


class ObserveIn(BaseModel):
    name: str = Field(default="default")
    y: float
    ts: float | None = None
    alpha_level: float | None = None
    alpha_season: float | None = None
    period: int | None = None


@router.post("/observe")
async def observe(payload: ObserveIn) -> dict[str, Any]:
    try:
        model = await _load(payload.name)
        # Optionally update hyperparameters on the fly
        st = model.state
        if payload.alpha_level is not None:
            st.alpha_level = float(payload.alpha_level)
        if payload.alpha_season is not None:
            st.alpha_season = float(payload.alpha_season)
        if payload.period is not None and int(payload.period) > 1:
            st.period = int(payload.period)
            # Ensure season keys exist after period change
            for i in range(st.period):
                st.season.setdefault(i, 0.0)
        model.update(payload.y, ts=payload.ts)
        await _save(payload.name, model)
        return {"ok": True, "name": payload.name, "state": model.state.__dict__}
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forecast")
async def forecast(name: str = "default", horizon: int = 30, start_ts: float | None = None):
    try:
        model = await _load(name)
        preds = model.forecast(max(1, int(horizon)), start_ts=start_ts)
        return {"ok": True, "name": name, "horizon": int(horizon), "pred": preds}
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))


class ResetIn(BaseModel):
    name: str = Field(default="default")


@router.post("/reset")
async def reset(payload: ResetIn):
    try:
        model = SeasonalEWMA(default_state())
        await _save(payload.name, model)
        return {"ok": True, "name": payload.name}
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e))
