import json
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence, Any, List, Dict, Literal

from langchain.agents import create_agent
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSequence, Runnable, RunnableConfig, RunnableLambda
from transformers import AutoTokenizer


class Llm(ABC):
    """
    Abstract class for accessing LLM models.

    This class provides a standardized interface for interacting with different LLM
    providers (like OpenAI or Gemini) using the LangChain framework, handling
    prompt preprocessing, token counting, and configuration management.
    Concrete subclasses must implement provider-specific logic.
    """

    class Role(Enum):
        """Enumeration for standard conversational roles."""
        SYSTEM = 0
        HUMAN = 1
        AI = 2

    @dataclass
    class Response:
        """Standardized structure for LLM responses across all provider subclasses."""
        text: str = None
        image_url: str = None
        image_base64: str = None
        tool_calls: list[dict] = field(default_factory=list)
        citations: list[dict] = field(default_factory=list)
        thought: str = None
        metadata: Any = None
        raw: Any = None

    def __init__(self, llm: Runnable, role_names: dict = None):
        """
        Initializes the LLM wrapper.

        Args:
            llm: The underlying LangChain Runnable object for the specific LLM.
            role_names: Optional dictionary to map internal Role enums to custom
                        string names (e.g., HUMAN -> "user", AI -> "assistant").
        """
        self.llm = llm
        # Default role names used for converting history into LangChain format
        self.role_names = {
            self.Role.SYSTEM: "system",
            self.Role.HUMAN: "user",
            self.Role.AI: "assistant",
        }
        if role_names:
            # Overwrite defaults if custom roles are provided
            self.role_names.update(role_names)

        # Use GPT-2 tokenizer as a robust, universal approximation for token counting
        self.tokenizer = AutoTokenizer.from_pretrained("gpt2")

    def invoke(
            self,
            prompt: Sequence[tuple[Role | str, str] | str] | Sequence[BaseMessage] | str,
            **kwargs
    ) -> Response:
        """
        Processes the prompt, executes the LLM chain, and returns the cleaned response.

        Args:
            prompt: The input prompt. Can be:
                    - A simple string
                    - A sequence of (Role/role_name, content) tuples representing chat history
                    - A sequence of LangChain BaseMessage objects (HumanMessage, SystemMessage, AIMessage, etc.)
            **kwargs: Additional arguments passed to the chain, including
                      'arguments' (for prompt template values) and 'task' (for metadata).

        Returns:
            A dictionary containing the cleaned response from the LLM.
        """
        # Format the prompt into a LangChain ChatPromptTemplate object
        prompt_format = kwargs.pop("prompt_format", "f-string")
        prompt = self.preprocess_prompt(prompt, prompt_format)

        # Prompt template parameters for filling holes in the prompt
        arguments = kwargs.get("arguments", {})

        # Create a sequential chain: Prompt -> LLM -> Response Cleanup
        # Type: ignore because clean_up_response is a method, but RunnableLambda accepts callables
        chain = RunnableSequence(prompt | self.llm | RunnableLambda(self.clean_up_response))  # type: ignore[arg-type]

        # Task, e.g., chat or completion.
        # Some LLM models need to distinguish chat or completion.
        # This is a way for the derived class to pass in its purpose.
        task = kwargs.get("task", self.get_default_task())
        config = RunnableConfig(metadata={"task": task})

        # Execute the chain
        response: Llm.Response = chain.invoke(input=arguments, config=config, **kwargs)

        return response

    def preprocess_prompt(
            self,
            prompt: Sequence[tuple[Role | str, str] | str] | Sequence[BaseMessage] | str,
            prompt_format: Literal["f-string", "mustache", "jinja2"]
    ) -> ChatPromptTemplate:
        """
        Converts various input prompt formats into a standardized ChatPromptTemplate.
        
        Escapes curly braces inside code blocks (```...```) to prevent LangChain from
        interpreting them as template variables, while preserving actual template
        variables outside code blocks.
        """
        def escape_code_blocks(text: str) -> str:
            """
            Escape curly braces inside code blocks (```...```) while preserving
            template variables outside code blocks.
            
            Strategy:
            1. Find all code blocks (```language ... ``` or ``` ... ```)
            2. Escape curly braces inside code blocks only
            3. Leave everything else unchanged (including template variables)
            """
            # Pattern to match code blocks: ```optional_language\ncontent\n```
            # This handles both ```json\n...\n``` and ```\n...\n``` formats
            code_block_pattern = r'```(\w+)?\n(.*?)```'
            
            def escape_code_content(match):
                """Escape curly braces inside a code block."""
                language = match.group(1) or ''
                code_content = match.group(2)
                # Escape all curly braces in the code content
                escaped_content = code_content.replace("{", "{{").replace("}", "}}")
                return f"```{language}\n{escaped_content}```"
            
            # Replace code blocks with escaped versions
            result = re.sub(code_block_pattern, escape_code_content, text, flags=re.DOTALL)
            return result
        
        # If the prompt is a simple string, wrap it as a single message
        if isinstance(prompt, str):
            # This handles single instruction prompts
            human_role_name = self.role_names[self.Role.HUMAN]
            return ChatPromptTemplate(messages=[(human_role_name, escape_code_blocks(prompt))], template_format=prompt_format)
        elif len(prompt) > 0 and isinstance(prompt[0], BaseMessage):
            # Handle Sequence[BaseMessage] - convert BaseMessage objects to (role, content) tuples
            messages = []
            for msg in prompt:
                # Map BaseMessage types to role names
                if isinstance(msg, SystemMessage):
                    role_name = self.role_names[self.Role.SYSTEM]
                elif isinstance(msg, HumanMessage):
                    role_name = self.role_names[self.Role.HUMAN]
                elif isinstance(msg, AIMessage):
                    role_name = self.role_names[self.Role.AI]
                else:
                    # For other BaseMessage subclasses, try to get the type from the message
                    # Most BaseMessage subclasses have a 'type' attribute
                    msg_type = getattr(msg, 'type', 'human')
                    # Map common message types to role names
                    if msg_type == 'system':
                        role_name = self.role_names[self.Role.SYSTEM]
                    elif msg_type == 'human' or msg_type == 'user':
                        role_name = self.role_names[self.Role.HUMAN]
                    elif msg_type == 'ai' or msg_type == 'assistant':
                        role_name = self.role_names[self.Role.AI]
                    else:
                        # Default to human if unknown
                        role_name = self.role_names[self.Role.HUMAN]
                
                # Extract content from the message
                # Content might be a string, list (for multimodal), or other type
                raw_content = msg.content if hasattr(msg, 'content') else str(msg)
                # Convert to string if needed (handles multimodal content)
                if isinstance(raw_content, str):
                    content = raw_content
                elif isinstance(raw_content, list):
                    # For multimodal content, extract text parts and join them
                    text_parts = []
                    for part in raw_content:
                        if isinstance(part, str):
                            text_parts.append(part)
                        elif isinstance(part, dict) and 'text' in part:
                            text_parts.append(part['text'])
                        else:
                            text_parts.append(str(part))
                    content = '\n'.join(text_parts)
                else:
                    content = str(raw_content)
                # Escape curly braces inside code blocks only
                escaped_content = escape_code_blocks(content)
                messages.append((role_name, escaped_content))
            return ChatPromptTemplate(messages=messages, template_format=prompt_format)
        else:
            # Reformat the sequence of (Role, content) tuples into LangChain messages
            messages = []
            for msg in prompt:
                role_name = self.role_names[msg[0]] if isinstance(msg[0], self.Role) else msg[0]
                # Escape curly braces inside code blocks only
                escaped_content = escape_code_blocks(msg[1])
                messages.append((role_name, escaped_content))
            return ChatPromptTemplate(messages=messages, template_format=prompt_format)

    @abstractmethod
    def clean_up_response(self, response: Any) -> Response:
        """
        Abstract method to clean up and standardize the LLM's raw response.

        Concrete implementation must extract text, cost metadata, etc., and return a dict.
        """
        pass

    def get_num_tokens(self, text: str) -> int:
        """
        Estimates the number of tokens in a given text using the GPT-2 tokenizer.
        """
        return len(self.tokenizer.encode(text))

    @abstractmethod
    def get_max_tokens(self) -> int:
        """
        Abstract method to return the maximum context window size for the underlying model.
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """
        Returns canonical model name
        """
        pass

    def get_default_task(self) -> str:
        """Returns the default task type for metadata."""
        return "chat"

    @classmethod
    @abstractmethod
    def get_supported_models(cls) -> List[str]:
        """Abstract method to return a list of model names supported by the subclass."""
        pass

    #
    # LangChain adapters (Allowing the Llm object to be used seamlessly in LangChain chains)
    #
    @abstractmethod
    def as_runnable(self) -> Runnable:
        """Returns the LLM instance as a LangChain Runnable."""
        pass

    @abstractmethod
    def as_language_model(self) -> BaseLanguageModel:
        """Returns the LLM instance as a LangChain BaseLanguageModel."""
        pass

    #
    # Helper functions
    #
    @classmethod
    def _alias2model(cls, models: Dict[str, dict]) -> Dict[str, str]:
        """Helper to create a mapping from model aliases to canonical model names."""
        a2m = dict()
        for model, properties in models.items():
            aliases = properties.get("aliases", [])
            for alias in aliases:
                a2m[alias] = model
        return a2m

    @classmethod
    def _model_token_limit(cls, models: Dict[str, dict], default: int) -> Dict[str, int]:
        """Helper to extract token limits from model configuration data."""
        limits = dict()
        for model, properties in models.items():
            limits[model] = properties.get("token_limit", default)
        return limits

    @staticmethod
    def _safe_json_loads(x):
        try:
            return json.loads(x) if isinstance(x, str) else x
        except Exception:
            return None

    @staticmethod
    def _extract_sources_from_observation(obs) -> List[str]:
        urls = []
        data = Llm._safe_json_loads(obs)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    url = item.get("url")
                    if url:
                        urls.append(url)
        elif isinstance(data, dict):
            url = data.get("url")
            if url:
                urls.append(url)
        return urls

    @classmethod
    def _make_agent_runnable(cls, llm, tools, system_prompt: str = "You are helpful.") -> Runnable:
        # Create agent using new LangChain 1.0 API
        # create_agent takes model, tools, and system_prompt directly
        # Type: ignore because BaseLanguageModel is compatible (BaseChatModel extends it)
        agent = create_agent(
            model=llm,  # type: ignore[arg-type]
            tools=tools,
            system_prompt=system_prompt,
        )

        def _invoke(x):
            from langchain_core.messages import HumanMessage
            
            # The new agent expects messages as input
            # x can be a string or a dict with "input" and "chat_history"
            if isinstance(x, str):
                messages = [HumanMessage(content=x)]
                chat_history = []
            elif isinstance(x, dict):
                input_text = x.get("input", "")
                chat_history = x.get("chat_history", [])
                messages = chat_history + [HumanMessage(content=input_text)]
            else:
                messages = [HumanMessage(content=str(x))]
                chat_history = []
            
            # Invoke the agent (returns state with messages)
            # Type: ignore because LangGraph state graph accepts dict with "messages" key
            result_state: Dict[str, Any] = agent.invoke({"messages": messages})  # type: ignore[arg-type]
            
            # Extract the last AI message as the output
            output_messages = result_state.get("messages", [])
            if output_messages:
                last_message = output_messages[-1]
                output_text = last_message.content if hasattr(last_message, 'content') else str(last_message)
            else:
                output_text = ""
            
            # Extract intermediate steps from state if available
            # The new agent stores tool calls in the messages themselves
            steps = result_state.get("intermediate_steps", [])
            tools_used: List[str] = []
            sources: List[str] = []
            
            # Extract tool calls from messages
            for msg in output_messages:
                # Check if message has tool calls (new format)
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        tool_name = tool_call.get('name') if isinstance(tool_call, dict) else getattr(tool_call, 'name', None)
                        if tool_name:
                            tools_used.append(tool_name)
            
            # Also check intermediate_steps if available (for backward compatibility)
            for step in steps:
                if isinstance(step, tuple) and len(step) >= 2:
                    action, observation = step[0], step[1]
                    tool_name = getattr(action, "tool", None)
                    if tool_name:
                        tools_used.append(tool_name)
                    sources.extend(Llm._extract_sources_from_observation(observation))
            
            # dedupe but keep order
            def _dedupe(seq): return list(dict.fromkeys(seq))
            tools_used = _dedupe(tools_used)
            sources = _dedupe(sources)
            
            # Optional compact trace
            compact_trace = []
            for step in steps:
                if isinstance(step, tuple) and len(step) >= 2:
                    action, observation = step[0], step[1]
                    tool_name = getattr(action, "tool", None)
                    tool_args = getattr(action, "tool_input", None)
                    compact_trace.append({
                        "tool": tool_name,
                        "args_preview": str(tool_args)[:200] if tool_args is not None else None,
                        "obs_preview": (observation[:200] if isinstance(observation, str) else None)
                    })
            
            meta = {
                "agent_executor": "tool_calling",
                "model": getattr(llm, "model_name", getattr(llm, "model", None)),
                "num_steps": len(steps),
                "tools_used": tools_used,
                "sources": sources,
            }
            
            return AIMessage(
                id=str(uuid.uuid4()),
                content=output_text,
                response_metadata=meta,
                additional_kwargs={"trace": compact_trace} if compact_trace else {},
            )
        
        # RunnableLambda can handle functions that return single values (not just iterators)
        return RunnableLambda(_invoke)  # type: ignore[arg-type]


