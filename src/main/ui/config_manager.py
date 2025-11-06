import configparser
import sys
from pathlib import Path


class ConfigManager:
    def __init__(self):
        self.config_file = self._find_config_file()
        self.config = configparser.ConfigParser()
        self._load_config()

    @classmethod
    def _find_config_file(cls):
        """Find the config file, checking command line args first."""
        # Check for -p or --properties
        if '-p' in sys.argv:
            try:
                index = sys.argv.index('-p')
                return Path(sys.argv[index + 1])
            except (IndexError, ValueError):
                pass
        if '--properties' in sys.argv:
            try:
                index = sys.argv.index('--properties')
                return Path(sys.argv[index + 1])
            except (IndexError, ValueError):
                pass
        # Default path
        return Path("config.ini")

    def _set_defaults(self):
        """Sets in-memory defaults for a clean config object."""
        self.config['General'] = {
            'keys_file': 'deployment/dev/api_keys.json',
            'chat_history_root': 'deployment/dev/chats',
            'providers': 'OpenAI, Anthropic, Google AI, DeepInfra',
            'models': 'gpt-4o, gemini-2.5, llama-4'
        }
        self.config['gpt-4o'] = {
            'temperature': '0.7'
        }
        self.config['gemini-2.5'] = {
            'temperature': '0.8'
        }
        self.config['Invocation'] = {
            'max_tokens': '4096'
        }

    def _create_default_config_file(self):
        """Creates a default config file on disk using the in-memory defaults."""
        try:
            # Ensure the parent directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            print(f"Default config file created at {self.config_file}")
        except IOError as e:
            print(f"Error: Unable to create default config file: {e}")

    def _load_config(self):
        """
        Load the config file. If it doesn't exist, create one from defaults.
        If it's corrupt, load in-memory defaults.
        """
        if not self.config_file.exists():
            print(f"Warning: Config file not found at {self.config_file}. Creating default.")
            self._set_defaults()
            self._create_default_config_file()
            return

        try:
            self.config.read(self.config_file)
            # Check if it's empty or corrupt
            if not self.config.sections():
                raise configparser.Error("Config file is empty or corrupt.")
        except Exception as e:
            print(f"Error reading config file: {e}. Loading in-memory defaults.")
            # Clear the corrupt config and load defaults
            self.config = configparser.ConfigParser()
            self._set_defaults()

    def _get_list(self, key):
        """Helper to get a comma-separated list from the [General] section."""
        try:
            value_str = self.config.get('General', key, fallback='')
            return [item.strip() for item in value_str.split(',') if item.strip()]
        except Exception:
            return []

    def get_keys_file_path(self) -> str:
        return self.config.get('General', 'keys_file', fallback='api_keys.json')

    def get_chat_history_root(self) -> str:
        return self.config.get('General', 'chat_history_root', fallback='chats')

    def get_providers(self) -> list:
        return self._get_list('providers')

    def get_models(self) -> list:
        return self._get_list('models')

    def get_model_arguments(self, model_name: str) -> dict:
        """
        Returns a dictionary of arguments for a specific model,
        reading from the section [model_name].
        """
        args = {}
        if self.config.has_section(model_name):
            try:
                for key, value in self.config.items(model_name):
                    # Try to convert to float or int, otherwise keep as string
                    try:
                        if '.' in value:
                            args[key] = float(value)
                        else:
                            args[key] = int(value)
                    except ValueError:
                        args[key] = value
            except Exception as e:
                print(f"Error reading model arguments for {model_name}: {e}")
        return args

    def get_invocation_arguments(self) -> dict:
        """
        Returns a dictionary of arguments for the .invoke() call,
        reading from the [Invocation] section.
        """
        args = {}
        if self.config.has_section('Invocation'):
            try:
                for key, value in self.config.items('Invocation'):
                    # Try to convert to float or int, otherwise keep as string
                    try:
                        if '.' in value:
                            args[key] = float(value)
                        else:
                            args[key] = int(value)
                    except ValueError:
                        args[key] = value
            except Exception as e:
                print(f"Error reading invocation arguments: {e}")
        return args

    def get_log_level(self) -> str:
        """
        Returns the log level from the [General] section.
        Defaults to 'warning' if not specified or invalid.
        Valid values: debug, info, warning, error
        """
        level = self.config.get('General', 'logging', fallback='warning').lower()
        valid_levels = ['debug', 'info', 'warning', 'error']
        if level in valid_levels:
            return level
        return 'warning'
