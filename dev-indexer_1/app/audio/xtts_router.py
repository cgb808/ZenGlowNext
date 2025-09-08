"""XTTS Voice Cloning Router (Coqui XTTS v2 scaffold)

Runs locally if xtts model + inference script available. This is a thin wrapper intended
for future expansion (caching cloned voices, multi-speaker sessions).

Environment:
  XTTS_SCRIPT: path to a python module/cli that can synthesize (default: scripts/xtts_infer.py)
  XTTS_MODEL_DIR: directory containing XTTS weights

Endpoint:
  POST /audio/xtts_clone  (text + reference wav upload)

For now we shell out to keep dependencies optional.
"""

from __future__ import annotations

import base64
import os
import subprocess
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

XTTS_SCRIPT = os.getenv("XTTS_SCRIPT", "scripts/xtts_infer.py")
XTTS_MODEL_DIR = os.getenv("XTTS_MODEL_DIR", "models/xtts")

router = APIRouter(prefix="/audio", tags=["audio-xtts"])  # separate tag


def run_xtts_simple(text: str, ref_path: str) -> bytes:
    """Helper for internal reuse (returns raw wav bytes)."""
    if not os.path.exists(XTTS_SCRIPT):
        raise RuntimeError("xtts script not found")
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as out_f:
        out_path = out_f.name
    cmd = [
        "python",
        XTTS_SCRIPT,
        "--model_dir",
        XTTS_MODEL_DIR,
        "--ref",
        ref_path,
        "--text",
        text,
        "--out",
        out_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=180)
    if proc.returncode != 0:
        raise RuntimeError(
            f"xtts failed: {proc.stderr.decode('utf-8','ignore')[-300:]}"
        )
    try:
        with open(out_path, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(out_path):
            try:
                os.unlink(out_path)
            except Exception:
                pass


class XTTSClonePayload(BaseModel):
    text: str
    format: str | None = None  # wav|base64


@router.post("/xtts_clone")
async def xtts_clone(payload: XTTSClonePayload, ref: UploadFile = File(...)):
    if not os.path.exists(XTTS_SCRIPT):
        raise HTTPException(500, detail="xtts script not found")
    ref_suffix = os.path.splitext(ref.filename or "ref.wav")[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=ref_suffix) as ref_f:
        ref_bytes = await ref.read()
        ref_f.write(ref_bytes)
        ref_path = ref_f.name
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as out_f:
        out_path = out_f.name
    cmd = [
        "python",
        XTTS_SCRIPT,
        "--model_dir",
        XTTS_MODEL_DIR,
        "--ref",
        ref_path,
        "--text",
        payload.text,
        "--out",
        out_path,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=180)
    except subprocess.TimeoutExpired:
        for p in (ref_path, out_path):
            if os.path.exists(p):
                os.unlink(p)
        raise HTTPException(504, detail="xtts inference timeout")
    if proc.returncode != 0:
        stderr_tail = proc.stderr.decode("utf-8", errors="ignore")[-400:]
        for p in (ref_path, out_path):
            if os.path.exists(p):
                os.unlink(p)
        raise HTTPException(500, detail=f"xtts failed: {stderr_tail}")
    try:
        with open(out_path, "rb") as f:
            audio_bytes = f.read()
    finally:
        for p in (ref_path, out_path):
            if os.path.exists(p):
                os.unlink(p)
    if payload.format == "wav" or payload.format is None:
        b64 = base64.b64encode(audio_bytes).decode("ascii")
        return {"audio_base64": b64, "mime": "audio/wav", "bytes": len(audio_bytes)}
    elif payload.format == "base64":
        b64 = base64.b64encode(audio_bytes).decode("ascii")
        return {"audio_base64": b64, "mime": "audio/wav", "bytes": len(audio_bytes)}
    else:
        raise HTTPException(400, detail="invalid format")
