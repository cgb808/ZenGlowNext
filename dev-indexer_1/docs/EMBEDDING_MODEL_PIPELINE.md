# Embedding Model Fine-Tune, Quantize & Serve

This pipeline lets you adapt a base embedding model (e.g. `BAAI/bge-small-en-v1.5`) to your domain, optionally LoRA fine–tune it, quantize (4/8–bit) for memory savings, and expose an HTTP `/embed` endpoint compatible with existing `EMBED_ENDPOINT` usage.

---

## Quick Path (Makefile Targets)

```bash
make train-deps                                     # install training deps (adds on top of runtime requirements)
make embed-finetune DATA=data/finetune/pairs.tsv OUTPUT=models/bge-small-finetuned EPOCHS=2 BATCH=128 LR=2e-5 USE_LORA=1
make embed-quantize MODEL=models/bge-small-finetuned OUTPUT=models/bge-small-finetuned-int8 DTYPE=int8
make embed-serve MODEL=models/bge-small-finetuned-int8 PORT=8000 NORMALIZE=1
```

Then point workers to the new endpoint:

```
EMBED_ENDPOINT=http://localhost:8000/embed
```

---

## 1. Install Dependencies (Manual Route)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt            # runtime
pip install -r requirements-train.txt      # training (torch, transformers, peft, bitsandbytes, etc.)
```

> If you only need to serve an already–built model, `requirements-train.txt` may still be required (SentenceTransformer + backend libs).

---

## 2. Prepare Training Data

Create a TSV (no header) of positive semantic pairs:

```
text_a<TAB>text_b
```

Store at `data/finetune/pairs.tsv` (create directories as needed).

Supported by `train_embedding_model.py`:

- TSV (tab–separated, 2 columns)
- CSV (comma–separated, 2 columns)
- JSONL lines with either `{ "text_a": ..., "text_b": ... }` or `{ "a":..., "b":... }` keys.

Quality Tips:

- Balance lengths (avoid systematic short vs long bias).
- Remove near duplicates (hash + Hamming / cosine filtering) to reduce overfitting.
- Curate domain–specific synonyms & contextual paraphrases.

---

## 3. Fine-Tune (LoRA Optional)

Script: `fine_tuning/training/scripts/train_embedding_model.py`

Example (manual):

```bash
python fine_tuning/training/scripts/train_embedding_model.py \
  --data data/finetune/pairs.tsv \
  --base-model BAAI/bge-small-en-v1.5 \
  --epochs 2 --batch-size 128 --lr 2e-5 \
  --output models/bge-small-finetuned \
  --use-lora
```

Key Flags:

- `--use-lora` (optional) to reduce VRAM and speed adaptation.
- `--eval-sample-size N` to run a quick similarity sanity eval (if present in script options—extend as needed).

Outputs under `models/bge-small-finetuned/` include SentenceTransformer config + adapter weights (if LoRA).

Checkpointing / Resuming: extend script (future) with `--save-every` or leverage `accelerate` for distributed.

---

## 4. (Optional) Quantize

Script: `fine_tuning/training/scripts/quantize_embedding_model.py`

Int8:

```bash
python fine_tuning/training/scripts/quantize_embedding_model.py \
  --model-path models/bge-small-finetuned \
  --output models/bge-small-finetuned-int8 --dtype int8
```

Int4:

```bash
python fine_tuning/training/scripts/quantize_embedding_model.py \
  --model-path models/bge-small-finetuned \
  --output models/bge-small-finetuned-int4 --dtype int4
```

Notes:

- Requires `bitsandbytes` (installed via `requirements-train.txt`).
- Produces a new SentenceTransformer directory preserving tokenizer + config.
- Evaluate recall / similarity drift before production swap.

---

## 5. Serve Model

Script: `scripts/serve_embedding_model.py`

Basic:

```bash
python scripts/serve_embedding_model.py --model models/bge-small-finetuned-int8 --port 8000 --normalize
```

Endpoints:

- `POST /embed` `{ "inputs": ["text1", "text2"] }` -> embeddings
- `GET /healthz` liveness
- `GET /info` model metadata (dim, device, quantization heuristic)
- `GET /metrics` request counters & latency aggregates

Test:

```bash
curl -s localhost:8000/healthz
curl -s -X POST localhost:8000/embed -H 'Content-Type: application/json' \
  -d '{"inputs":["hello world","vector database"]}' | jq .
```

Environment Overrides:

```
SERVE_MODEL, SERVE_PORT, SERVE_HOST, SERVE_DEVICE, \
SERVE_CONCURRENCY, SERVE_BATCH_SIZE, SERVE_NORMALIZE=1
```

Makefile shortcut:

```bash
make embed-serve MODEL=models/bge-small-finetuned-int8 PORT=8000 NORMALIZE=1
```

---

## 6. Point Workers / Retrieval Pipeline

Update environment (e.g., `.env`, docker-compose, k8s configmap):

```
EMBED_ENDPOINT=http://embed-model:8000/embed
```

Restart dependent services to pick up the new endpoint.

---

## 7. Validation & Benchmarking (Recommended)

Create a small evaluation set of (anchor, positive, hard_negative) triples. Run cosine similarity before & after fine–tune:

1. Encode with base model.
2. Encode with fine–tuned / quantized model.
3. Track Mean Reciprocal Rank (MRR) or Hit@K improvements.

Add a lightweight script (future): `scripts/eval_embedding_model.py` to automate.

---

## 8. Operational Considerations

- Concurrency: `--concurrency` semaphore limits concurrent encode calls (avoid GPU memory spikes).
- Normalization: `--normalize` outputs unit vectors (skip if downstream handles normalization once during indexing).
- Cold Start: First request triggers any lazy weight init; warm up with a small dummy batch.
- Observability: `/metrics` is minimal—integrate with Prometheus by adding proper exposition formatting if needed.

---

## 9. Licensing

Verify upstream base model license (e.g., BAAI/bge) for commercial redistribution. Maintain attribution where required.

---

## 10. Roadmap (Next Enhancements)

- Add evaluation script & CI threshold for regression detection.
- Automate LoRA adapter merge & export full precision variant.
- Support optional negative sampling (MultipleNegativesRankingLoss already implicit—extend dataset prep for hard negatives).
- Integrate retrieval pipeline swap + A/B test harness.

---

## Reference Scripts

| Purpose   | Script Path                                                |
| --------- | ---------------------------------------------------------- |
| Fine-tune | `fine_tuning/training/scripts/train_embedding_model.py`    |
| Quantize  | `fine_tuning/training/scripts/quantize_embedding_model.py` |
| Serve     | `scripts/serve_embedding_model.py`                         |

---

## Minimal Smoke Test

```bash
echo -e "hello\tworld" > data/finetune/pairs.tsv
make train-deps
make embed-finetune DATA=data/finetune/pairs.tsv OUTPUT=models/test-embed EPOCHS=1 BATCH=8
make embed-serve MODEL=models/test-embed PORT=8010 NORMALIZE=1 &
sleep 5
curl -s -X POST localhost:8010/embed -H 'Content-Type: application/json' -d '{"inputs":["hello","world"]}' | jq '.dim'
```

You should see the embedding dimension printed.

---

Happy embedding evolution.
