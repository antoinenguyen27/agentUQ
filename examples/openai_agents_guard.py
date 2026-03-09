from uq_runtime.adapters.openai_agents import OpenAIAgentsAdapter, model_settings_with_logprobs
from uq_runtime.analysis.analyzer import Analyzer


def main() -> None:
    settings = model_settings_with_logprobs(top_logprobs=2)
    print(settings)
    response = {
        "id": "resp_agent_1",
        "model": "gpt-4.1-mini",
        "output": [
            {"type": "function_call", "name": "send_email", "arguments": '{"to":}'},
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "Checking.",
                        "logprobs": [
                            {"token": "Checking", "logprob": -0.2, "top_logprobs": [{"token": "Checking", "logprob": -0.2}, {"token": "Looking", "logprob": -0.9}]},
                            {"token": ".", "logprob": -0.1, "top_logprobs": [{"token": ".", "logprob": -0.1}, {"token": "!", "logprob": -1.0}]},
                        ],
                    }
                ],
            },
        ],
    }
    adapter = OpenAIAgentsAdapter()
    request_meta = {"response_include": ["message.output_text.logprobs"], "top_logprobs": 2, "temperature": 0.0, "top_p": 1.0}
    record = adapter.capture(response, request_meta)
    result = Analyzer().analyze_step(record, adapter.capability_report(response, request_meta))
    print(result.action)


if __name__ == "__main__":
    main()
