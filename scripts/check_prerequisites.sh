#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=========================================================="
echo "          RUBY — System Prerequisites Checker             "
echo "=========================================================="

PASSED=0
WARNINGS=0
FAILED=0

check_cmd() {
    local name="$1"
    local cmd="$2"
    local min_ver="$3"
    
    if command -v "$cmd" > /dev/null 2>&1; then
        local ver
        ver=$($cmd --version 2>&1 | head -n 1)
        echo -e "[\e[32mOK\e[0m] $name found: $ver"
        PASSED=$((PASSED + 1))
    else
        echo -e "[\e[31mFAIL\e[0m] $name ($cmd) is NOT installed. Required for Ruby."
        FAILED=$((FAILED + 1))
    fi
}

check_optional_cmd() {
    local name="$1"
    local cmd="$2"
    local purpose="$3"
    
    if command -v "$cmd" > /dev/null 2>&1; then
        local ver
        ver=$($cmd --version 2>&1 | head -n 1)
        echo -e "[\e[32mOK\e[0m] $name found: $ver"
        PASSED=$((PASSED + 1))
    else
        echo -e "[\e[33mWARN\e[0m] $name ($cmd) not found ($purpose). Graceful fallback enabled."
        WARNINGS=$((WARNINGS + 1))
    fi
}

echo -e "\n--- Core Runtimes ---"
check_cmd "Python" "python3" "3.11"
check_cmd "Node.js" "node" "18.0"
check_cmd "npm" "npm" "9.0"
check_cmd "Git" "git" "2.0"

echo -e "\n--- Local AI Inference ---"
check_optional_cmd "Ollama Daemon" "ollama" "Local offline LLM inference"

echo -e "\n--- Acceleration Hardware ---"
if command -v nvidia-smi > /dev/null 2>&1; then
    GPU_NAME=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -n 1)
    echo -e "[\e[32mOK\e[0m] NVIDIA GPU Detected: $GPU_NAME"
    PASSED=$((PASSED + 1))
else
    echo -e "[\e[33mWARN\e[0m] nvidia-smi not detected. Ruby will run in CPU-only mode."
    WARNINGS=$((WARNINGS + 1))
fi

echo -e "\n--- Optional Auxiliary Utilities ---"
check_optional_cmd "LibreOffice" "libreoffice" "Legacy .doc and .ppt conversion"
check_optional_cmd "Tesseract OCR" "tesseract" "Scanned image and photo OCR"

echo -e "\n--- Python Virtual Environment ---"
if [ -d "$DIR/backend/.venv" ]; then
    echo -e "[\e[32mOK\e[0m] Backend virtual environment found: $DIR/backend/.venv"
    PASSED=$((PASSED + 1))
else
    echo -e "[\e[33mWARN\e[0m] Backend virtual environment missing. Run: cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    WARNINGS=$((WARNINGS + 1))
fi

echo -e "\n=========================================================="
echo "Summary: $PASSED passed, $WARNINGS warnings, $FAILED failed."
if [ "$FAILED" -eq 0 ]; then
    echo -e "\e[32mAll core prerequisites satisfied. System is ready to run RUBY.\e[0m"
    exit 0
else
    echo -e "\e[31mPlease install missing core prerequisites before launching RUBY.\e[0m"
    exit 1
fi
