"""설치 마법사 그림(packaging/art/*.bmp)을 만든다.

한글은 윈도우 글꼴(맑은 고딕)로 Pillow 가 직접 그린다 — Qt offscreen 은 글꼴이 없어 □□로 깨진다.
GitHub 빌드 서버에는 한글 글꼴이 없을 수 있으므로, 결과 bmp 는 저장소에 커밋해 두고 빌드 때 그대로 쓴다.

    python packaging/make_installer_art.py
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402
from PySide6.QtCore import QRectF, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication, QImage, QPainter  # noqa: E402

from dongwon_check import theme  # noqa: E402
from dongwon_check.widgets import paint_emblem  # noqa: E402

OUT = os.path.join(ROOT, "packaging", "art")
FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")


def font(bold: bool, size: int):
    return ImageFont.truetype(os.path.join(FONTS, "malgunbd.ttf" if bold else "malgun.ttf"), size)


def hex_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i: i + 2], 16) for i in (0, 2, 4))


def emblem(size: int, on_dark: bool) -> Image.Image:
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    paint_emblem(p, QRectF(0, 0, size, size), on_dark)
    p.end()
    tmp = os.path.join(OUT, "_e.png")
    img.save(tmp)
    out = Image.open(tmp).convert("RGBA")
    out.load()
    os.remove(tmp)
    return out


def gradient(w, h, top, bottom):
    a, b = hex_rgb(top), hex_rgb(bottom)
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / (h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)))
    return img


def big_panel(W=328, H=628) -> Image.Image:
    """왼쪽 세로 그림(2배 크기로 그리고 줄여 쓴다)."""
    img = gradient(W, H, theme.BLUE_DARK, theme.BLUE_MID).convert("RGBA")

    # 은은한 물결
    waves = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(waves)
    import math
    for k in range(6):
        pts = []
        base = H * 0.70 + k * 26
        for x in range(-10, W + 11, 4):
            pts.append((x, base + math.sin((x / W) * math.pi * 2 + k * 0.7) * (10 + k * 2)))
        d.line(pts, fill=(255, 255, 255, 34 - k * 4), width=3)
    img = Image.alpha_composite(img, waves)

    # 엠블럼 + 그림자
    es = 132
    em = emblem(es, on_dark=True)
    x, y = (W - es) // 2, 96
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([x + 4, y + 10, x + es + 4, y + es + 10], radius=32, fill=(0, 0, 0, 90))
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(10)))
    img.alpha_composite(em, (x, y))

    d = ImageDraw.Draw(img)

    def center(text, top, f, fill):
        w = d.textlength(text, font=f)
        d.text(((W - w) / 2, top), text, font=f, fill=fill)

    center("동원F&B", 274, font(True, 40), "white")
    center("매입대사 점검", 330, font(True, 28), (255, 255, 255, 235))
    d.line([(W / 2 - 22, 384), (W / 2 + 22, 384)], fill=hex_rgb(theme.ORANGE), width=4)
    center("원장 ↔ 거래처 매입자료", 404, font(False, 19), (214, 228, 250))
    center("자동 대사 프로그램", 432, font(False, 19), (214, 228, 250))
    center("일자 · 바코드 · 수량 · 단가 · 금액", H - 46, font(False, 15), (180, 203, 240))
    return img.convert("RGB")


def small_panel(S=110) -> Image.Image:
    img = Image.new("RGBA", (S, S), (255, 255, 255, 255))
    em = emblem(int(S * 0.86), on_dark=False)
    img.alpha_composite(em, ((S - em.width) // 2, (S - em.height) // 2))
    return img.convert("RGB")


def main():
    QGuiApplication(sys.argv)
    os.makedirs(OUT, exist_ok=True)
    big = big_panel()
    # Inno Setup 은 화면 배율(100·125·150·200%)에 맞는 크기를 골라 쓴다.
    for w, h in [(164, 314), (205, 392), (246, 471), (328, 628)]:
        big.resize((w, h), Image.LANCZOS).save(os.path.join(OUT, f"wizard-{w}.bmp"))
    small = small_panel()
    for s in (55, 69, 83, 110):
        small.resize((s, s), Image.LANCZOS).save(os.path.join(OUT, f"wizard-small-{s}.bmp"))
    big.save(os.path.join(OUT, "preview.png"))
    print("installer art →", OUT)


if __name__ == "__main__":
    main()
