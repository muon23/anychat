import os
import shutil
import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QStyle, QApplication, QMessageBox, QListWidget, QListWidgetItem

# This custom data role is the key. We'll store the full file path
# in each tree item under this role.
PathRole = Qt.ItemDataRole.UserRole + 1


class ChatHistoryManager:
    def __init__(self, history_root: Path):
        self.history_root = history_root
        # Ensure the root directory exists
        self.history_root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_icons(cls):
        """Helper to get standard system icons."""
        style = QApplication.style()
        return {
            "folder": style.standardIcon(QStyle.StandardPixmap.SP_DirIcon),
            "file": style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        }

    @staticmethod
    def _create_folder_item(parent, name: str, path: Path, icons: dict, item_flags) -> QTreeWidgetItem:
        """Creates a folder tree item with standard configuration."""
        folder_item = QTreeWidgetItem(parent, [name])
        folder_item.setIcon(0, icons["folder"])
        folder_item.setData(0, PathRole, str(path))
        folder_item.setFlags(item_flags | Qt.ItemFlag.ItemIsDropEnabled)
        folder_item.setData(0, Qt.ItemDataRole.CheckStateRole, None)  # Hide checkbox
        return folder_item

    @staticmethod
    def _create_file_item(parent, display_name: str, path: Path, icons: dict, item_flags) -> QTreeWidgetItem:
        """Creates a file tree item with standard configuration."""
        file_item = QTreeWidgetItem(parent, [display_name])
        file_item.setIcon(0, icons["file"])
        file_item.setData(0, PathRole, str(path))
        # Enable dragging for file items
        file_item.setFlags(item_flags | Qt.ItemFlag.ItemIsDragEnabled)
        file_item.setData(0, Qt.ItemDataRole.CheckStateRole, None)  # Hide checkbox
        return file_item

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
                    project_item = self._create_folder_item(parent_item, name, path, icons, item_flags)
                    self._load_recursive(path, project_item, icons)
                elif path.is_file() and name.endswith(".json"):
                    display_name = name.replace('.json', '')
                    self._create_file_item(parent_item, display_name, path, icons, item_flags)
        except OSError as e:
            print(f"Error reading directory {parent_dir}: {e}")

    def load_history(self, tree_widget: QTreeWidget):
        """Clears and reloads the entire chat history into the QTreeWidget. (Deprecated - use load_projects and load_top_level_chats)"""
        tree_widget.clear()
        icons = self.get_icons()
        tree_widget.setHeaderHidden(True)  # Hide the "1" header

        try:
            for name in sorted(os.listdir(self.history_root)):
                name = str(name)  # Ensure name is a string
                path = self.history_root / name

                # Set item flags to be enabled, selectable, and not checkable
                item_flags = (Qt.ItemFlag.ItemIsEnabled |
                              Qt.ItemFlag.ItemIsSelectable)

                if path.is_file() and path.suffix == '.json':
                    display_name = name.replace('.json', '')
                    self._create_file_item(tree_widget, display_name, path, icons, item_flags)
                elif path.is_dir():
                    project_item = self._create_folder_item(tree_widget, name, path, icons, item_flags)
                    self._load_recursive(path, project_item, icons)
        except OSError as e:
            print(f"Error reading history root {self.history_root}: {e}")
        print("Chat history loaded into tree.")
    
    def load_projects(self, tree_widget: QTreeWidget):
        """Loads only project directories into the QTreeWidget."""
        tree_widget.clear()
        icons = self.get_icons()
        tree_widget.setHeaderHidden(True)

        try:
            for name in sorted(os.listdir(self.history_root)):
                name = str(name)
                path = self.history_root / name

                item_flags = (Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)

                if path.is_dir():
                    project_item = self._create_folder_item(tree_widget, name, path, icons, item_flags)
                    self._load_recursive(path, project_item, icons)
        except OSError as e:
            print(f"Error reading history root {self.history_root}: {e}")
        print("Projects loaded into tree.")
    
    def load_top_level_chats(self, list_widget: QListWidget):
        """Loads only top-level chat files into the QListWidget."""
        list_widget.clear()
        icons = self.get_icons()

        try:
            for name in sorted(os.listdir(self.history_root)):
                name = str(name)
                path = self.history_root / name

                if path.is_file() and path.suffix == '.json':
                    display_name = name.replace('.json', '')
                    list_item = QListWidgetItem(display_name)
                    list_item.setIcon(icons["file"])
                    list_item.setData(PathRole, str(path))
                    # Enable dragging for list items
                    list_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)
                    list_widget.addItem(list_item)
        except OSError as e:
            print(f"Error reading history root {self.history_root}: {e}")
        print("Top-level chats loaded into list.")

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
            chat_item.setIcon(0, self.get_icons()["file"])
            chat_item.setData(0, PathRole, str(new_chat_path))
            item_flags = (Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
            chat_item.setFlags(item_flags)
            chat_item.setData(0, Qt.ItemDataRole.CheckStateRole, None)  # Hide checkbox

            if parent_project_item:
                parent_project_item.setExpanded(True)

            tree_widget.setCurrentItem(chat_item)
            return chat_item
        except OSError as e:
            print(f"Error creating new chat file: {e}")
            return None
    
    def create_new_chat_in_list(self, list_widget: QListWidget, parent_dir: Path):
        """Creates a new 'Chat N' file in the root directory and adds it to the list."""
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

            # Add the new chat to the list
            list_item = QListWidgetItem(chat_name)
            list_item.setIcon(self.get_icons()["file"])
            list_item.setData(PathRole, str(new_chat_path))
            list_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
            list_widget.addItem(list_item)
            list_widget.setCurrentItem(list_item)
            return list_item
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
            project_item.setIcon(0, self.get_icons()["folder"])
            project_item.setData(0, PathRole, str(new_project_path))
            item_flags = (Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDropEnabled | Qt.ItemFlag.ItemIsEditable)
            project_item.setFlags(item_flags)
            project_item.setData(0, Qt.ItemDataRole.CheckStateRole, None)  # Hide checkbox

            if parent_item:
                parent_item.setExpanded(True)

            tree_widget.setCurrentItem(project_item)
            return project_item
        except OSError as e:
            print(f"Error creating new project: {e}")
            return None

    @classmethod
    def rename_item(cls, old_path: Path, new_name: str, parent_widget) -> bool:
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

    @classmethod
    def delete_item(cls, path: Path, warning_callback) -> bool:
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
                        return False  # User cancelled
        except OSError as e:
            print(f"Error deleting {path}: {e}")
            return False

    @classmethod
    def load_chat(cls, file_path: Path) -> list[dict]:
        """Loads a chat history from a JSON file."""
        if not file_path.exists():
            print(f"Chat file not found: {file_path}")
            # Create it with an empty list if it doesn't exist
            cls.save_chat(file_path, [])
            return []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                messages = json.load(f)
                if isinstance(messages, list):
                    return messages
                return []  # Return empty list if file content is not a list
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error loading chat file {file_path}: {e}")
            return []

    @classmethod
    def save_chat(cls, file_path: Path, messages: list[dict]):
        """Saves a chat history to a JSON file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(messages, f, indent=2, ensure_ascii=False)
            print(f"Chat saved to {file_path}")
        except (IOError, TypeError) as e:
            print(f"Error saving chat file {file_path}: {e}")
