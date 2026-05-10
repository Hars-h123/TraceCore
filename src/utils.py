"""
utils.py - TraceCore shared utilities
Icons, colors, size formatting, report export, scan statistics.
"""

import os
import csv
import json
import datetime
from typing import List, Dict, Any
from scanner import RecoveredFile, FileStatus

# ── File type metadata ────────────────────────────────────────────────────────

EXT_META = {
    # Images
    "jpg":  ("🖼",  "#E74C3C", "Image"),
    "jpeg": ("🖼",  "#E74C3C", "Image"),
    "png":  ("🖼",  "#E74C3C", "Image"),
    "gif":  ("🖼",  "#E74C3C", "Image"),
    "bmp":  ("🖼",  "#E74C3C", "Image"),
    "webp": ("🖼",  "#E74C3C", "Image"),
    "svg":  ("🖼",  "#E74C3C", "Image"),
    "tiff": ("🖼",  "#E74C3C", "Image"),
    "heic": ("🖼",  "#E74C3C", "Image"),
    # Video
    "mp4":  ("🎬",  "#9B59B6", "Video"),
    "avi":  ("🎬",  "#9B59B6", "Video"),
    "mkv":  ("🎬",  "#9B59B6", "Video"),
    "mov":  ("🎬",  "#9B59B6", "Video"),
    "wmv":  ("🎬",  "#9B59B6", "Video"),
    "flv":  ("🎬",  "#9B59B6", "Video"),
    # Audio
    "mp3":  ("🎵",  "#1ABC9C", "Audio"),
    "wav":  ("🎵",  "#1ABC9C", "Audio"),
    "flac": ("🎵",  "#1ABC9C", "Audio"),
    "aac":  ("🎵",  "#1ABC9C", "Audio"),
    "ogg":  ("🎵",  "#1ABC9C", "Audio"),
    # Documents
    "pdf":  ("📄",  "#E67E22", "Document"),
    "docx": ("📝",  "#2980B9", "Document"),
    "doc":  ("📝",  "#2980B9", "Document"),
    "xlsx": ("📊",  "#27AE60", "Document"),
    "xls":  ("📊",  "#27AE60", "Document"),
    "pptx": ("📋",  "#E74C3C", "Document"),
    "txt":  ("📃",  "#7F8C8D", "Document"),
    "csv":  ("📊",  "#27AE60", "Document"),
    "rtf":  ("📝",  "#2980B9", "Document"),
    # Archives
    "zip":  ("🗜",  "#F39C12", "Archive"),
    "7z":   ("🗜",  "#F39C12", "Archive"),
    "rar":  ("🗜",  "#F39C12", "Archive"),
    "tar":  ("🗜",  "#F39C12", "Archive"),
    "gz":   ("🗜",  "#F39C12", "Archive"),
    # Code
    "py":   ("💻",  "#3498DB", "Code"),
    "js":   ("💻",  "#F1C40F", "Code"),
    "html": ("💻",  "#E67E22", "Code"),
    "css":  ("💻",  "#1ABC9C", "Code"),
    "c":    ("💻",  "#3498DB", "Code"),
    "cpp":  ("💻",  "#3498DB", "Code"),
    "rs":   ("💻",  "#E74C3C", "Code"),
    "go":   ("💻",  "#1ABC9C", "Code"),
    # Executables
    "exe":  ("⚙",   "#95A5A6", "Executable"),
    "dll":  ("⚙",   "#95A5A6", "Executable"),
    "so":   ("⚙",   "#95A5A6", "Executable"),
    "sh":   ("⚙",   "#2ECC71", "Executable"),
}

DEFAULT_META = ("📁", "#95A5A6", "Other")


def get_ext_meta(ext: str):
    """Returns (icon_char, color_hex, category) for a file extension."""
    return EXT_META.get(ext.lower(), DEFAULT_META)


def fmt_size(size: int) -> str:
    if size == 0:
        return "—"
    n = float(size)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def fmt_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}m {s}s"


# ── Scan statistics ───────────────────────────────────────────────────────────

class ScanStats:
    def __init__(self):
        self.reset()

    def reset(self):
        self.total_files   = 0
        self.total_bytes   = 0
        self.by_category: Dict[str, int] = {}
        self.by_status:   Dict[str, int] = {
            FileStatus.ACTIVE.value:  0,
            FileStatus.DELETED.value: 0,
            FileStatus.CARVED.value:  0,
        }
        self.largest_file: str  = ""
        self.largest_size: int  = 0

    def add(self, rf: RecoveredFile):
        self.total_files += 1
        self.total_bytes += rf.size
        _, _, cat = get_ext_meta(rf.ext)
        self.by_category[cat] = self.by_category.get(cat, 0) + 1
        self.by_status[rf.status.value] = self.by_status.get(rf.status.value, 0) + 1
        if rf.size > self.largest_size:
            self.largest_size = rf.size
            self.largest_file = rf.name

    def top_categories(self, n: int = 5):
        return sorted(self.by_category.items(), key=lambda x: x[1], reverse=True)[:n]


# ── Report export ─────────────────────────────────────────────────────────────

def export_csv(files: List[RecoveredFile], path: str):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Extension", "Size (bytes)", "Status",
                         "Description", "Path", "Offset"])
        for rf in files:
            writer.writerow([
                rf.name, rf.ext, rf.size, rf.status.value,
                rf.description, rf.path, rf.offset
            ])


