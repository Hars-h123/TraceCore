"""
drives.py - TraceCore drive/volume enumeration
Lists all mounted drives, partitions, and lets user pick a folder.
Cross-platform: Linux, macOS, Windows.
"""

import os
import platform
import subprocess
from dataclasses import dataclass
from typing import List

@dataclass
class DriveInfo:
    path:        str
    label:       str
    fs_type:     str
    total_bytes: int
    free_bytes:  int
    is_device:   bool   # True = raw block device (needs root), False = mounted path

    def size_str(self) -> str:
        return _human(self.total_bytes)

    def free_str(self) -> str:
        return _human(self.free_bytes)

    def icon_char(self) -> str:
        lp = self.path.lower()
        if any(x in lp for x in ["usb", "removable", "sdb", "sdc", "sdd"]):
            return "🔌"
        if any(x in lp for x in ["sda", "nvme", "hd"]):
            return "💾"
        if any(x in lp for x in ["cd", "dvd", "rom"]):
            return "💿"
        return "🖥"


def _human(n: int) -> str:
    for unit in ["B","KB","MB","GB","TB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def list_drives() -> List[DriveInfo]:
    sys = platform.system()
    if sys == "Linux":
        return _linux_drives()
    elif sys == "Darwin":
        return _macos_drives()
    elif sys == "Windows":
        return _windows_drives()
    return []


def _linux_drives() -> List[DriveInfo]:
    drives = []

    # Read /proc/mounts for mounted filesystems
    try:
        with open("/proc/mounts") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 3:
                    continue
                device, mountpoint, fstype = parts[0], parts[1], parts[2]

                skip = ["tmpfs","devtmpfs","sysfs","proc","cgroup",
                        "devpts","securityfs","pstore","bpf","tracefs",
                        "debugfs","hugetlbfs","mqueue","fusectl","none",
                        "overlay","udev","run","snap"]
                if fstype in skip or any(s in device for s in ["tmpfs","sysfs","proc","dev"]):
                    continue

                try:
                    sv = os.statvfs(mountpoint)
                    total = sv.f_frsize * sv.f_blocks
                    free  = sv.f_frsize * sv.f_bavail
                    label = _label_from_mount(device, mountpoint)
                    drives.append(DriveInfo(
                        path=mountpoint, label=label, fs_type=fstype,
                        total_bytes=total, free_bytes=free,
                        is_device=False
                    ))
                except (PermissionError, OSError):
                    pass
    except FileNotFoundError:
        pass

    # Also add raw block devices if we can find them
    try:
        result = subprocess.run(
            ["lsblk", "-rno", "NAME,TYPE,SIZE,MOUNTPOINT"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) < 2: continue
            name, dtype = parts[0], parts[1]
            if dtype not in ("disk", "part"): continue
            dev_path = f"/dev/{name}"
            if not os.path.exists(dev_path): continue
            # Only add if not already in list as mounted
            mounted_paths = [d.path for d in drives]
            mount = parts[3] if len(parts) > 3 else ""
            if mount and mount in mounted_paths: continue
            try:
                size_str = parts[2] if len(parts) > 2 else "?"
                # Convert lsblk size to bytes roughly
                total = _parse_lsblk_size(size_str)
                drives.append(DriveInfo(
                    path=dev_path,
                    label=f"{name.upper()} (raw device)",
                    fs_type="raw",
                    total_bytes=total, free_bytes=0,
                    is_device=True
                ))
            except Exception:
                pass
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return drives


def _label_from_mount(device: str, mountpoint: str) -> str:
    if mountpoint == "/":
        return "Root (/)"
    if "boot" in mountpoint:
        return f"Boot ({mountpoint})"
    if "home" in mountpoint:
        return f"Home ({mountpoint})"
    if "media" in mountpoint or "mnt" in mountpoint:
        parts = mountpoint.rstrip("/").split("/")
        return f"Removable: {parts[-1]}"
    return f"{device.split('/')[-1].upper()} ({mountpoint})"


def _parse_lsblk_size(s: str) -> int:
    """Convert '500G' -> bytes"""
    s = s.strip().upper()
    units = {"K":1024,"M":1024**2,"G":1024**3,"T":1024**4,"P":1024**5}
    for suffix, mult in units.items():
        if s.endswith(suffix):
            try:
                return int(float(s[:-1]) * mult)
            except ValueError:
                return 0
    try:
        return int(s)
    except ValueError:
        return 0


def _macos_drives() -> List[DriveInfo]:
    drives = []
    try:
        result = subprocess.run(
            ["df", "-k"], capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) < 6: continue
            device, total_k, used_k, free_k, _, mount = parts[:6]
            skip = ["devfs","map","tmpfs"]
            if any(s in device for s in skip): continue
            try:
                total = int(total_k) * 1024
                free  = int(free_k)  * 1024
                drives.append(DriveInfo(
                    path=mount, label=_macos_label(mount),
                    fs_type="apfs", total_bytes=total, free_bytes=free,
                    is_device=False
                ))
            except ValueError:
                pass
    except Exception:
        pass
    return drives


def _macos_label(mount: str) -> str:
    if mount == "/": return "Macintosh HD (/)"
    parts = mount.rstrip("/").split("/")
    return parts[-1] or mount


def _windows_drives() -> List[DriveInfo]:
    drives = []
    import string
    for letter in string.ascii_uppercase:
        path = f"{letter}:\\"
        if os.path.exists(path):
            try:
                sv = os.statvfs(path) if platform.system() != "Windows" else None
                if platform.system() == "Windows":
                    import ctypes
                    free_b  = ctypes.c_ulonglong(0)
                    total_b = ctypes.c_ulonglong(0)
                    ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                        path, None, ctypes.byref(total_b), ctypes.byref(free_b))
                    total = total_b.value
                    free  = free_b.value
                else:
                    total = sv.f_frsize * sv.f_blocks
                    free  = sv.f_frsize * sv.f_bavail
                drives.append(DriveInfo(
                    path=path, label=f"Drive {letter}:",
                    fs_type="ntfs", total_bytes=total, free_bytes=free,
                    is_device=False
                ))
            except Exception:
                pass
    return drives
