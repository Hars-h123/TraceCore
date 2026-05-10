@echo off
REM build_windows.bat — TraceCore build script for Windows
REM Produces: dist\TraceCore.exe

echo ==========================================
echo      TraceCore -- Build System (Win)
echo ==========================================
echo.

REM Install deps if needed
pip install PyQt6 pyinstaller

echo [*] Building TraceCore...
pyinstaller --clean --noconfirm TraceCore.spec

echo.
echo ==========================================
echo   Build complete!
echo   Executable: dist\TraceCore.exe
echo ==========================================
echo.
echo Run: dist\TraceCore.exe
echo For raw disk access, run as Administrator.
pause
