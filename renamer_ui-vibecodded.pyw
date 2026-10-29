import math, os, sys, uuid, datetime
from PySide6.QtCore import Qt, QEvent, QUrl, QRectF, QPoint, QPointF, QMimeData
from PySide6.QtGui import (QColor, QPainter, QPainterPath, QPen, QPixmap, QDrag, QFont, QFontMetricsF, QImage, QTextCharFormat,
                           QTextCursor, QTextDocument, QTextFormat, QTextImageFormat)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QLabel, QLineEdit, QPushButton, QToolButton, QFrame,
    QSplitter, QTableWidget, QTableWidgetItem, QHeaderView, QStackedWidget,
    QFileDialog, QMessageBox, QAbstractItemView, QTextEdit, QInputDialog)

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

CATS = {"num": ("Numbering", "#5b8cff"), "time": ("Date & time", "#3ecf8e"),
        "name": ("Old name", "#b07cff")}

# key, label, category, description, parameter hint (None = none), default value
COMPONENTS = [
    ("number", "Number", "num", "Sequential file number (1, 2, 3…). Numbered separately in each folder.", None, ""),
    ("numfrom", "Number from…", "num", "Sequential number starting from the given value.", "start", "1"),
    ("date", "Date", "time", "Today's date, e.g. 2026-10-18.", None, ""),
    ("year", "Year", "time", "Current year.", None, ""),
    ("month", "Month (number)", "time", "Current month number.", None, ""),
    ("wmonth", "Month (name)", "time", "Name of the current month, e.g. October.", None, ""),
    ("day", "Day", "time", "Current day of the month.", None, ""),
    ("hour", "Time", "time", "Current hour and minute, e.g. 14.35.", None, ""),
    ("hoursec", "Time + sec.", "time", "Hour, minute and second, e.g. 14.35.07.", None, ""),
    ("oldname", "Old name", "name", "Inserts the current file name (without extension).", None, ""),
    ("cut", "Remove phrases", "name", "Old name only: removes the given phrases. Separate with semicolons: phrase1;phrase2", "phrase1;phrase2", ""),
    ("replace", "Replace in name", "name", "Old name only: replaces text. Format: old=new", "old=new", ""),
    ("trim", "Trim name", "name", "Old name only: positive numbers cut from the left, negative from the right, e.g. 2;-1", "2;-1", ""),
]
COMP = {c[0]: c for c in COMPONENTS}

QSS = """
* { font-family: 'Segoe UI', 'Inter', sans-serif; font-size: 13px; color: #e6e8ee; }
QMainWindow, QWidget#root { background: #14161c; }
QWidget#panel { background: #1b1e26; border-radius: 12px; }
QLabel#h { color: #8a92a6; font-size: 11px; font-weight: 600; letter-spacing: 1px; }
QLabel#desc { color: #9aa3b8; background: #14161c; border-radius: 8px; padding: 8px; }
QListWidget { background: transparent; border: none; outline: none; }
QListWidget#components::item { padding: 8px 10px; border-radius: 8px; margin: 1px 0; }
QListWidget#components::item:hover { background: #272b36; }
QListWidget#cards::item:selected, QListWidget#cards::item:hover { background: transparent; }
QFrame#card { background: #262a35; border-radius: 10px; border-left: 4px solid #5b8cff; }
QFrame#card[cat="time"] { border-left-color: #3ecf8e; }
QFrame#card[cat="name"] { border-left-color: #b07cff; }
QFrame#card[cat="text"] { border-left-color: #ffb454; }
QLineEdit { background: #14161c; border: 1px solid #323847; border-radius: 6px; padding: 4px 8px; }
QLineEdit:focus { border-color: #6c8cff; }
QPushButton { background: #272b36; border: none; border-radius: 8px; padding: 7px 14px; }
QPushButton:hover { background: #31364a; }
QPushButton#primary { background: #5b7cff; font-weight: 600; padding: 10px 22px; }
QPushButton#primary:hover { background: #7390ff; }
QPushButton#primary:disabled { background: #2a2f3d; color: #6b7285; }
QToolButton { background: transparent; border: none; color: #8a92a6; border-radius: 10px; padding: 2px 6px; }
QToolButton:hover { background: #3a2f35; color: #ff6b7a; }
QTableWidget { background: transparent; border: none; gridline-color: transparent; alternate-background-color: #1f232c; }
QHeaderView { background: transparent; border: none; }
QHeaderView::section { background: transparent; border: none; color: #8a92a6; padding: 6px; font-weight: 600; }
QTableCornerButton::section { background: transparent; border: none; }
QTextEdit#scheme { background: #262a35; border: 1px solid #323847; border-radius: 10px; padding: 6px 12px; font-size: 15px; }
QTextEdit#scheme:focus { border-color: #6c8cff; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 4px 2px; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px 4px; }
QScrollBar::handle:vertical { background: #3a4155; border-radius: 3px; min-height: 36px; }
QScrollBar::handle:horizontal { background: #3a4155; border-radius: 3px; min-width: 36px; }
QScrollBar::handle:hover { background: #5b7cff; }
QScrollBar::handle:pressed { background: #7390ff; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; background: none; border: none; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }
QToolTip { background: #272b36; color: #e6e8ee; border: 1px solid #3a4053; padding: 6px; }
QSplitter::handle { background: transparent; }
"""


