from uq_runtime.adapters.openai_responses import OpenAIResponsesAdapter
from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig


def main() -> None:
    response = {
        "id": "resp_123",
        "model": "gpt-4.1-mini",
        "output": [
            {"type": "function_call", "name": "weather_lookup", "arguments": '{"city":}'},
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "Checking.",
                        "logprobs": [
                            {"token": "Checking", "logprob": -0.2, "top_logprobs": [{"token": "Checking", "logprob": -0.2}, {"token": "Looking", "logprob": -1.1}]},
                            {"token": ".", "logprob": -0.1, "top_logprobs": [{"token": ".", "logprob": -0.1}, {"token": "!", "logprob": -1.5}]},
                        ],
                    }
                ],
            },
        ],
    }
    request_meta = {"include": ["message.output_text.logprobs"], "top_logprobs": 2, "temperature": 0.0, "top_p": 1.0}
    adapter = OpenAIResponsesAdapter()
    analyzer = Analyzer(UQConfig(mode="canonical", policy="balanced", tolerance="strict"))
    record = adapter.capture(response, request_meta)
    result = analyzer.analyze_step(record, adapter.capability_report(response, request_meta))
    print(result.pretty())


if __name__ == "__main__":
    main()
