import sys
import types

from agentuq.analysis.analyzer import Analyzer
from agentuq.schemas.config import UQConfig
from agentuq.schemas.records import CapabilityReport, GenerationRecord, StructuredBlock, TopToken
from agentuq.schemas.results import Action, Decision, Diagnostics, Event, EventSeverity, PrimaryScoreType, SegmentMetrics, SegmentResult, UQResult


def _quiet_record() -> tuple[GenerationRecord, CapabilityReport]:
    record = GenerationRecord(
        provider="openai",
        transport="direct_api",
        model="gpt-test",
        temperature=0.0,
        top_p=1.0,
        raw_text="Paris.",
        selected_tokens=["Paris", "."],
        selected_logprobs=[-0.01, -0.01],
        top_logprobs=[
            [TopToken(token="Paris", logprob=-0.01), TopToken(token="London", logprob=-4.0)],
            [TopToken(token=".", logprob=-0.01), TopToken(token="!", logprob=-3.0)],
        ],
        structured_blocks=[StructuredBlock(type="output_text", text="Paris.", metadata={"role": "final"})],
        metadata={"request_logprobs": True, "request_topk": 2, "deterministic": True},
    )
    capability = CapabilityReport(
        selected_token_logprobs=True,
        topk_logprobs=True,
        topk_k=2,
        structured_blocks=True,
        request_attempted_logprobs=True,
        request_attempted_topk=2,
    )
    return record, capability


def _noisy_record() -> tuple[GenerationRecord, CapabilityReport]:
    raw_text = 'weather{"city":"Paris"}'
    record = GenerationRecord(
        provider="openai",
        transport="direct_api",
        model="gpt-test",
        temperature=0.8,
        top_p=1.0,
        raw_text=raw_text,
        selected_tokens=["weather", '{"city"', ":", '"Paris"', "}"],
        selected_logprobs=[-0.1, -0.2, -0.05, -3.8, -0.1],
        top_logprobs=[
            [TopToken(token="weather", logprob=-0.1), TopToken(token="search", logprob=-1.3)],
            [TopToken(token='{"city"', logprob=-0.2), TopToken(token='{"name"', logprob=-1.0)],
            [TopToken(token=":", logprob=-0.05), TopToken(token=",", logprob=-2.0)],
            [TopToken(token='"Paris"', logprob=-3.8), TopToken(token='"London"', logprob=-3.9)],
            [TopToken(token="}", logprob=-0.1), TopToken(token="]", logprob=-1.2)],
        ],
        structured_blocks=[
            StructuredBlock(
                type="function_call",
                name="weather",
                arguments='{"city":"Paris"}',
                text=raw_text,
                char_start=0,
                char_end=len(raw_text),
                metadata={"token_grounded": True},
            )
        ],
        metadata={"request_logprobs": True, "request_topk": 2, "deterministic": False},
    )
    capability = CapabilityReport(
        selected_token_logprobs=True,
        topk_logprobs=True,
        topk_k=2,
        structured_blocks=True,
        function_call_structure=True,
        request_attempted_logprobs=True,
        request_attempted_topk=2,
    )
    return record, capability


def _multi_driver_result() -> UQResult:
    _record, capability = _quiet_record()
    driver_event_1 = Event(
        type="LOW_MARGIN_CLUSTER",
        severity=EventSeverity.WARN,
        segment_id="seg-1",
        message="Repeated low-margin tokens in segment.",
        details={"low_margin_run_max": 2, "min_run": 1, "low_margin_rate": 0.2, "threshold": 0.25},
    )
    driver_event_2 = Event(
        type="LOW_MARGIN_CLUSTER",
        severity=EventSeverity.WARN,
        segment_id="seg-2",
        message="Repeated low-margin tokens in segment.",
        details={"low_margin_run_max": 1, "min_run": 1, "low_margin_rate": 0.1, "threshold": 0.25},
    )
    return UQResult(
        primary_score=2.0,
        primary_score_type=PrimaryScoreType.G_NLL,
        mode="canonical",
        capability_level=capability.level,
        capability_report=capability,
        segments=[
            SegmentResult(
                id="seg-1",
                kind="final_answer_text",
                priority="informational",
                text="First prose span.",
                token_span=(0, 3),
                primary_score=1.2,
                metrics=SegmentMetrics(low_margin_run_max=2, low_margin_rate=0.2, max_surprise=0.8),
                events=[driver_event_1],
                recommended_action=Action.CONTINUE_WITH_ANNOTATION,
            ),
            SegmentResult(
                id="seg-2",
                kind="final_answer_text",
                priority="informational",
                text="Second prose span.",
                token_span=(3, 5),
                primary_score=0.8,
                metrics=SegmentMetrics(low_margin_run_max=1, low_margin_rate=0.1, max_surprise=0.7),
                events=[driver_event_2],
                recommended_action=Action.CONTINUE_WITH_ANNOTATION,
            ),
        ],
        events=[driver_event_1, driver_event_2],
        action=Action.CONTINUE_WITH_ANNOTATION,
        diagnostics=Diagnostics(token_count=5),
        decision=Decision(
            action=Action.CONTINUE_WITH_ANNOTATION,
            rationale="Policy preset balanced selected continue_with_annotation based on segment events.",
        ),
    )