def build_name(cards, i, old, now, pre="", suf=""):
    """Builds a new name (without extension) from the list of cards plus text before and after."""
    if not (cards or pre or suf):
        return old
    work, mods = old, False
    for c in cards:
        k, v = c["key"], c["value"]
        try:
            if k == "cut":
                for s in filter(None, v.split(";")):
                    work = work.replace(s, "")
                mods = True
            elif k == "replace" and "=" in v:
                a, b = v.split("=", 1)
                if a:
                    work = work.replace(a, b)
                mods = True
            elif k == "trim":
                for s in filter(None, v.split(";")):
                    n = int(s)
                    work = work[:n] if n < 0 else work[n:]
                mods = True
        except ValueError:
            pass
    parts, used_old = [], False
    for c in cards:
        k, v = c["key"], c["value"]
        if k == "number": parts.append(str(i))
        elif k == "numfrom":
            try: start = int(v)
            except ValueError: start = 1
            parts.append(str(start - 1 + i))
        elif k == "text": parts.append(v)
        elif k == "oldname": parts.append(work); used_old = True
        elif k == "date": parts.append(now.date().isoformat())
        elif k == "year": parts.append(str(now.year))
        elif k == "month": parts.append(str(now.month))
        elif k == "wmonth": parts.append(MONTHS[now.month - 1])
        elif k == "day": parts.append(str(now.day))
        elif k == "hour": parts.append(f"{now.hour}.{now.minute}")
        elif k == "hoursec": parts.append(f"{now.hour}.{now.minute}.{now.second}")
    if mods and not used_old:
        parts.append(work)  # as in the original: a modifier without ?oldname appends the old name
    return pre + "".join(parts) + suf


P_KEY, P_VAL = QTextFormat.UserProperty + 1, QTextFormat.UserProperty + 2


def chip_label(key, val):
    label = COMP[key][1].rstrip("…")
    return f"{label}: {val or '…'}" if COMP[key][4] else label


MIME = "application/x-renamer-chip"
CHIP_H, CLOSE_W = 46, 44


def make_chip(key, val, dpr=1.0):
    """Draws a component as a card: dark background, coloured bar on the left, ✕ on the right.
    The image uses the screen's physical resolution (dpr), so it is not scaled and the edges stay smooth.
    Returns (image, width, height) in logical pixels."""
    font = QFont()
    font.setFamilies(["Segoe UI", "Inter", "Sans Serif"])
    font.setPixelSize(16)
    label, color = chip_label(key, val), QColor(CATS[COMP[key][2]][1])
    tw = int(QFontMetricsF(font).horizontalAdvance(label)) + 12
    w, h, m = tw + 18 + CLOSE_W, CHIP_H, 4  # m = side margin
    W, H = math.ceil((w + 2 * m) * dpr), math.ceil(h * dpr)
    img = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    img.setDevicePixelRatio(dpr)
    img.fill(Qt.transparent)
    p = QPainter(img)  # drawing in logical coordinates
    p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
    p.translate(m, 0)
    p.setFont(font)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 12, 12)
    p.setClipPath(path)
    p.fillPath(path, QColor("#2b303d"))
    p.fillRect(QRectF(0, 0, 5, h), color)
    p.setClipping(False)
    p.setPen(QColor("#3a4155"))
    p.drawPath(path)
    p.setPen(QColor("#e6e8ee"))
    p.drawText(QRectF(18, 0, tw, h), Qt.AlignVCenter | Qt.AlignLeft, label)
    p.setPen(QColor("#3a4155"))  # separator dividing the ✕ zone from the rest of the card
    p.drawLine(QPointF(w - CLOSE_W + 0.5, 11), QPointF(w - CLOSE_W + 0.5, h - 11))
    p.setPen(QPen(QColor("#8a92a6"), 2, Qt.SolidLine, Qt.RoundCap))
    cx, cy, d = w - CLOSE_W / 2, h / 2, 5
    p.drawLine(QPointF(cx - d, cy - d), QPointF(cx + d, cy + d))
    p.drawLine(QPointF(cx - d, cy + d), QPointF(cx + d, cy - d))
    p.end()
    return img, W / dpr, H / dpr


