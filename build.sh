#!/usr/bin/env bash
# build.sh — TraceCore build script
# Produces a single-file executable: dist/TraceCore
#
# Usage:
#   chmod +x build.sh
#   ./build.sh
#
# Requirements:
#   pip install PyQt6 pyinstaller

set -e

echo "╔══════════════════════════════════════╗"
echo "║     TraceCore — Build System         ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Check dependencies
python3 -c "import PyQt6" 2>/dev/null || {
    echo "[!] PyQt6 not found. Installing..."
    pip install PyQt6 --break-system-packages
}
python3 -c "import PyInstaller" 2>/dev/null || {
    echo "[!] PyInstaller not found. Installing..."
    pip install pyinstaller --break-system-packages
}

echo "[*] Building TraceCore..."
pyinstaller --clean --noconfirm TraceCore.spec

echo ""
echo "╔══════════════════════════════════════╗"
echo "║  Build complete!                     ║"
echo "║  Executable: dist/TraceCore          ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "Run with:  ./dist/TraceCore"
echo "Or (root): sudo ./dist/TraceCore"
echo ""
echo "NOTE: For raw device scanning (/dev/sdX),"
echo "      run as root or add your user to disk group:"
echo "      sudo usermod -a -G disk \$USER"
