import os
import subprocess
import tempfile
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile

# Environment overrides
WHISPER_BASE = os.getenv("WHISPER_CPP_DIR", "vendor/whisper.cpp")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small.en")
MODEL_PATH = os.path.join(WHISPER_BASE, "models", f"ggml-{WHISPER_MODEL}.bin")
BINARY_PATH = os.path.join(WHISPER_BASE, "main")

router = APIRouter(prefix="/audio", tags=["audio"])


@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...), language: Optional[str] = None):
    if not os.path.exists(BINARY_PATH):
        raise HTTPException(
            status_code=500, detail="whisper.cpp binary not built (run setup script)"
        )
    if not os.path.exists(MODEL_PATH):
        raise HTTPException(status_code=500, detail=f"model not found: {MODEL_PATH}")
    # Save to temp
    suffix = os.path.splitext(file.filename or "upload.wav")[1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name
    cmd = [BINARY_PATH, "-m", MODEL_PATH, "-f", tmp_path, "-otxt"]
    if language:
        cmd += ["-l", language]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        os.unlink(tmp_path)
        raise HTTPException(status_code=504, detail="transcription timeout")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    if proc.returncode != 0:
        raise HTTPException(
            status_code=500, detail=f"whisper.cpp failed: {proc.stderr[-400:]}"
        )
    # Output text file is same path with .txt
    txt_path = tmp_path + ".txt"
    transcript = ""
    if os.path.exists(txt_path):
        with open(txt_path, "r") as f:
            transcript = f.read().strip()
        os.unlink(txt_path)
    else:
        # Some builds print transcript directly to stdout
        transcript = proc.stdout.strip()
    return {"model": WHISPER_MODEL, "language": language, "transcript": transcript}
