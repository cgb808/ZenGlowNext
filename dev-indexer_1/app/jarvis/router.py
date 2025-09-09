from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/jarvis", tags=["jarvis"])

try:
    # Prefer reusing the provided local script
    from Phi3.5Jarvis import infer as jarvis_infer  # type: ignore
except Exception:  # pragma: no cover
    # Fallback: load from workspace root by path
    jarvis_infer = None  # type: ignore
    try:
        import importlib.util
        import pathlib

        here = pathlib.Path(__file__).resolve()
        root = here.parent.parent.parent  # app/jarvis/router.py -> repo root
        alt = root / "Phi3.5Jarvis.py"
        if alt.exists():
            spec = importlib.util.spec_from_file_location("Phi3_5Jarvis", str(alt))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[attr-defined]
                jarvis_infer = getattr(mod, "infer", None)
    except Exception:
        jarvis_infer = None  # type: ignore


class InferIn(BaseModel):
    prompt: str
    adapter: str = Field(..., description="Path or repo id of the LoRA/adapter")
    base: str = Field(default_factory=lambda: os.getenv("JARVIS_BASE", "microsoft/Phi-3.5-mini-instruct"))
    max_new_tokens: int = 256
    temperature: Optional[float] = None
    quant_4bit: bool = Field(default_factory=lambda: os.getenv("JARVIS_QUANT_4BIT", "1").lower() in {"1", "true", "yes"})


@router.get("/ping")
def ping() -> dict[str, Any]:
    available = jarvis_infer is not None
    info: dict[str, Any] = {"ok": True, "available": available}
    if available:
        try:
            import torch  # type: ignore

            info.update(
                {
                    "cuda": bool(getattr(torch, "cuda", None) and torch.cuda.is_available()),
                    "bf16": bool(
                        getattr(torch, "cuda", None)
                        and hasattr(torch.cuda, "is_bf16_supported")
                        and torch.cuda.is_bf16_supported()
                    ),
                }
            )
        except Exception:
            pass
    return info


@router.post("/infer")
async def infer(payload: InferIn) -> dict[str, Any]:
    if jarvis_infer is None:
        raise HTTPException(status_code=503, detail="Jarvis not available: missing dependencies or script import")
    try:
        # Run in a worker thread to avoid blocking the event loop
        def _call() -> str:
            return jarvis_infer(  # type: ignore[misc]
                base=payload.base,
                adapter=payload.adapter,
                prompt=payload.prompt,
                max_new_tokens=payload.max_new_tokens,
                quant_4bit=payload.quant_4bit,
                temperature=payload.temperature,
            )

        text: str = await asyncio.to_thread(_call)
        return {"ok": True, "text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
