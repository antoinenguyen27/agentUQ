from uq_runtime.adapters.openrouter import OpenRouterAdapter
from uq_runtime.analysis.analyzer import Analyzer


def main() -> None:
    response = {
        "id": "or_1",
        "model": "openai/gpt-4o-mini",
        "choices": [
            {
                "message": {
                    "tool_calls": [{"id": "call_1", "function": {"name": "weather_lookup", "arguments": '{"city":"Paris"}'}}]
                },
                "logprobs": {"content": [{"token": "weather_lookup", "logprob": -0.2, "top_logprobs": [{"token": "weather_lookup", "logprob": -0.2}, {"token": "search", "logprob": -1.2}]}]},
            }
        ],
    }
    request_meta = {"logprobs": True, "top_logprobs": 2, "provider": {"require_parameters": True}, "deterministic": True}
    adapter = OpenRouterAdapter()
    record = adapter.capture(response, request_meta)
    result = Analyzer().analyze_step(record, adapter.capability_report(response, request_meta))
    print(result.capability_report)
    print(result.decision.action)


if __name__ == "__main__":
    main()

