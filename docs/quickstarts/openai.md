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
    input="Return a tool call for weather in Paris.",
    tools=[{
        "type": "function",
        "name": "weather_lookup",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
            "additionalProperties": False,
        },
    }],
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
    "include_output_text_logprobs": True,
    "top_logprobs": 5,
    "deterministic": True,
})
result = analyzer.analyze_step(record, adapter.capability_report(response, {"include_output_text_logprobs": True, "top_logprobs": 5}))
print(result.action)
```

## Capture -> analyze -> decide

Use `OpenAIResponsesAdapter` or `OpenAIChatAdapter`, then pass the normalized record into `Analyzer`.

For canonical mode, keep the request strictly greedy: `temperature=0`, `top_p=1`, and deterministic metadata in the capture request meta. If any of that is missing, AgentUQ will analyze the step in realized mode instead.

## Sample output excerpt

```text
mode=canonical
primary_score_type=g_nll
segment=tool_argument_leaf jsonpath=$.city action=regenerate_segment
```

## Troubleshooting

- Chat Completions: pass `logprobs=True` and `top_logprobs=k`.
- Responses: include `message.output_text.logprobs`; verify output content actually contains token details.
- This example can be adapted into a local live smoke test, but AgentUQ does not run provider-backed tests in required OSS CI.