class SchemeEdit(QTextEdit):
    """Single-line text field into which components can be inserted (by clicking or dragging)."""

    def __init__(self, source):
        super().__init__(objectName="scheme")
        self.source = source
        self.setLineWrapMode(QTextEdit.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # horizontal scrollbar when the scheme is wider than the field
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFixedHeight(86)
        self.setAcceptDrops(True)
        self.setPlaceholderText("Type text and drag components in between the characters…")
        self._press = None
        self._drop = None  # position of the insertion marker while dragging
        self.viewport().setMouseTracking(True)

    def _chip_format(self, key, val):
        dpr = self.devicePixelRatioF()
        img, w, h = make_chip(key, val, dpr)
        name = f"chip:{abs(hash((key, val, dpr)))}"
        self.document().addResource(QTextDocument.ImageResource, QUrl(name), img)
        fmt = QTextImageFormat()
        fmt.setName(name)
        fmt.setWidth(w)
        fmt.setHeight(h)
        fmt.setProperty(P_KEY, key)
        fmt.setProperty(P_VAL, val)
        fmt.setVerticalAlignment(QTextCharFormat.AlignMiddle)
        return fmt

    def insert_chip(self, key, value=None, cursor=None):
        if value is None:
            value = COMP[key][5]
            if COMP[key][4] and not value:  # component with a parameter – ask for it
                value, ok = QInputDialog.getText(self, COMP[key][1], COMP[key][3])
                if not ok:
                    return
        c = cursor or self.textCursor()
        c.insertImage(self._chip_format(key, value))
        self.setTextCursor(c)
        self.ensureCursorVisible()
        self.setCurrentCharFormat(QTextCharFormat())  # subsequent text without the component format
        self.setFocus()

    def items(self):
        """Field contents as a list of cards (text = single characters)."""
        doc, out = self.document(), []
        for p in range(doc.characterCount() - 1):
            ch = doc.characterAt(p)
            c = QTextCursor(doc)
            c.setPosition(p + 1)
            fmt = c.charFormat()
            if ch == "\ufffc" and fmt.property(P_KEY):
                out.append({"key": fmt.property(P_KEY), "value": fmt.property(P_VAL) or ""})
            elif ch not in "\u2029\n\ufffc":
                out.append({"key": "text", "value": ch})
        return out

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            return
        super().keyPressEvent(e)

    # --- mouse handling on components: ✕ removes, dragging moves, double-click edits the parameter
    def chip_at(self, pt):
        doc, pos = self.document(), self.cursorForPosition(pt).position()
        for p in (pos, pos - 1):
            if p < 0 or p >= doc.characterCount() - 1 or doc.characterAt(p) != "\ufffc":
                continue
            tc = QTextCursor(doc)
            tc.setPosition(p)
            left = self.cursorRect(tc).left()
            tc.setPosition(p + 1, QTextCursor.KeepAnchor)
            fmt = tc.charFormat()
            if fmt.property(P_KEY) and left <= pt.x() <= left + fmt.toImageFormat().width():
                return p, fmt, left
        return None

    @staticmethod
    def _on_close(pt, hit):
        return pt.x() >= hit[2] + hit[1].toImageFormat().width() - CLOSE_W

    def _select(self, p):
        tc = QTextCursor(self.document())
        tc.setPosition(p)
        tc.setPosition(p + 1, QTextCursor.KeepAnchor)
        return tc

    def mousePressEvent(self, e):
        self._press = None
        if e.button() == Qt.LeftButton:
            pt = e.position().toPoint()
            hit = self.chip_at(pt)
            if hit:
                self._press = (pt, hit)
                return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        pt = e.position().toPoint()
        if self._press:
            if e.buttons() & Qt.LeftButton and \
                    (pt - self._press[0]).manhattanLength() >= QApplication.startDragDistance():
                hit, self._press = self._press[1], None
                self._drag_chip(hit)
            return
        hit = self.chip_at(pt)
        self.viewport().setCursor(Qt.IBeamCursor if not hit else
                                  Qt.PointingHandCursor if self._on_close(pt, hit) else Qt.OpenHandCursor)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._press:
            pt, hit = self._press
            self._press = None
            if self._on_close(pt, hit):
                if self._on_close(e.position().toPoint(), hit):  # ✕ only if pressed and released within it
                    self._select(hit[0]).removeSelectedText()
            elif COMP[hit[1].property(P_KEY)][4]:
                self.edit_chip(hit[0])  # a single click on a card with a parameter edits its value
            else:
                c = QTextCursor(self.document())
                c.setPosition(hit[0] + 1)
                self.setTextCursor(c)
            return
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        if self.chip_at(e.position().toPoint()):
            return self.mousePressEvent(e)  # treat the second click as a regular click
        super().mouseDoubleClickEvent(e)

    def edit_chip(self, p):
        fmt = self._select(p).charFormat()
        key = fmt.property(P_KEY)
        if COMP[key][4]:
            val, ok = QInputDialog.getText(self, COMP[key][1], COMP[key][3], text=fmt.property(P_VAL) or "")
            if ok:
                self._select(p).setCharFormat(self._chip_format(key, val))

    def _drag_chip(self, hit):
        p, fmt, _ = hit
        md = QMimeData()
        md.setData(MIME, str(p).encode())
        img, w, h = make_chip(fmt.property(P_KEY), fmt.property(P_VAL) or "", self.devicePixelRatioF())
        pm = QPixmap.fromImage(img)
        d = QDrag(self)
        d.setMimeData(md)
        d.setPixmap(pm)
        d.setHotSpot(QPoint(int(w / 2), int(h / 2)))
        d.exec(Qt.MoveAction)

    def move_chip(self, src, target):
        if target in (src, src + 1):
            return
        sel = self._select(src)
        fmt = sel.charFormat().toImageFormat()
        c = QTextCursor(self.document())
        c.beginEditBlock()
        sel.removeSelectedText()
        c.setPosition(target - 1 if target > src else target)
        c.insertImage(fmt)
        c.endEditBlock()
        c.setPosition(c.position())
        self.setTextCursor(c)

    # --- dropping: from the component list (new) or from the field itself (move)
    def _ours(self, e):
        return e.source() is self.source or e.mimeData().hasFormat(MIME)

    def set_drop(self, pos):
        self._drop = pos
        self.viewport().update()

    def drop_target(self, pt):
        """Nearest insertion point – also works when the pointer is outside the text (top/bottom/sides)."""
        vp = self.viewport().rect()
        pt = QPoint(min(max(pt.x(), 0), vp.width() - 1), vp.height() // 2)
        return self.cursorForPosition(pt).position()

    def accept_drag(self, e, pt):
        bar, vw = self.horizontalScrollBar(), self.viewport().width()
        if pt.x() < 40:  # scroll at the edges while dragging
            bar.setValue(bar.value() - 25)
        elif pt.x() > vw - 40:
            bar.setValue(bar.value() + 25)
        self.set_drop(self.drop_target(pt))
        e.acceptProposedAction()

    def accept_drop(self, e, pt):
        target = self.drop_target(pt)
        self.set_drop(None)
        md = e.mimeData()
        if md.hasFormat(MIME):
            self.move_chip(int(bytes(md.data(MIME)).decode()), target)
            e.setDropAction(Qt.MoveAction)
        else:
            it = self.source.currentItem()
            if not (it and it.data(Qt.UserRole)):
                return e.ignore()
            c = QTextCursor(self.document())
            c.setPosition(target)
            self.insert_chip(it.data(Qt.UserRole), cursor=c)
            e.setDropAction(Qt.CopyAction)
        e.accept()

    def paintEvent(self, e):
        super().paintEvent(e)
        if self._drop is not None:  # clear insertion-point marker
            tc = QTextCursor(self.document())
            tc.setPosition(self._drop)
            x = self.cursorRect(tc).left()
            p = QPainter(self.viewport())
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#6c8cff"))
            h = CHIP_H + 4
            p.drawRoundedRect(QRectF(x - 1, self.viewport().height() / 2 - h / 2, 3, h), 1.5, 1.5)

    def wheelEvent(self, e):  # mouse wheel scrolls horizontally
        bar = self.horizontalScrollBar()
        bar.setValue(bar.value() - (e.angleDelta().y() or e.angleDelta().x()))
        e.accept()

    def dragEnterEvent(self, e):
        if self._ours(e):
            self.accept_drag(e, e.position().toPoint())
        elif e.mimeData().hasUrls():
            e.ignore()  # files from the system are handled by the main window
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if self._ours(e):
            self.accept_drag(e, e.position().toPoint())
        elif e.mimeData().hasUrls():
            e.ignore()
        else:
            super().dragMoveEvent(e)

    def dragLeaveEvent(self, e):
        self.set_drop(None)
        super().dragLeaveEvent(e)

    def dropEvent(self, e):
        if self._ours(e):
            self.accept_drop(e, e.position().toPoint())
        elif e.mimeData().hasUrls():
            e.ignore()
        else:
            super().dropEvent(e)


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Renamer")
        self.setAcceptDrops(True)
        self.files, self.plan = [], []

        root = QWidget(objectName="root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(12)
        split = QSplitter(Qt.Horizontal)
        outer.addWidget(split, 1)

        # --- left panel: components
        left = QWidget(objectName="panel")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(14, 14, 14, 14)
        ll.addWidget(QLabel("COMPONENTS", objectName="h"))
        self.comp_list = QListWidget(objectName="components")
        self.comp_list.setDragEnabled(True)
        self.comp_list.setDragDropMode(QAbstractItemView.DragOnly)
        self.comp_list.setMouseTracking(True)
        self.comp_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        for cat, (title, color) in CATS.items():
            h = QListWidgetItem(title.upper())
            h.setFlags(Qt.NoItemFlags)
            h.setForeground(QColor("#6b7285"))
            self.comp_list.addItem(h)
            for key, label, c, desc, *_ in COMPONENTS:
                if c == cat:
                    it = QListWidgetItem("●  " + label)
                    it.setForeground(QColor(color))
                    it.setData(Qt.UserRole, key)
                    it.setToolTip(desc)
                    self.comp_list.addItem(it)
        self.comp_list.itemEntered.connect(lambda it: self.desc.setText(
            COMP[it.data(Qt.UserRole)][3] if it.data(Qt.UserRole) else ""))
        self.comp_list.itemClicked.connect(
            lambda it: it.data(Qt.UserRole) and self.edit.insert_chip(it.data(Qt.UserRole)))
        ll.addWidget(self.comp_list, 1)
        self.desc = QLabel("Hover over a component to see its description.", objectName="desc")
        self.desc.setWordWrap(True)
        self.desc.setMinimumHeight(70)
        self.desc.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        ll.addWidget(self.desc)
        split.addWidget(left)

        # --- right panel: preview
        right = QWidget(objectName="panel")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(14, 14, 14, 14)
        top = QHBoxLayout()
        top.addWidget(QLabel("PREVIEW", objectName="h"))
        self.count = QLabel("0 files", objectName="h")
        top.addWidget(self.count)
        top.addStretch()
        self.ext = QLineEdit()
        self.ext.setPlaceholderText("Extension filter, e.g. .jpg,.png")
        self.ext.setFixedWidth(200)
        self.ext.textChanged.connect(self.refresh)
        top.addWidget(self.ext)
        for text, fn in (("Files…", self.pick_files), ("Folder…", self.pick_dir), ("Clear", self.clear_files)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            top.addWidget(b)
        rl.addLayout(top)
        self.stack = QStackedWidget()
        hint = QLabel("Drag files or a folder here\nor use the buttons above")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color:#6b7285; font-size:15px;")
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Current name", "New name"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.stack.addWidget(hint)
        self.stack.addWidget(self.table)
        rl.addWidget(self.stack, 1)
        split.addWidget(right)
        split.setSizes([270, 800])
        split.setStretchFactor(1, 1)

        # --- bottom bar: cards
        self.bottom = bottom = QWidget(objectName="panel")
        bottom.setAcceptDrops(True)  # the whole bottom panel is a drop zone
        bottom.installEventFilter(self)
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(14, 12, 14, 12)
        head = QHBoxLayout()
        head.addWidget(QLabel("NAME SCHEME  ·  type text and drag components in between the characters", objectName="h"))
        head.addStretch()
        self.go = QPushButton("Rename", objectName="primary")
        self.go.clicked.connect(self.do_rename)
        head.addWidget(self.go)
        bl.addLayout(head)
        self.edit = SchemeEdit(self.comp_list)
        self.edit.insert_chip("oldname")  # default: old name
        self.edit.textChanged.connect(self.refresh)
        bl.addWidget(self.edit)
        outer.addWidget(bottom)
        self.refresh()

    def eventFilter(self, obj, ev):
        if obj is self.bottom and ev.type() in (QEvent.DragEnter, QEvent.DragMove, QEvent.DragLeave, QEvent.Drop):
            if ev.type() == QEvent.DragLeave:
                self.edit.set_drop(None)
            elif self.edit._ours(ev):
                pt = self.edit.viewport().mapFrom(self.bottom, ev.position().toPoint())
                if ev.type() == QEvent.Drop:
                    self.edit.accept_drop(ev, pt)
                else:
                    self.edit.accept_drag(ev, pt)
                return True
        return super().eventFilter(obj, ev)

    # --- files
    def add_paths(self, paths):
        for p in paths:
            found = [os.path.join(p, f) for f in sorted(os.listdir(p))] if os.path.isdir(p) else [p]
            for f in found:
                if os.path.isfile(f) and f not in self.files:
                    self.files.append(f)
        self.refresh()

    def pick_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select files")
        self.add_paths(paths)

    def pick_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select folder")
        if d:
            self.add_paths([d])

    def clear_files(self):
        self.files = []
        self.refresh()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            self.add_paths([u.toLocalFile() for u in e.mimeData().urls()])

    # --- preview
    def refresh(self, *_):
        exts = tuple(x if x.startswith(".") else "." + x
                     for x in (s.strip().lower() for s in self.ext.text().split(",")) if x)
        now, counters, self.plan = datetime.datetime.now(), {}, []
        cards = self.edit.items()
        for f in self.files:
            if exts and not f.lower().endswith(exts):
                continue
            d = os.path.dirname(f)
            counters[d] = counters.get(d, 0) + 1
            stem, e = os.path.splitext(os.path.basename(f))
            self.plan.append((f, os.path.join(d, build_name(cards, counters[d], stem, now) + e)))
        targets = [os.path.normcase(dst) for _, dst in self.plan]
        sources = {os.path.normcase(s) for s, _ in self.plan}
        bad = False
        self.table.setRowCount(len(self.plan))
        for r, (src, dst) in enumerate(self.plan):
            nd = os.path.normcase(dst)
            err = ("Duplicate name in this batch" if targets.count(nd) > 1 else
                   "A file with this name already exists" if os.path.exists(dst) and nd not in sources else "")
            bad |= bool(err)
            a = QTableWidgetItem(os.path.basename(src))
            b = QTableWidgetItem(("⚠ " if err else "→ ") + os.path.basename(dst))
            a.setToolTip(src)
            b.setToolTip(err or dst)
            if err:
                b.setForeground(QColor("#ff6b7a"))
            elif src == dst:
                b.setForeground(QColor("#6b7285"))
            else:
                b.setForeground(QColor("#7ee2a8"))
            self.table.setItem(r, 0, a)
            self.table.setItem(r, 1, b)
        self.stack.setCurrentIndex(1 if self.plan else 0)
        self.count.setText(f"{len(self.plan)} file" + ("" if len(self.plan) == 1 else "s"))
        self.go.setEnabled(bool(self.plan) and not bad and any(s != d for s, d in self.plan))

    def do_rename(self):
        plan = [(s, d) for s, d in self.plan if s != d]
        try:
            tmp = []
            for s, d in plan:  # two-step, to avoid name collisions when swapping
                t = s + f".tmp_{uuid.uuid4().hex}"
                os.rename(s, t)
                tmp.append((t, d))
            for t, d in tmp:
                os.rename(t, d)
        except OSError as ex:
            QMessageBox.critical(self, "Error", str(ex))
            return
        self.files = []
        self.refresh()
        QMessageBox.information(self, "Done", f"Files renamed: {len(plan)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    w = Main()
    w.resize(1150, 720)
    w.show()
    sys.exit(app.exec())
