"""아이콘(.ico)과 설치 마법사 그림(.bmp)을 앱 엠블럼으로 그린다.

    python packaging/make_assets.py
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PIL import Image  # noqa: E402
from PySide6.QtCore import QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QLinearGradient, QPainter, QPen  # noqa: E402

from dongwon_check import theme  # noqa: E402
from dongwon_check.widgets import paint_emblem  # noqa: E402

OUT = os.path.join(ROOT, "assets")


def render(w, h, draw) -> Image.Image:
    img = QImage(w, h, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    draw(p)
    p.end()
    path = os.path.join(OUT, "_tmp.png")
    img.save(path)
    out = Image.open(path).convert("RGBA")
    out.load()
    os.remove(path)
    return out


def main():
    QGuiApplication(sys.argv)
    os.makedirs(OUT, exist_ok=True)

    big = render(256, 256, lambda p: paint_emblem(p, QRectF(8, 8, 240, 240)))
    big.save(os.path.join(OUT, "app.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    big.save(os.path.join(OUT, "logo.png"))

    def wizard(p: QPainter):
        g = QLinearGradient(0, 0, 0, 314)
        g.setColorAt(0, QColor(theme.BLUE_DARK))
        g.setColorAt(1, QColor(theme.BLUE_MID))
        p.fillRect(0, 0, 164, 314, g)
        p.setPen(QPen(QColor(255, 255, 255, 40), 2))
        for k in range(4):
            y = 230 + k * 16
            p.drawArc(-40 + k * 10, y, 260, 40, 0, 180 * 16)
        paint_emblem(p, QRectF(42, 48, 80, 80), on_dark=True)
        p.setPen(QColor("white"))
        f = QFont(theme.FONT, 13)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(0, 150, 164, 30), Qt.AlignCenter, "동원F&B")
        p.setFont(QFont(theme.FONT, 10))
        p.drawText(QRectF(0, 178, 164, 24), Qt.AlignCenter, "매입대사 점검")

    bg = Image.new("RGB", (164, 314), theme.BLUE)
    wiz = render(164, 314, wizard)
    bg.paste(wiz, (0, 0), wiz)
    bg.save(os.path.join(OUT, "wizard.bmp"))

    small = Image.new("RGB", (55, 55), "white")
    em = render(55, 55, lambda p: paint_emblem(p, QRectF(3, 3, 49, 49)))
    small.paste(em, (0, 0), em)
    small.save(os.path.join(OUT, "wizard-small.bmp"))
    print("assets →", OUT)


if __name__ == "__main__":
    main()
