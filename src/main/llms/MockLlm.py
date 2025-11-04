from typing import List, Any, Sequence

from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import Runnable, RunnableLambda

from llms import Llm


class MockLlm(Llm):

    def __echo_last_user_message(self, messages: list) -> AIMessage:
        """Extracts the content of the last HumanMessage and returns it as an AIMessage."""
        for message in reversed(messages):
            if isinstance(message, HumanMessage):
                return AIMessage(content=message.content)
        return AIMessage(content="No user message found")

    def __init__(self):
        self.llm = RunnableLambda(self.__echo_last_user_message)
        super().__init__(self.llm)

    def clean_up_response(self, response: Any) -> Llm.Response:
        return response

    def get_max_tokens(self) -> int:
        return 1000_000

    def get_model_name(self) -> str:
        return "mock"

    @classmethod
    def get_supported_models(cls) -> List[str]:
        return ["mock"]

    def invoke(self, prompt: Sequence[tuple[Llm.Role | str, str] | str] | str, **kwargs) -> Llm.Response:
        if isinstance(prompt, str):
            return Llm.Response(text=prompt)

        for msg in reversed(prompt):
            role = msg[0]
            if role == Llm.Role.HUMAN or role in ["user", "human"]:
                return Llm.Response(text="MOCK:  " + msg[1])

    def as_runnable(self) -> Runnable:
        return self.llm

    def as_language_model(self) -> BaseLanguageModel:
        pass