def test_pretty_summary_includes_explanatory_event_thresholds():
    analyzer = Analyzer(UQConfig(mode="realized"))
    record, capability = _noisy_record()
    result = analyzer.analyze_step(record, capability)

    rendered = result.pretty()

    assert result.resolved_thresholds is not None
    assert "Summary" in rendered
    assert "recommended_action:" in rendered
    assert "rationale:" in rendered
    assert "mode: realized" in rendered
    assert "whole_response_score:" in rendered
    assert "whole_response_score_note: Summarizes the full emitted path; it does not determine the recommended action by itself." in rendered
    assert "Risk Summary" in rendered
    assert "decision_driving_segment:" in rendered
    assert "decision_driving_segments:" in rendered
    assert "decision_driver_preview:" in rendered
    assert "decision_note: The recommended action comes from the segment events and policy mapping in this section." in rendered
    assert "capability: full" in rendered
    assert "Segments" in rendered
    assert "tool argument value" in rendered
    assert "ARGUMENT_VALUE_UNCERTAIN" in rendered
    assert "action_head_surprise=" in rendered


def test_pretty_compact_omits_segment_section_for_quiet_result():
    analyzer = Analyzer(UQConfig(mode="auto"))
    record, capability = _quiet_record()
    result = analyzer.analyze_step(record, capability)

    rendered = result.pretty(verbosity="compact")

    assert "Summary" in rendered
    assert "mode: canonical" in rendered
    assert "capability: full" in rendered
    assert "Segments" not in rendered
    assert "Highlights" not in rendered


def test_pretty_renders_cluster_events_from_actual_trigger_details():
    record = GenerationRecord(
        provider="openai",
        transport="direct_api",
        model="gpt-test",
        temperature=0.0,
        top_p=1.0,
        raw_text="hello",
        selected_tokens=["hello"],
        selected_logprobs=[-0.2],
        top_logprobs=[[TopToken(token="hello", logprob=-0.2), TopToken(token="hullo", logprob=-0.21), TopToken(token="hey", logprob=-0.22)]],
        structured_blocks=[StructuredBlock(type="output_text", text="hello", metadata={"role": "final"})],
        metadata={"request_logprobs": True, "request_topk": 3, "deterministic": True},
    )
    capability = CapabilityReport(
        selected_token_logprobs=True,
        topk_logprobs=True,
        topk_k=3,
        structured_blocks=True,
        request_attempted_logprobs=True,
        request_attempted_topk=3,
    )
    rendered = Analyzer(UQConfig(mode="canonical", tolerance="strict")).analyze_step(record, capability).pretty()

    assert "low_margin_run_max=1 >= min_run=1" in rendered
    assert "mean_margin_log" not in rendered


def test_pretty_debug_can_show_all_thresholds():
    analyzer = Analyzer(UQConfig(mode="auto"))
    record, capability = _quiet_record()
    result = analyzer.analyze_step(record, capability)

    rendered = result.pretty(verbosity="debug", show_thresholds="all")

    assert "Technical Details" in rendered
    assert "capability_details:" in rendered
    assert "Segments" in rendered
    assert "surprise:" in rendered
    assert "margin:" in rendered
    assert "entropy:" in rendered
    assert "rank:" in rendered
    assert "thresholds:" in rendered
    assert "low_margin_log=" in rendered
    assert "action_head_surprise=" in rendered
    assert "debug_kind: final_answer_text" in rendered


def test_pretty_surfaces_capability_gaps_before_segments():
    analyzer = Analyzer(UQConfig(mode="auto"))
    record, _capability = _quiet_record()
    degraded = CapabilityReport(
        selected_token_logprobs=True,
        topk_logprobs=False,
        structured_blocks=True,
        request_attempted_logprobs=True,
        request_attempted_topk=2,
        degraded_reason="router removed top-k support",
    )

    result = analyzer.analyze_step(record, degraded)
    rendered = result.pretty()

    assert "Capability Gaps" in rendered
    assert "Selected-token logprobs are available, but top-k diagnostics are unavailable." in rendered
    assert "router removed top-k support" in rendered
    assert rendered.index("Capability Gaps") < rendered.index("Segments")


