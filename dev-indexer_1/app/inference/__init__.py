"""Inference utilities: logging + gating.

Lightweight wrappers; actual model invocation added later. Designed so:
 - Works without transformers installed (logprobs optional)
 - Can store aggregated metrics even if only top token returned (API providers)
"""
