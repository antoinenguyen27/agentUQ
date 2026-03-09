from uq_runtime.adapters.together import TogetherAdapter
from uq_runtime.analysis.analyzer import Analyzer


def main() -> None:
    response = {
        "id": "tog_1",
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "choices": [
            {
                "message": {"role": "assistant", "content": "Paris"},
                "logprobs": {
                    "tokens": ["Paris"],
                    "token_logprobs": [-0.3],
                    "top_logprobs": [{"Paris": -0.3, "London": -0.8}],
                },
            }
        ],
    }
    request_meta = {"logprobs": 2, "temperature": 0.6, "deterministic": False}
    adapter = TogetherAdapter()
    record = adapter.capture(response, request_meta)
    result = Analyzer().analyze_step(record, adapter.capability_report(response, request_meta))
    print(result.pretty())


if __name__ == "__main__":
    main()
