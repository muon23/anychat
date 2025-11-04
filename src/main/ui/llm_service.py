# This module will import your local llms module
# Adjust the import path as needed for your project structure
try:
    # Assuming 'llms' is a package/module in your project's PYTHONPATH
    import llms
except ImportError:
    print("CRITICAL: Could not import the 'llms' module.")
    # Create a mock for testing if the module isn't found
    class MockBot:
        def __init__(self, *args, **kwargs):
            print(f"MockBot created with args: {args}, kwargs: {kwargs}")
            self.text = "This is a mock response from a mock bot."

        def invoke(self, *args, **kwargs):
            print(f"MockBot invoked with args: {args}, kwargs: {kwargs}")
            return self

    class MockLLMs:
        def of(self, *args, **kwargs):
            return MockBot(*args, **kwargs)

    llms = MockLLMs()


class LLMService:
    def __init__(self, config_manager, key_manager):
        self.config_manager = config_manager
        self.key_manager = key_manager
        print("LLMService initialized.")

    def get_response(self, model_name: str, messages: list):
        """
        Gets a response from the LLM, configuring it with arguments
        from the config file and injecting the correct API key.
        """

        # 1. Get ALL model and invocation arguments from config
        model_args = self.config_manager.get_model_arguments(model_name)
        invocation_args = self.config_manager.get_invocation_arguments()

        # 2. Find the provider for the selected model
        #    We use .pop() to get the provider AND remove it from the
        #    dict so it's not passed to llms.of() as a model argument.
        provider = model_args.pop('provider', None)

        if provider:
            # 3. If a provider is listed, get its key from the KeyManager
            api_key = self.key_manager.get_key(provider)

            if api_key:
                # 4. If a key exists, add it as 'model_key'
                model_args['model_key'] = api_key
                print(f"Found provider '{provider}'. Injecting 'model_key'.")
            else:
                print(f"Found provider '{provider}' but no API key is set. Proceeding without 'model_key'.")
        else:
            print(f"No provider listed for model '{model_name}'. Proceeding without 'model_key'.")

        # 5. Print the final arguments for debugging
        print(f"Calling llms.of() with model_args: {model_args}")
        print(f"Calling bot.invoke() with invocation_args: {invocation_args}")

        try:
            # 6. Create bot instance
            # We pass model_args (which may or may not have 'model_key')
            bot = llms.of(model_name, **model_args)

            # 7. Invoke bot
            result = bot.invoke(messages, **invocation_args)

            # 8. Return the text content
            return result.text

        except Exception as e:
            print(f"Error during LLM invocation: {e}")
            return f"Error: {e}"

