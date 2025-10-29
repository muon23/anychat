import json
from pathlib import Path


class KeyManager:
    def __init__(self, keys_file_path: Path, providers: list):
        """
        Initializes the key manager with a specific file path and list of providers
        from the configuration.
        """
        self.keys_file = keys_file_path
        self.providers = providers
        self.keys = {}
        self.load_keys()

    def load_keys(self):
        """
        Loads keys from the JSON file.
        Returns a dictionary with all configured providers;
        keys that aren't found will have an empty string value.
        """
        if self.keys_file.exists():
            try:
                with open(self.keys_file, 'r', encoding='utf-8') as f:
                    saved_keys = json.load(f)
            except json.JSONDecodeError:
                saved_keys = {}
        else:
            saved_keys = {}

        # Ensure all configured providers are in the keys dict
        self.keys = {}
        for provider in self.providers:
            self.keys[provider] = saved_keys.get(provider, "")

        return self.keys

    def save_keys(self, keys_dict):
        """
        Saves the provided dictionary of keys to the JSON file.
        """
        try:
            # Ensure the parent directory exists
            self.keys_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.keys_file, 'w', encoding='utf-8') as f:
                json.dump(keys_dict, f, indent=2)
            # Update the manager's internal state
            self.load_keys()
            return True
        except IOError as e:
            print(f"Error saving keys: {e}")
            return False

    def get_key(self, provider):
        """Gets a specific key."""
        return self.keys.get(provider, "")
