from uq_runtime.adapters.openai_agents import OpenAIAgentsAdapter, model_settings_with_logprobs
from uq_runtime.analysis.analyzer import Analyzer


def main() -> None:
    settings = model_settings_with_logprobs(top_logprobs=2)
    print(settings)
    response = {
        "id": "resp_agent_1",
        "model": "gpt-4.1-mini",
        "output": [{"type": "function_call", "name": "send_email", "arguments": '{"to":"wrong@example.com"}'}],
    }
    adapter = OpenAIAgentsAdapter()
    request_meta = {"include_output_text_logprobs": True, "top_logprobs": 2, "deterministic": True}
    record = adapter.capture(response, request_meta)
    result = Analyzer().analyze_step(record, adapter.capability_report(response, request_meta))
    print(result.action)


if __name__ == "__main__":
    main()

