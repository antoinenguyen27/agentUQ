from agentuq.integrations.langgraph_hook import enrich_graph_state, should_interrupt_before_tool
from agentuq.schemas.config import UQConfig
from agentuq.schemas.results import UQResult


class Response:
    def __init__(self) -> None:
        self.content = "Checking."
        self.additional_kwargs = {}
        self.tool_calls = [{"id": "call_1", "name": "browser", "args": {"selector": "#delete"}, "type": "tool_call"}]
        self.response_metadata = {
            "logprobs": {
                "content": [
                    {"token": "Checking", "logprob": -0.7, "top_logprobs": [{"token": "Checking", "logprob": -0.7}, {"token": "Looking", "logprob": -0.8}]},
                    {"token": ".", "logprob": -0.1, "top_logprobs": [{"token": ".", "logprob": -0.1}, {"token": "!", "logprob": -0.5}]},
                ]
            },
            "model_name": "gpt-4o-mini",
        }


def main() -> None:
    state = {}
    state = enrich_graph_state(state, Response(), UQConfig(policy="conservative", tolerance="strict"))
    print(UQResult.model_validate(state["uq_result"]).pretty())
    print(should_interrupt_before_tool("browser", state))


if __name__ == "__main__":
    main()
