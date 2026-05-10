@echo off
cd /d "%~dp0"

:: Check if venv exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [TraceCore] No venv found, using system Python
)

:: Launch the app (pythonw = no console window; python = with console for debugging)
:: Use pythonw for a clean app launch, python if you want to see error logs
pythonw src\main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [TraceCore] App exited with an error. Re-running with console to show logs...
    pause
    python src\main.py
    pause
)
