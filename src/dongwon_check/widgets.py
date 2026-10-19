"""화면 부품 — 엠블럼, 파일 끌어놓기 영역, KPI 카드, 결과 표 모델."""

from __future__ import annotations

import datetime as dt
import os

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPointF, QRectF, QSortFilterProxyModel, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from . import theme
from .engine import ResultRow

EXCEL_EXT = (".xlsx", ".xlsm", ".xls")


def paint_emblem(p: QPainter, rect: QRectF, on_dark: bool = False):
    """앱 엠블럼: 파란 타일 + 흰 체크 + 물결(바다). 아이콘 생성에도 같은 그림을 쓴다."""
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    s = min(rect.width(), rect.height())
    r = QRectF(rect.x(), rect.y(), s, s)
    g = QLinearGradient(r.topLeft(), r.bottomRight())
    if on_dark:
        g.setColorAt(0, QColor("#FFFFFF"))
        g.setColorAt(1, QColor("#DCE9FB"))
    else:
        g.setColorAt(0, QColor(theme.BLUE))
        g.setColorAt(1, QColor(theme.SKY))
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(g))
    p.drawRoundedRect(r, s * 0.24, s * 0.24)

    ink = QColor(theme.BLUE) if on_dark else QColor("white")
    wave = QColor(theme.SKY) if on_dark else QColor(theme.WAVE)
    # 물결
    path = QPainterPath()
    y = r.y() + s * 0.74
    path.moveTo(r.x() + s * 0.16, y)
    path.cubicTo(r.x() + s * 0.33, y - s * 0.09, r.x() + s * 0.42, y + s * 0.09, r.x() + s * 0.58, y)
    path.cubicTo(r.x() + s * 0.70, y - s * 0.07, r.x() + s * 0.78, y + s * 0.05, r.x() + s * 0.86, y - s * 0.01)
    p.setPen(QPen(wave, s * 0.075, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawPath(path)
    # 체크
    p.setPen(QPen(ink, s * 0.11, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawPolyline([
        QPointF(r.x() + s * 0.25, r.y() + s * 0.43),
        QPointF(r.x() + s * 0.43, r.y() + s * 0.60),
        QPointF(r.x() + s * 0.76, r.y() + s * 0.24),
    ])
    p.restore()


class Emblem(QWidget):
    def __init__(self, size: int = 40, on_dark: bool = False, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.on_dark = on_dark

    def paintEvent(self, _):
        p = QPainter(self)
        paint_emblem(p, QRectF(self.rect()), self.on_dark)


class HeaderBar(QWidget):
    """상단 동원 블루 띠."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(76)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        g = QLinearGradient(0, 0, self.width(), 0)
        g.setColorAt(0, QColor(theme.BLUE_DARK))
        g.setColorAt(0.6, QColor(theme.BLUE))
        g.setColorAt(1, QColor(theme.BLUE_MID))
        p.fillRect(self.rect(), g)
        # 오른쪽 장식 물결
        p.setPen(QPen(QColor(255, 255, 255, 28), 2))
        w, h = self.width(), self.height()
        for k in range(3):
            path = QPainterPath()
            y = h * (0.45 + k * 0.18)
            path.moveTo(w * 0.55, y)
            path.cubicTo(w * 0.70, y - 18, w * 0.80, y + 18, w, y - 6)
            p.drawPath(path)


class Card(QFrame):
    def __init__(self, title: str = "", step: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(16, 14, 16, 16)
        self.body.setSpacing(10)
        if title:
            row = QHBoxLayout()
            row.setSpacing(8)
            if step:
                badge = QLabel(step)
                badge.setObjectName("stepBadge")
                badge.setFixedSize(22, 22)
                badge.setAlignment(Qt.AlignCenter)
                row.addWidget(badge)
            t = QLabel(title)
            t.setObjectName("cardTitle")
            row.addWidget(t)
            row.addStretch()
            self.header = row
            self.body.addLayout(row)


class DropZone(QFrame):
    """엑셀 파일을 끌어놓거나 눌러서 고르는 영역."""

    files_dropped = Signal(list)
    clicked = Signal()

    def __init__(self, text: str, sub: str, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(84)
        self._hover = False
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(2)
        self.title = QLabel(text)
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet(f"color:{theme.BLUE}; font-weight:700; background:transparent;")
        self.sub = QLabel(sub)
        self.sub.setAlignment(Qt.AlignCenter)
        self.sub.setStyleSheet(f"color:{theme.MUTED}; font-size:9pt; background:transparent;")
        lay.addWidget(self.title)
        lay.addWidget(self.sub)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setBrush(QColor(theme.SKY_LIGHT if self._hover else "#F8FAFE"))
        pen = QPen(QColor(theme.SKY if self._hover else "#B9C8E0"), 1.5, Qt.DashLine)
        p.setPen(pen)
        p.drawRoundedRect(r, 10, 10)

    def _set_hover(self, v):
        self._hover = v
        self.update()

    def enterEvent(self, e):
        self._set_hover(True)

    def leaveEvent(self, e):
        self._set_hover(False)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._set_hover(True)

    def dragLeaveEvent(self, e):
        self._set_hover(False)

    def dropEvent(self, e):
        self._set_hover(False)
        paths = [u.toLocalFile() for u in e.mimeData().urls()]
        paths = [p for p in paths if p.lower().endswith(EXCEL_EXT) and not os.path.basename(p).startswith("~$")]
        if paths:
            self.files_dropped.emit(paths)


class Kpi(QFrame):
    """숫자 하나를 크게 보여주는 카드."""

    def __init__(self, label: str, color: str = theme.BLUE, bg: str = "white", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(f"#card {{ background:{bg}; border:1px solid {theme.LINE}; border-radius:12px; }}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(0)
        self.label = QLabel(label)
        self.label.setStyleSheet(f"color:{color}; font-size:9pt; font-weight:600; background:transparent;")
        self.value = QLabel("–")
        self.value.setStyleSheet(f"color:{color}; font-size:18pt; font-weight:800; background:transparent;")
        self.sub = QLabel("")
        self.sub.setStyleSheet(f"color:{theme.MUTED}; font-size:8pt; background:transparent;")
        lay.addWidget(self.label)
        lay.addWidget(self.value)
        lay.addWidget(self.sub)

    def set(self, value: str, sub: str = ""):
        self.value.setText(value)
        self.sub.setText(sub)


# ---------------------------------------------------------------------------
# 결과 표
# ---------------------------------------------------------------------------

COLUMNS = ["일자", "바코드", "상품명", "동원 수량", "동원 단가", "동원 금액", "거래처 수량", "거래처 단가",
           "거래처 금액", "수량차", "금액차", "판정", "거래처 일자", "메모"]
NUMERIC = {3, 4, 5, 6, 7, 8, 9, 10}


def _fmt(v, digits=0):
    if v is None:
        return ""
    if digits:
        return f"{v:,.{digits}f}"
    return f"{v:,.0f}" if abs(v - round(v)) < 1e-9 else f"{v:,.2f}"


class ResultModel(QAbstractTableModel):
    def __init__(self, rows: list[ResultRow] | None = None, parent=None):
        super().__init__(parent)
        self.rows = rows or []
        self._bold = QFont(theme.FONT)
        self._bold.setBold(True)

    def set_rows(self, rows: list[ResultRow]):
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return COLUMNS[section]
        return None

    def _value(self, r: ResultRow, c: int):
        return [
            r.date, r.barcode, r.name, r.l_qty, r.l_unit, r.l_amt, r.v_qty, r.v_unit, r.v_amt,
            r.qty_diff, r.amt_diff, r.status, r.v_date, r.memo,
        ][c]

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        r = self.rows[index.row()]
        c = index.column()
        v = self._value(r, c)
        if role == Qt.DisplayRole:
            if isinstance(v, dt.date):
                return v.strftime("%Y-%m-%d")
            if c == 0 and v is None:
                return "기간합계"
            if c in NUMERIC:
                if c in (9, 10) and not v:
                    return "–"
                if c in (4, 7) and v is not None and abs(v - round(v)) > 1e-9:
                    return _fmt(v, 1)
                return _fmt(v)
            return v
        if role == Qt.UserRole:  # 정렬용 원값
            if isinstance(v, dt.date):
                return v.toordinal()
            return v if v is not None else ""
        if role == Qt.TextAlignmentRole:
            if c in NUMERIC:
                return int(Qt.AlignRight | Qt.AlignVCenter)
            if c in (0, 11, 12):
                return int(Qt.AlignCenter)
            return int(Qt.AlignLeft | Qt.AlignVCenter)
        if role == Qt.BackgroundRole:
            if r.status != "일치":
                return QColor(theme.STATUS_COLORS[r.status][0])
        if role == Qt.ForegroundRole:
            if c == 11:
                return QColor(theme.STATUS_COLORS[r.status][1])
            if c in (9, 10) and isinstance(v, (int, float)) and v < -1e-9:
                return QColor("#C62828")
        if role == Qt.FontRole and (c == 11 or (r.status == "수량차이" and c in (3, 6, 9))
                                    or (r.status == "단가차이" and c in (4, 7, 10))):
            return self._bold
        if role == Qt.ToolTipRole:
            parts = []
            if r.l_rows:
                parts.append(f"동원 원본행: {', '.join(map(str, r.l_rows))}")
            if r.v_rows:
                parts.append(f"거래처 원본행: {', '.join(map(str, r.v_rows))}")
            return "\n".join(parts) or None
        return None


class ResultFilter(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.status: str | None = None
        self.text = ""
        self.setSortRole(Qt.UserRole)

    def set_status(self, s: str | None):
        self.status = s
        self.invalidateFilter()

    def set_text(self, t: str):
        self.text = t.strip().lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        r: ResultRow = self.sourceModel().rows[source_row]
        if self.status and r.status != self.status:
            return False
        if self.text and self.text not in f"{r.barcode} {r.name} {r.memo}".lower():
            return False
        return True

    def lessThan(self, left, right):
        a, b = left.data(Qt.UserRole), right.data(Qt.UserRole)
        try:
            return a < b
        except TypeError:
            return str(a) < str(b)
