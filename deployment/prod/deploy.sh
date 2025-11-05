#!/bin/bash

# Deployment script for macOS production environment
# This script should be run from the project root directory after cloning from GitHub

set -e  # Exit on error

# Get the project root directory (parent of deployment/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "Project root: $PROJECT_ROOT"

# Check if Python 3.11 is available, install if not
if ! command -v python3.11 &> /dev/null; then
    echo "Python 3.11 is not installed. Attempting to install..."
    
    # Check if Homebrew is installed
    if command -v brew &> /dev/null; then
        echo "Installing Python 3.11 via Homebrew..."
        brew install python@3.11
        
        # Verify installation
        if ! command -v python3.11 &> /dev/null; then
            echo "Error: Python 3.11 installation failed or not found in PATH."
            echo "Please ensure Homebrew installed Python 3.11 and it's in your PATH."
            echo "You may need to run: brew link python@3.11"
            exit 1
        fi
    else
        echo "Error: Homebrew is not installed."
        echo "Please install Homebrew first:"
        echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
        echo ""
        echo "Then run this script again, or install Python 3.11 manually."
        exit 1
    fi
fi

PYTHON_VERSION=$(python3.11 --version)
echo "Found: $PYTHON_VERSION"

# Check if venv exists
VENV_DIR="$PROJECT_ROOT/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3.11 -m venv "$VENV_DIR"
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Check if packages are installed
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "Error: requirements.txt not found at $REQUIREMENTS_FILE"
    exit 1
fi

# Check if packages need to be installed
if [ ! -f "$VENV_DIR/.installed" ] || [ "$REQUIREMENTS_FILE" -nt "$VENV_DIR/.installed" ]; then
    echo "Installing/updating packages from requirements.txt..."
    pip install --upgrade pip
    pip install -r "$REQUIREMENTS_FILE"
    touch "$VENV_DIR/.installed"
    echo "Packages installed."
else
    echo "Packages already installed (up to date)."
fi

# Verify config file exists
CONFIG_FILE="$PROJECT_ROOT/deployment/prod/config.ini"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Warning: Config file not found at $CONFIG_FILE"
    echo "The application may use default configuration."
fi

# Run the application
echo "Starting application..."
echo "Running: python src/main/ui/main_window.py -p deployment/prod/config.ini"
python src/main/ui/main_window.py -p deployment/prod/config.ini

