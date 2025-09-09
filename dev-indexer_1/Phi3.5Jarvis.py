#!/usr/bin/env python3
import argparse
import torch
from typing import Optional
from transformers import AutoModelForCausalLM, AutoTokenizer
try:
    from transformers import BitsAndBytesConfig  # type: ignore
except Exception:
    BitsAndBytesConfig = None  # type: ignore
from peft import PeftModel


def infer(base: str, adapter: str, prompt: str, max_new_tokens: int = 256, quant_4bit: bool = True, temperature: Optional[float] = None) -> str:
    quant = None
    if quant_4bit and BitsAndBytesConfig is not None and torch.cuda.is_available():
        compute = torch.bfloat16 if getattr(torch.cuda, 'is_bf16_supported', lambda: False)() else torch.float16
        quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=compute, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True)

    tok = AutoTokenizer.from_pretrained(base, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base,
        **({"quantization_config": quant} if quant is not None else {}),
        device_map={"": 0} if torch.cuda.is_available() else None,
        trust_remote_code=True,
        attn_implementation="eager",
        low_cpu_mem_usage=True,
    )
    model = PeftModel.from_pretrained(model, adapter)
    # Workaround for Transformers<=4.56 cache API
    try:
        model.generation_config.cache_implementation = None
    except Exception:
        pass
    model.config.use_cache = False
    model.eval()

    # Build a chat-style prompt using template if available
    if hasattr(tok, "apply_chat_template") and getattr(tok, "chat_template", None):
        messages = [{"role": "user", "content": prompt}]
        text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    else:
        text = f"<|user|> {prompt}\n<|assistant|>"

    inputs = tok(text, return_tensors="pt").to(model.device)
    gen_kwargs = {
        "max_new_tokens": max_new_tokens,
        "do_sample": False if (temperature is None or temperature <= 0) else True,
        "temperature": max(temperature, 1e-6) if (temperature is not None and temperature > 0) else 1.0,
        "pad_token_id": tok.eos_token_id,
        "use_cache": False,
    }
    with torch.no_grad():
        out = model.generate(**inputs, **gen_kwargs)
    return tok.decode(out[0], skip_special_tokens=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="microsoft/Phi-3.5-mini-instruct")
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--max-new-tokens", type=int, default=256)
    ap.add_argument("--no-quant-4bit", action="store_true", help="Disable 4-bit loading")
    ap.add_argument("--temperature", type=float, default=None)
    args = ap.parse_args()

    text = infer(
        base=args.base,
        adapter=args.adapter,
        prompt=args.prompt,
        max_new_tokens=args.max_new_tokens,
        quant_4bit=not args.no_quant_4bit,
        temperature=args.temperature,
    )
    print(text)


if __name__ == "__main__":
    main()