def test_pretty_clarifies_when_multiple_segments_share_the_decision():
    rendered = _multi_driver_result().pretty()

    assert "decision_driving_segment: representative segment:" in rendered
    assert "2 matching drivers" in rendered
    assert "decision_driver_type: informational prose spans" in rendered
    assert "The first line shows a representative driver; the list below shows all matching drivers." in rendered


def test_rich_render_requires_optional_dependency():
    import builtins

    analyzer = Analyzer(UQConfig(mode="auto"))
    record, capability = _quiet_record()
    result = analyzer.analyze_step(record, capability)
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "rich.console":
            raise ImportError("rich unavailable")
        return real_import(name, globals, locals, fromlist, level)

    builtins.__import__ = fake_import
    try:
        try:
            result.rich_renderable()
        except RuntimeError as exc:
            assert "pip install agentuq[rich]" in str(exc)
        else:
            raise AssertionError("Expected missing rich dependency to raise RuntimeError")
    finally:
        builtins.__import__ = real_import


def test_rich_renderable_uses_shared_sections_with_fake_rich(monkeypatch):
    class FakeText:
        def __init__(self) -> None:
            self.parts: list[str] = []

        def append(self, text: str, style: str | None = None) -> None:
            self.parts.append(text)

        def __str__(self) -> str:
            return "".join(self.parts)

    class FakeTable:
        def __init__(self, *_args, **_kwargs) -> None:
            self.rows: list[tuple[str, ...]] = []
            self.expand = False

        @classmethod
        def grid(cls, *_args, **_kwargs):
            return cls()

        def add_column(self, *_args, **_kwargs) -> None:
            return None

        def add_row(self, *values) -> None:
            self.rows.append(tuple(str(value) for value in values))

        def __str__(self) -> str:
            return "\n".join(" | ".join(row) for row in self.rows)

    class FakePanel:
        def __init__(self, renderable, title: str = "", border_style: str = "") -> None:
            self.renderable = renderable
            self.title = title
            self.border_style = border_style

        def __str__(self) -> str:
            return f"{self.title}\n{self.renderable}"

    class FakeGroup:
        def __init__(self, *renderables) -> None:
            self.renderables = renderables

        def __str__(self) -> str:
            return "\n".join(str(renderable) for renderable in self.renderables)

    class FakeConsole:
        def __init__(self) -> None:
            self.output: list[str] = []

        def print(self, renderable) -> None:
            self.output.append(str(renderable))

    fake_rich = types.ModuleType("rich")
    fake_console = types.ModuleType("rich.console")
    fake_panel = types.ModuleType("rich.panel")
    fake_table = types.ModuleType("rich.table")
    fake_text = types.ModuleType("rich.text")
    fake_console.Console = FakeConsole
    fake_console.Group = FakeGroup
    fake_panel.Panel = FakePanel
    fake_table.Table = FakeTable
    fake_text.Text = FakeText

    monkeypatch.setitem(sys.modules, "rich", fake_rich)
    monkeypatch.setitem(sys.modules, "rich.console", fake_console)
    monkeypatch.setitem(sys.modules, "rich.panel", fake_panel)
    monkeypatch.setitem(sys.modules, "rich.table", fake_table)
    monkeypatch.setitem(sys.modules, "rich.text", fake_text)

    analyzer = Analyzer(UQConfig(mode="realized"))
    record, capability = _noisy_record()
    result = analyzer.analyze_step(record, capability)

    renderable = result.rich_renderable(verbosity="debug", show_thresholds="all")
    rendered = str(renderable)

    assert "Summary" in rendered
    assert "Risk Summary" in rendered
    assert "whole response score" in rendered
    assert "decision driving segment" in rendered
    assert "decision driver preview" in rendered
    assert "decision note" in rendered
    assert "Segments" in rendered
    assert "tool argument value" in rendered
    assert "code=ARGUMENT_VALUE_UNCERTAIN" in rendered
    assert "thresholds" in rendered

    multi_driver_rendered = str(_multi_driver_result().rich_renderable())
    assert "representative segment:" in multi_driver_rendered
    assert "2 matching drivers" in multi_driver_rendered
    assert "informational prose spans" in multi_driver_rendered

    console = FakeConsole()
    result.rich_console_render(console=console)
    assert console.output
    assert "Summary" in console.output[0]


def test_pretty_rejects_invalid_options():
    analyzer = Analyzer(UQConfig(mode="auto"))
    record, capability = _quiet_record()
    result = analyzer.analyze_step(record, capability)

    try:
        result.pretty(verbosity="loud")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected invalid verbosity to raise ValueError")

    try:
        result.pretty(show_thresholds="sometimes")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected invalid threshold display to raise ValueError")
