import sys
from pathlib import Path
import traceback

# --- Add parent directory to sys.path ---
# This assumes llm_service.py is in src/main/ui and llms is in src/main/llms
try:
    current_file_path = Path(__file__).resolve()
    parent_dir = current_file_path.parent
    main_dir = parent_dir.parent

    if str(main_dir) not in sys.path:
        sys.path.append(str(main_dir))
        print(f"Added {main_dir} to sys.path for llms module")

    import llms
except ImportError as e:
    print(f"CRITICAL: Error importing local llms module: {e}")
    # Create a mock llms object if import fails, so the app can still run
    class MockLLM:
        def invoke(self, *args, **kwargs):
            return type('obj', (object,), {'text': f'Error: llms module not found. {e}'})

    class MockLLMs:
        def of(self, *args, **kwargs):
            return MockLLM()
    llms = MockLLMs()


class LLMService:
    def __init__(self, config_manager, key_manager):
        self.config_manager = config_manager
        self.key_manager = key_manager

    def get_response(self, model_name: str, messages: list) -> str:
        """
        Gets a response from the specified LLM, handling config and keys.
        """
        try:
            print(f"LLMService: Getting response for model: {model_name}")

            # --- FIX: Use the correct function names ---
            model_args = self.config_manager.get_model_arguments(model_name)
            invocation_args = self.config_manager.get_invocation_arguments()
            # --- END FIX ---

            # 2. Get provider and key
            provider = model_args.get("provider")
            model_key = None
            if provider:
                key = self.key_manager.get_key(provider)
                if key:
                    model_key = key
                    print(f"LLMService: Found key for provider: {provider}")

            # 3. Build final argument dict
            model_args_with_key = model_args.copy()
            if model_key:
                model_args_with_key["model_key"] = model_key

            # 4. Create bot instance
            print(f"Calling llms.of({model_name}, ...)")
            bot = llms.of(model_name, **model_args_with_key)

            # 5. Format messages for the 'llms' library
            formatted_messages = []
            for msg in messages:
                formatted_messages.append((msg.get("role"), msg.get("content")))

            # 6. Call the bot
            print(f"Invoking {model_name} with {len(formatted_messages)} messages and args {invocation_args}")
            response = bot.invoke(formatted_messages, **invocation_args)

            if not hasattr(response, 'text'):
                raise ValueError("LLM response object has no 'text' attribute.")

            return response.text

        except Exception as e:
            print(f"Error during LLM call: {e}")
            traceback.print_exc() # Print full traceback to console
            return f"Error: {e}"

