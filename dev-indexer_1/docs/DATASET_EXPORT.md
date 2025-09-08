## Family Dataset Export Quick Guide

Artifacts:
- `scripts/build_family_dataset.py` creates JSONL datasets + manifest.

Output structure (example):
```
datasets/family/
  instruction.jsonl
  conversations.jsonl
  all.jsonl
  manifest.json
```

Instruction line example:
```json
{"instruction":"Retrieve document titled 'Willow Fall 2025 Reading Assessment' for entity willow","output":{"entity_id":"willow","kind":"document","title":"Willow Fall 2025 Reading Assessment","tags":["reading","assessment","2025","fall"]},"meta":{"source":"artifact"}}
```

Conversation line example:
```json
{"messages":[{"role":"system","content":"You are a family tutoring & data assistant."},{"role":"user","content":"Can you summarize the media titled 'Willow Science Project Volcano Photo' for willow?"},{"role":"assistant","content":"The media 'Willow Science Project Volcano Photo' for willow has tags: science, project, photo."}],"meta":{"scenario":"artifact_retrieval","artifact_id":"art-2"}}
```

Manifest fields:
- `files.*.sha256`: integrity verification for transport.
- `schema.instruction` & `schema.conversation`: minimal schema contract.

Training ingestion hints:
1. For chat fine-tune frameworks (e.g., OpenAI format, Axolotl, vLLM SFT): map each `messages` array directly.
2. For instruction SFT: flatten instruction/output pairs into prompt/response with delimiter (e.g., `\n\n### Response:`).
3. Keep artifact tags in context; they supply grounded retrieval signals.
4. Optionally mix `instruction.jsonl` and `conversations.jsonl` with sampling ratio (e.g., 60/40) if not using `all.jsonl`.

Export command examples:
```
python scripts/build_family_dataset.py --out datasets/family \
  --conversation-weights artifact_retrieval=2,follow_up=1

tar -czf family_dataset.tar.gz -C datasets family
sha256sum family_dataset.tar.gz > family_dataset.tar.gz.sha256
```

Safety note: No SSNs or high-risk PII stored; birthdates only appear where policy allows (current seed adults). Downstream models should still be aligned with refusal patterns (see guardianship_policy scenario) to avoid hallucinated disclosure.
