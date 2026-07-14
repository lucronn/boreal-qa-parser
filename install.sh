#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Define color codes for formatting output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}==================================================${NC}"
echo -e "${CYAN}        Boreal QA Parser Installer                ${NC}"
echo -e "${CYAN}==================================================${NC}"

# Ensure we are in the correct directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# 1. Check for Git
if ! command -v git &> /dev/null; then
    echo -e "${RED}Error: Git is not installed. Please install git and try again.${NC}"
    exit 1
fi

# 2. Check for Python3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python3 is not installed. Please install Python3 and try again.${NC}"
    exit 1
fi

# 3. Determine if using uv or pip/venv
if command -v uv &> /dev/null; then
    echo -e "${GREEN}Detected 'uv' packaging tool. Installing using uv...${NC}"
    
    # Install editable package via uv
    uv pip install -e . 2>/dev/null || uv pip install --system -e .
    
    echo -e "${GREEN}Successfully built and installed package with uv!${NC}"
else
    echo -e "${YELLOW}'uv' not found. Falling back to standard virtualenv + pip setup...${NC}"
    
    if [ ! -d ".venv" ]; then
        echo -e "${CYAN}Creating virtual environment in .venv...${NC}"
        python3 -m venv .venv
    fi
    
    echo -e "${CYAN}Activating virtual environment and installing...${NC}"
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -e .
    
    echo -e "${GREEN}Successfully built and installed package in .venv!${NC}"
fi

# 4. Link or provide helper info for user bin
USER_BIN_DIR="$HOME/.local/bin"
mkdir -p "$USER_BIN_DIR"

if command -v uv &> /dev/null; then
    # With uv, find where uv installed the script or create a wrapper
    CLI_PATH=$(which boreal-cli 2>/dev/null || echo "")
fi

if [ -f ".venv/bin/boreal-cli" ]; then
    CLI_PATH="$DIR/.venv/bin/boreal-cli"
fi

if [ -n "$CLI_PATH" ] || [ -f ".venv/bin/boreal-cli" ]; then
    # Create a symlink or direct copy to ~/.local/bin/boreal-cli
    DEST_PATH="$USER_BIN_DIR/boreal-cli"
    
    # Use realpath or absolute path for symlink
    ABS_CLI_PATH="${CLI_PATH:-$DIR/.venv/bin/boreal-cli}"
    
    rm -f "$DEST_PATH"
    ln -s "$ABS_CLI_PATH" "$DEST_PATH"
    chmod +x "$DEST_PATH"
    echo -e "${GREEN}Symlinked 'boreal-cli' into $DEST_PATH${NC}"
fi

echo -e "\n${GREEN}Installation Complete! 🎉${NC}"
echo -e "You can run the tool using:"
echo -e "  ${CYAN}boreal-cli list${NC}"
echo -e "\nIf the command is not found, make sure ${YELLOW}$HOME/.local/bin${NC} is added to your ${YELLOW}PATH${NC} environment variable."
echo -e "Add this to your shell profile (.bashrc or .zshrc):\n"
echo -e "  ${CYAN}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}\n"
