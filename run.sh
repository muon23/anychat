#!/bin/zsh

# Get the project root directory (where this script is located)
SCRIPT_DIR="$(cd "$(dirname "${(%):-%x}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Add src/main to PYTHONPATH so local modules can be imported
export PYTHONPATH="${PROJECT_ROOT}/src/main:${PYTHONPATH}"

python src/main/ui/main_window.py -p deployment/"${1:-prod}"/config.ini