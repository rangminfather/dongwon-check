"""앱 아이콘(.ico)을 엠블럼으로 그린다(설치 마법사 그림은 make_installer_art.py).

    python packaging/make_assets.py
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PIL import Image  # noqa: E402
from PySide6.QtCore import QRectF, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication, QImage, QPainter  # noqa: E402

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

    print("assets →", OUT)


if __name__ == "__main__":
    main()
