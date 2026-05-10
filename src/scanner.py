"""
scanner.py - TraceCore scan engine
Handles: filesystem quick scan + raw deep scan (file carving by magic bytes)
READ-ONLY disk access only.

Deleted file detection strategies:
  Windows : $Recycle.Bin (user-deleted), $MFT raw parse (NTFS deleted entries),
            shadow copies listing, recently deleted temp/system locations
  Linux   : /proc/*/fd links marked (deleted), ext journal heuristics
  macOS   : ~/.Trash, /Volumes/*/.Trashes
"""

import os
import struct
import threading
import platform
import stat
import time
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Callable
from enum import Enum

# ── File signatures (magic bytes) for deep scan ──────────────────────────────
FILE_SIGNATURES = [
    # (extension, header_bytes, optional_footer, description)
    ("jpg",  b"\xFF\xD8\xFF",               b"\xFF\xD9",       "JPEG Image"),
    ("png",  b"\x89PNG\r\n\x1a\n",          b"\x00\x00IEND\xaeB`\x82", "PNG Image"),
    ("gif",  b"GIF87a",                     b"\x00\x3b",       "GIF Image"),
    ("gif",  b"GIF89a",                     b"\x00\x3b",       "GIF Image"),
    ("bmp",  b"BM",                         None,              "BMP Image"),
    ("mp4",  b"\x00\x00\x00\x18ftyp",      None,              "MP4 Video"),
    ("mp4",  b"\x00\x00\x00\x20ftyp",      None,              "MP4 Video"),
    ("mp4",  b"\x00\x00\x00\x1cftyp",      None,              "MP4 Video"),
    ("avi",  b"RIFF",                       None,              "AVI Video"),
    ("mp3",  b"\xFF\xFB",                   None,              "MP3 Audio"),
    ("mp3",  b"\xFF\xF3",                   None,              "MP3 Audio"),
    ("mp3",  b"ID3",                        None,              "MP3 Audio"),
    ("wav",  b"RIFF",                       None,              "WAV Audio"),
    ("pdf",  b"%PDF-",                      b"%%EOF",          "PDF Document"),
    ("zip",  b"PK\x03\x04",               b"PK\x05\x06",     "ZIP Archive"),
    ("docx", b"PK\x03\x04",               None,              "DOCX Document"),
    ("xlsx", b"PK\x03\x04",               None,              "XLSX Spreadsheet"),
    ("txt",  None,                          None,              "Text File"),
    ("exe",  b"MZ",                         None,              "Executable"),
    ("7z",   b"7z\xbc\xaf'\x1c",           None,              "7-Zip Archive"),
    ("rar",  b"Rar!\x1a\x07",              None,              "RAR Archive"),
]

MAX_CARVED_SIZE = {
    "jpg": 20 * 1024 * 1024,
    "png": 30 * 1024 * 1024,
    "gif": 10 * 1024 * 1024,
    "bmp": 50 * 1024 * 1024,
    "mp4": 4  * 1024 * 1024 * 1024,
    "avi": 2  * 1024 * 1024 * 1024,
    "mp3": 50 * 1024 * 1024,
    "wav": 500* 1024 * 1024,
    "pdf": 100* 1024 * 1024,
    "zip": 500* 1024 * 1024,
    "docx":100* 1024 * 1024,
    "xlsx":100* 1024 * 1024,
    "txt": 10 * 1024 * 1024,
    "exe": 200* 1024 * 1024,
    "7z":  500* 1024 * 1024,
    "rar": 500* 1024 * 1024,
}

class ScanMode(Enum):
    QUICK = "quick"
    DEEP  = "deep"

class FileStatus(Enum):
    ACTIVE  = "Active"    # File exists on the system right now
    DELETED = "Removed"   # File was deleted (removed from filesystem index)
    CARVED  = "Erased"    # File was formatted/overwritten, recovered by raw carving

