from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

try:  # optional import; router remains mountable without Redis
    import redis.asyncio as aioredis  # type: ignore
except Exception:  # pragma: no cover
    aioredis = None  # type: ignore
try:
    import redis as sync_redis  # type: ignore
except Exception:  # pragma: no cover
    sync_redis = None  # type: ignore

from .meta_prophet import SeasonalEWMA, SeasonalEWMAState, default_state


router = APIRouter(prefix="/swarm/predict", tags=["swarm-predictor"])


_MEM_STORE: dict[str, str] = {}


def _key(name: str) -> str:
    return f"swarm:forecaster:{name}" if name else "swarm:forecaster:default"


def _redis_params() -> tuple[str, int]:
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    return host, port


async def _load(name: str) -> SeasonalEWMA:
    k = _key(name)
    host, port = _redis_params()
    # Try async redis first
    if aioredis is not None:
        try:
            r = aioredis.Redis(host=host, port=port)
            raw = await r.get(k)
            if raw:
                s = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)
                return SeasonalEWMA.from_json(s)
        except Exception:
            pass
    # Fallback to sync redis in a thread
    if sync_redis is not None:
        try:
            import anyio

            def _get_sync() -> bytes | str | None:
                try:
                    r = sync_redis.StrictRedis(host=host, port=port)
                    return r.get(k)  # type: ignore[return-value]
                except Exception:
                    return None

            raw = await anyio.to_thread.run_sync(_get_sync)
            if raw:
                s = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)
                return SeasonalEWMA.from_json(s)
        except Exception:
            pass
    # In-memory fallback
    s = _MEM_STORE.get(k)
    if s:
        try:
            return SeasonalEWMA.from_json(s)
        except Exception:
            pass
    return SeasonalEWMA(default_state())


async def _save(name: str, model: SeasonalEWMA) -> None:
    k = _key(name)
    host, port = _redis_params()
    payload = model.to_json()
    if aioredis is not None:
        try:
            r = aioredis.Redis(host=host, port=port)
            await r.set(k, payload)
            return
        except Exception:
            pass
    if sync_redis is not None:
        try:
            import anyio

            def _set_sync() -> None:
                try:
                    r = sync_redis.StrictRedis(host=host, port=port)
                    r.set(k, payload)
                except Exception:
                    pass

            await anyio.to_thread.run_sync(_set_sync)
            return
        except Exception:
            pass
    _MEM_STORE[k] = payload


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
