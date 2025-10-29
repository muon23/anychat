import argparse
import configparser
import os
from pathlib import Path

class ConfigManager:
    """
    Manages loading configuration from a properties file (.ini)
    and command-line arguments.
    """
    def __init__(self, default_config_path='deployment/dev/config.ini'):
        self.config_file = self._get_config_path(default_config_path)
        self.config = configparser.ConfigParser()
        self._load_config()

    def _get_config_path(self, default_path):
        parser = argparse.ArgumentParser()
        parser.add_argument('-p', '--properties', help='Path to the properties file.')
        # Parse known args to avoid conflicts with Qt's args
        args, _ = parser.parse_known_args()
        return args.properties if args.properties else default_path

    def _load_config(self):
        print(f"Loading configuration from: {self.config_file}")
        if not os.path.exists(self.config_file):
            print(f"Warning: Config file not found at {self.config_file}. Creating default.")
            self._create_default_config()
        try:
            self.config.read(self.config_file)
        except configparser.Error as e:
            print(f"Error reading config file: {e}. Using defaults.")
            self._set_defaults()

    def _set_defaults(self):
        """Sets in-memory defaults if config file is missing or corrupt."""
        self.config['General'] = {
            'keys_file': 'deployment/dev/api_keys.json',
            'providers': 'OpenAI, Anthropic, Google AI',
            'models': 'gpt-4o, claude-3-opus'
        }

    def _create_default_config(self):
        """Creates a default config file."""
        self._set_defaults()
        try:
            config_path = Path(self.config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                self.config.write(f)
            print(f"Default config file created at {self.config_file}")
        except OSError as e:
            print(f"Error: Unable to create default config file: {e}")

    def get_keys_file_path(self) -> str:
        return self.config.get('General', 'keys_file', fallback='deployment/dev/api_keys.json')

    def _get_list_from_config(self, section, key) -> list[str]:
        """Helper to get a comma-separated list from the config."""
        try:
            list_str = self.config.get(section, key)
            if not list_str:
                return []
            return [item.strip() for item in list_str.split(',') if item.strip()]
        except (configparser.NoSectionError, configparser.NoOptionError):
            return []

    def get_providers(self) -> list[str]:
        """Reads the list of providers from the [General] section."""
        providers = self._get_list_from_config('General', 'providers')
        if not providers:
            print("Warning: No providers found in config, using defaults.")
            return ['OpenAI', 'Anthropic', 'Google AI']
        return providers

    def get_models(self) -> list[str]:
        """Reads the list of curated models from the [General] section."""
        models = self._get_list_from_config('General', 'models')
        if not models:
            print("Warning: No models found in config, using defaults.")
            return ['gpt-4o'] # Fallback to a single default
        return models

