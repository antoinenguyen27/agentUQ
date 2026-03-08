from uq_runtime.adapters.together import TogetherAdapter
from uq_runtime.analysis.analyzer import Analyzer


def main() -> None:
    response = {
        "id": "tog_1",
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "output": {
            "text": "Action: click(selector=\"#delete\")",
            "tokens": ["click", "(", '"#delete"', ")"],
            "token_logprobs": [-0.6, -0.1, -3.9, -0.2],
            "top_logprobs": [{"click": -0.6, "type": -0.7}, {"(": -0.1}, {'"#delete"': -3.9, '"#cancel"': -4.0}, {")": -0.2}],
        },
    }
    request_meta = {"logprobs": 2, "temperature": 0.6, "deterministic": False}
    adapter = TogetherAdapter()
    record = adapter.capture(response, request_meta)
    result = Analyzer().analyze_step(record, adapter.capability_report(response, request_meta))
    print(result.events)


if __name__ == "__main__":
    main()

