import os, sys, json, tempfile, subprocess, urllib.request, urllib.parse
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QUrl, QProcess
from PySide6.QtGui import QAction, QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPlainTextEdit, QListWidget, QListWidgetItem, QPushButton, QLabel, QLineEdit,
    QFileDialog, QMessageBox, QTabWidget, QFrame, QToolBar, QStatusBar, QInputDialog
)

APP_DIR = Path(__file__).resolve().parent
if getattr(sys, "frozen", False):
    USER_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "OCEANA"
    SCRIPTS_DIR = USER_DATA_DIR / "scripts"
else:
    SCRIPTS_DIR = APP_DIR / "scripts"
MAX_SCRIPT_BYTES = 1_000_000
ALLOWED_HOST = "raw.githubusercontent.com"

class LuaHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []
        def fmt(color, bold=False, italic=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold: f.setFontWeight(QFont.Weight.Bold)
            if italic: f.setFontItalic(True)
            return f
        keyword = fmt("#65b8ff", True)
        builtin = fmt("#72d6c4")
        string = fmt("#d6a7ff")
        number = fmt("#f2bd75")
        comment = fmt("#71869e", False, True)
        for word in ("and break do else elseif end false for function if in local nil not or repeat return then true until while goto"):
            self.rules.append((rf"\b{word}\b", keyword))
        for word in ("print pairs ipairs next type tostring tonumber select assert error pcall xpcall math string table coroutine utf8 load loadstring"):
            self.rules.append((rf"\b{word}\b", builtin))
        self.rules += [
            (r'"[^"\\]*(?:\\.[^"\\]*)*"', string),
            (r"'[^'\\]*(?:\\.[^'\\]*)*'", string),
            (r"\b[0-9]+(?:\.[0-9]+)?\b", number),
            (r"--.*$", comment),
        ]

    def highlightBlock(self, text):
        import re
        for pattern, style in self.rules:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), style)

class Editor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setFont(QFont("Cascadia Code", 11))
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.highlighter = LuaHighlighter(self.document())
        self.setPlaceholderText("-- Write Lua here\\nprint('Hello from OCEANA')")

