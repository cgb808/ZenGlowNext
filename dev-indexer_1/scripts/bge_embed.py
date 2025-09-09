#!/usr/bin/env python3
"""
BGE small embedding helper (default: BAAI/bge-small-en-v1.5, 384-dim).

- Minimal mean-pooling over last_hidden_state using attention mask.
- Optional device selection and (best-effort) 8-bit loading if available.
- Thin CLI: read texts from --input (one per line) or --json '[...]' and emit JSON.

Notes:
- Requires transformers + torch. In containers, build with INSTALL_HEAVY_EXTRAS=1
  or install these locally in your environment.
- If storing into Postgres/pgvector, ensure your table vector dimension matches
  the model (e.g., 384 for bge-small-en-v1.5).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Iterable, List, Optional

DEFAULT_EMBED_MODEL = os.environ.get("EMBED_MODEL", "BAAI/bge-small-en-v1.5")


def _import_heavy():
    try:
        import torch  # type: ignore
        from transformers import AutoTokenizer, AutoModel  # type: ignore
    except Exception as e:  # pragma: no cover - runtime guard
        raise SystemExit(
            "Missing heavy deps. Install torch+transformers or rebuild with INSTALL_HEAVY_EXTRAS=1."
        ) from e
    return torch, AutoTokenizer, AutoModel


def load_model(
    model_name: str = DEFAULT_EMBED_MODEL,
    device: Optional[str] = None,
    load_in_8bit: bool = False,
):
    """
    Load tokenizer + model. If load_in_8bit=True and bitsandbytes stack is present,
    attempt to load 8-bit; otherwise fall back gracefully to standard fp32/fp16.
    """
    torch, AutoTokenizer, AutoModel = _import_heavy()
    tok = AutoTokenizer.from_pretrained(model_name)

    mdl = None
    if load_in_8bit:
        try:
            # Best-effort 8-bit path; requires bitsandbytes + accelerate
            mdl = AutoModel.from_pretrained(model_name, load_in_8bit=True, device_map="auto")
            device = device or ("cuda" if torch.cuda.is_available() else "cpu")
            # device_map handles placement; don't .to(device) in 8-bit mode
        except Exception:
            # Fallback to normal load if 8-bit not available
            pass

    if mdl is None:
        mdl = AutoModel.from_pretrained(model_name)
        device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        mdl.to(device)

    mdl.eval()
    return tok, mdl


def embed_texts(
    texts: List[str],
    tok,
    mdl,
    device: Optional[str] = None,
    max_length: int = 512,
) -> List[List[float]]:
    """Compute mean-pooled embeddings for a batch of texts."""
    torch, _, _ = _import_heavy()
    if device is None:
        device = next(mdl.parameters()).device if hasattr(mdl, "parameters") else (
            "cuda" if torch.cuda.is_available() else "cpu"
        )
    out_vectors: List[List[float]] = []
    with torch.no_grad():
        for t in texts:
            inputs = tok(t, return_tensors="pt", truncation=True, max_length=max_length)
            inputs = {k: v.to(device) for k, v in inputs.items()}
            outputs = mdl(**inputs)
            last_hidden = outputs.last_hidden_state  # [1, seq, hidden]
            mask = inputs["attention_mask"].unsqueeze(-1).expand(last_hidden.size()).float()
            masked = last_hidden * mask
            summed = masked.sum(dim=1)
            counts = mask.sum(dim=1).clamp(min=1e-9)
            mean = summed / counts
            out_vectors.append(mean[0].detach().cpu().float().tolist())
    return out_vectors


def _read_texts(args) -> List[str]:
    if args.json:
        data = json.loads(args.json)
        if not isinstance(data, list):
            raise SystemExit("--json must be a JSON array of strings")
        return [str(x) for x in data]
    if args.input and args.input != "-":
        with open(args.input, "r", encoding="utf-8") as f:
            return [line.rstrip("\n") for line in f if line.strip()]
    # stdin
    return [line.rstrip("\n") for line in sys.stdin if line.strip()]


def main() -> int:  # pragma: no cover
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=DEFAULT_EMBED_MODEL)
    p.add_argument("--device", default=None)
    p.add_argument("--json", help="JSON array of strings")
    p.add_argument("--input", "-i", help="Path to newline-delimited text file (or '-' for stdin)")
    p.add_argument("--output", "-o", help="Output JSON path (defaults to stdout)")
    p.add_argument("--max-length", type=int, default=512)
    p.add_argument("--load-8bit", action="store_true", help="Attempt 8-bit model load if available")
    args = p.parse_args()

    tok, mdl = load_model(args.model, args.device, args.load_8bit)
    texts = _read_texts(args)
    vecs = embed_texts(texts, tok, mdl, args.device, args.max_length)

    dim = len(vecs[0]) if vecs else 0
    result = {"model": args.model, "device": args.device, "dim": dim, "embeddings": vecs}
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f)
    else:
        json.dump(result, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
