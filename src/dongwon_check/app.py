"""앱 시작점."""

from __future__ import annotations

import os
import sys
import tempfile

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap, QPolygonF
from PySide6.QtWidgets import QApplication

from . import theme
from .main_window import MainWindow
from .version import APP_NAME_EN, ORG_NAME, __version__
from .widgets import paint_emblem


def emblem_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        paint_emblem(p, QRectF(0, 0, size, size))
        p.end()
        icon.addPixmap(pm)
    return icon


def arrow_images() -> tuple[str, str]:
    """QSS 에 쓸 위/아래 화살표 PNG 를 임시 폴더에 그려 둔다."""
    folder = os.path.join(tempfile.gettempdir(), "DongwonCheck")
    os.makedirs(folder, exist_ok=True)
    out = []
    for name, pts in (("down", [(2, 6), (14, 6), (8, 12)]), ("up", [(2, 11), (14, 11), (8, 5)])):
        pm = QPixmap(16, 16)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(theme.MUTED))
        p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in pts]))
        p.end()
        path = os.path.join(folder, f"arrow-{name}.png")
        pm.save(path)
        out.append(path.replace("\\", "/"))
    return out[0], out[1]


def main() -> int:
    if sys.platform == "win32":
        try:  # 작업 표시줄에 파이썬 아이콘 대신 앱 아이콘이 보이도록
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"DongwonFNB.{APP_NAME_EN}.{__version__}")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME_EN)
    app.setOrganizationName(ORG_NAME)
    app.setApplicationVersion(__version__)
    app.setStyle("Fusion")
    app.setFont(QFont(theme.FONT, 10))
    app.setStyleSheet(theme.build_qss(*arrow_images()))
    icon = emblem_icon()
    app.setWindowIcon(icon)
    win = MainWindow(icon)
    win.show()
    return app.exec()
