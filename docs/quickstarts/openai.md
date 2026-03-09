# OpenAI Quickstart

Use the Responses API for new agentic integrations. AgentUQ supports both Responses and Chat Completions.

## Install

```bash
pip install openai
pip install -e .[dev]
```

## Minimal request with readable terminal output

Responses API:

```python
from openai import OpenAI
from uq_runtime.adapters.openai_responses import OpenAIResponsesAdapter
from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig

client = OpenAI()
request_meta = {
    "model": "gpt-4.1-mini",
    "include": ["message.output_text.logprobs"],
    "top_logprobs": 5,
    "temperature": 0.0,
    "top_p": 1.0,
}
response = client.responses.create(
    model=request_meta["model"],
    input="Return the single word Paris.",
    include=request_meta["include"],
    top_logprobs=request_meta["top_logprobs"],
    temperature=request_meta["temperature"],
    top_p=request_meta["top_p"],
)

adapter = OpenAIResponsesAdapter()
analyzer = Analyzer(UQConfig(policy="balanced", tolerance="strict"))
record = adapter.capture(response, request_meta)
result = analyzer.analyze_step(record, adapter.capability_report(response, request_meta))
print(result.pretty())
```

## Capture -> analyze -> decide

Use `OpenAIResponsesAdapter` or `OpenAIChatAdapter`, then pass the normalized record into `Analyzer`.

For canonical mode, keep the request strictly greedy: `temperature=0`, `top_p=1`, and deterministic metadata in the capture request meta. If any of that is missing, AgentUQ will analyze the step in realized mode instead.

For a fuller diagnostic view, use `result.pretty(verbosity="debug", show_thresholds="all")`.

## Sample output excerpt

```text
Summary
  mode: canonical
  reason: auto-selected canonical mode from strictly greedy metadata
  score: 0.021 g_nll
  action: continue
  rationale: Policy preset balanced selected continue based on segment events.
  capability: full

Segments
  final_answer_text [informational] -> continue
    text: Paris.
    metrics: score=0.021 avg_surprise=0.011 max_surprise=0.018 mean_entropy=0.104
    events: none
```

## Troubleshooting

- Chat Completions: pass `logprobs=True` and `top_logprobs=k`.
- Responses: include `message.output_text.logprobs`; do not assume function-call items carry token logprobs.
- OpenAI-family tool calls are captured structurally, but tool-name/tool-argument segments require explicit token grounding rather than incidental mentions in assistant prose.
- This example can be adapted into a local live smoke test, but AgentUQ does not run provider-backed tests in required OSS CI.
