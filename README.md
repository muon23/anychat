# AnyChat

A modern, desktop chat application for interacting with multiple Large Language Model (LLM) providers through a unified interface. Built with PySide6 (Qt) and LangChain, AnyChat provides a rich, responsive UI for managing conversations, projects, and multiple AI models.

## Features

### Core Functionality
- **Multi-Provider Support**: Seamlessly switch between OpenAI, Google AI (Gemini), DeepInfra, and HuggingFace models
- **Project Management**: Organize chats into hierarchical projects with drag-and-drop support
- **Chat History**: Persistent chat history stored as JSON files
- **Message Editing**: Edit, regenerate, and refine messages with full conversation context
- **Fork Conversations**: Create new chat branches from any point in a conversation
- **Web Search Integration**: Optional web search tools for supported models (DuckDuckGo)
- **Markdown Rendering**: Rich markdown rendering for assistant messages
- **Raw/Rendered Mode**: Toggle between rendered markdown and raw text views
- **Message Refinement**: Refine assistant responses with custom prompts
- **Model Aliases**: Short aliases for commonly used models (e.g., `gpt-3.5` → `gpt-3.5-turbo`)

## Supported LLM Providers and Models

### OpenAI (via `langchain-openai`)
- `gpt-5`, `gpt-5.1` (400K context window)
- `gpt-4o`, `gpt-4o-mini` (16K context window)
- `gpt-4.1`
- `gpt-4` (8K context window)
- `gpt-3.5-turbo` (alias: `gpt-3.5`)
- `o1`, `o3-mini` (reasoning models)

**Web Search Support**: `gpt-4o`, `gpt-4o-mini`, `gpt-4.1`, `gpt-5`

### Google AI / Gemini (via `langchain-google-genai`)
- `gemini-2.5-pro` (alias: `gemini-2.5`)
- `gemini-2.5-flash`
- `gemini-2.0-flash` (alias: `gemini-2`)
- `gemini-2.0-flash-thinking-exp-01-21` (alias: `gemini-2t`)

### DeepInfra (via OpenAI-compatible API)
- `meta-llama/Llama-3.3-70B-Instruct` (alias: `llama-3`)
- `meta-llama/Llama-4-Scout-17B-16E-Instruct` (alias: `llama-4`)
- `deepseek-ai/DeepSeek-V3.1` (alias: `deepseek-v3.1`)
- `moonshotai/Kimi-K2-Instruct-0905` (alias: `kimi-k2`)
- `Sao10K/L3.3-70B-Euryale-v2.3` (alias: `euryale`)
- `microsoft/WizardLM-2-8x22B` (alias: `wizard-2`)

**Web Search Support**: `llama-3`, `llama-4`, `deepseek-v3.1`, `kimi-k2`

### HuggingFace
- Local and remote HuggingFace models via Transformers

### Mock LLM
- `mock` - For testing and development

## Installation