def export_json(files: List[RecoveredFile], path: str, stats: ScanStats,
                source: str, mode: str, elapsed: float):
    data = {
        "report": {
            "generated":   datetime.datetime.now().isoformat(),
            "source":      source,
            "scan_mode":   mode,
            "elapsed_sec": round(elapsed, 2),
        },
        "summary": {
            "total_files":   stats.total_files,
            "total_bytes":   stats.total_bytes,
            "by_category":   stats.by_category,
            "by_status":     stats.by_status,
            "largest_file":  stats.largest_file,
            "largest_size":  stats.largest_size,
        },
        "files": [
            {
                "name":        rf.name,
                "ext":         rf.ext,
                "size":        rf.size,
                "status":      rf.status.value,
                "description": rf.description,
                "path":        rf.path,
                "offset":      rf.offset,
            }
            for rf in files
        ]
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def export_html(files: List[RecoveredFile], path: str, stats: ScanStats,
                source: str, mode: str, elapsed: float):
    """Generate a self-contained HTML report."""
    rows = ""
    for rf in files:
        icon, color, _ = get_ext_meta(rf.ext)
        status_colors = {
            "Active":  ("#27AE60", "#EAF9F0"),
            "Removed": ("#E74C3C", "#FDECEA"),
            "Erased":  ("#9B59B6", "#F5EEF8"),
        }
        fg, bg = status_colors.get(rf.status.value, ("#000", "#fff"))
        rows += f"""
        <tr>
          <td>{icon} {rf.name}</td>
          <td style="color:{color};font-weight:600">{rf.ext.upper()}</td>
          <td>{fmt_size(rf.size)}</td>
          <td><span style="color:{fg};background:{bg};padding:2px 8px;border-radius:4px;font-size:11px">{rf.status.value}</span></td>
          <td style="font-size:11px;color:#666">{rf.path[:60]}{'...' if len(rf.path)>60 else ''}</td>
        </tr>"""

    cat_bars = ""
    max_cat = max((v for _, v in stats.top_categories()), default=1)
    for cat, count in stats.top_categories(8):
        pct = int(count / max_cat * 100)
        icon, color, _ = get_ext_meta(cat.lower())
        cat_bars += f"""
        <div style="margin:6px 0">
          <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:2px">
            <span>{cat}</span><span style="color:#999">{count:,}</span>
          </div>
          <div style="background:#eee;border-radius:4px;height:6px">
            <div style="background:{color};width:{pct}%;height:6px;border-radius:4px"></div>
          </div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>TraceCore Recovery Report</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #EFEEEA; color: #000; }}
  .header {{ background: #273F4F; color: white; padding: 24px 32px; display:flex; align-items:center; gap:16px; }}
  .logo {{ font-size: 24px; font-weight: 800; color: #FE7743; }}
  .sub  {{ font-size: 13px; opacity: 0.7; }}
  .content {{ padding: 24px 32px; }}
  .cards {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 20px 0; }}
  .card {{ background: white; border-radius: 10px; padding: 16px 20px; border: 1px solid #ddd; }}
  .card .num {{ font-size: 24px; font-weight: 800; color: #FE7743; }}
  .card .lbl {{ font-size: 11px; color: #999; margin-top: 4px; }}
  .section {{ background: white; border-radius: 12px; border: 1px solid #ddd; padding: 20px; margin: 16px 0; }}
  .section h3 {{ font-size: 14px; color: #273F4F; margin-bottom: 12px; font-weight: 700; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  th {{ background: #273F4F; color: white; padding: 8px 12px; text-align: left; }}
  td {{ padding: 7px 12px; border-bottom: 1px solid #f0f0f0; }}
  tr:hover td {{ background: #FFF8F5; }}
  .meta {{ font-size: 12px; color: #666; margin-bottom: 16px; }}
</style>
</head>
<body>
<div class="header">
  <div>
    <div class="logo">TraceCore</div>
    <div class="sub">Data Recovery Report</div>
  </div>
</div>
<div class="content">
  <p class="meta">
    Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} &nbsp;|&nbsp;
    Source: <strong>{source}</strong> &nbsp;|&nbsp;
    Mode: <strong>{mode}</strong> &nbsp;|&nbsp;
    Duration: <strong>{fmt_time(elapsed)}</strong>
  </p>
  <div class="cards">
    <div class="card"><div class="num">{stats.total_files:,}</div><div class="lbl">Total Files</div></div>
    <div class="card"><div class="num">{fmt_size(stats.total_bytes)}</div><div class="lbl">Total Size</div></div>
    <div class="card"><div class="num">{stats.by_status.get('Active',0):,}</div><div class="lbl">Active Files</div></div>
    <div class="card"><div class="num">{stats.by_status.get('Erased',0) + stats.by_status.get('Removed',0):,}</div><div class="lbl">Recoverable</div></div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
    <div class="section"><h3>By Category</h3>{cat_bars}</div>
    <div class="section"><h3>By Status</h3>
      {''.join(f'<div style="margin:8px 0;display:flex;justify-content:space-between"><span>{k}</span><strong>{v:,}</strong></div>' for k,v in stats.by_status.items())}
    </div>
  </div>
  <div class="section">
    <h3>File List ({len(files):,} files)</h3>
    <table>
      <tr><th>Name</th><th>Type</th><th>Size</th><th>Status</th><th>Path</th></tr>
      {rows}
    </table>
  </div>
</div>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)