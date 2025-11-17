import unittest
from typing import List

from langchain.agents import create_agent
from langchain_core.prompt_values import StringPromptValue
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool

import llms
from llms import DeepInfraLlm


class RunnableToLLMAdapterTest(unittest.TestCase):
    count = 10
    llllm = llms.of("llama-3").as_language_model()

    def test_predict(self):
        llm = DeepInfraLlm("llama-3").as_language_model()
        prompt_value = StringPromptValue(text="What is the capital of Japan?")
        result = llm.invoke(prompt_value)
        self.assertIn("Tokyo", result)

    def test_agent_support(self):
        llm = DeepInfraLlm("llama-3").as_language_model()

        def look_up(query: str) -> str:
            # Mocking no answers
            quarters = 1 if "4Q24" in query else 0
            quarters += 1 if "1Q25" in query else 0
            quarters += 1 if "2Q25" in query else 0

            if quarters != 1:
                return "not found"

            print(f"*** search: {query}")
            answer = f"{self.count}%"
            self.count += 1
            return answer

        def decompose_question(query: str) -> List[str]:
            print(f"*** decompose: {query}")

            prompt = f"""
            Break up the following question into multiple simple questions, each on its own line.
            ===
            {query}
            """

            response = llm.invoke(StringPromptValue(text=prompt))

            print(response)
            return response.split("\n")

        tools = [
            Tool(
                name="look_up",
                func=look_up,
                description="Look up specific information in the database.  Only capable of one single answer."
            ),
            Tool(
                name="decompose_question",
                func=decompose_question,
                description="Break down complex questions into smaller sub-questions."
            )
        ]

        prompt = PromptTemplate.from_template("""
            You are an AI agent tasked with answering questions. You have access to the following tool_specs:
            {tool_specs}
            
            The tool_specs you can use are: {tool_names}
            
            Question: {input}
            Current Context: {context}
            Previous Steps: {agent_scratchpad}
            
            Follow these steps:
            1. Determine if the question can be answered directly or if it requires additional information.
            2. If additional information is needed, decide whether to search for it or break the question into sub-questions.
            3. Use the tool_specs as needed to gather information or decompose the question.
            4. If a tool fails to provide useful results after 2 attempts, stop using it and try another tool.
            5. If no tool_specs can provide the necessary information, explain why the question cannot be answered and provide suggestions for how to find the answer.
            6. Combine all the information to provide a final answer.
     
            Important:
            - If you have enough information to answer the question, provide a **Final Answer** and nothing else.
            - If you need more information, specify an **Action** and an **Action Input**, and do not provide a final answer.

            Respond in the following format:
            Thought: [Your reasoning process]
            Action: [The tool to use, if applicable]
            Action Input: [Your input to the tool, if applicable]
            
            OR
            
            If you have a final answer:
            Thought: [Your reasoning process]
            Final Answer: [Your complete response]
            """)

        # Create agent using new LangChain 1.0 API
        # Note: The new create_agent doesn't use PromptTemplate the same way
        # It uses system_prompt instead. For this test, we'll extract the system message
        system_prompt = """
            You are an AI agent tasked with answering questions. You have access to tools.
            
            Follow these steps:
            1. Determine if the question can be answered directly or if it requires additional information.
            2. If additional information is needed, use the available tools.
            3. Combine all the information to provide a final answer.
        """
        
        # Type: ignore because BaseLanguageModel is compatible (BaseChatModel extends it)
        agent = create_agent(
            model=llm,  # type: ignore[arg-type]
            tools=tools,
            system_prompt=system_prompt
        )

        # Execute a query - new API expects messages
        from langchain_core.messages import HumanMessage
        result_state = agent.invoke({
            "messages": [HumanMessage(content="What was the company's profit margin trend over the last 3 quarters?  Today: 2Q25")]
        })
        
        # Extract result from state
        result = result_state.get("messages", [])[-1].content if result_state.get("messages") else ""
        print(result)

        self.assertEqual(True, True)  # add assertion here


if __name__ == '__main__':
    unittest.main()
