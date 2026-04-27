@echo off
setlocal

cd /d "%~dp0"

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=py -3.12"
) else (
    set "PYTHON_CMD=python"
)

%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Python 3.12 is required. Install Python 3.12 or make sure py -3.12 is available.
    exit /b 1
)

if exist "venv" if not exist "venv\Scripts\python.exe" (
    echo Removing incomplete virtual environment...
    rmdir /s /q "venv"
)

if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo Removing virtual environment that is not Python 3.12...
        rmdir /s /q "venv"
    )
)

if not exist "venv\Scripts\python.exe" (
    echo Creating Python 3.12 virtual environment...
    %PYTHON_CMD% -m venv venv
    if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%
)

call "venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo Created .env from .env.example. Add your GEMINI_API_KEY before uploading PDFs or generating AI responses.
)

cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
