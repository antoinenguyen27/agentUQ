"""Fireworks OpenAI-compatible adapter."""

from __future__ import annotations

from typing import Any

from uq_runtime.adapters.base import as_dict
from uq_runtime.adapters.openai_chat import OpenAIChatAdapter
from uq_runtime.schemas.records import CapabilityReport, GenerationRecord


class FireworksAdapter:
    provider = "fireworks"
    transport = "direct_api"

    def __init__(self) -> None:
        self._delegate = OpenAIChatAdapter()

    def capture(self, response: Any, request_meta: dict | None = None) -> GenerationRecord:
        record = self._delegate.capture(as_dict(response), request_meta)
        record.provider = self.provider
        return record

    def capability_report(self, response: Any, request_meta: dict | None = None) -> CapabilityReport:
        record = self.capture(response, request_meta)
        return self._delegate.capability_report(as_dict(response), request_meta).model_copy(update={"provider_declared_support": True})