@dataclass
class RecoveredFile:
    name:        str
    ext:         str
    size:        int
    path:        str
    status:      FileStatus
    description: str
    offset:      int = 0
    data_offset: int = 0
    preview_data: Optional[bytes] = None

    def size_str(self) -> str:
        n = float(self.size)
        for unit in ["B","KB","MB","GB"]:
            if n < 1024:
                return f"{n:.1f} {unit}"
            n /= 1024
        return f"{n:.1f} TB"


class ScanEngine:
    """
    Main scan engine.
    quick_scan : walks filesystem for active files AND probes OS-level deleted
                 file sources (Recycle Bin, $MFT, Trash, /proc) per platform.
    deep_scan  : reads raw bytes, carves files by magic numbers.
    """

    def __init__(self):
        self._stop_flag  = threading.Event()
        self._pause_flag = threading.Event()
        self._pause_flag.set()

    def stop(self):   self._stop_flag.set()
    def pause(self):  self._pause_flag.clear()
    def resume(self): self._pause_flag.set()
    def reset(self):
        self._stop_flag.clear()
        self._pause_flag.set()

    # ── Quick Scan ────────────────────────────────────────────────────────────
    def quick_scan(self,
                   root: str,
                   progress_cb: Callable[[int, int, str], None],
                   result_cb:   Callable[["RecoveredFile"], None]):
        self.reset()
        sys = platform.system()

        # ── Phase 1: Active files ────────────────────────────────────────────
        all_paths = []
        for dirpath, dirs, files in os.walk(root, followlinks=False):
            if self._stop_flag.is_set(): return
            # Skip known system/recovery noise dirs
            dirs[:] = [d for d in dirs if d not in
                       {"$RECYCLE.BIN", "System Volume Information",
                        "$MFT", "lost+found"}]
            for fn in files:
                all_paths.append(os.path.join(dirpath, fn))

        total = len(all_paths)
        for i, fpath in enumerate(all_paths):
            self._pause_flag.wait()
            if self._stop_flag.is_set(): return
            progress_cb(i + 1, total, fpath)
            try:
                s    = os.stat(fpath)
                ext  = Path(fpath).suffix.lstrip(".").lower() or "dat"
                rf   = RecoveredFile(
                    name=Path(fpath).name, ext=ext, size=s.st_size,
                    path=fpath, status=FileStatus.ACTIVE,
                    description=self._ext_desc(ext)
                )
                result_cb(rf)
            except (PermissionError, OSError):
                pass

        # ── Phase 2: Deleted files (platform-specific) ───────────────────────
        progress_cb(total, total, "Scanning for deleted files…")

        if sys == "Windows":
            self._scan_recycle_bin(root, result_cb, progress_cb)
            self._scan_mft_deleted(root, result_cb, progress_cb)
        elif sys == "Linux":
            self._scan_proc_deleted(root, result_cb)
            self._scan_linux_trash(result_cb, progress_cb)
        elif sys == "Darwin":
            self._scan_macos_trash(result_cb, progress_cb)

        progress_cb(total, total, "Done")

    # ── Windows: $Recycle.Bin ─────────────────────────────────────────────────
    def _scan_recycle_bin(self, root: str, result_cb, progress_cb):
        """
        Scan all $RECYCLE.BIN folders accessible on every drive.
        Each deleted file has a paired $I (metadata) + $R (data) file.
        $I file: header = 8-byte version, 8-byte size, 8-byte timestamp,
                 then UTF-16LE original path (variable length).
        """
        drives = self._get_windows_drives()
        for drive in drives:
            recycle = os.path.join(drive, "$RECYCLE.BIN")
            if not os.path.exists(recycle):
                continue
            try:
                for sid_dir in os.scandir(recycle):
                    if not sid_dir.is_dir():
                        continue
                    try:
                        for entry in os.scandir(sid_dir.path):
                            if self._stop_flag.is_set(): return
                            name = entry.name
                            # $I files hold the metadata for deleted items
                            if name.startswith("$I"):
                                r_name = "$R" + name[2:]
                                r_path = os.path.join(sid_dir.path, r_name)
                                orig_name, orig_size, deleted_time = \
                                    self._parse_recycle_i_file(entry.path)
                                # Use $R path (actual data) if it exists
                                data_path = r_path if os.path.exists(r_path) else entry.path
                                if not orig_name:
                                    orig_name = name
                                ext  = Path(orig_name).suffix.lstrip(".").lower() or "dat"
                                size = orig_size
                                try:
                                    if os.path.exists(r_path):
                                        size = os.path.getsize(r_path)
                                except OSError:
                                    pass
                                progress_cb(0, 0, f"Recycle Bin: {orig_name}")
                                rf = RecoveredFile(
                                    name=orig_name,
                                    ext=ext,
                                    size=size,
                                    path=data_path,
                                    status=FileStatus.DELETED,
                                    description=self._ext_desc(ext) + " (Recycle Bin)"
                                )
                                result_cb(rf)
                    except (PermissionError, OSError):
                        pass
            except (PermissionError, OSError):
                pass

    def _parse_recycle_i_file(self, path: str):
        """
        Parse Windows $I metadata file.
        Returns (original_filename, file_size, deleted_datetime_str).
        Format v2 (Win 7+): [8 version][8 size][8 FILETIME][variable UTF-16LE path]
        """
        try:
            with open(path, "rb") as f:
                data = f.read()
            if len(data) < 24:
                return None, 0, ""
            version = struct.unpack_from("<q", data, 0)[0]
            size    = struct.unpack_from("<q", data, 8)[0]
            ftime   = struct.unpack_from("<q", data, 16)[0]
            # Convert FILETIME to readable string
            try:
                EPOCH_DIFF = 116444736000000000
                ts = (ftime - EPOCH_DIFF) / 10_000_000
                import datetime
                dt = datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
            except Exception:
                dt = ""
            # Read original path (UTF-16LE)
            if version == 2:
                # v2: 4-byte name length follows at offset 24
                if len(data) >= 28:
                    name_len = struct.unpack_from("<I", data, 24)[0]
                    name_bytes = data[28: 28 + name_len * 2]
                else:
                    name_bytes = data[24:]
            else:
                # v1: path starts at offset 24, null-terminated UTF-16LE
                name_bytes = data[24:]
            orig_path = name_bytes.decode("utf-16-le", errors="replace").rstrip("\x00")
            orig_name = os.path.basename(orig_path) or orig_path
            return orig_name, max(size, 0), dt
        except Exception:
            return None, 0, ""

    def _get_windows_drives(self):
        """Return list of drive root paths on Windows."""
        drives = []
        try:
            import string
            for letter in string.ascii_uppercase:
                d = f"{letter}:\\"
                if os.path.exists(d):
                    drives.append(d)
        except Exception:
            pass
        return drives

    # ── Windows: $MFT raw parse (NTFS deleted entries) ────────────────────────
    def _scan_mft_deleted(self, root: str, result_cb, progress_cb):
        """
        Try to open and parse $MFT on the NTFS volume to find deleted entries.
        Requires admin/elevated privileges. Skips silently if not available.

        MFT record signature = "FILE" (0x46494C45). Records with the
        'in-use' flag bit 0 cleared are deleted entries.
        """
        # Determine drive letter from root
        if len(root) >= 2 and root[1] == ":":
            drive = root[:2]
        else:
            return

        mft_path = drive + "\\$MFT"
        RECORD_SIZE = 1024
        HEADER_SIG  = b"FILE"
        FLAG_IN_USE = 0x0001

        try:
            progress_cb(0, 0, "Scanning $MFT for deleted entries (needs admin)…")
            with open(mft_path, "rb") as mft:
                record_num = 0
                found = 0
                while not self._stop_flag.is_set():
                    raw = mft.read(RECORD_SIZE)
                    if not raw or len(raw) < RECORD_SIZE:
                        break
                    record_num += 1
                    if raw[:4] != HEADER_SIG:
                        continue
                    try:
                        flags = struct.unpack_from("<H", raw, 22)[0]
                        if flags & FLAG_IN_USE:
                            continue  # still active, skip
                        # Parse $FILE_NAME attribute to get name + size
                        name, size = self._parse_mft_record(raw)
                        if not name or name in (".", ".."):
                            continue
                        ext = Path(name).suffix.lstrip(".").lower() or "dat"
                        found += 1
                        if record_num % 500 == 0:
                            progress_cb(0, 0, f"$MFT: {record_num:,} records, {found} deleted found")
                        rf = RecoveredFile(
                            name=name,
                            ext=ext,
                            size=size,
                            path=f"{drive}\\[MFT record #{record_num}]",
                            status=FileStatus.DELETED,
                            description=self._ext_desc(ext) + " (NTFS deleted)"
                        )
                        result_cb(rf)
                    except Exception:
                        continue
        except (PermissionError, OSError, FileNotFoundError):
            # Normal — app not running as admin, or non-NTFS drive
            pass

    def _parse_mft_record(self, raw: bytes):
        """
        Extract filename and size from an MFT record.
        Walks the attribute list to find $FILE_NAME (type 0x30).
        Returns (name_str, size_int).
        """
        try:
            attr_offset = struct.unpack_from("<H", raw, 20)[0]
            pos = attr_offset
            name = ""
            size = 0
            while pos + 8 <= len(raw):
                attr_type   = struct.unpack_from("<I", raw, pos)[0]
                attr_length = struct.unpack_from("<I", raw, pos + 4)[0]
                if attr_type == 0xFFFFFFFF or attr_length == 0:
                    break
                # $DATA attribute (0x80) — get allocated size
                if attr_type == 0x80 and not size:
                    non_res = raw[pos + 8]
                    if non_res:  # non-resident
                        try:
                            size = struct.unpack_from("<q", raw, pos + 48)[0]
                        except Exception:
                            pass
                    else:
                        try:
                            content_len = struct.unpack_from("<I", raw, pos + 16)[0]
                            size = content_len
                        except Exception:
                            pass
                # $FILE_NAME attribute (0x30) — get name
                if attr_type == 0x30 and not name:
                    non_res = raw[pos + 8]
                    if not non_res:
                        content_off = struct.unpack_from("<H", raw, pos + 20)[0]
                        content_start = pos + content_off
                        # $FILE_NAME content: 66 bytes fixed header then name
                        fn_start = content_start + 66
                        fn_len   = raw[content_start + 64] if content_start + 65 <= len(raw) else 0
                        if fn_len > 0 and fn_start + fn_len * 2 <= len(raw):
                            name_bytes = raw[fn_start: fn_start + fn_len * 2]
                            name = name_bytes.decode("utf-16-le", errors="replace")
                pos += attr_length
            return name, max(size, 0)
        except Exception:
            return "", 0

    # ── Linux: /proc deleted + Trash ──────────────────────────────────────────
    def _scan_proc_deleted(self, root: str, result_cb: Callable):
        """Reads /proc/*/fd symlinks to find '(deleted)' files still open."""
        try:
            proc = Path("/proc")
            for pid_dir in proc.iterdir():
                if not pid_dir.name.isdigit(): continue
                fd_dir = pid_dir / "fd"
                if not fd_dir.exists(): continue
                try:
                    for fd in fd_dir.iterdir():
                        try:
                            link = os.readlink(str(fd))
                            if "(deleted)" in link and root in link:
                                real = link.replace(" (deleted)", "")
                                ext  = Path(real).suffix.lstrip(".").lower() or "dat"
                                rf = RecoveredFile(
                                    name=Path(real).name + " [deleted]",
                                    ext=ext, size=0,
                                    path=str(fd),
                                    status=FileStatus.DELETED,
                                    description=self._ext_desc(ext) + " (deleted, still open)"
                                )
                                result_cb(rf)
                        except (OSError, PermissionError): pass
                except (OSError, PermissionError): pass
        except Exception: pass

    def _scan_linux_trash(self, result_cb: Callable, progress_cb: Callable):
        """Scan XDG Trash directories on Linux (~/.local/share/Trash and per-volume)."""
        trash_dirs = []
        # User trash
        home_trash = Path.home() / ".local" / "share" / "Trash" / "files"
        if home_trash.exists():
            trash_dirs.append(home_trash)
        # Per-volume .Trash-<uid>
        try:
            uid = os.getuid()
            for mount in Path("/media").iterdir():
                t = mount / f".Trash-{uid}" / "files"
                if t.exists():
                    trash_dirs.append(t)
        except Exception:
            pass

        for trash_dir in trash_dirs:
            try:
                for entry in os.scandir(trash_dir):
                    if self._stop_flag.is_set(): return
                    try:
                        ext  = Path(entry.name).suffix.lstrip(".").lower() or "dat"
                        size = entry.stat().st_size if not entry.is_dir() else 0
                        progress_cb(0, 0, f"Trash: {entry.name}")
                        rf = RecoveredFile(
                            name=entry.name,
                            ext=ext, size=size,
                            path=entry.path,
                            status=FileStatus.DELETED,
                            description=self._ext_desc(ext) + " (Trash)"
                        )
                        result_cb(rf)
                    except (OSError, PermissionError):
                        pass
            except (OSError, PermissionError):
                pass

    # ── macOS: Trash ──────────────────────────────────────────────────────────
    def _scan_macos_trash(self, result_cb: Callable, progress_cb: Callable):
        """Scan ~/.Trash and /Volumes/*/.Trashes on macOS."""
        trash_dirs = []
        home_trash = Path.home() / ".Trash"
        if home_trash.exists():
            trash_dirs.append(home_trash)
        volumes = Path("/Volumes")
        if volumes.exists():
            try:
                uid = os.getuid()
                for vol in volumes.iterdir():
                    t = vol / ".Trashes" / str(uid)
                    if t.exists():
                        trash_dirs.append(t)
            except Exception:
                pass

        for trash_dir in trash_dirs:
            try:
                for entry in os.scandir(trash_dir):
                    if self._stop_flag.is_set(): return
                    try:
                        ext  = Path(entry.name).suffix.lstrip(".").lower() or "dat"
                        size = entry.stat().st_size if not entry.is_dir() else 0
                        progress_cb(0, 0, f"Trash: {entry.name}")
                        rf = RecoveredFile(
                            name=entry.name,
                            ext=ext, size=size,
                            path=entry.path,
                            status=FileStatus.DELETED,
                            description=self._ext_desc(ext) + " (Trash)"
                        )
                        result_cb(rf)
                    except (OSError, PermissionError):
                        pass
            except (OSError, PermissionError):
                pass

    # ── Deep Scan ─────────────────────────────────────────────────────────────
    def deep_scan(self,
                  source: str,
                  progress_cb: Callable[[int, int, str], None],
                  result_cb:   Callable[["RecoveredFile"], None],
                  block_size:  int = 512 * 1024):
        self.reset()
        if os.path.isdir(source):
            self._deep_scan_directory(source, progress_cb, result_cb, block_size)
        else:
            self._deep_scan_file_or_device(source, progress_cb, result_cb, block_size)

    def _deep_scan_directory(self, directory: str, progress_cb, result_cb, block_size):
        all_files = []
        for dirpath, _, files in os.walk(directory, followlinks=False):
            for fn in files:
                all_files.append(os.path.join(dirpath, fn))
        total = len(all_files)
        found_count = [0]
        for i, fpath in enumerate(all_files):
            self._pause_flag.wait()
            if self._stop_flag.is_set(): return
            progress_cb(i + 1, total, f"Carving: {fpath}")
            try:
                with open(fpath, "rb") as f:
                    data = f.read()
                for rf in self._carve_buffer(data, fpath, found_count):
                    result_cb(rf)
            except (PermissionError, OSError, IsADirectoryError):
                pass
        progress_cb(total, total, "Deep scan complete")

    def _deep_scan_file_or_device(self, source: str, progress_cb, result_cb, block_size):
        try:
            total_size = self._get_size(source)
        except Exception as e:
            progress_cb(0, 1, f"Cannot open: {e}")
            return
        found_count = [0]
        overlap     = 64
        prev_tail   = b""
        bytes_read  = 0
        try:
            flags = os.O_RDONLY
            if platform.system() == "Linux":
                flags |= os.O_DIRECT if hasattr(os, "O_DIRECT") else 0
            fd_raw = os.open(source, flags)
        except PermissionError:
            progress_cb(0, 1, "Permission denied - try running as root/sudo")
            return
        except OSError as e:
            progress_cb(0, 1, f"Cannot open device: {e}")
            return
        try:
            with os.fdopen(fd_raw, "rb", buffering=0) as f:
                while not self._stop_flag.is_set():
                    self._pause_flag.wait()
                    chunk = f.read(block_size)
                    if not chunk: break
                    buf    = prev_tail + chunk
                    carved = self._carve_buffer(buf, source, found_count,
                                                base_offset=max(0, bytes_read - overlap))
                    for rf in carved:
                        result_cb(rf)
                    prev_tail   = chunk[-overlap:]
                    bytes_read += len(chunk)
                    pct = min(bytes_read, total_size) if total_size > 0 else bytes_read
                    progress_cb(pct, max(total_size, 1),
                                f"Scanning offset {bytes_read:,} | Found: {found_count[0]}")
        except Exception as e:
            progress_cb(bytes_read, max(total_size, 1), f"Scan error: {e}")
        finally:
            progress_cb(total_size, max(total_size, 1), "Deep scan complete")

    def _carve_buffer(self, buf: bytes, source_path: str,
                      found_count: list, base_offset: int = 0) -> List[RecoveredFile]:
        results = []
        buf_len = len(buf)
        for ext, header, footer, desc in FILE_SIGNATURES:
            if header is None:
                continue
            pos = 0
            while True:
                idx = buf.find(header, pos)
                if idx == -1: break
                max_size = MAX_CARVED_SIZE.get(ext, 10 * 1024 * 1024)
                if footer:
                    end_idx = buf.find(footer, idx + len(header))
                    if end_idx == -1:
                        end_idx = min(idx + max_size, buf_len)
                    else:
                        end_idx += len(footer)
                else:
                    end_idx = min(idx + max_size, buf_len)
                carved_data = buf[idx:end_idx]
                size = len(carved_data)
                if size < 8:
                    pos = idx + 1; continue
                actual_ext = ext
                if ext in ("zip", "docx", "xlsx") and header == b"PK\x03\x04":
                    actual_ext = self._identify_zip_variant(carved_data)
                found_count[0] += 1
                fname = f"recovered_{found_count[0]:05d}.{actual_ext}"
                rf = RecoveredFile(
                    name=fname, ext=actual_ext, size=size,
                    path=source_path, status=FileStatus.CARVED,
                    description=f"{desc} (carved)",
                    offset=base_offset + idx, data_offset=idx,
                    preview_data=carved_data[:4096] if size > 0 else b""
                )
                if size <= 2 * 1024 * 1024:
                    rf.preview_data = carved_data
                results.append(rf)
                pos = idx + max(1, size)
        return results

    def _identify_zip_variant(self, data: bytes) -> str:
        markers = {b"word/": "docx", b"xl/": "xlsx", b"ppt/": "pptx"}
        for marker, ext in markers.items():
            if marker in data[:2048]:
                return ext
        return "zip"

    def _get_size(self, path: str) -> int:
        try:
            s = os.stat(path)
            if stat.S_ISBLK(s.st_mode):
                import fcntl, array
                buf = array.array("B", [0] * 8)
                BLKGETSIZE64 = 0x80081272
                with open(path, "rb") as f:
                    fcntl.ioctl(f.fileno(), BLKGETSIZE64, buf)
                return struct.unpack("Q", bytes(buf))[0]
            return s.st_size
        except Exception:
            return 0

    def _ext_desc(self, ext: str) -> str:
        mapping = {
            "jpg":"JPEG Image","jpeg":"JPEG Image","png":"PNG Image",
            "gif":"GIF Image","bmp":"BMP Image","svg":"SVG Image",
            "mp4":"MP4 Video","avi":"AVI Video","mkv":"MKV Video","mov":"MOV Video",
            "mp3":"MP3 Audio","wav":"WAV Audio","flac":"FLAC Audio","aac":"AAC Audio",
            "pdf":"PDF Document","docx":"Word Document","xlsx":"Excel Sheet",
            "pptx":"PowerPoint","txt":"Text File","csv":"CSV Data",
            "zip":"ZIP Archive","7z":"7-Zip Archive","rar":"RAR Archive",
            "tar":"TAR Archive","exe":"Executable","dll":"Library",
            "py":"Python Script","js":"JavaScript","html":"HTML File",
            "css":"CSS File",
        }
        return mapping.get(ext.lower(), f"{ext.upper()} File")


