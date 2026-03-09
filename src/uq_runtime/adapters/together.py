"""Together adapter."""

from __future__ import annotations

from typing import Any

from uq_runtime.adapters.base import as_dict, block, infer_capability, normalize_top_logprobs
from uq_runtime.schemas.records import CapabilityReport, GenerationRecord


class TogetherAdapter:
    provider = "together"
    transport = "direct_api"

    def capture(self, response: Any, request_meta: dict | None = None) -> GenerationRecord:
        data = as_dict(response)
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        logprobs_payload = choice.get("logprobs") or {}
        output = data.get("output") or {}
        text = message.get("content") or output.get("text") or ""
        tokens = logprobs_payload.get("tokens") or output.get("tokens") or []
        token_logprobs = logprobs_payload.get("token_logprobs") or output.get("token_logprobs") or []
        raw_top = logprobs_payload.get("top_logprobs") or output.get("top_logprobs") or []
        top_logprobs = []
        for item in raw_top:
            if isinstance(item, dict):
                top_logprobs.append(
                    normalize_top_logprobs(
                        [{"token": token, "logprob": logprob} for token, logprob in item.items()]
                    )
                )
            elif isinstance(item, list):
                top_logprobs.append(normalize_top_logprobs(item))
            else:
                top_logprobs.append([])
        return GenerationRecord(
            provider=self.provider,
            transport=self.transport,
            model=data.get("model") or (request_meta or {}).get("model") or "unknown",
            request_id=data.get("id"),
            temperature=(request_meta or {}).get("temperature"),
            top_p=(request_meta or {}).get("top_p"),
            max_tokens=(request_meta or {}).get("max_tokens"),
            raw_text=text,
            selected_tokens=[str(token) for token in tokens],
            selected_logprobs=[float(value) for value in token_logprobs] or None,
            top_logprobs=top_logprobs or None,
            structured_blocks=[block("output_text", text=text, metadata={"role": "final"})] if text else [],
            metadata={
                "request_logprobs": bool((request_meta or {}).get("logprobs")),
                "request_topk": (request_meta or {}).get("logprobs"),
                "deterministic": (request_meta or {}).get("deterministic"),
            },
        )

    def capability_report(self, response: Any, request_meta: dict | None = None) -> CapabilityReport:
        return infer_capability(self.capture(response, request_meta), request_meta, declared_support=True)
