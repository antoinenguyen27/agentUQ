from uq_runtime.adapters.litellm import LiteLLMAdapter
from uq_runtime.analysis.analyzer import Analyzer


def main() -> None:
    response = {
        "id": "litellm_1",
        "model": "openai/gpt-4o-mini",
        "choices": [{"message": {"content": 'Action: click(selector="#submit")'}, "logprobs": {"content": [{"token": "click", "logprob": -0.4, "top_logprobs": [{"token": "click", "logprob": -0.4}, {"token": "type", "logprob": -0.5}]}]}}],
    }
    request_meta = {"logprobs": True, "top_logprobs": 2, "drop_params": False, "deterministic": True}
    adapter = LiteLLMAdapter()
    record = adapter.capture(response, request_meta)
    result = Analyzer().analyze_step(record, adapter.capability_report(response, request_meta))
    print(result.pretty())


if __name__ == "__main__":
    main()
