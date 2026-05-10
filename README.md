# TraceCore — Professional Data Recovery Software

A native desktop data recovery application built with Python + PyQt6.
Performs real filesystem and raw sector scanning — no web tech, no simulation.

## Project Structure

```
TraceCore/
├── src/
│   ├── main.py       — Qt6 GUI: all screens, scan progress, file list, preview, recovery
│   ├── scanner.py    — Scan engine: quick scan + deep scan (file carving by magic bytes)
│   └── drives.py     — Drive/volume enumeration (Linux, macOS, Windows)
├── TraceCore.spec    — PyInstaller build config
├── build.sh          — Linux/macOS build script
├── build_windows.bat — Windows build script
├── requirements.txt  — Python dependencies
└── README.md
```

## Features

- **Quick Scan** — Filesystem walk, finds all accessible files + detects deleted files
  still open in /proc (Linux)
- **Deep Scan** — Raw byte scan with file carving using magic number signatures
- **Supports**: JPG, PNG, GIF, BMP, MP4, AVI, MP3, WAV, PDF, DOCX, XLSX, ZIP, 7Z, RAR, TXT, EXE
- **Preview** — Inline image rendering + text preview panel
- **Recovery** — Copies active files or reconstructs carved data to any destination folder
- **Drive picker** — Enumerates all mounted volumes + raw block devices
- **Folder scan** — Browse and scan any specific folder/path
- **Filter** — Filter results by file extension

## Build Instructions

### Linux / macOS

```bash
# Install dependencies
pip install PyQt6 pyinstaller

# Build
chmod +x build.sh
./build.sh

# Run
./dist/TraceCore

# For raw disk access (block devices like /dev/sda):
sudo ./dist/TraceCore
# OR add yourself to disk group:
sudo usermod -a -G disk $USER
```

### Windows

```bat
REM Run as Administrator for raw disk access
build_windows.bat
dist\TraceCore.exe
```

### Run without building (development mode)

```bash
pip install PyQt6
cd src
python3 main.py
```

## Permissions

| Feature | Requires |
|---------|----------|
| Folder scan | Normal user |
| Mounted drive scan | Normal user |
| Raw block device scan (/dev/sdX) | root or disk group |
| /proc deleted file detection | Normal user |

## Technical Notes

- **Read-only**: TraceCore never writes to scanned drives/devices
- **File carving** reads raw bytes in 512KB blocks with overlap buffering
  to catch signatures that span block boundaries
- **Magic numbers** used for: JPG (FF D8 FF), PNG (89 50 4E 47), PDF (%PDF-),
  ZIP/DOCX/XLSX (PK\x03\x04), MP4 (ftyp), MP3 (FF FB / ID3), and more
- **Live results**: Shows files as they are found during scan (up to 5,000 live rows)
- **Deep scan on folders**: Carves every file in the folder for embedded/hidden data
- **Deep scan on devices**: Reads raw sectors sequentially from start to end

## Colors / Theme

| Variable | Hex | Usage |
|----------|-----|-------|
| Primary | #FE7743 | Buttons, progress bars, highlights |
| Background | #EFEEEA | Main window background |
| Accent | #273F4F | Headers, sidebar, table headers |
| Base | #000000 | Text |
