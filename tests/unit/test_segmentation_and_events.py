from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig
from uq_runtime.schemas.records import CapabilityReport, GenerationRecord, StructuredBlock, TopToken
from uq_runtime.schemas.results import Action


def test_json_and_browser_segmentation():
    record = GenerationRecord(
        provider="openai",
        transport="direct_api",
        model="gpt-test",
        temperature=0.0,
        top_p=1.0,
        raw_text='click(selector="#submit")\n{"url":"https://example.com","count":2}',
        selected_tokens=["click", "(", 'selector', "=", '"#submit"', ")", '{"url"', ":", '"https://example.com"', ",", '"count"', ":", "2", "}"],
        selected_logprobs=[-0.1] * 14,
        top_logprobs=[[TopToken(token="x", logprob=-0.1), TopToken(token="y", logprob=-0.4)]] * 14,
        structured_blocks=[StructuredBlock(type="json", text='{"url":"https://example.com","count":2}')],
        metadata={"request_logprobs": True, "request_topk": 2, "deterministic": True},
    )
    capability = CapabilityReport(selected_token_logprobs=True, topk_logprobs=True, topk_k=2, structured_blocks=True, request_attempted_logprobs=True, request_attempted_topk=2)
    result = Analyzer(UQConfig()).analyze_step(record, capability)
    kinds = {segment.kind for segment in result.segments}
    assert "browser_action" in kinds
    assert "browser_selector" in kinds
    assert "json_leaf" in kinds


def test_schema_invalid_blocks_execution():
    raw_text = 'tool{"city":}'
    record = GenerationRecord(
        provider="openai",
        transport="direct_api",
        model="gpt-test",
        raw_text=raw_text,
        selected_tokens=["tool", '{"city"', ":", "}"],
        selected_logprobs=[-0.1, -0.2, -0.3, -0.2],
        structured_blocks=[
            StructuredBlock(
                type="function_call",
                name="tool",
                arguments='{"city":}',
                text=raw_text,
                char_start=0,
                char_end=len(raw_text),
                metadata={"token_grounded": True},
            )
        ],
        metadata={"request_logprobs": True, "deterministic": True},
    )
    capability = CapabilityReport(selected_token_logprobs=True, topk_logprobs=False, structured_blocks=True, function_call_structure=True, request_attempted_logprobs=True)
    result = Analyzer(UQConfig(mode="realized", capability={"fail_on_missing_topk": False})).analyze_step(record, capability)
    assert any(event.type == "SCHEMA_INVALID" for event in result.events)
    assert result.decision.action == Action.BLOCK_EXECUTION


def test_off_topk_token_event_in_realized_mode():
    record = GenerationRecord(
        provider="openai",
        transport="direct_api",
        model="gpt-test",
        temperature=0.8,
        raw_text="DROP TABLE users",
        selected_tokens=["DROP", " TABLE", " users"],
        selected_logprobs=[-0.5, -1.0, -1.2],
        top_logprobs=[
            [TopToken(token="SELECT", logprob=-0.2), TopToken(token="UPDATE", logprob=-0.4)],
            [TopToken(token=" FROM", logprob=-0.4), TopToken(token=" users", logprob=-0.5)],
            [TopToken(token=" accounts", logprob=-0.3), TopToken(token=" logs", logprob=-0.7)],
        ],
        metadata={"request_logprobs": True, "request_topk": 2, "deterministic": False},
    )
    capability = CapabilityReport(selected_token_logprobs=True, topk_logprobs=True, topk_k=2, request_attempted_logprobs=True, request_attempted_topk=2)
    result = Analyzer(UQConfig(mode="realized")).analyze_step(record, capability)
    assert any(event.type == "OFF_TOPK_TOKEN" for event in result.events)
