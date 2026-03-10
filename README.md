# AgentUQ

Single-pass runtime reliability gate for LLM agents using token logprobs.

AgentUQ turns provider-native token logprobs into localized runtime decisions for agent steps. It does not claim to know whether an output is true. It tells you where a generation looked brittle or ambiguous and whether the workflow should continue, annotate the trace, regenerate a risky span, retry the step, dry-run verify, ask for confirmation, or block execution.

## Why teams use it

- Catch brittle action-bearing spans before execution: SQL clauses, tool arguments, selectors, URLs, paths, shell flags, and JSON leaves
- Localize risk to the exact span that matters instead of treating the whole response as one opaque score
- Spend expensive verification selectively by using AgentUQ as the first-pass gate

## Install

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
```

Examples below assume the public package and import namespace `agentuq`.

## Minimal loop

```python
from openai import OpenAI

from agentuq import Analyzer, UQConfig
from agentuq.adapters.openai_responses import OpenAIResponsesAdapter

client = OpenAI()
response = client.responses.create(
    model="gpt-4.1-mini",
    input="Return the single word Paris.",
    include=["message.output_text.logprobs"],
    top_logprobs=5,
    temperature=0.0,
    top_p=1.0,
)

adapter = OpenAIResponsesAdapter()
analyzer = Analyzer(UQConfig(policy="balanced", tolerance="strict"))
record = adapter.capture(
    response,
    {
        "model": "gpt-4.1-mini",
        "include": ["message.output_text.logprobs"],
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
            "model": "gpt-4.1-mini",
            "include": ["message.output_text.logprobs"],
            "top_logprobs": 5,
            "temperature": 0.0,
            "top_p": 1.0,
        },
    ),
)

print(result.pretty())
```

## Documentation

The web docs are built with Docusaurus from the canonical Markdown in [`docs/`](docs) and the site app in [`website/`](website).

- Start here: [docs/index.mdx](docs/index.mdx)
- Get started: [docs/get-started/index.md](docs/get-started/index.md)
- Provider and framework quickstarts: [docs/quickstarts/index.md](docs/quickstarts/index.md)
- Concepts: [docs/concepts/index.md](docs/concepts/index.md)
- API reference: [docs/concepts/public_api.md](docs/concepts/public_api.md)
- Maintainers: [docs/maintainers/index.md](docs/maintainers/index.md)
- Contributing: [CONTRIBUTING.md](CONTRIBUTING.md)

## Repo layout

- [`src/agentuq`](src/agentuq): library code
- [`examples`](examples): usage examples
- [`tests`](tests): offline, contract, and optional live tests
- [`docs`](docs): canonical documentation content
- [`website`](website): Docusaurus site and Vercel-facing app

## Testing

Default pytest runs only offline tests:

```bash
python -m pytest
```

Live smoke checks are manual and opt-in:

```bash
AGENTUQ_RUN_LIVE=1 python -m pytest -m live
```
