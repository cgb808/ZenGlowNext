"""Speaker Recognition & Enrollment Router

Provides endpoints to:
  * Enroll a speaker (store voice embedding)
  * Identify speaker from an audio sample

Uses Resemblyzer for voice embeddings if available; falls back to a zero vector.
Embeddings stored in memory for now; future: persist to DB (users/user_embeddings).
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import time
from typing import Dict, List

import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

SPEAKER_AUDIO_DIR = os.getenv("SPEAKER_AUDIO_DIR", "data/speakers")
os.makedirs(SPEAKER_AUDIO_DIR, exist_ok=True)

SPEAKER_MIN_SIM = float(os.getenv("SPEAKER_MIN_SIM", "0.6"))

try:  # optional dependency
    from resemblyzer import VoiceEncoder, preprocess_wav

    _encoder: VoiceEncoder | None = VoiceEncoder()
except Exception:  # pragma: no cover - optional path
    _encoder = None

router = APIRouter(prefix="/audio", tags=["audio-speaker"])  # grouped under audio

_SPEAKER_DB: Dict[str, Dict[str, object]] = {}


def _safe_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name.strip())[:64]


def _profile_path(name: str) -> str:
    return os.path.join(SPEAKER_AUDIO_DIR, f"{_safe_name(name)}.wav")


def _store_profile_index():  # lightweight persistence
    idx_path = os.path.join(SPEAKER_AUDIO_DIR, "profiles.json")
    try:
        serial = {
            n: {k: v for k, v in d.items() if k != "embedding"}
            for n, d in _SPEAKER_DB.items()
        }
        with open(idx_path, "w") as f:
            json.dump(serial, f)
    except Exception:
        pass


def _load_profile_index():
    idx_path = os.path.join(SPEAKER_AUDIO_DIR, "profiles.json")
    if not os.path.exists(idx_path):
        return
    try:
        with open(idx_path, "r") as f:
            serial = json.load(f)
        for name, meta in serial.items():
            path = meta.get("audio_path")
            if path and os.path.exists(path) and _encoder is not None:
                try:
                    wav = preprocess_wav(path)
                    emb = _encoder.embed_utterance(wav)
                except Exception:
                    emb = np.zeros(256, dtype=np.float32)
            else:
                emb = np.zeros(256, dtype=np.float32)
            _SPEAKER_DB[name] = {"embedding": emb.astype(np.float32), **meta}
    except Exception:
        pass


_load_profile_index()


class SpeakerList(BaseModel):
    speakers: List[str]


@router.get("/speakers", response_model=SpeakerList)
def list_speakers():
    return SpeakerList(speakers=sorted(_SPEAKER_DB.keys()))


@router.get("/speakers/meta")
def list_speakers_meta():
    out = {}
    for name, rec in _SPEAKER_DB.items():
        out[name] = {k: v for k, v in rec.items() if k != "embedding"}
    return out


@router.post("/speaker/enroll")
async def enroll_speaker(name: str = Form(...), file: UploadFile = File(...)):
    safe = _safe_name(name)
    raw = await file.read()
    dest = _profile_path(safe)
    with open(dest, "wb") as f:
        f.write(raw)
    if _encoder is None:
        emb = np.zeros(256, dtype=np.float32)
    else:
        try:
            wav = preprocess_wav(io.BytesIO(raw))
            emb = _encoder.embed_utterance(wav)
        except Exception as e:
            raise HTTPException(400, detail=f"failed to process audio: {e}")
    record = {
        "embedding": emb.astype(np.float32),
        "audio_path": dest,
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    _SPEAKER_DB[safe] = record
    _store_profile_index()
    return {
        "enrolled": safe,
        "audio_path": dest,
        "embedding_dim": int(record["embedding"].shape[0]),
        "warning": None if _encoder else "resemblyzer not installed; zero vector used",
    }


@router.post("/speaker/identify")
async def identify_speaker(file: UploadFile = File(...)):
    data = await file.read()
    if not _SPEAKER_DB:
        raise HTTPException(404, detail="no enrolled speakers")
    if _encoder is None:
        raise HTTPException(500, detail="resemblyzer not available")
    try:
        wav = preprocess_wav(io.BytesIO(data))
        probe = _encoder.embed_utterance(wav)
    except Exception as e:
        raise HTTPException(400, detail=f"failed to process audio: {e}")
    best_name = None
    best_score = -1.0
    for name, rec in _SPEAKER_DB.items():
        emb = rec["embedding"]  # type: ignore
        emb = np.asarray(emb)
        num = float(np.dot(probe, emb))
        den = float(np.linalg.norm(probe) * np.linalg.norm(emb) + 1e-9)
        sim = num / den
        if sim > best_score:
            best_score = sim
            best_name = name
    matched = best_score >= SPEAKER_MIN_SIM
    return {
        "identified": best_name if matched else None,
        "similarity": best_score,
        "threshold": SPEAKER_MIN_SIM,
    }


def _run_xtts(text: str, ref_path: str):
    from .xtts_router import XTTS_MODEL_DIR, XTTS_SCRIPT  # lazy import

    if not os.path.exists(XTTS_SCRIPT):
        raise HTTPException(500, detail="xtts script not found")
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
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=180)
    except subprocess.TimeoutExpired:
        raise HTTPException(504, detail="xtts inference timeout")
    if proc.returncode != 0:
        raise HTTPException(
            500, detail=f"xtts failed: {proc.stderr.decode('utf-8', 'ignore')[-300:]}"
        )
    try:
        with open(out_path, "rb") as f:
            audio = f.read()
    finally:
        if os.path.exists(out_path):
            try:
                os.unlink(out_path)
            except Exception:
                pass
    return base64.b64encode(audio).decode("ascii"), len(audio)


@router.post("/speaker/identify_clone")
async def identify_and_clone(text: str = Form(...), file: UploadFile = File(...)):
    """Identify speaker from uploaded sample and clone voice for response text.

    Fallback: if no match >= threshold, 404.
    """
    id_result = await identify_speaker(file)  # re-use logic (file consumed there)
    speaker = id_result.get("identified")  # type: ignore
    if not speaker:
        raise HTTPException(404, detail="speaker_not_confident")
    rec = _SPEAKER_DB.get(speaker)
    if not rec:
        raise HTTPException(404, detail="speaker_profile_missing")
    ref_path = rec.get("audio_path")  # type: ignore
    if not isinstance(ref_path, str) or not os.path.exists(ref_path):
        raise HTTPException(500, detail="reference_audio_missing")
    b64, size = _run_xtts(text, ref_path)
    return {
        "speaker": speaker,
        "audio_base64": b64,
        "bytes": size,
        "similarity": id_result.get("similarity"),
    }


@router.post("/speaker/clone_profile")
async def clone_by_profile(text: str = Form(...), speaker: str = Form(...)):
    rec = _SPEAKER_DB.get(speaker)
    if not rec:
        raise HTTPException(404, detail="unknown_speaker")
    ref_path = rec.get("audio_path")  # type: ignore
    if not isinstance(ref_path, str) or not os.path.exists(ref_path):
        raise HTTPException(500, detail="reference_audio_missing")
    b64, size = _run_xtts(text, ref_path)
    return {"speaker": speaker, "audio_base64": b64, "bytes": size}
