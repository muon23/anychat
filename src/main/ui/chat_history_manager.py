import os
from pathlib import Path

from PySide6.QtCore import Qt  # <-- Import Qt for flags
# We need QIcon from QtGui and QStyle from QtWidgets
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QInputDialog, QMessageBox, QStyle

# A custom data role to store the file path in a tree item
PathRole = 10  # Qt::UserRole starts at 10

class ChatHistoryManager:
    """
    Manages loading, creating, and organizing chat projects and files
    in the chat history tree.
    """
    def __init__(self, history_root: Path):
        self.history_root = history_root
        self.history_root.mkdir(parents=True, exist_ok=True)
        print(f"Chat history root initialized at: {self.history_root.resolve()}")

    def _load_recursive(self, parent_item, parent_path):
        """Helper function to recursively load history."""
        try:
            # Get the standard icons from the application's style
            style = parent_item.treeWidget().style()
            folder_icon = style.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
            file_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)

            for name_bytes in sorted(os.listdir(parent_path)):
                name = str(name_bytes)
                path = parent_path / name

                if path.is_dir():
                    # This is a project or subproject
                    project_item = QTreeWidgetItem(parent_item, [name])
                    project_item.setIcon(0, folder_icon)
                    project_item.setData(0, PathRole, str(path))

                    # --- FIX 3: Force-hide checkbox via data role ---
                    project_item.setData(0, Qt.ItemDataRole.CheckStateRole, None)
                    # --- End Fix ---

                    # Recurse
                    self._load_recursive(project_item, path)
                elif path.is_file() and path.suffix == '.json' and not name.startswith("Chat "):
                    # This is a named chat file
                    chat_item = QTreeWidgetItem(parent_item, [name.replace('.json', '')])
                    chat_item.setIcon(0, file_icon)
                    chat_item.setData(0, PathRole, str(path))

                    # --- FIX 3: Force-hide checkbox via data role ---
                    chat_item.setData(0, Qt.ItemDataRole.CheckStateRole, None)
                    # --- End Fix ---

        except OSError as e:
            print(f"Error scanning directory {parent_path}: {e}")

    def load_history(self, tree_widget: QTreeWidget):
        """
        Scans the history_root directory and populates the QTreeWidget.
        Folders are projects, .json files are chats.
        """
        tree_widget.clear()

        # Get the file icon for temporary chats
        style = tree_widget.style()
        file_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)

        # Load temporary "Chat N" files at the root
        try:
            for name_bytes in sorted(os.listdir(self.history_root)):
                name = str(name_bytes)
                path = self.history_root / name
                if path.is_file() and path.suffix == '.json' and name.startswith("Chat "):
                    chat_item = QTreeWidgetItem(tree_widget, [name.replace('.json', '')])
                    chat_item.setIcon(0, file_icon)
                    chat_item.setData(0, PathRole, str(path))

                    # --- FIX 3: Force-hide checkbox via data role ---
                    chat_item.setData(0, Qt.ItemDataRole.CheckStateRole, None)
                    # --- End Fix ---

        except OSError as e:
            print(f"Error scanning root directory {self.history_root}: {e}")

        # Load all projects and their sub-items
        self._load_recursive(tree_widget.invisibleRootItem(), self.history_root)

        tree_widget.expandAll()
        print("Chat history loaded into tree.")

    def _get_parent_path(self, parent_item: QTreeWidgetItem) -> Path:
        """Determines the correct file path for a new item based on its parent."""
        if parent_item:
            # This is a subproject or a chat in a project
            return Path(parent_item.data(0, PathRole))
        else:
            # This is a top-level item
            return self.history_root

    def create_project(self, tree_widget: QTreeWidget, parent_item: QTreeWidgetItem = None):
        """
        Prompts the user for a new project name and creates a directory
        under the given parent (or root if parent is None).
        """
        parent_path = self._get_parent_path(parent_item)

        project_name, ok = QInputDialog.getText(tree_widget.window(),
                                                "New Project", "Enter project name:")

        if ok and project_name:
            try:
                new_project_path = parent_path / project_name
                new_project_path.mkdir(parents=True, exist_ok=False)
                print(f"Created new project: {new_project_path}")
                self.load_history(tree_widget)
            except FileExistsError:
                QMessageBox.warning(tree_widget.window(), "Error",
                                    f"A project named '{project_name}' already exists here.")
            except OSError as e:
                QMessageBox.warning(tree_widget.window(), "Error",
                                    f"Could not create project: {e}")

    def create_new_chat(self, tree_widget: QTreeWidget, parent_project_item: QTreeWidgetItem = None):
        """
        Creates a new chat file.
        If parent_project_item is None, creates a 'Chat N.json' in the root.
        If parent_project_item is provided, prompts for a name and creates a file in that project.
        """
        parent_path = self._get_parent_path(parent_project_item)

        if parent_project_item:
            # Case 1: Create a named chat inside a specific project
            project_name = parent_project_item.text(0)
            chat_name, ok = QInputDialog.getText(tree_widget.window(),
                                                 "New Chat", f"Enter new chat name for project '{project_name}':")
        else:
            # Case 2: Create a temporary "Chat N" in the root
            chat_name, ok = self._get_next_temp_chat_name()
            if not ok: # Error message is handled inside the helper
                QMessageBox.warning(tree_widget.window(), "Error", chat_name)
                return

        if ok and chat_name:
            try:
                chat_file_name = f"{chat_name}.json"
                new_chat_path = parent_path / chat_file_name

                if new_chat_path.exists():
                    raise FileExistsError(f"A chat named '{chat_name}' already exists in this location.")

                # Create an empty JSON file
                with open(new_chat_path, 'w') as f:
                    f.write("[]") # Start with an empty JSON list for messages

                print(f"Created new chat: {new_chat_path}")
                self.load_history(tree_widget)
            except FileExistsError as e:
                QMessageBox.warning(tree_widget.window(), "Error", str(e))
            except OSError as e:
                QMessageBox.warning(tree_widget.window(), "Error",
                                    f"Could not create chat file: {e}")

    def _get_next_temp_chat_name(self) -> (str, bool):
        """Finds the next available 'Chat N' name."""
        try:
            i = 1
            while True:
                chat_name = f"Chat {i}"
                chat_path = self.history_root / f"{chat_name}.json"
                if not chat_path.exists():
                    return chat_name, True
                i += 1
                if i > 1000: # Safety break
                    return "Could not find an available chat name.", False
        except Exception as e:
            return f"Error finding chat name: {e}", False




