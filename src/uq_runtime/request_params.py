"""Provider-specific request helpers."""

from __future__ import annotations


def request_params(provider: str, mode: str = "auto", topk: int = 5) -> dict:
    provider = provider.lower()
    deterministic = mode == "canonical"
    if provider == "openai":
        params = {
            "top_logprobs": topk,
            "temperature": 0.0 if deterministic else 0.7,
            "top_p": 1.0,
            "deterministic": deterministic,
        }
        params["include_output_text_logprobs"] = True
        params["logprobs"] = True
        return params
    if provider == "openrouter":
        return {
            "logprobs": True,
            "top_logprobs": topk,
            "provider": {"require_parameters": True},
            "temperature": 0.0 if deterministic else 0.7,
            "top_p": 1.0,
            "deterministic": deterministic,
        }
    if provider == "litellm":
        return {
            "logprobs": True,
            "top_logprobs": topk,
            "drop_params": False,
            "temperature": 0.0 if deterministic else 0.7,
            "top_p": 1.0,
            "deterministic": deterministic,
        }
    if provider == "gemini":
        return {
            "responseLogprobs": True,
            "logprobs": topk,
            "temperature": 0.0 if deterministic else 0.7,
            "topP": 1.0,
            "deterministic": deterministic,
        }
    if provider in {"fireworks", "together"}:
        return {
            "logprobs": True if provider == "fireworks" else topk,
            "top_logprobs": topk if provider == "fireworks" else None,
            "temperature": 0.0 if deterministic else 0.7,
            "top_p": 1.0,
            "deterministic": deterministic,
        }
    raise ValueError(f"Unsupported provider for request helper: {provider}")

