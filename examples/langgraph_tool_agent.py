from uq_runtime.integrations.langgraph_hook import enrich_graph_state, should_interrupt_before_tool
from uq_runtime.schemas.config import UQConfig


class Response:
    def __init__(self) -> None:
        self.content = ""
        self.additional_kwargs = {"tool_calls": [{"id": "call_1", "function": {"name": "browser", "arguments": '{"selector":"#delete"}'}}]}
        self.response_metadata = {
            "logprobs": {"content": [{"token": "browser", "logprob": -0.7, "top_logprobs": [{"token": "browser", "logprob": -0.7}, {"token": "click", "logprob": -0.8}]}]},
            "model_name": "gpt-4o-mini",
        }


def main() -> None:
    state = {}
    state = enrich_graph_state(state, Response(), UQConfig(policy="conservative", tolerance="strict"))
    print(should_interrupt_before_tool("browser", state))


if __name__ == "__main__":
    main()
