"""MiniMax OpenAI-compatible adapter."""

from __future__ import annotations

from typing import Any

from agentuq.adapters.base import as_dict, infer_capability
from agentuq.adapters.openai_chat import OpenAIChatAdapter
from agentuq.schemas.records import CapabilityReport, GenerationRecord


class MiniMaxAdapter:
    """Adapter for MiniMax chat completions.

    MiniMax exposes an OpenAI-compatible chat completions endpoint at
    ``https://api.minimax.io/v1`` and supports ``logprobs`` and
    ``top_logprobs`` parameters in the standard OpenAI format.

    The adapter delegates to :class:`OpenAIChatAdapter` for response
    normalization and overrides provider metadata.
    """

    provider = "minimax"
    transport = "direct_api"

    def __init__(self) -> None:
        self._delegate = OpenAIChatAdapter()

    @classmethod
    def from_response(cls, response: Any, request_meta: dict | None = None) -> GenerationRecord:
        return cls().capture(response, request_meta)

    def capture(self, response: Any, request_meta: dict | None = None) -> GenerationRecord:
        record = self._delegate.capture(as_dict(response), request_meta)
        record.provider = self.provider
        record.transport = self.transport
        return record

    def capability_report(self, response: Any, request_meta: dict | None = None) -> CapabilityReport:
        return infer_capability(self.capture(response, request_meta), request_meta, declared_support=True)
