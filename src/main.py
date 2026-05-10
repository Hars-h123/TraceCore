"""
main.py — TraceCore v2  (enhanced)
Native Qt6 desktop data recovery application.
Theme: #FE7743 primary | #EFEEEA bg | #273F4F accent | #000 base
"""

import sys, os, time, platform, datetime, threading
from pathlib import Path
from typing import List, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QSplitter, QFrame, QScrollArea,
    QCheckBox, QMessageBox, QComboBox, QStackedWidget, QGroupBox,
    QTextEdit, QSizePolicy, QAbstractItemView, QStatusBar,
    QLineEdit, QGridLayout, QSpacerItem, QTabWidget, QDialog,
    QDialogButtonBox, QMenu, QToolButton
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QSize, QTimer, QRect, QPoint
)
from PyQt6.QtGui import (
    QColor, QPalette, QFont, QIcon, QPixmap, QPainter, QBrush,
    QPen, QLinearGradient, QImage, QAction, QKeySequence, QShortcut
)

sys.path.insert(0, os.path.dirname(__file__))
from scanner import ScanEngine, ScanMode, RecoveredFile, FileStatus, recover_files
from drives  import list_drives, DriveInfo
from utils   import (get_ext_meta, fmt_size, fmt_time, ScanStats,
                     export_csv, export_json, export_html)

# ── Theme ─────────────────────────────────────────────────────────────────────
PRIMARY  = "#FE7743"
BG       = "#EFEEEA"
ACCENT   = "#273F4F"
BASE     = "#000000"
WHITE    = "#FFFFFF"
LIGHT_BG = "#F7F6F2"
CARD_BG  = "#FFFFFF"
BORDER   = "#D8D6D0"
SUCCESS  = "#27AE60"
DANGER   = "#E74C3C"
MUTED    = "#8A9BA8"
WARN     = "#F39C12"

QSS = f"""
QMainWindow, QWidget {{
    background-color: {BG};
    color: {BASE};
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif;
    font-size: 13px;
}}
QLabel  {{ color: {BASE}; background: transparent; }}
QDialog {{ background: {BG}; }}
QPushButton {{
    background-color: {PRIMARY}; color: white; border: none;
    border-radius: 8px; padding: 9px 20px;
    font-size: 13px; font-weight: 600; min-height: 34px;
}}
QPushButton:hover   {{ background-color: #FF8C5A; }}
QPushButton:pressed {{ background-color: #E0603A; }}
QPushButton:disabled {{ background-color: {BORDER}; color: {MUTED}; }}
QPushButton#ghost {{
    background: transparent; color: {ACCENT};
    border: 1.5px solid {ACCENT};
}}
QPushButton#ghost:hover {{ background: {ACCENT}; color: white; }}
QPushButton#danger {{ background: {DANGER}; }}
QPushButton#danger:hover {{ background: #C0392B; }}
QProgressBar {{
    border: none; border-radius: 6px; background-color: {BORDER};
    text-align: center; color: white; font-size: 11px;
}}
QProgressBar::chunk {{
    background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {PRIMARY}, stop:1 #FF9A6C);
    border-radius: 6px;
}}
QTableWidget {{
    background-color: {CARD_BG}; border: 1px solid {BORDER};
    border-radius: 8px; gridline-color: transparent;
    selection-background-color: #FEE8DF; selection-color: {BASE}; outline: none;
}}
QTableWidget::item {{ padding: 5px 10px; border-bottom: 1px solid {LIGHT_BG}; }}
QTableWidget::item:selected {{ background-color: #FEE8DF; color: {BASE}; }}
QTableWidget::item:alternate {{ background-color: {LIGHT_BG}; }}
QHeaderView::section {{
    background-color: {ACCENT}; color: white; padding: 8px 10px;
    border: none; font-weight: 700; font-size: 11px; letter-spacing: 0.5px;
}}
QHeaderView::section:hover {{ background-color: #3A5468; }}
QComboBox, QLineEdit {{
    background-color: {CARD_BG}; border: 1.5px solid {BORDER};
    border-radius: 8px; padding: 7px 12px;
    font-size: 13px; color: {BASE}; min-height: 34px;
}}
QComboBox:focus, QLineEdit:focus {{ border-color: {PRIMARY}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background: {CARD_BG}; border: 1px solid {BORDER};
    selection-background-color: #FEE8DF;
}}
QScrollBar:vertical {{
    background: {LIGHT_BG}; width: 7px; border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER}; border-radius: 4px; min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{ background: {MUTED}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ height: 7px; background: {LIGHT_BG}; border-radius: 4px; }}
QScrollBar::handle:horizontal {{ background: {BORDER}; border-radius: 4px; min-width: 20px; }}
QTextEdit {{
    background: {CARD_BG}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 8px; color: {BASE};
    font-family: 'Courier New', monospace; font-size: 12px;
}}
QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: 8px; background: {CARD_BG}; }}
QTabBar::tab {{
    background: {LIGHT_BG}; color: {MUTED}; padding: 8px 20px;
    border-top-left-radius: 8px; border-top-right-radius: 8px;
    font-weight: 600; font-size: 12px;
}}
QTabBar::tab:selected {{ background: {CARD_BG}; color: {ACCENT}; border-bottom: 2px solid {PRIMARY}; }}
QTabBar::tab:hover {{ color: {ACCENT}; }}
QStatusBar {{ background: {ACCENT}; color: rgba(255,255,255,0.85); font-size: 12px; padding: 0 8px; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border: 2px solid {ACCENT}; border-radius: 4px; background: white;
}}
QCheckBox::indicator:hover {{ border-color: {PRIMARY}; background: #FFF3EE; }}
QCheckBox::indicator:checked {{
    background-color: {PRIMARY}; border-color: {PRIMARY};
}}
QToolButton {{
    background: transparent; border: none; padding: 6px;
    border-radius: 6px; color: white;
}}
QToolButton:hover {{ background: rgba(255,255,255,0.12); }}
QMenu {{
    background: {CARD_BG}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 4px;
}}
QMenu::item {{ padding: 7px 20px; border-radius: 4px; }}
QMenu::item:selected {{ background: #FEE8DF; color: {BASE}; }}
"""

# ── Workers ───────────────────────────────────────────────────────────────────

class ScanWorker(QThread):
    progress   = pyqtSignal(int, int, str)
    file_found = pyqtSignal(object)
    finished   = pyqtSignal(int)
    def __init__(self, engine, source, mode):
        super().__init__()
        self.engine = engine; self.source = source; self.mode = mode
        self._count = 0
    def run(self):
        def on_file(rf): self._count += 1; self.file_found.emit(rf)
        def on_prog(c,t,m): self.progress.emit(c,t,m)
        if self.mode == ScanMode.QUICK:
            self.engine.quick_scan(self.source, on_prog, on_file)
        else:
            self.engine.deep_scan(self.source, on_prog, on_file)
        self.finished.emit(self._count)

class RecoverWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(list)
    def __init__(self, files, dest):
        super().__init__()
        self.files = files; self.dest = dest
    def run(self):
        self.finished.emit(
            recover_files(self.files, self.dest,
                          lambda c,t,m: self.progress.emit(c,t,m)))

# ── Widgets ───────────────────────────────────────────────────────────────────

class SectionLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(
            f"color:{MUTED};font-size:10px;font-weight:700;letter-spacing:1.2px;")

class Card(QFrame):
    def __init__(self, parent=None, radius=12, bg=CARD_BG):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame{{background:{bg};border:1px solid {BORDER};border-radius:{radius}px;}}")

class StatCard(QFrame):
    def __init__(self, label, value="0", color=PRIMARY, icon="", parent=None):
        super().__init__(parent)
        self.setFixedHeight(88)
        self.setStyleSheet(
            f"QFrame{{background:{CARD_BG};border:1px solid {BORDER};border-radius:12px;}}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(2)
        top = QHBoxLayout()
        self.val = QLabel(value)
        self.val.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self.val.setStyleSheet(f"color:{color};")
        top.addWidget(self.val)
        top.addStretch()
        if icon:
            ic = QLabel(icon)
            ic.setFont(QFont("Segoe UI Emoji", 18))
            top.addWidget(ic)
        lay.addLayout(top)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color:{MUTED};font-size:11px;")
        lay.addWidget(lbl)
    def set_value(self, v): self.val.setText(str(v))

class MiniBar(QFrame):
    def __init__(self, label, count, max_count, color, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self.setStyleSheet("background:transparent;border:none;")
        lay = QHBoxLayout(self); lay.setContentsMargins(0,2,0,2); lay.setSpacing(8)
        lbl = QLabel(label); lbl.setFixedWidth(76)
        lbl.setStyleSheet(f"color:{BASE};font-size:11px;"); lay.addWidget(lbl)
        bar_bg = QFrame()
        bar_bg.setStyleSheet(f"background:{LIGHT_BG};border-radius:3px;border:none;")
        bar_bg.setFixedHeight(8)
        blay = QHBoxLayout(bar_bg); blay.setContentsMargins(0,0,0,0); blay.setSpacing(0)
        pct = max(int(count / max(max_count,1) * 100), 2)
        fill = QFrame(); fill.setFixedHeight(8)
        fill.setStyleSheet(f"background:{color};border-radius:3px;border:none;")
        fill.setFixedWidth(int(pct * 1.6))
        blay.addWidget(fill); blay.addStretch()
        lay.addWidget(bar_bg, 1)
        cnt = QLabel(f"{count:,}"); cnt.setFixedWidth(52)
        cnt.setAlignment(Qt.AlignmentFlag.AlignRight)
        cnt.setStyleSheet(f"color:{MUTED};font-size:11px;"); lay.addWidget(cnt)

class DriveCard(QFrame):
    clicked = pyqtSignal(object)
    def __init__(self, drive, parent=None):
        super().__init__(parent)
        self.drive = drive
        self._sel  = False
        self.setFixedHeight(86)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._restyle()
        lay = QHBoxLayout(self); lay.setContentsMargins(16,10,16,10); lay.setSpacing(12)
        icon = QLabel(drive.icon_char())
        icon.setFont(QFont("Segoe UI Emoji", 22)); icon.setFixedWidth(36); lay.addWidget(icon)
        info = QVBoxLayout(); info.setSpacing(2)
        name = QLabel(drive.label)
        name.setFont(QFont("Segoe UI",11,QFont.Weight.Bold))
        name.setStyleSheet(f"color:{ACCENT};")
        detail = QLabel(f"{drive.path}  •  {drive.size_str()}  •  Free: {drive.free_str()}  •  {drive.fs_type.upper()}")
        detail.setStyleSheet(f"color:{MUTED};font-size:11px;")
        bar = QProgressBar()
        used = int((1 - drive.free_bytes / max(drive.total_bytes,1)) * 100)
        bar.setValue(used); bar.setFixedHeight(4); bar.setTextVisible(False)
        bar.setStyleSheet(
            f"QProgressBar{{background:{LIGHT_BG};border-radius:2px;border:none;}}"
            f"QProgressBar::chunk{{background:{PRIMARY};border-radius:2px;}}")
        info.addWidget(name); info.addWidget(detail); info.addWidget(bar)
        lay.addLayout(info)
    def _restyle(self):
        if self._sel:
            self.setStyleSheet(f"DriveCard{{background:#FFF8F5;border:2px solid {PRIMARY};border-radius:12px;}}")
        else:
            self.setStyleSheet(
                f"DriveCard{{background:{CARD_BG};border:1.5px solid {BORDER};border-radius:12px;}}"
                f"DriveCard:hover{{border:2px solid {PRIMARY};background:#FFF8F5;}}")
    def set_selected(self, v): self._sel = v; self._restyle()
    def mousePressEvent(self, e): self.clicked.emit(self.drive)

class ImagePreview(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(180)
        self.setStyleSheet(
            f"background:{LIGHT_BG};border:1px solid {BORDER};"
            f"border-radius:8px;color:{MUTED};font-size:12px;")
        self.setText("Select a file to preview")
    def show_image(self, data):
        px = QPixmap()
        if px.loadFromData(data):
            px = px.scaled(self.width()-16, self.height()-16,
                           Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
            self.setPixmap(px)
        else:
            self.setText("⚠  Cannot render image")
    def show_text(self, data):
        try: text = data[:2000].decode("utf-8", errors="replace")[:500]
        except: text = "Cannot decode"
        self.setText(f"<pre style='font-size:11px;white-space:pre-wrap'>{text}</pre>")
    def reset(self, msg="Select a file to preview"):
        self.setPixmap(QPixmap()); self.setText(msg)

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About TraceCore"); self.setFixedSize(420, 340)
        self.setStyleSheet(f"background:{BG};")
        lay = QVBoxLayout(self); lay.setContentsMargins(32,28,32,28); lay.setSpacing(12)
        logo = QLabel("🔍  TraceCore")
        logo.setFont(QFont("Segoe UI",22,QFont.Weight.Bold))
        logo.setStyleSheet(f"color:{ACCENT};"); lay.addWidget(logo)
        ver = QLabel("Version 2.0  •  Professional Data Recovery")
        ver.setStyleSheet(f"color:{MUTED};font-size:12px;"); lay.addWidget(ver)
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color:{BORDER};"); lay.addWidget(sep)
        for k, v in [
            ("Engine",  "Python 3 + PyQt6 native desktop"),
            ("Scan",    "Quick (filesystem) + Deep (file carving)"),
            ("Formats", "JPG PNG GIF BMP MP4 AVI MP3 WAV PDF DOCX XLSX ZIP 7Z RAR TXT"),
            ("Access",  "Read-only — never modifies scanned media"),
            ("System",  platform.system() + " " + platform.machine()),
            ("Python",  sys.version.split()[0]),
        ]:
            row = QHBoxLayout()
            kl = QLabel(k+":"); kl.setFixedWidth(80)
            kl.setStyleSheet(f"color:{MUTED};font-size:12px;font-weight:600;")
            vl = QLabel(v); vl.setWordWrap(True)
            vl.setStyleSheet(f"color:{BASE};font-size:12px;")
            row.addWidget(kl); row.addWidget(vl,1); lay.addLayout(row)
        lay.addStretch()
        btn = QPushButton("Close"); btn.setFixedWidth(100)
        btn.clicked.connect(self.accept)
        h = QHBoxLayout(); h.addStretch(); h.addWidget(btn); lay.addLayout(h)

# ── Main Window ────────────────────────────────────────────────────────────────

class TraceCoreApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TraceCore – Data Recovery")
        self.setMinimumSize(1120, 700)
        self.resize(1300, 820)
        self._engine     = ScanEngine()
        self._results:   List[RecoveredFile] = []
        self._stats      = ScanStats()
        self._scan_worker  = None
        self._rec_worker   = None
        self._source:    Optional[str] = None
        self._scan_mode  = ScanMode.QUICK
        self._scanning   = False
        self._scan_start = 0.0
        self._elapsed    = 0.0
        self._drive_cards: List[DriveCard] = []
        self._build_ui()
        self.setStyleSheet(QSS)
        self._refresh_drives()
        self._setup_shortcuts()

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        c = QWidget(); self.setCentralWidget(c)
        root = QVBoxLayout(c); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        root.addWidget(self._mk_header())
        body = QHBoxLayout(); body.setContentsMargins(0,0,0,0); body.setSpacing(0)
        body.addWidget(self._mk_sidebar())
        self.stack = QStackedWidget()
        self.stack.addWidget(self._mk_drive_page())
        self.stack.addWidget(self._mk_scan_page())
        self.stack.addWidget(self._mk_results_page())
        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready  •  Select a drive or folder to begin")

    def _mk_header(self):
        h = QFrame(); h.setFixedHeight(58)
        h.setStyleSheet(f"background:{ACCENT};border:none;")
        lay = QHBoxLayout(h); lay.setContentsMargins(20,0,12,0)
        # ── Logo image + text ─────────────────────────────────────────────────
        logo_lbl = QLabel()
        logo_lbl.setStyleSheet("background:transparent;border:none;")
        _logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                  "resources", "logo.png")
        if os.path.exists(_logo_path):
            _px = QPixmap(_logo_path).scaled(
                36, 36,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(_px)
        else:
            logo_lbl.setText("🔍")
            logo_lbl.setFont(QFont("Segoe UI Emoji", 18))
        logo_lbl.setFixedSize(40, 40)
        lay.addWidget(logo_lbl)
        brand = QLabel("TraceCore")
        brand.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        brand.setStyleSheet("color:#FE7743;background:transparent;margin-left:4px;")
        lay.addWidget(brand)
        sub = QLabel("Data Recovery")
        sub.setStyleSheet(f"color:rgba(255,255,255,0.4);font-size:12px;background:transparent;margin-left:4px;")
        lay.addWidget(sub); lay.addStretch()
        self.nav_btns = []
        for i,(label,icon) in enumerate([("Drives","🖥"),("Scan","⚡"),("Results","📋")]):
            btn = QPushButton(f"{icon}  {label}")
            btn.clicked.connect(lambda _,idx=i: self._nav(idx))
            self.nav_btns.append(btn); lay.addWidget(btn)
        self._nav_style_all(0)
        lay.addSpacing(8)
        self.btn_export = QToolButton()
        self.btn_export.setText("Export ▾")
        self.btn_export.setStyleSheet(
            f"QToolButton{{background:rgba(255,255,255,0.08);color:white;"
            f"border:1px solid rgba(255,255,255,0.2);border-radius:6px;"
            f"padding:6px 14px;font-size:12px;font-weight:600;}}"
            f"QToolButton:hover{{background:rgba(255,255,255,0.15);}}")
        self.btn_export.setEnabled(False)
        em = QMenu(self)
        em.addAction("📄  Export CSV",   lambda: self._export("csv"))
        em.addAction("📋  Export JSON",  lambda: self._export("json"))
        em.addAction("🌐  Export HTML",  lambda: self._export("html"))
        self.btn_export.setMenu(em)
        self.btn_export.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        lay.addWidget(self.btn_export)
        btn_about = QToolButton(); btn_about.setText("ℹ")
        btn_about.setStyleSheet(
            "QToolButton{background:transparent;color:rgba(255,255,255,0.5);"
            "border:none;font-size:16px;padding:4px 10px;border-radius:6px;}"
            "QToolButton:hover{color:white;background:rgba(255,255,255,0.1);}")
        btn_about.clicked.connect(lambda: AboutDialog(self).exec())
        lay.addWidget(btn_about)
        return h

    def _nav_style_all(self, active_idx):
        for i, btn in enumerate(self.nav_btns):
            if i == active_idx:
                btn.setStyleSheet(
                    f"QPushButton{{background:rgba(254,119,67,0.2);color:#FE7743;"
                    f"border:none;font-size:13px;font-weight:700;"
                    f"padding:8px 18px;border-radius:8px;}}")
            else:
                btn.setStyleSheet(
                    f"QPushButton{{background:transparent;color:rgba(255,255,255,0.6);"
                    f"border:none;font-size:13px;font-weight:500;"
                    f"padding:8px 18px;border-radius:8px;}}"
                    f"QPushButton:hover{{background:rgba(255,255,255,0.1);color:white;}}")

    def _nav(self, idx):
        self.stack.setCurrentIndex(idx)
        self._nav_style_all(idx)

    def _mk_sidebar(self):
        sb = QFrame(); sb.setFixedWidth(226)
        sb.setStyleSheet(
            f"QFrame{{background:{CARD_BG};border-right:1px solid {BORDER};border-radius:0;}}")
        lay = QVBoxLayout(sb); lay.setContentsMargins(14,20,14,20); lay.setSpacing(6)
        lay.addWidget(SectionLabel("SCAN MODE")); lay.addSpacing(4)
        self.btn_quick = QPushButton("⚡  Quick Scan")
        self.btn_deep  = QPushButton("🔬  Deep Scan")
        self._style_mode_btn(self.btn_quick, True)
        self._style_mode_btn(self.btn_deep,  False)
        self.btn_quick.clicked.connect(lambda: self._set_mode(ScanMode.QUICK))
        self.btn_deep.clicked.connect( lambda: self._set_mode(ScanMode.DEEP))
        lay.addWidget(self.btn_quick); lay.addWidget(self.btn_deep)
        self.mode_desc = QLabel("Walks the filesystem quickly.\nFinds all accessible files.")
        self.mode_desc.setWordWrap(True)
        self.mode_desc.setStyleSheet(
            f"color:{MUTED};font-size:11px;background:{LIGHT_BG};border-radius:6px;padding:8px;")
        lay.addWidget(self.mode_desc); lay.addSpacing(12)
        lay.addWidget(SectionLabel("SOURCE")); lay.addSpacing(4)
        self.src_lbl = QLabel("None selected")
        self.src_lbl.setWordWrap(True)
        self.src_lbl.setStyleSheet(
            f"background:{LIGHT_BG};border:1px solid {BORDER};"
            f"border-radius:8px;padding:8px;color:{MUTED};font-size:11px;")
        lay.addWidget(self.src_lbl)
        bf = QPushButton("📁  Browse Folder"); bf.setObjectName("ghost")
        bf.clicked.connect(self._browse); lay.addWidget(bf); lay.addSpacing(12)
        lay.addWidget(SectionLabel("SHOW FILES")); lay.addSpacing(4)
        self.chk_show_active  = QCheckBox("Active (on disk)")
        self.chk_show_removed = QCheckBox("Removed (deleted)")
        self.chk_show_erased  = QCheckBox("Erased (formatted)")
        self.chk_show_active.setChecked(False)
        self.chk_show_removed.setChecked(True)
        self.chk_show_erased.setChecked(True)
        self.chk_show_active.setStyleSheet(f"QCheckBox{{color:{MUTED};font-size:11px;}}")
        self.chk_show_removed.setStyleSheet(f"QCheckBox{{color:{DANGER};font-size:11px;}}")
        self.chk_show_erased.setStyleSheet(f"QCheckBox{{color:#9B59B6;font-size:11px;}}")
        for chk in [self.chk_show_active, self.chk_show_removed, self.chk_show_erased]:
            chk.stateChanged.connect(self._apply_filter)
            lay.addWidget(chk)
        lay.addSpacing(4)
        tip = QLabel("Search & type filter\nlive in Results view \u2192")
        tip.setWordWrap(True)
        tip.setStyleSheet(
            f"color:{MUTED};font-size:10px;background:{LIGHT_BG};"
            f"border-radius:6px;padding:6px 8px;")
        lay.addWidget(tip)
        lay.addStretch()
        self.btn_start = QPushButton("▶  Start Scan")
        self.btn_start.setMinimumHeight(42)
        self.btn_start.setFont(QFont("Segoe UI",13,QFont.Weight.Bold))
        self.btn_start.clicked.connect(self._start_scan)
        lay.addWidget(self.btn_start)
        self.btn_stop = QPushButton("⏹  Stop Scan"); self.btn_stop.setObjectName("danger")
        self.btn_stop.setEnabled(False); self.btn_stop.setMinimumHeight(36)
        self.btn_stop.clicked.connect(self._stop_scan)
        lay.addWidget(self.btn_stop)
        return sb

    def _style_mode_btn(self, btn, active):
        if active:
            btn.setStyleSheet(
                f"QPushButton{{background:{PRIMARY};color:white;border:none;"
                f"border-radius:8px;padding:9px 12px;font-size:12px;"
                f"font-weight:700;text-align:left;}}")
        else:
            btn.setStyleSheet(
                f"QPushButton{{background:{LIGHT_BG};color:{ACCENT};"
                f"border:1.5px solid {BORDER};border-radius:8px;padding:9px 12px;"
                f"font-size:12px;font-weight:600;text-align:left;}}"
                f"QPushButton:hover{{background:#EAE9E4;}}")

    def _mk_drive_page(self):
        page = QWidget()
        lay = QVBoxLayout(page); lay.setContentsMargins(28,24,28,24); lay.setSpacing(14)
        tr = QHBoxLayout()
        t = QLabel("Select Drive or Folder")
        t.setFont(QFont("Segoe UI",18,QFont.Weight.Bold))
        t.setStyleSheet(f"color:{ACCENT};"); tr.addWidget(t); tr.addStretch()
        br = QPushButton("↻  Refresh"); br.setObjectName("ghost")
        br.setFixedWidth(110); br.clicked.connect(self._refresh_drives)
        tr.addWidget(br); lay.addLayout(tr)
        sub = QLabel(
            "Choose a volume to scan. For raw sector scanning of block devices, "
            "run TraceCore with elevated privileges (sudo).")
        sub.setWordWrap(True); sub.setStyleSheet(f"color:{MUTED};font-size:12px;")
        lay.addWidget(sub)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent;")
        self.drives_widget = QWidget()
        self.drives_widget.setStyleSheet("background:transparent;")
        self.drives_layout = QVBoxLayout(self.drives_widget)
        self.drives_layout.setSpacing(10); self.drives_layout.setContentsMargins(0,0,4,0)
        self.drives_layout.addStretch()
        scroll.setWidget(self.drives_widget); lay.addWidget(scroll, 1)
        tip = QLabel(
            "💡  Quick Scan: fast filesystem walk — best for accidentally deleted files on healthy drives.\n"
            "🔬  Deep Scan: raw byte carving — best for formatted, corrupted, or overwritten media.")
        tip.setWordWrap(True)
        tip.setStyleSheet(
            f"background:#FFF8F5;border:1px solid #FDD5C4;border-radius:10px;"
            f"padding:14px;color:#7A4030;font-size:12px;")
        lay.addWidget(tip)
        return page

    def _mk_scan_page(self):
        page = QWidget()
        lay = QVBoxLayout(page); lay.setContentsMargins(28,24,28,24); lay.setSpacing(14)
        self.scan_title = QLabel("Scanning…")
        self.scan_title.setFont(QFont("Segoe UI",18,QFont.Weight.Bold))
        self.scan_title.setStyleSheet(f"color:{ACCENT};"); lay.addWidget(self.scan_title)
        pc = Card()
        pl = QVBoxLayout(pc); pl.setContentsMargins(20,16,20,16); pl.setSpacing(10)
        self.prog_status = QLabel("Initializing…")
        self.prog_status.setStyleSheet(f"color:{MUTED};font-size:12px;"); pl.addWidget(self.prog_status)
        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0,100); self.prog_bar.setFixedHeight(16); self.prog_bar.setFormat("%p%")
        pl.addWidget(self.prog_bar)
        sc_row = QHBoxLayout(); sc_row.setSpacing(10)
        self.sc_found = StatCard("Files Found","0",   PRIMARY,"📁")
        self.sc_size  = StatCard("Scanned",    "0 B", ACCENT, "💾")
        self.sc_speed = StatCard("Speed",      "—",   BASE,   "⚡")
        self.sc_time  = StatCard("Elapsed",    "0s",  MUTED,  "⏱")
        for s in [self.sc_found, self.sc_size, self.sc_speed, self.sc_time]:
            sc_row.addWidget(s)
        pl.addLayout(sc_row); lay.addWidget(pc)
        self._tick_timer = QTimer()
        self._tick_timer.timeout.connect(self._update_elapsed)
        lh = QHBoxLayout()
        ll = QLabel("Live Results")
        ll.setFont(QFont("Segoe UI",13,QFont.Weight.Bold))
        ll.setStyleSheet(f"color:{ACCENT};"); lh.addWidget(ll); lh.addStretch()
        self.live_count = QLabel("0 files")
        self.live_count.setStyleSheet(f"color:{MUTED};font-size:12px;")
        lh.addWidget(self.live_count); lay.addLayout(lh)
        self.live_table = self._mk_table(checkboxes=False)
        lay.addWidget(self.live_table, 1)
        return page

    def _mk_results_page(self):
        page = QWidget()
        lay = QVBoxLayout(page); lay.setContentsMargins(28,24,28,24); lay.setSpacing(10)
        # Row 1: title + action buttons
        hdr = QHBoxLayout()
        self.results_title = QLabel("Results")
        self.results_title.setFont(QFont("Segoe UI",18,QFont.Weight.Bold))
        self.results_title.setStyleSheet(f"color:{ACCENT};"); hdr.addWidget(self.results_title)
        hdr.addStretch()
        self.btn_sel_all  = QPushButton("☑  All");  self.btn_sel_all.setObjectName("ghost")
        self.btn_sel_none = QPushButton("Deselect"); self.btn_sel_none.setObjectName("ghost")
        self.btn_recover  = QPushButton("💾  Recover Selected")
        self.btn_sel_all.setFixedWidth(80); self.btn_sel_none.setFixedWidth(90)
        self.btn_recover.setMinimumWidth(180); self.btn_recover.setEnabled(False)
        self.btn_sel_all.clicked.connect(lambda: self._set_all_checked(True))
        self.btn_sel_none.clicked.connect(lambda: self._set_all_checked(False))
        self.btn_recover.clicked.connect(self._recover)
        for b in [self.btn_sel_all, self.btn_sel_none, self.btn_recover]:
            hdr.addWidget(b)
        lay.addLayout(hdr)
        # Row 2: search/filter bar
        search_row = QHBoxLayout(); search_row.setSpacing(8)
        self.name_search = QLineEdit()
        self.name_search.setPlaceholderText("🔍  Search by file name…")
        self.name_search.setMinimumWidth(220)
        self.name_search.textChanged.connect(self._apply_filter)
        self.name_search.setStyleSheet(
            f"QLineEdit{{background:white;border:1.5px solid {BORDER};"
            f"border-radius:8px;padding:7px 12px 7px 10px;font-size:13px;}}"
            f"QLineEdit:focus{{border-color:{PRIMARY};}}")
        self.btn_clear_name = QPushButton("✕")
        self.btn_clear_name.setFixedSize(28,28)
        self.btn_clear_name.setObjectName("ghost")
        self.btn_clear_name.clicked.connect(lambda: self.name_search.clear())
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("📂  Filter by type: jpg, png, pdf…")
        self.filter_edit.setMinimumWidth(200)
        self.filter_edit.textChanged.connect(self._apply_filter)
        self.filter_edit.setStyleSheet(
            f"QLineEdit{{background:white;border:1.5px solid {BORDER};"
            f"border-radius:8px;padding:7px 12px 7px 10px;font-size:13px;}}"
            f"QLineEdit:focus{{border-color:{PRIMARY};}}")
        self.btn_clear_type = QPushButton("✕")
        self.btn_clear_type.setFixedSize(28,28)
        self.btn_clear_type.setObjectName("ghost")
        self.btn_clear_type.clicked.connect(lambda: self.filter_edit.clear())
        self.filter_status = QLabel("")
        self.filter_status.setStyleSheet(f"color:{MUTED};font-size:11px;min-width:70px;")
        search_row.addWidget(self.name_search, 2)
        search_row.addWidget(self.btn_clear_name)
        search_row.addSpacing(8)
        search_row.addWidget(self.filter_edit, 2)
        search_row.addWidget(self.btn_clear_type)
        search_row.addWidget(self.filter_status)
        search_row.addStretch()
        lay.addLayout(search_row)
        self.result_tabs = QTabWidget()
        self.result_tabs.addTab(self._mk_results_tab(), "📋  File List")
        self.result_tabs.addTab(self._mk_stats_tab(),   "📊  Statistics")
        lay.addWidget(self.result_tabs, 1)
        self.summary_lbl = QLabel("No results yet.")
        self.summary_lbl.setStyleSheet(
            f"background:{LIGHT_BG};border-radius:6px;padding:8px 12px;"
            f"color:{MUTED};font-size:12px;")
        lay.addWidget(self.summary_lbl)
        self.rec_bar = QProgressBar(); self.rec_bar.setFixedHeight(10); self.rec_bar.hide()
        lay.addWidget(self.rec_bar)
        return page

    def _mk_results_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w); lay.setContentsMargins(0,8,0,0); lay.setSpacing(6)
        self.results_table = self._mk_table(checkboxes=True)
        self.results_table.itemSelectionChanged.connect(self._on_select)
        self.results_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self._row_context_menu)
        sp = QSplitter(Qt.Orientation.Horizontal)
        sp.addWidget(self.results_table)
        sp.addWidget(self._mk_preview_panel())
        sp.setSizes([720,320]); lay.addWidget(sp)
        return w

    def _mk_preview_panel(self):
        pf = Card(radius=10)
        pl = QVBoxLayout(pf); pl.setContentsMargins(12,12,12,12); pl.setSpacing(8)
        pt = QLabel("Preview")
        pt.setFont(QFont("Segoe UI",12,QFont.Weight.Bold))
        pt.setStyleSheet(f"color:{ACCENT};"); pl.addWidget(pt)
        self.img_preview = ImagePreview(); pl.addWidget(self.img_preview, 1)
        self.meta_text = QTextEdit(); self.meta_text.setReadOnly(True)
        self.meta_text.setFixedHeight(130); pl.addWidget(self.meta_text)
        return pf

    def _mk_stats_tab(self):
        w = QWidget(); w.setStyleSheet(f"background:{BG};")
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent;")
        inner = QWidget(); inner.setStyleSheet("background:transparent;")
        self.stats_layout = QVBoxLayout(inner)
        self.stats_layout.setContentsMargins(4,8,4,8); self.stats_layout.setSpacing(14)
        self.stats_layout.addStretch()
        scroll.setWidget(inner)
        vl = QVBoxLayout(w); vl.setContentsMargins(0,0,0,0); vl.addWidget(scroll)
        return w

    def _mk_table(self, checkboxes=False):
        cols = (["","Name","Type","Size","Status","Path"] if checkboxes
                else ["Name","Type","Size","Status","Path"])
        t = QTableWidget(0, len(cols))
        t.setHorizontalHeaderLabels(cols)
        t.horizontalHeader().setStretchLastSection(True)
        t.verticalHeader().setVisible(False)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setShowGrid(False); t.setAlternatingRowColors(True)
        t.setStyleSheet(t.styleSheet() + "QTableWidget{alternate-background-color:#F7F6F2;}")
        if checkboxes:
            t.setColumnWidth(0, 42)
            t.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            t.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            for c in [2, 3, 4]: t.setColumnWidth(c, 100)
        else:
            t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        return t

    # ── Logic ──────────────────────────────────────────────────────────────────

    def _refresh_drives(self):
        while self.drives_layout.count() > 1:
            item = self.drives_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self._drive_cards.clear()
        drives = list_drives()
        if not drives:
            lbl = QLabel("No drives detected.\nTry running with elevated privileges.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color:{MUTED};font-size:13px;")
            self.drives_layout.insertWidget(0, lbl)
        else:
            for d in drives:
                card = DriveCard(d); card.clicked.connect(self._on_drive_click)
                self._drive_cards.append(card)
                self.drives_layout.insertWidget(self.drives_layout.count()-1, card)
        self.status_bar.showMessage(f"{len(drives)} drive(s) detected  •  Select one to begin")

    def _set_mode(self, mode):
        self._scan_mode = mode
        q = (mode == ScanMode.QUICK)
        self._style_mode_btn(self.btn_quick, q)
        self._style_mode_btn(self.btn_deep,  not q)
        self.mode_desc.setText(
            "Walks the filesystem quickly.\nBest for accessible/deleted files." if q else
            "Reads raw bytes sector-by-sector.\nBest for formatted/corrupted media.")

    def _on_drive_click(self, drive):
        self._source = drive.path
        for card in self._drive_cards:
            card.set_selected(card.drive.path == drive.path)
        short = drive.label if len(drive.label) < 30 else drive.label[:27]+"…"
        self._set_src(short)
        self.status_bar.showMessage(f"Selected: {drive.label}  •  Press Start Scan to begin")

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder", os.path.expanduser("~"))
        if folder:
            self._source = folder
            disp = folder if len(folder) < 32 else "…"+folder[-29:]
            self._set_src(disp)
            for card in self._drive_cards: card.set_selected(False)
            self.status_bar.showMessage(f"Source: {folder}")

    def _set_src(self, text):
        self.src_lbl.setText(text)
        self.src_lbl.setStyleSheet(
            f"background:#FFF8F5;border:1.5px solid {PRIMARY};"
            f"border-radius:8px;padding:8px;color:{ACCENT};"
            f"font-size:11px;font-weight:600;")

    def _start_scan(self):
        if not self._source:
            QMessageBox.warning(self, "No Source",
                                "Please select a drive or folder first."); return
        self._results.clear(); self._stats.reset()
        self._clear_table(self.live_table); self._clear_table(self.results_table)
        self.img_preview.reset(); self.meta_text.clear()
        mode_str = "Quick" if self._scan_mode == ScanMode.QUICK else "Deep"
        src_d = self._source if len(self._source) < 55 else "…"+self._source[-52:]
        self.scan_title.setText(f"{mode_str} Scan  ·  {src_d}")
        self.prog_status.setText("Starting…"); self.prog_bar.setValue(0)
        for sc in [self.sc_found, self.sc_size, self.sc_speed, self.sc_time]: sc.set_value("0")
        self.sc_speed.set_value("—")
        self.stack.setCurrentIndex(1); self._nav(1)
        self.btn_start.setEnabled(False); self.btn_stop.setEnabled(True)
        self._scanning = True; self._scan_start = time.time()
        self._tick_timer.start(1000)
        if self._scan_mode == ScanMode.DEEP:
            self.prog_bar.setRange(0,0)
        else:
            self.prog_bar.setRange(0,100)
        self._scan_worker = ScanWorker(self._engine, self._source, self._scan_mode)
        self._scan_worker.progress.connect(self._on_progress)
        self._scan_worker.file_found.connect(self._on_file_found)
        self._scan_worker.finished.connect(self._on_scan_done)
        self._scan_worker.start()

    def _stop_scan(self):
        self._engine.stop(); self.btn_stop.setEnabled(False)
        self.prog_status.setText("Stopping…")

    def _on_progress(self, cur, total, msg):
        if total > 0:
            self.prog_bar.setRange(0,100)
            self.prog_bar.setValue(min(int(cur/total*100),100))
        disp = msg if len(msg)<90 else "…"+msg[-87:]
        self.prog_status.setText(disp)
        elapsed = time.time()-self._scan_start
        if elapsed > 0.5 and cur > 0:
            mb = cur/(1024*1024)
            self.sc_size.set_value(f"{mb:.1f} MB" if mb<1024 else f"{mb/1024:.2f} GB")
            self.sc_speed.set_value(f"{mb/elapsed:.1f} MB/s")

    def _on_file_found(self, rf):
        self._results.append(rf); self._stats.add(rf)
        n = len(self._results)
        self.sc_found.set_value(f"{n:,}")
        self.live_count.setText(f"{n:,} files")
        if n <= 8000: self._add_row(self.live_table, rf, checkboxes=False)

    def _update_elapsed(self):
        if self._scanning:
            self._elapsed = time.time()-self._scan_start
            self.sc_time.set_value(fmt_time(self._elapsed))

    def _on_scan_done(self, count):
        self._scanning = False; self._tick_timer.stop()
        self._elapsed = time.time()-self._scan_start
        self.sc_time.set_value(fmt_time(self._elapsed))
        self.btn_start.setEnabled(True); self.btn_stop.setEnabled(False)
        self.prog_bar.setRange(0,100); self.prog_bar.setValue(100)
        self.prog_status.setText(
            f"✅  Scan complete  ·  {count:,} files  ·  {fmt_time(self._elapsed)}")
        self.status_bar.showMessage(
            f"Scan complete — {count:,} files  |  {fmt_time(self._elapsed)}")
        self._populate_results()
        self.btn_recover.setEnabled(count > 0)
        self.btn_export.setEnabled(count > 0)
        if count > 0: self.stack.setCurrentIndex(2); self._nav(2)

    def _populate_results(self):
        self._clear_table(self.results_table)
        for rf in self._results: self._add_row(self.results_table, rf, checkboxes=True)
        self.results_title.setText(f"Results  ({len(self._results):,} files)")
        self._apply_filter()   # apply status filter right away (hides Active by default)
        self._update_summary(); self._rebuild_stats_tab()

    def _add_row(self, table, rf, checkboxes):
        icon, color, _ = get_ext_meta(rf.ext)
        row = table.rowCount(); table.insertRow(row); table.setRowHeight(row, 36)
        col = 0
        if checkboxes:
            chk = QCheckBox()
            chk.setStyleSheet(
                f"QCheckBox::indicator{{"
                f"  width:18px; height:18px;"
                f"  border:2px solid {ACCENT}; border-radius:4px; background:white;}}"
                f"QCheckBox::indicator:checked{{"
                f"  background-color:{PRIMARY}; border-color:{PRIMARY};}}"
                f"QCheckBox::indicator:hover{{border-color:{PRIMARY}; background:#FFF3EE;}}"
            )
            cw = QWidget()
            cw.setStyleSheet("background:transparent;")
            cl = QHBoxLayout(cw)
            cl.addWidget(chk)
            cl.setContentsMargins(10, 0, 0, 0)
            cl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            chk.stateChanged.connect(self._update_summary)
            table.setCellWidget(row, col, cw); col += 1
        ni = QTableWidgetItem(f"{icon}  {rf.name}")
        ni.setData(Qt.ItemDataRole.UserRole, rf)
        table.setItem(row, col, ni); col += 1
        ti = QTableWidgetItem(rf.ext.upper() or "—")
        ti.setForeground(QColor(color)); ti.setFont(QFont("Segoe UI",11,QFont.Weight.Bold))
        table.setItem(row, col, ti); col += 1
        table.setItem(row, col, QTableWidgetItem(fmt_size(rf.size))); col += 1
        fg = {FileStatus.ACTIVE:SUCCESS, FileStatus.DELETED:DANGER, FileStatus.CARVED:"#9B59B6"}
        si = QTableWidgetItem(rf.status.value)
        si.setForeground(QColor(fg.get(rf.status, BASE)))
        si.setFont(QFont("Segoe UI",11,QFont.Weight.Bold))
        table.setItem(row, col, si); col += 1
        pd = rf.path if len(rf.path)<55 else "…"+rf.path[-52:]
        table.setItem(row, col, QTableWidgetItem(pd))

    def _on_select(self):
        for item in self.results_table.selectedItems():
            rf = item.data(Qt.ItemDataRole.UserRole)
            if rf: self._show_preview(rf); return

    def _show_preview(self, rf):
        icon, color, cat = get_ext_meta(rf.ext)
        meta = (f"Name:     {rf.name}\nType:     {rf.description}\n"
                f"Category: {cat}\nSize:     {fmt_size(rf.size)}\n"
                f"Status:   {rf.status.value}\nPath:     {rf.path}\n")
        if rf.offset: meta += f"Offset:   {rf.offset:,} bytes\n"
        self.meta_text.setPlainText(meta)
        ext = rf.ext.lower()
        if ext in ("jpg","jpeg","png","gif","bmp","webp","tiff"):
            data = rf.preview_data
            if not data:
                # For ACTIVE files, read from path directly
                # For DELETED ($R files in Recycle Bin) or CARVED, also try reading from path
                _read_path = rf.path
                if rf.status == FileStatus.DELETED:
                    # The $R file is the actual data file for Recycle Bin entries
                    _r_candidate = rf.path  # already set to $R file in scanner
                    if not os.path.exists(_r_candidate):
                        # Try deriving $R from $I path
                        _r_candidate = rf.path.replace("$I", "$R") if "$I" in rf.path else rf.path
                    _read_path = _r_candidate
                try:
                    if os.path.exists(_read_path):
                        with open(_read_path, "rb") as f:
                            data = f.read(4 * 1024 * 1024)
                        rf.preview_data = data  # cache it
                except Exception:
                    data = None
            if data:
                self.img_preview.show_image(data)
            else:
                self.img_preview.reset("No preview data available")
        elif ext in ("txt","csv","log","py","js","html","xml","json","md","sh","c","cpp","rs"):
            data = rf.preview_data
            if not data:
                _read_path = rf.path
                if rf.status == FileStatus.DELETED:
                    _r_candidate = rf.path.replace("$I", "$R") if "$I" in rf.path else rf.path
                    _read_path = _r_candidate
                try:
                    if os.path.exists(_read_path):
                        with open(_read_path, "rb") as f:
                            data = f.read(4096)
                        rf.preview_data = data
                except Exception:
                    data = None
            if data: self.img_preview.show_text(data)
            else: self.img_preview.reset("No text preview available")
        else:
            self.img_preview.reset(f"{icon}  {rf.description}\n\nNo visual preview available.")

    def _row_context_menu(self, pos):
        item = self.results_table.itemAt(pos)
        if not item: return
        rf = item.data(Qt.ItemDataRole.UserRole)
        if not rf: return
        menu = QMenu(self)
        menu.addAction("💾  Recover this file", lambda: self._recover_single(rf))
        menu.addAction("📋  Copy path",
            lambda: QApplication.clipboard().setText(rf.path))
        if rf.status == FileStatus.ACTIVE and os.path.exists(rf.path):
            menu.addAction("📂  Open folder", lambda: self._open_folder(rf.path))
        menu.exec(self.results_table.viewport().mapToGlobal(pos))

    def _recover_single(self, rf):
        dest = QFileDialog.getExistingDirectory(
            self, "Recovery Destination", os.path.expanduser("~/Desktop"))
        if dest: self._run_recovery([rf], dest)

    def _open_folder(self, path):
        folder = os.path.dirname(path)
        sys_map = {"Windows": lambda: os.startfile(folder),
                   "Darwin":  lambda: os.system(f'open "{folder}"')}
        sys_map.get(platform.system(), lambda: os.system(f'xdg-open "{folder}"'))()

    def _set_all_checked(self, state):
        for row in range(self.results_table.rowCount()):
            if self.results_table.isRowHidden(row): continue
            cw = self.results_table.cellWidget(row, 0)
            if cw:
                chk = cw.findChild(QCheckBox)
                if chk: chk.setChecked(state)

    def _update_summary(self):
        total = self.results_table.rowCount()
        visible = sum(1 for r in range(total) if not self.results_table.isRowHidden(r))
        checked = 0
        for row in range(total):
            cw = self.results_table.cellWidget(row, 0)
            if cw:
                chk = cw.findChild(QCheckBox)
                if chk and chk.isChecked(): checked += 1
        self.summary_lbl.setText(
            f"{total:,} total  ·  {visible:,} shown  ·  {checked:,} selected")
        self.btn_recover.setEnabled(checked > 0)

    def _apply_filter(self, *_):
        name_q = self.name_search.text().strip().lower()
        exts   = {e.strip().lower() for e in self.filter_edit.text().split(",") if e.strip()}
        show_active  = self.chk_show_active.isChecked()
        show_removed = self.chk_show_removed.isChecked()
        show_erased  = self.chk_show_erased.isChecked()

        STATUS_MAP = {
            FileStatus.ACTIVE:  show_active,
            FileStatus.DELETED: show_removed,
            FileStatus.CARVED:  show_erased,
        }

        for row in range(self.results_table.rowCount()):
            item = self.results_table.item(row, 1)
            if not item:
                continue
            rf = item.data(Qt.ItemDataRole.UserRole)
            if not rf:
                continue

            hide = False
            # Status filter
            if not STATUS_MAP.get(rf.status, True):
                hide = True
            # Type filter
            elif exts and rf.ext.lower() not in exts:
                hide = True
            # Name search
            elif name_q and name_q not in rf.name.lower():
                hide = True

            (self.results_table.hideRow if hide else self.results_table.showRow)(row)

        self._update_summary()
        found = sum(1 for r in range(self.results_table.rowCount())
                    if not self.results_table.isRowHidden(r))
        self.filter_status.setText(f"{found:,} shown")

    def _recover(self):
        selected = []
        for row in range(self.results_table.rowCount()):
            cw = self.results_table.cellWidget(row, 0)
            if cw:
                chk = cw.findChild(QCheckBox)
                if chk and chk.isChecked():
                    item = self.results_table.item(row, 1)
                    if item:
                        rf = item.data(Qt.ItemDataRole.UserRole)
                        if rf: selected.append(rf)
        if not selected:
            QMessageBox.information(self,"Nothing Selected","Check at least one file."); return
        dest = QFileDialog.getExistingDirectory(
            self,"Recovery Destination",os.path.expanduser("~/Desktop"))
        if dest: self._run_recovery(selected, dest)

    def _run_recovery(self, files, dest):
        self.btn_recover.setEnabled(False); self.rec_bar.show(); self.rec_bar.setValue(0)
        self.status_bar.showMessage(f"Recovering {len(files):,} files to {dest}…")
        self._rec_worker = RecoverWorker(files, dest)
        self._rec_worker.progress.connect(
            lambda c,t,_: self.rec_bar.setValue(int(c/max(t,1)*100)))
        self._rec_worker.finished.connect(lambda p: self._on_recover_done(p, dest))
        self._rec_worker.start()

    def _on_recover_done(self, paths, dest):
        self.rec_bar.hide(); self.btn_recover.setEnabled(True)
        n = len(paths)
        self.status_bar.showMessage(f"✅  Recovered {n} files to {dest}")
        QMessageBox.information(self,"Recovery Complete",
            f"Successfully recovered {n} file(s) to:\n{dest}")

    def _rebuild_stats_tab(self):
        while self.stats_layout.count() > 1:
            item = self.stats_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        s = self._stats
        mode_str = "Quick" if self._scan_mode == ScanMode.QUICK else "Deep"
        # Summary stat cards
        sr = QHBoxLayout(); sr.setSpacing(10)
        for label,val,color,icon in [
            ("Total Files",  f"{s.total_files:,}",  PRIMARY, "📁"),
            ("Total Size",   fmt_size(s.total_bytes),ACCENT,  "💾"),
            ("Active",       f"{s.by_status.get('Active',0):,}", SUCCESS,"✅"),
            ("Recoverable",  f"{s.by_status.get('Carved',0)+s.by_status.get('Deleted',0):,}", WARN,"⚠"),
        ]:
            sr.addWidget(StatCard(label, val, color, icon))
        sw = QWidget(); sw.setStyleSheet("background:transparent;"); sw.setLayout(sr)
        self.stats_layout.insertWidget(self.stats_layout.count()-1, sw)
        # Scan info
        info = Card(); il = QGridLayout(info)
        il.setContentsMargins(16,14,16,14); il.setSpacing(8)
        for r,(k,v) in enumerate([
            ("Source",  self._source or "—"),
            ("Mode",    mode_str),
            ("Duration",fmt_time(self._elapsed)),
            ("Largest", f"{s.largest_file} ({fmt_size(s.largest_size)})"),
            ("Time",    datetime.datetime.now().strftime("%Y-%m-%d %H:%M")),
        ]):
            kl = QLabel(k+":"); kl.setFixedWidth(80)
            kl.setStyleSheet(f"color:{MUTED};font-size:12px;font-weight:600;")
            vl = QLabel(v); vl.setWordWrap(True)
            vl.setStyleSheet(f"color:{BASE};font-size:12px;")
            il.addWidget(kl,r,0); il.addWidget(vl,r,1)
        self.stats_layout.insertWidget(self.stats_layout.count()-1, info)
        # Category breakdown
        if s.by_category:
            cc = Card(); cl = QVBoxLayout(cc)
            cl.setContentsMargins(16,14,16,14); cl.setSpacing(4)
            ct = QLabel("Files by Category")
            ct.setFont(QFont("Segoe UI",12,QFont.Weight.Bold))
            ct.setStyleSheet(f"color:{ACCENT};"); cl.addWidget(ct)
            max_v = max(s.by_category.values(), default=1)
            for cat,count in s.top_categories(10):
                _,color,_ = get_ext_meta(cat.lower())
                cl.addWidget(MiniBar(cat, count, max_v, color))
            self.stats_layout.insertWidget(self.stats_layout.count()-1, cc)
        # Status breakdown
        sc_card = Card(); sl = QVBoxLayout(sc_card)
        sl.setContentsMargins(16,14,16,14); sl.setSpacing(4)
        stt = QLabel("Files by Status")
        stt.setFont(QFont("Segoe UI",12,QFont.Weight.Bold))
        stt.setStyleSheet(f"color:{ACCENT};"); sl.addWidget(stt)
        scol = {"Active":SUCCESS,"Removed":DANGER,"Erased":"#9B59B6"}
        max_s = max(s.by_status.values(), default=1)
        for sn,count in s.by_status.items():
            sl.addWidget(MiniBar(sn, count, max_s, scol.get(sn,MUTED)))
        self.stats_layout.insertWidget(self.stats_layout.count()-1, sc_card)

    def _export(self, fmt):
        mode_str = "Quick" if self._scan_mode == ScanMode.QUICK else "Deep"
        ext_map = {"csv":"CSV Files (*.csv)","json":"JSON Files (*.json)","html":"HTML Files (*.html)"}
        path,_ = QFileDialog.getSaveFileName(
            self,"Export Report",f"tracecore_report.{fmt}",ext_map[fmt])
        if not path: return
        try:
            if fmt=="csv":  export_csv(self._results, path)
            elif fmt=="json": export_json(self._results, path, self._stats,
                                          self._source or "", mode_str, self._elapsed)
            elif fmt=="html": export_html(self._results, path, self._stats,
                                          self._source or "", mode_str, self._elapsed)
            self.status_bar.showMessage(f"✅  Exported {fmt.upper()} to {path}")
            QMessageBox.information(self,"Export Complete",f"Saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self,"Export Failed",str(e))

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Return"), self).activated.connect(self._start_scan)
        QShortcut(QKeySequence("Escape"),      self).activated.connect(self._stop_scan)
        QShortcut(QKeySequence("Ctrl+A"),      self).activated.connect(lambda: self._set_all_checked(True))
        QShortcut(QKeySequence("Ctrl+D"),      self).activated.connect(lambda: self._set_all_checked(False))
        QShortcut(QKeySequence("Ctrl+E"),      self).activated.connect(lambda: self._export("html"))
        QShortcut(QKeySequence("Ctrl+R"),      self).activated.connect(self._recover)
        for i in range(3):
            QShortcut(QKeySequence(str(i+1)), self).activated.connect(
                lambda _=None, idx=i: self._nav(idx))

    def _clear_table(self, t): t.setRowCount(0)

    def closeEvent(self, event):
        self._engine.stop(); event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("TraceCore")
    app.setApplicationDisplayName("TraceCore – Data Recovery")
    if hasattr(Qt.ApplicationAttribute,"AA_UseHighDpiPixmaps"):
        app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    win = TraceCoreApp(); win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()