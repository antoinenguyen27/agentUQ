---
title: Fireworks Quickstart
description: Normalize Fireworks chat completions into AgentUQ records and capability reports.
slug: /quickstarts/fireworks
sidebar_position: 6
---

# Fireworks Quickstart

Fireworks exposes chat completions with an OpenAI-compatible `choices[0].logprobs.content` shape when you request `logprobs=True`, with compatibility fallbacks for older token-array payloads.

**Status:** `Preview`

## Install

```bash
pip install agentuq openai
```

## Minimal request with readable terminal output

```python
from openai import OpenAI
from agentuq import Analyzer, UQConfig
from agentuq.adapters.fireworks import FireworksAdapter

client = OpenAI(base_url="https://api.fireworks.ai/inference/v1", api_key="...")
response = client.chat.completions.create(
    model="accounts/fireworks/models/llama-v3p1-8b-instruct",
    messages=[{"role": "user", "content": "Return a SQL query for active users."}],
    logprobs=True,
    top_logprobs=5,
    temperature=0.0,
    top_p=1.0,
)

adapter = FireworksAdapter()
analyzer = Analyzer(UQConfig(policy="balanced", tolerance="strict"))
record = adapter.capture(
    response,
    {
        "model": "accounts/fireworks/models/llama-v3p1-8b-instruct",
        "logprobs": True,
        "top_logprobs": 5,
        "temperature": 0.0,
        "top_p": 1.0,
    },
)
result = analyzer.analyze_step(
    record,
    adapter.capability_report(
        response,
        {
            "model": "accounts/fireworks/models/llama-v3p1-8b-instruct",
            "logprobs": True,
            "top_logprobs": 5,
            "temperature": 0.0,
            "top_p": 1.0,
        },
    ),
)
print(result.pretty())
```

## Sample output excerpt

```text
Summary
  recommended_action: Dry-run verify
  rationale: Policy preset balanced selected dry_run_verify based on segment events.
  mode: canonical
  whole_response_score: 3.844 g_nll
  whole_response_score_note: Summarizes the full emitted path; it does not determine the recommended action by itself.
  capability: full

Segments
  SQL clause [critical_action] -> Dry-run verify
    text: WHERE active = true
    surprise: score=1.922 nll=1.922 avg=0.641 p95=4.182 max=4.182 tail=4.182
    events:
      - LOW_PROB_SPIKE [high]: Highly improbable token spike detected. (max_surprise=4.182 >= spike_surprise=3.500)
```

## Troubleshooting

- Request `logprobs=True` and `top_logprobs=k`.
- AgentUQ prefers the OpenAI-compatible `choices[0].logprobs.content` format, and falls back to legacy token arrays or `raw_output.completion_logprobs` when needed.
- In this OSS repo, live Fireworks checks are manual and opt-in.
