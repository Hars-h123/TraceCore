# TraceCore

Professional desktop data recovery software built with Python and PyQt6.  
TraceCore performs real filesystem and raw sector scanning to detect, preview, and recover deleted, hidden, or lost files — all through a clean native desktop interface.

---

## Features

- Quick Scan for fast filesystem-based recovery
- Deep Scan with raw sector file carving
- Supports recovery of images, videos, documents, archives, audio files, executables, and more
- Live scan results with filtering support
- Built-in preview for images and text files
- Drive & folder scanning support
- Cross-platform support for Windows, Linux, and macOS
- Native desktop experience — no browser or web wrappers

---

## Supported File Types

| Category | Formats |
|----------|----------|
| Images | JPG, PNG, GIF, BMP |
| Videos | MP4, AVI |
| Audio | MP3, WAV |
| Documents | PDF, DOCX, XLSX, TXT |
| Archives | ZIP, 7Z, RAR |
| Executables | EXE |

---

## Tech Stack

- Python
- PyQt6
- PyInstaller

---

## Project Structure

```bash
TraceCore/
├── src/
│   ├── main.py
│   ├── scanner.py
│   └── drives.py
├── TraceCore.spec
├── build.sh
├── build_windows.bat
├── requirements.txt
└── README.md
```

---

## Installation

### Clone the Repository

```bash
git clone <your-repo-link>
cd TraceCore
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Running in Development Mode

```bash
cd src
python main.py
```

---

## Building the Application

### Linux / macOS

```bash
chmod +x build.sh
./build.sh
```

### Windows

```bat
build_windows.bat
```

The final executable will be available inside the `dist/` folder.

---

## Permissions

Some advanced recovery operations may require administrator/root access for raw disk scanning.

| Feature | Permission |
|----------|-------------|
| Folder Scan | Normal User |
| Mounted Drive Scan | Normal User |
| Raw Sector Scan | Administrator / Root |

---

## How TraceCore Works

### Quick Scan
Scans the filesystem structure to locate accessible and recently deleted files quickly.

### Deep Scan
Performs low-level raw byte scanning using file signature detection (magic numbers) to recover fragmented or hidden data directly from storage sectors.

---

## Design Philosophy

TraceCore focuses on:
- Simplicity
- Native desktop performance
- Read-only recovery safety
- Lightweight architecture
- Practical usability over unnecessary complexity

---

## Disclaimer

TraceCore is intended for educational, recovery, and research purposes only.  
Always avoid writing new data to a drive after accidental deletion to maximize recovery success.

---

## Author

Developed by Harsh Damania