# ── Recovery ──────────────────────────────────────────────────────────────────

def recover_files(files: List[RecoveredFile],
                  dest_dir: str,
                  progress_cb: Callable[[int, int, str], None]) -> List[str]:
    os.makedirs(dest_dir, exist_ok=True)
    recovered = []
    total = len(files)
    for i, rf in enumerate(files):
        progress_cb(i + 1, total, rf.name)
        dest_path = _unique_path(os.path.join(dest_dir, rf.name))
        try:
            if rf.status == FileStatus.ACTIVE:
                import shutil
                shutil.copy2(rf.path, dest_path)
                recovered.append(dest_path)
            elif rf.status in (FileStatus.CARVED, FileStatus.DELETED):
                if rf.preview_data and len(rf.preview_data) == rf.size:
                    with open(dest_path, "wb") as out:
                        out.write(rf.preview_data)
                    recovered.append(dest_path)
                else:
                    # For Recycle Bin / Trash entries the path IS the data file ($R file)
                    data_path = rf.path
                    # If path points to $I metadata file, derive the $R data file
                    import re as _re
                    if os.path.basename(data_path).startswith("$I"):
                        _r_path = os.path.join(
                            os.path.dirname(data_path),
                            "$R" + os.path.basename(data_path)[2:])
                        if os.path.exists(_r_path):
                            data_path = _r_path
                    if os.path.exists(data_path):
                        import shutil
                        shutil.copy2(data_path, dest_path)
                        recovered.append(dest_path)
                    elif rf.offset and not rf.path.endswith("]"):
                        # Raw carve from disk at offset
                        try:
                            with open(rf.path, "rb") as src:
                                src.seek(rf.offset)
                                data = src.read(rf.size)
                            with open(dest_path, "wb") as out:
                                out.write(data)
                            recovered.append(dest_path)
                        except Exception as e:
                            print(f"[recover] Carve failed {rf.name}: {e}")
                    else:
                        print(f"[recover] No data source for {rf.name}")
        except Exception as e:
            print(f"[recover] Failed {rf.name}: {e}")
    progress_cb(total, total, "Done")
    return recovered


def _unique_path(path: str) -> str:
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    n = 1
    while os.path.exists(f"{base}_{n}{ext}"):
        n += 1
    return f"{base}_{n}{ext}"