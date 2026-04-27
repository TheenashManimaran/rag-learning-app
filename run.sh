#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

case "$(uname -s 2>/dev/null || echo unknown)" in
  MINGW*|MSYS*|CYGWIN*)
    IS_WINDOWS=1
    ;;
  *)
    IS_WINDOWS=0
    ;;
esac

if [ "$IS_WINDOWS" -eq 1 ] && command -v py >/dev/null 2>&1; then
  PYTHON_CMD=(py -3.12)
elif command -v python3.12 >/dev/null 2>&1; then
  PYTHON_CMD=(python3.12)
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD=(python3)
else
  PYTHON_CMD=(python)
fi

PYTHON_VERSION="$("${PYTHON_CMD[@]}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [ "$PYTHON_VERSION" != "3.12" ]; then
  echo "Python 3.12 is required, but ${PYTHON_CMD[*]} is Python $PYTHON_VERSION."
  echo "Install Python 3.12 or run the Windows script with: run.bat"
  exit 1
fi

if [ "$IS_WINDOWS" -eq 1 ]; then
  VENV_PYTHON="venv/Scripts/python.exe"
  ACTIVATE_SCRIPT="venv/Scripts/activate"
else
  VENV_PYTHON="venv/bin/python"
  ACTIVATE_SCRIPT="venv/bin/activate"
fi

if [ -d "venv" ] && [ ! -x "$VENV_PYTHON" ]; then
  echo "Removing incomplete virtual environment..."
  rm -rf venv
fi

if [ -x "$VENV_PYTHON" ]; then
  VENV_VERSION="$("$VENV_PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  if [ "$VENV_VERSION" != "3.12" ]; then
    echo "Removing Python $VENV_VERSION virtual environment; Python 3.12 is required..."
    rm -rf venv
  fi
fi

if [ ! -x "$VENV_PYTHON" ]; then
  echo "Creating Python 3.12 virtual environment..."
  "${PYTHON_CMD[@]}" -m venv venv
fi

source "$ACTIVATE_SCRIPT"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [ ! -f ".env" ]; then
  cp ".env.example" ".env"
  echo "Created .env from .env.example. Add your GEMINI_API_KEY before uploading PDFs or generating AI responses."
fi

cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