class Oceana(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OCEANA EXECUTOR — Standalone Lua")
        self.resize(1320, 850)
        self.setMinimumSize(980, 650)
        self.current_process = None
        self.current_temp = None
        self._build_ui()
        self._load_script_list()
        self.new_tab("Untitled", "-- OCEANA EXECUTOR | Standalone Lua runtime\\nprint('Hello from OCEANA')\\n")

    def _build_ui(self):
        self.setStyleSheet("""
        QMainWindow, QWidget { background:#080e18; color:#d8e7f7; }
        QLabel#brand { color:#42b7ff; font-size:25px; font-weight:800; letter-spacing:2px; }
        QLabel#sub { color:#7892ad; font-size:10px; font-weight:700; }
        QFrame#top { background:#0d1726; border-bottom:1px solid #183653; }
        QFrame#panel { background:#0b1421; border:1px solid #152b43; border-radius:10px; }
        QPushButton { background:#14263b; color:#d7e8f8; border:1px solid #254664;
                      border-radius:7px; padding:9px 14px; font-weight:700; }
        QPushButton:hover { background:#1a3855; border-color:#38aaff; }
        QPushButton#run { background:#087fc5; border:1px solid #31b5ff; color:white; }
        QPushButton#run:hover { background:#1199e5; }
        QPushButton#stop { background:#48202a; border:1px solid #874052; }
        QLineEdit { background:#09111d; color:#dcecff; border:1px solid #24415f;
                    border-radius:6px; padding:9px; }
        QListWidget { background:#09111d; border:0; outline:0; }
        QListWidget::item { padding:9px; border-radius:5px; }
        QListWidget::item:selected { background:#12395b; color:white; }
        QTabWidget::pane { border:1px solid #1b3855; border-radius:8px; background:#0a1320; }
        QTabBar::tab { background:#101d2d; color:#8ea8c2; padding:10px 18px;
                       border:1px solid #1b3855; border-bottom:0; }
        QTabBar::tab:selected { background:#153655; color:white; }
        QPlainTextEdit { background:#08111d; color:#d9e8f7; border:0; selection-background-color:#174d78; }
        QStatusBar { background:#0b1421; color:#7f9ab5; border-top:1px solid #183653; }
        QToolBar { background:#0b1421; border:0; spacing:7px; padding:8px; }
        """)
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(14, 12, 14, 10)
        outer.setSpacing(10)

        top = QFrame(); top.setObjectName("top")
        top_l = QHBoxLayout(top); top_l.setContentsMargins(16, 9, 16, 9)
        brand_col = QVBoxLayout()
        brand = QLabel("OCEANA"); brand.setObjectName("brand")
        sub = QLabel("EXECUTOR  /  LUA WORKSPACE"); sub.setObjectName("sub")
        brand_col.addWidget(brand); brand_col.addWidget(sub)
        top_l.addLayout(brand_col); top_l.addStretch()
        self.runtime_label = QLabel("● STANDALONE LUA RUNTIME")
        self.runtime_label.setStyleSheet("color:#6bc9ff;font-weight:700;")
        top_l.addWidget(self.runtime_label)
        outer.addWidget(top)

        actions = QHBoxLayout()
        for label, fn, obj in [
            ("＋ New", self.new_empty, ""),
            ("Open", self.open_file, ""),
            ("Save", self.save_file, ""),
            ("Load raw URL", self.load_url, ""),
            ("▶ Run", self.run_script, "run"),
            ("■ Stop", self.stop_script, "stop"),
        ]:
            b = QPushButton(label)
            if obj: b.setObjectName(obj)
            b.clicked.connect(fn); actions.addWidget(b)
        actions.addStretch()
        outer.addLayout(actions)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(5)
        left = QFrame(); left.setObjectName("panel")
        left_l = QVBoxLayout(left); left_l.setContentsMargins(10, 12, 10, 10)
        left_l.addWidget(QLabel("SCRIPT LIBRARY"))
        self.search = QLineEdit(); self.search.setPlaceholderText("Filter saved scripts…")
        self.search.textChanged.connect(self.filter_scripts)
        left_l.addWidget(self.search)
        self.script_list = QListWidget()
        self.script_list.itemDoubleClicked.connect(self.open_library_item)
        left_l.addWidget(self.script_list, 1)
        add_btn = QPushButton("＋ Add local script")
        add_btn.clicked.connect(self.import_to_library)
        left_l.addWidget(add_btn)
        splitter.addWidget(left)

        right = QWidget(); right_l = QVBoxLayout(right); right_l.setContentsMargins(0,0,0,0)
        self.tabs = QTabWidget(); self.tabs.setTabsClosable(True); self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        right_l.addWidget(self.tabs, 1)

        console_panel = QFrame(); console_panel.setObjectName("panel")
        cp = QVBoxLayout(console_panel); cp.setContentsMargins(12,8,12,8)
        console_head = QHBoxLayout()
        console_head.addWidget(QLabel("OUTPUT CONSOLE"))
        console_head.addStretch()
        clear = QPushButton("Clear"); clear.clicked.connect(lambda: self.console.clear())
        console_head.addWidget(clear)
        cp.addLayout(console_head)
        self.console = QPlainTextEdit(); self.console.setReadOnly(True); self.console.setMaximumBlockCount(1500)
        self.console.setFont(QFont("Cascadia Code", 9)); self.console.setFixedHeight(175)
        cp.addWidget(self.console)
        right_l.addWidget(console_panel)
        splitter.addWidget(right)
        splitter.setSizes([230, 1000])
        outer.addWidget(splitter, 1)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready • Scripts run in an isolated standalone Lua process")

    def editor(self):
        w = self.tabs.currentWidget()
        return w if isinstance(w, Editor) else None

    def new_tab(self, title, source=""):
        e = Editor(); e.setPlainText(source)
        index = self.tabs.addTab(e, title)
        self.tabs.setCurrentIndex(index)
        e.document().modificationChanged.connect(lambda changed, ed=e: self._mark_tab(ed, changed))
        return e

    def _mark_tab(self, editor, changed):
        idx = self.tabs.indexOf(editor)
        if idx >= 0:
            base = self.tabs.tabText(idx).rstrip(" *")
            self.tabs.setTabText(idx, base + (" *" if changed else ""))

    def new_empty(self):
        self.new_tab("Untitled", "")

    def close_tab(self, index):
        if self.tabs.count() > 1:
            self.tabs.removeTab(index)

    def _write_console(self, text):
        self.console.appendPlainText(text)

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Lua script", str(SCRIPTS_DIR), "Lua scripts (*.lua *.txt);;All files (*)")
        if not path: return
        try:
            source = Path(path).read_text(encoding="utf-8-sig")
            e = self.new_tab(Path(path).name, source)
            e.setProperty("file_path", path)
            self.statusBar().showMessage("Opened " + path, 5000)
        except Exception as exc:
            QMessageBox.critical(self, "Open failed", str(exc))

    def save_file(self):
        e = self.editor()
        if not e: return
        path = e.property("file_path")
        if not path:
            path, _ = QFileDialog.getSaveFileName(self, "Save Lua script", str(SCRIPTS_DIR / "script.lua"), "Lua scripts (*.lua)")
            if not path: return
            e.setProperty("file_path", path)
        try:
            Path(path).write_text(e.toPlainText(), encoding="utf-8")
            e.document().setModified(False)
            self.statusBar().showMessage("Saved " + path, 5000)
            self._load_script_list()
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))

    def load_url(self):
        url, ok = QInputDialog.getText(self, "Load raw Lua URL", "HTTPS raw.githubusercontent.com URL:")
        if not ok or not url.strip(): return
        url = url.strip()
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
            QMessageBox.warning(self, "URL blocked", "Only HTTPS raw.githubusercontent.com URLs are allowed.")
            return
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "OCEANA-Lua-Workspace/2.0"})
            opener = urllib.request.build_opener(_SafeRedirectHandler())
            with opener.open(req, timeout=12) as response:
                data = response.read(MAX_SCRIPT_BYTES + 1)
            if len(data) > MAX_SCRIPT_BYTES:
                raise ValueError("File exceeds the 1 MB limit.")
            source = data.decode("utf-8-sig")
            self.new_tab("GitHub script", source)
            self._write_console("[OCEANA] Loaded source into editor. Review it before running.")
        except Exception as exc:
            QMessageBox.critical(self, "Download failed", str(exc))

    def run_script(self):
        if self.current_process is not None:
            QMessageBox.information(self, "Already running", "Stop the current script before starting another.")
            return
        e = self.editor()
        if not e:
            return
        source = e.toPlainText()
        fd, path = tempfile.mkstemp(prefix="oceana_", suffix=".lua")
        os.close(fd)
        Path(path).write_text(source, encoding="utf-8")
        self.current_temp = path
        process = QProcess(self)
        if getattr(sys, "frozen", False):
            process.setProgram(sys.executable)
            process.setArguments(["--oceana-runner", path])
            process.setWorkingDirectory(str(SCRIPTS_DIR.parent))
        else:
            runner = str(APP_DIR / "runner.py")
            process.setProgram(sys.executable)
            process.setArguments([runner, path])
            process.setWorkingDirectory(str(APP_DIR))
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(self._read_process_output)
        process.finished.connect(self._process_finished)
        self.current_process = process
        process.start()
        if not process.waitForStarted(3000):
            message = process.errorString()
            self._cleanup_process()
            QMessageBox.critical(self, "Run failed", message)
            return
        self._write_console("[OCEANA] Started standalone Lua runtime.")
        self.statusBar().showMessage("Running • 15 second limit")
        self.timeout_timer = QTimer(self)
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self._timeout_process)
        self.timeout_timer.start(15000)

    def _read_process_output(self):
        if self.current_process is None:
            return
        data = bytes(self.current_process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if data:
            for line in data.rstrip("\n").splitlines():
                self._write_console(line)

    def _process_finished(self, exit_code, exit_status):
        self._read_process_output()
        self._write_console("[OCEANA] Process exited with code " + str(exit_code))
        self._cleanup_process()
        self.statusBar().showMessage("Ready")

    def _timeout_process(self):
        if self.current_process is not None:
            self._write_console("[OCEANA] Execution stopped: 15 second time limit reached.")
            self.stop_script()

    def stop_script(self):
        if self.current_process is not None:
            self.current_process.kill()
            self._write_console("[OCEANA] Stop requested.")
            self._cleanup_process()
            self.statusBar().showMessage("Stopped")

    def _cleanup_process(self):
        if hasattr(self, "timeout_timer"):
            self.timeout_timer.stop()
        process = self.current_process
        self.current_process = None
        if process is not None:
            process.deleteLater()
        if self.current_temp:
            try:
                os.remove(self.current_temp)
            except OSError:
                pass
            self.current_temp = None

    def _load_script_list(self):
        SCRIPTS_DIR.mkdir(exist_ok=True)
        self.script_list.clear()
        for path in sorted(SCRIPTS_DIR.glob("*.lua")):
            self.script_list.addItem(QListWidgetItem(path.name))

    def filter_scripts(self, text):
        for i in range(self.script_list.count()):
            item = self.script_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def open_library_item(self, item):
        path = SCRIPTS_DIR / item.text()
        try:
            self.new_tab(path.name, path.read_text(encoding="utf-8-sig")).setProperty("file_path", str(path))
        except Exception as exc:
            QMessageBox.critical(self, "Library error", str(exc))

    def import_to_library(self):
        path, _ = QFileDialog.getOpenFileName(self, "Add script to library", "", "Lua scripts (*.lua *.txt);;All files (*)")
        if not path: return
        dest = SCRIPTS_DIR / Path(path).name
        if dest.exists():
            QMessageBox.warning(self, "Already exists", "A script with that filename is already in the library.")
            return
        try:
            dest.write_bytes(Path(path).read_bytes())
            self._load_script_list()
        except Exception as exc:
            QMessageBox.critical(self, "Import failed", str(exc))

class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        p = urllib.parse.urlparse(newurl)
        if p.scheme != "https" or p.hostname != ALLOWED_HOST:
            raise urllib.error.HTTPError(newurl, code, "Redirect outside allowed host blocked", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--oceana-runner":
        import runner
        sys.argv = ["runner.py", sys.argv[2]]
        raise SystemExit(runner.main())
    app = QApplication(sys.argv)
    app.setApplicationName("OCEANA EXECUTOR")
    window = Oceana()
    window.show()
    sys.exit(app.exec())
