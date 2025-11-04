import os
import shutil
import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QStyle, QApplication, QMessageBox

# This custom data role is the key. We'll store the full file path
# in each tree item under this role.
PathRole = Qt.ItemDataRole.UserRole + 1


class ChatHistoryManager:
    def __init__(self, history_root: Path):
        self.history_root = history_root
        # Ensure the root directory exists
        self.history_root.mkdir(parents=True, exist_ok=True)

    def _get_icons(self):
        """Helper to get standard system icons."""
        style = QApplication.style()
        return {
            "folder": style.standardIcon(QStyle.StandardPixmap.SP_DirIcon),
            "file": style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        }

    def _load_recursive(self, parent_dir: Path, parent_item: QTreeWidgetItem, icons: dict):
        """Recursively load the contents of a project directory."""
        try:
            for name in sorted(os.listdir(parent_dir)):
                name = str(name)  # Ensure name is a string
                path = parent_dir / name

                # Set item flags to be enabled, selectable, and not checkable
                item_flags = (Qt.ItemFlag.ItemIsEnabled |
                              Qt.ItemFlag.ItemIsSelectable)

                if path.is_dir():
                    project_item = QTreeWidgetItem(parent_item, [name])
                    project_item.setIcon(0, icons["folder"])
                    project_item.setData(0, PathRole, str(path))
                    # Allow items to be parents
                    item_flags |= Qt.ItemFlag.ItemIsDropEnabled
                    project_item.setFlags(item_flags)
                    project_item.setData(0, Qt.ItemDataRole.CheckStateRole, None) # Hide checkbox
                    self._load_recursive(path, project_item, icons)
                elif path.is_file() and name.endswith(".json"):
                    display_name = name.replace('.json', '')
                    chat_item = QTreeWidgetItem(parent_item, [display_name])
                    chat_item.setIcon(0, icons["file"])
                    chat_item.setData(0, PathRole, str(path))
                    chat_item.setFlags(item_flags)
                    chat_item.setData(0, Qt.ItemDataRole.CheckStateRole, None) # Hide checkbox
        except OSError as e:
            print(f"Error reading directory {parent_dir}: {e}")

    def load_history(self, tree_widget: QTreeWidget):
        """Clears and reloads the entire chat history into the QTreeWidget."""
        tree_widget.clear()
        icons = self._get_icons()
        tree_widget.setHeaderHidden(True) # Hide the "1" header

        try:
            for name in sorted(os.listdir(self.history_root)):
                name = str(name)  # Ensure name is a string
                path = self.history_root / name

                # Set item flags to be enabled, selectable, and not checkable
                item_flags = (Qt.ItemFlag.ItemIsEnabled |
                              Qt.ItemFlag.ItemIsSelectable)

                if path.is_file() and path.suffix == '.json' and name.startswith("Chat "):
                    chat_item = QTreeWidgetItem(tree_widget, [name.replace('.json', '')])
                    chat_item.setIcon(0, icons["file"])
                    chat_item.setData(0, PathRole, str(path))
                    chat_item.setFlags(item_flags)
                    chat_item.setData(0, Qt.ItemDataRole.CheckStateRole, None) # Hide checkbox
                elif path.is_dir():
                    project_item = QTreeWidgetItem(tree_widget, [name])
                    project_item.setIcon(0, icons["folder"])
                    project_item.setData(0, PathRole, str(path))
                    item_flags |= Qt.ItemFlag.ItemIsDropEnabled # Make it a parent
                    project_item.setFlags(item_flags)
                    project_item.setData(0, Qt.ItemDataRole.CheckStateRole, None) # Hide checkbox
                    self._load_recursive(path, project_item, icons)
        except OSError as e:
            print(f"Error reading history root {self.history_root}: {e}")
        print("Chat history loaded into tree.")

    def create_new_chat(self, tree_widget: QTreeWidget, parent_project_item: QTreeWidgetItem = None):
        """Creates a new 'Chat N' file in the specified project or root."""
        parent_dir = self.history_root
        parent_node = tree_widget

        if parent_project_item:
            parent_dir = Path(parent_project_item.data(0, PathRole))
            parent_node = parent_project_item

        # Find the next available "Chat N" number
        i = 1
        while True:
            chat_name = f"Chat {i}"
            new_chat_path = parent_dir / f"{chat_name}.json"
            if not new_chat_path.exists():
                break
            i += 1

        try:
            # Create the empty chat file with an empty list
            with open(new_chat_path, 'w', encoding='utf-8') as f:
                json.dump([], f)

            # Add the new chat to the tree
            chat_item = QTreeWidgetItem(parent_node, [chat_name])
            chat_item.setIcon(0, self._get_icons()["file"])
            chat_item.setData(0, PathRole, str(new_chat_path))
            item_flags = (Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            chat_item.setFlags(item_flags)
            chat_item.setData(0, Qt.ItemDataRole.CheckStateRole, None) # Hide checkbox

            if parent_project_item:
                parent_project_item.setExpanded(True)

            tree_widget.setCurrentItem(chat_item)
            return chat_item
        except OSError as e:
            print(f"Error creating new chat file: {e}")
            return None

    def create_project(self, tree_widget: QTreeWidget, parent_item: QTreeWidgetItem = None):
        """Creates a new project directory."""
        parent_dir = self.history_root
        parent_node = tree_widget

        if parent_item:
            parent_dir = Path(parent_item.data(0, PathRole))
            parent_node = parent_item

        # Find the next available "New Project N" name
        i = 1
        while True:
            project_name = f"New Project {i}"
            new_project_path = parent_dir / project_name
            if not new_project_path.exists():
                break
            i += 1

        try:
            new_project_path.mkdir()
            project_item = QTreeWidgetItem(parent_node, [project_name])
            project_item.setIcon(0, self._get_icons()["folder"])
            project_item.setData(0, PathRole, str(new_project_path))
            item_flags = (Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDropEnabled)
            project_item.setFlags(item_flags)
            project_item.setData(0, Qt.ItemDataRole.CheckStateRole, None) # Hide checkbox

            if parent_item:
                parent_item.setExpanded(True)

            tree_widget.setCurrentItem(project_item)
            return project_item
        except OSError as e:
            print(f"Error creating new project: {e}")
            return None

    def rename_item(self, old_path: Path, new_name: str, parent_widget) -> bool:
        """Renames a file or directory."""
        try:
            if old_path.is_file():
                # For files, use with_stem to change the name before the .json
                new_path = old_path.with_stem(new_name)
            else:
                # For directories, just change the name
                new_path = old_path.with_name(new_name)

            if new_path.exists():
                QMessageBox.warning(parent_widget, "Rename Error", "An item with this name already exists.")
                return False

            old_path.rename(new_path)
            return True
        except OSError as e:
            QMessageBox.warning(parent_widget, "Rename Error", f"Could not rename: {e}")
            return False

    def delete_item(self, path: Path, warning_callback) -> bool:
        """Deletes a file or directory. Uses callback for non-empty dir warning."""
        try:
            if path.is_file():
                path.unlink()
                return True
            elif path.is_dir():
                if not any(path.iterdir()):
                    # Directory is empty, just delete it
                    path.rmdir()
                    return True
                else:
                    # Directory is not empty, show warning
                    if warning_callback(path):
                        shutil.rmtree(path)
                        return True
                    else:
                        return False # User cancelled
        except OSError as e:
            print(f"Error deleting {path}: {e}")
            return False

    # --- NEW: Method to load a chat file ---
    def load_chat(self, file_path: Path) -> list[dict]:
        """Loads a chat history from a JSON file."""
        if not file_path.exists():
            print(f"Chat file not found: {file_path}")
            # Create it with an empty list if it doesn't exist
            self.save_chat(file_path, [])
            return []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                messages = json.load(f)
                if isinstance(messages, list):
                    return messages
                return [] # Return empty list if file content is not a list
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error loading chat file {file_path}: {e}")
            return []

    # --- NEW: Method to save a chat file ---
    def save_chat(self, file_path: Path, messages: list[dict]):
        """Saves a chat history to a JSON file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(messages, f, indent=2, ensure_ascii=False)
            print(f"Chat saved to {file_path}")
        except (IOError, TypeError) as e:
            print(f"Error saving chat file {file_path}: {e}")

