"""Provider-specific request helpers."""

from __future__ import annotations


def request_params(provider: str, mode: str = "auto", topk: int = 5, transport: str | None = None) -> dict:
    provider = provider.lower()
    deterministic = mode == "canonical"
    if provider == "openai":
        if transport in {None, "responses"}:
            return {
                "include": ["message.output_text.logprobs"],
                "top_logprobs": topk,
                "temperature": 0.0 if deterministic else 0.7,
                "top_p": 1.0,
            }
        if transport == "chat":
            return {
                "logprobs": True,
                "top_logprobs": topk,
                "temperature": 0.0 if deterministic else 0.7,
                "top_p": 1.0,
            }
        raise ValueError(f"Unsupported OpenAI transport for request helper: {transport}")
    if provider == "openrouter":
        return {
            "logprobs": True,
            "top_logprobs": topk,
            "provider": {"require_parameters": True},
            "temperature": 0.0 if deterministic else 0.7,
            "top_p": 1.0,
        }
    if provider == "litellm":
        return {
            "logprobs": True,
            "top_logprobs": topk,
            "drop_params": False,
            "temperature": 0.0 if deterministic else 0.7,
            "top_p": 1.0,
        }
    if provider == "gemini":
        return {
            "responseLogprobs": True,
            "logprobs": topk,
            "temperature": 0.0 if deterministic else 0.7,
            "topP": 1.0,
        }
    if provider == "fireworks":
        return {
            "logprobs": True,
            "top_logprobs": topk,
            "temperature": 0.0 if deterministic else 0.7,
            "top_p": 1.0,
        }
    if provider == "together":
        return {
            "logprobs": topk,
            "temperature": 0.0 if deterministic else 0.7,
            "top_p": 1.0,
        }
    raise ValueError(f"Unsupported provider for request helper: {provider}")
