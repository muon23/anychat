#!/bin/zsh

# Get the project root directory (where this script is located)
SCRIPT_DIR="$(cd "$(dirname "${(%):-%x}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Use Python from virtual environment if it exists
if [ -d "${PROJECT_ROOT}/venv" ]; then
    PYTHON="${PROJECT_ROOT}/venv/bin/python"
elif [ -d "${PROJECT_ROOT}/.venv" ]; then
    PYTHON="${PROJECT_ROOT}/.venv/bin/python"
else
    # Fall back to system python (may not have required packages)
    PYTHON="python3"
    echo "Warning: No virtual environment found. Using system Python. This may not have required packages installed."
fi

# Add src/main to PYTHONPATH so local modules can be imported
export PYTHONPATH="${PROJECT_ROOT}/src/main:${PYTHONPATH}"

# Run the application
"${PYTHON}" src/main/ui/main_window.py -p deployment/"${1:-prod}"/config.ini