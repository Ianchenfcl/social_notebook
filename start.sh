#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}===================================================================${NC}"
echo ""
echo -e "         ${GREEN}Love AI Tutor Workspace Startup (macOS/Linux)${NC}"
echo ""
echo -e "${GREEN}===================================================================${NC}"
echo ""

# Check Python installation
echo -e "[*] Checking Python installation..."
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}[ERROR] Python was not found in your system PATH!${NC}"
    echo "Please install Python 3.9+ and make sure it is in your PATH."
    exit 1
fi

# Check virtual environment
echo -e "[*] Checking Python virtual environment (.venv)..."
if [ -f ".venv/bin/python" ]; then
    echo -e "${GREEN}[SUCCESS] Virtual environment found.${NC}"
    PY_EXEC=".venv/bin/python"
else
    echo -e "${YELLOW}[*] Creating virtual environment (.venv)...${NC}"
    $PYTHON_CMD -m venv .venv
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[SUCCESS] Virtual environment created successfully.${NC}"
        PY_EXEC=".venv/bin/python"
    else
        echo -e "${YELLOW}[WARNING] Failed to create virtual environment. Using global Python...${NC}"
        PY_EXEC=$PYTHON_CMD
    fi
fi

# Upgrade package management tools
echo -e "[*] Upgrading pip, setuptools, and wheel in virtual environment..."
$PY_EXEC -m pip install --upgrade pip setuptools wheel --quiet

# Install dependencies
echo -e "[*] Installing requirements (this might take a few moments)..."
$PY_EXEC -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}[WARNING] Dependency installation completed with warnings.${NC}"
else
    echo -e "${GREEN}[SUCCESS] Dependencies verified.${NC}"
fi

echo ""
echo -e "[*] Opening browser to http://localhost:8000..."

# Platform-specific browser opening
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open "http://localhost:8000"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; then
        if command -v xdg-open &>/dev/null; then
            xdg-open "http://localhost:8000"
        else
            echo -e "[INFO] Could not open browser automatically. Please open http://localhost:8000 manually."
        fi
    else
        echo -e "[INFO] Running in headless environment. Please access the application by navigating to http://<server-ip>:8000 in your browser."
    fi
else
    echo -e "[INFO] Please open http://localhost:8000 in your browser."
fi

# Launch FastAPI backend server
echo -e "${GREEN}[*] Launching FastAPI backend server...${NC}"
$PY_EXEC -m uvicorn app:app --reload --port 8000
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERROR] Server exited abnormally.${NC}"
    exit 1
fi
