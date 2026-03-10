"""Gemini adapter."""

from __future__ import annotations

from typing import Any

from agentuq.adapters.base import as_dict, block, infer_capability
from agentuq.schemas.records import CapabilityReport, GenerationRecord, TopToken


class GeminiAdapter:
    provider = "gemini"
    transport = "direct_api"

    def capture(self, response: Any, request_meta: dict | None = None) -> GenerationRecord:
        data = as_dict(response)
        candidates = data.get("candidates") or []
        candidate = candidates[0] if candidates else {}
        content = candidate.get("content") or {}
        parts = content.get("parts") or []
        text = "".join(part.get("text", "") for part in parts)
        logprobs_result = candidate.get("logprobsResult") or candidate.get("logprobs_result") or {}
        chosen = logprobs_result.get("chosenCandidates") or logprobs_result.get("chosen_candidates") or []
        top = logprobs_result.get("topCandidates") or logprobs_result.get("top_candidates") or []
        tokens: list[str] = []
        logprobs: list[float] = []
        top_logprobs: list[list[TopToken]] = []
        for index, item in enumerate(chosen):
            token = item.get("token") or item.get("text") or ""
            tokens.append(token)
            logprobs.append(float(item.get("logProbability") or item.get("log_probability") or item.get("logprob") or 0.0))
            bucket = top[index].get("candidates") if index < len(top) and isinstance(top[index], dict) else top[index] if index < len(top) else []
            top_logprobs.append(
                [
                    TopToken(
                        token=str(candidate_item.get("token") or candidate_item.get("text")),
                        logprob=float(candidate_item.get("logProbability") or candidate_item.get("log_probability") or candidate_item.get("logprob") or 0.0),
                    )
                    for candidate_item in bucket or []
                    if (candidate_item.get("token") or candidate_item.get("text")) is not None
                ]
            )
        blocks = [block("output_text", text=text, metadata={"role": "final"})] if text else []
        return GenerationRecord(
            provider=self.provider,
            transport=self.transport,
            model=data.get("modelVersion") or (request_meta or {}).get("model") or "unknown",
            request_id=data.get("responseId"),
            temperature=(request_meta or {}).get("temperature"),
            top_p=(request_meta or {}).get("topP"),
            max_tokens=(request_meta or {}).get("maxOutputTokens"),
            raw_text=text,
            selected_tokens=tokens,
            selected_logprobs=logprobs or None,
            top_logprobs=top_logprobs or None,
            structured_blocks=blocks,
            metadata={
                "request_logprobs": bool((request_meta or {}).get("responseLogprobs")),
                "request_topk": (request_meta or {}).get("logprobs"),
                "deterministic": (request_meta or {}).get("deterministic"),
            },
        )

    def capability_report(self, response: Any, request_meta: dict | None = None) -> CapabilityReport:
        return infer_capability(self.capture(response, request_meta), request_meta, declared_support=True)

