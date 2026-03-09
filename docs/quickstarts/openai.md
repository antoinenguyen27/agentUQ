# OpenAI Quickstart

Use the Responses API for new agentic integrations. AgentUQ supports both Responses and Chat Completions.

## Install

```bash
pip install openai
pip install -e .[dev]
```

## Minimal request with logprobs

Responses API:

```python
from openai import OpenAI
from uq_runtime.adapters.openai_responses import OpenAIResponsesAdapter
from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig

client = OpenAI()
response = client.responses.create(
    model="gpt-4.1-mini",
    input="Return the single word Paris.",
    include=["message.output_text.logprobs"],
    top_logprobs=5,
    temperature=0.0,
)

adapter = OpenAIResponsesAdapter()
analyzer = Analyzer(UQConfig(policy="balanced", tolerance="strict"))
record = adapter.capture(response, {
    "model": "gpt-4.1-mini",
    "temperature": 0.0,
    "top_p": 1.0,
    "include": ["message.output_text.logprobs"],
    "top_logprobs": 5,
})
result = analyzer.analyze_step(
    record,
    adapter.capability_report(response, {"include": ["message.output_text.logprobs"], "top_logprobs": 5, "temperature": 0.0, "top_p": 1.0}),
)
print(result.action)
```

## Capture -> analyze -> decide

Use `OpenAIResponsesAdapter` or `OpenAIChatAdapter`, then pass the normalized record into `Analyzer`.

For canonical mode, keep the request strictly greedy: `temperature=0`, `top_p=1`, and deterministic metadata in the capture request meta. If any of that is missing, AgentUQ will analyze the step in realized mode instead.

## Sample output excerpt

```text
mode=canonical
primary_score_type=g_nll
segment=final_answer_text action=continue
```

## Troubleshooting

- Chat Completions: pass `logprobs=True` and `top_logprobs=k`.
- Responses: include `message.output_text.logprobs`; do not assume function-call items carry token logprobs.
- OpenAI-family tool calls are captured structurally, but tool-name/tool-argument segments require explicit token grounding rather than incidental mentions in assistant prose.
- This example can be adapted into a local live smoke test, but AgentUQ does not run provider-backed tests in required OSS CI.
