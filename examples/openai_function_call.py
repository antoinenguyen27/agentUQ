from uq_runtime.adapters.openai_responses import OpenAIResponsesAdapter
from uq_runtime.analysis.analyzer import Analyzer
from uq_runtime.schemas.config import UQConfig


def main() -> None:
    response = {
        "id": "resp_123",
        "model": "gpt-4.1-mini",
        "output": [
            {"type": "function_call", "name": "weather_lookup", "arguments": '{"city":"Pariss"}'},
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "",
                        "logprobs": [
                            {"token": "weather_lookup", "logprob": -0.2, "top_logprobs": [{"token": "weather_lookup", "logprob": -0.2}, {"token": "search_web", "logprob": -1.1}]},
                            {"token": '{"city"', "logprob": -0.3, "top_logprobs": [{"token": '{"city"', "logprob": -0.3}, {"token": '{"location"', "logprob": -0.9}]},
                            {"token": ":", "logprob": -0.1, "top_logprobs": [{"token": ":", "logprob": -0.1}, {"token": ",", "logprob": -2.0}]},
                            {"token": '"Pariss"', "logprob": -4.4, "top_logprobs": [{"token": '"Paris"', "logprob": -3.8}, {"token": '"Pariss"', "logprob": -4.4}]},
                        ],
                    }
                ],
            },
        ],
    }
    request_meta = {"include_output_text_logprobs": True, "top_logprobs": 2, "temperature": 0.0, "top_p": 1.0, "deterministic": True}
    adapter = OpenAIResponsesAdapter()
    analyzer = Analyzer(UQConfig(mode="canonical"))
    record = adapter.capture(response, request_meta)
    result = analyzer.analyze_step(record, adapter.capability_report(response, request_meta))
    print("capture -> analyze -> decide")
    print(result.primary_score_type, result.action)
    for segment in result.segments:
        if segment.events:
            print(segment.kind, segment.text, [event.type for event in segment.events], segment.recommended_action)


if __name__ == "__main__":
    main()