### Prerequisites
- Python 3.11 or higher
- Qt libraries (installed automatically with PySide6)
- Enchant library for spell checking:
  - **macOS**: `brew install enchant`
  - **Linux**: `sudo apt-get install enchant` (Ubuntu/Debian) or equivalent
  - **Windows**: Install from [Enchant downloads](https://github.com/AbiWord/enchant/releases)

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd anychat
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install PyEnchant** (after installing system enchant library):
   ```bash
   pip install pyenchant>=3.2.0
   ```

## Configuration

### Configuration File

Create a `config.ini` file (or use the provided `deployment/prod/config.ini` as a template):

```ini
[General]
keys_file = deployment/prod/api_keys.json
chat_history_root = deployment/prod/chats

# Comma-separated list of provider names to show in the Keys dialog
providers = OpenAI, Google AI

# Comma-separated list of curated models to show in the dropdown
models = gpt-5.1, gpt-4o, gemini-2.5, deepseek-v3.1

[gpt-5.1]
provider = OpenAI

[gpt-4o]
provider = OpenAI
temperature = 0.7
top_p = 1.0

[gemini-2.5]
provider = Google AI

[deepseek-v3.1]
provider = DeepInfra
```

### Command Line Options

Run with a custom config file:
```bash
python src/main/ui/main_window.py -p path/to/config.ini
# or
python src/main/ui/main_window.py --properties path/to/config.ini
```

Or use the provided script:
```bash
./run.sh  # Uses deployment/prod/config.ini
```

## Usage

### Starting the Application

```bash
python src/main/ui/main_window.py
```

Or use the run script:
```bash
./run.sh
```

### API Keys

API keys are entered through the application's UI after launching:

1. **Click the "Keys" button** in the toolbar (or access via menu)
2. **Enter your API keys** for each provider you want to use
3. **Click "Save"** - keys are automatically saved to the JSON file specified in `config.ini`

The keys file path is specified in the `keys_file` setting in `config.ini`. You don't need to create this file manually - it will be created automatically when you save keys through the dialog.

**Security Note**: The keys file must be located outside the chat history root directory for security reasons. The application will check this on startup and exit with an error if the keys file is inside the chat history directory.

### Basic Operations

1. **Create a New Chat**: Click "New Chat" button or use the keyboard shortcut
2. **Select a Model**: Choose from the model dropdown in the toolbar
3. **Send Messages**: Type your message and press Enter or click "Send"
4. **Edit Messages**: Click the edit button on any message bubble
5. **Regenerate Responses**: Click the regenerate button on assistant messages
6. **Fork Conversations**: Click the fork button on user messages to create a new branch
7. **Refine Responses**: Use the "Refine" button in the regenerate dialog to improve responses

### Project Management

- **Create Projects**: Click "New Project" to create a project folder
- **Organize Chats**: Drag and drop chats into projects
- **Nested Projects**: Create subprojects by dragging projects into other projects
- **Move to Top Level**: Drag items to empty space below the list to move to top level

### System Messages

- Access system message templates from the menu
- Customize system prompts for different use cases
- Templates are stored in the `system_message_templates` directory

## Project Structure

```
anychat/
├── src/
│   ├── main/
│   │   ├── llms/              # LLM provider implementations
│   │   │   ├── GptLlm.py      # OpenAI GPT models
│   │   │   ├── GeminiLlm.py   # Google Gemini models
│   │   │   ├── DeepInfraLlm.py # DeepInfra models
│   │   │   ├── HuggingFaceLlm.py # HuggingFace models
│   │   │   ├── websearch/     # Web search tools
│   │   │   ├── kvquery/       # Key-value query tools
│   │   │   └── sqlquery/      # SQL query tools
│   │   └── ui/                 # UI components
│   │       ├── main_window.py # Main application window
│   │       ├── chat_message_widget.py # Message bubble widget
│   │       ├── chat_history_manager.py # Chat history management
│   │       ├── config_manager.py # Configuration management
│   │       ├── key_manager.py # API key management
│   │       └── ...
│   └── test/                   # Test files
├── deployment/
│   ├── dev/                    # Development configuration
│   │   ├── config.ini
│   │   ├── api_keys.json
│   │   └── chats/              # Chat history storage
│   └── prod/                   # Production configuration
├── notebooks/                  # Jupyter notebooks for experimentation
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Development

### Architecture

- **UI Framework**: PySide6 (Qt for Python)
- **LLM Integration**: LangChain 1.0+ with LangGraph for agents
- **Async Processing**: QThread for non-blocking LLM calls
- **Data Storage**: JSON files for chat history
- **Configuration**: INI files with ConfigParser

### Key Components

- **MainWindow**: Main application window managing UI state and user interactions
- **LLMService**: Service layer for LLM invocations
- **ChatHistoryManager**: Manages chat file operations and project structure
- **ConfigManager**: Handles configuration file loading and validation
- **KeyManager**: Manages API keys securely
- **ChatMessageWidget**: Individual message bubble with editing/regeneration capabilities

### Testing

Run tests:
```bash
python -m pytest src/test/
```

Or run individual test files:
```bash
python src/test/llms/LlmTest.py
python src/test/llms/RunnableToLLMAdapterTest.py
```

## Dependencies

### Core
- **PySide6** >= 6.0.0 - Qt framework for Python
- **LangChain** >= 1.0.7 - LLM framework and abstractions
- **LangChain Core** >= 1.0.5 - Core LangChain components
- **LangGraph** >= 1.0.0 - Agent orchestration
- **LangChain Classic** >= 1.0.0 - Compatibility layer

### LLM Providers
- **langchain-openai** >= 1.0.3 - OpenAI integration
- **langchain-google-genai** >= 3.0.3 - Google AI integration
- **langchain-community** >= 0.4.1 - Community integrations

### Utilities
- **transformers** >= 4.57.0 - HuggingFace models
- **httpx** >= 0.28.1 - HTTP client
- **trafilatura** >= 2.0.0 - Web content extraction
- **ddgs** >= 9.6.1 - DuckDuckGo search
- **pydantic** >= 2.12.0 - Data validation
- **pyenchant** >= 3.2.0 - Spell checking
- **markdown** >= 3.4.0 - Markdown rendering
- **torch** >= 2.8.0 - PyTorch (for some HuggingFace models)

See `requirements.txt` for the complete list.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [LangChain](https://www.langchain.com/) and [LangGraph](https://github.com/langchain-ai/langgraph)
- UI framework: [PySide6](https://www.qt.io/qt-for-python)
- Icons and UI elements: Qt standard icons
