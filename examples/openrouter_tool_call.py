from uq_runtime.adapters.openrouter import OpenRouterAdapter
from uq_runtime.analysis.analyzer import Analyzer


def main() -> None:
    response = {
        "id": "or_1",
        "model": "openai/gpt-4o-mini",
        "choices": [
            {
                "message": {
                    "content": "Checking.",
                    "tool_calls": [{"id": "call_1", "function": {"name": "weather_lookup", "arguments": '{"city":"Paris"}'}}],
                },
                "logprobs": {
                    "content": [
                        {"token": "Checking", "logprob": -0.2, "top_logprobs": [{"token": "Checking", "logprob": -0.2}, {"token": "Looking", "logprob": -1.2}]},
                        {"token": ".", "logprob": -0.1, "top_logprobs": [{"token": ".", "logprob": -0.1}, {"token": "!", "logprob": -1.0}]},
                    ]
                },
            }
        ],
    }
    request_meta = {"logprobs": True, "top_logprobs": 2, "provider": {"require_parameters": True}, "temperature": 0.0, "top_p": 1.0}
    adapter = OpenRouterAdapter()
    record = adapter.capture(response, request_meta)
    result = Analyzer().analyze_step(record, adapter.capability_report(response, request_meta))
    print(result.pretty())


if __name__ == "__main__":
    main()
