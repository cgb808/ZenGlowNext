# Inference Logging & Logprob Gating

## Current State
- No runtime HuggingFace `transformers` dependency installed (only vendor conversion scripts reference it).
- No existing inference wrapper producing logits/logprobs.
- Added schema (`sql/inference_logging.sql`) + Python helpers (`app/inference/`).

## Goals
1. Capture model uncertainty (avg logprob, entropy, top1 probability).
2. Persist events & (optionally) per-token logprobs for analysis, retraining, guardrails.
3. Derive a gating decision: proceed | reflect | retrieve | abstain.
4. Leverage TimescaleDB for retention + rollups (optional).

## DB Schema
Tables:
- model_inference_events: aggregated metrics & decision.
- model_inference_token_stats: detailed generated token logprobs.

Metrics stored:
- avg_logprob: mean log p(token) for generated tokens.
- entropy: approximate uncertainty (computed from subset of logprobs).
- top1_prob: exp(logprob_first_token) heuristic.

## Gating Strategy (Initial Heuristics)
| Condition | Action |
|-----------|--------|
| avg_logprob < -1.5 | reflect (ask model for reasoning / chain-of-thought style clarification) |
| entropy > 2.5 | retrieve (augment with external knowledge) |
| top1_prob < 0.20 | abstain (respond: "I’m not certain—let’s clarify.") |
| else | proceed |

These thresholds will be tuned with empirical distributions (p50/p90).

## Integration Flow
1. Run model inference obtaining logits (local) or provider logprobs.
2. Convert to token_logprobs: list[(token, logprob)].
3. Call `gating.gate_from_token_logprobs` or compute metrics + `decide_action`.
4. Execute action:
   - proceed: return answer.
   - reflect: run a secondary prompt (self-reflection) before final answer.
   - retrieve: perform retrieval (e.g., vector DB) then re-query model.
   - abstain: return clarification prompt / ask user for more context.
5. Persist via `logging.log_inference_event(...)` supplying final decision.

## Timescale Enablement (Optional)
```
CREATE EXTENSION IF NOT EXISTS timescaledb;
SELECT create_hypertable('model_inference_events', 'ts', if_not_exists => TRUE);
SELECT add_retention_policy('model_inference_events', INTERVAL '30 days');
```

## Example Wrapper (Pseudo)
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

tok = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)
inputs = tok(prompt, return_tensors='pt')
out = model.generate(**inputs, max_new_tokens=64, output_scores=True, return_dict_in_generate=True)
seq = out.sequences[0][inputs['input_ids'].shape[1]:]
logits = torch.stack(out.scores)  # [T, 1, V]
probs = torch.log_softmax(logits, dim=-1)
token_logprobs = []
for t, tok_id in enumerate(seq):
    lp = float(probs[t, 0, tok_id])
    token_logprobs.append((tok.convert_ids_to_tokens([tok_id])[0], lp))
decision = gate_from_token_logprobs(token_logprobs)
log_inference_event(dsn, model_name, user_id, prompt_tokens=len(inputs['input_ids'][0]), completion_tokens=len(seq), latency_ms=lat, token_logprobs=token_logprobs, decision=decision, meta={"prompt_hash": "..."})
```

## Privacy / PII
- Do not store full prompts by default—only token-level probabilities & hashed prompt (e.g., SHA256).
- `meta` bucket can include a truncated prompt preview (<128 chars) if needed.

## Next Steps
- Wire into actual inference service once model integration selected.
- Add rollup view (hourly aggregates) for dashboards.
- Add decision distribution monitoring (alert if abstain rate > threshold).
