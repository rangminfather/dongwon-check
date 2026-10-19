"""동원 블루 테마 — 색·글꼴·QSS 를 한곳에서 관리한다."""

BLUE_DARK = "#072B66"
BLUE = "#0B3D91"
BLUE_MID = "#1559C2"
SKY = "#2E7BD6"
SKY_LIGHT = "#E8F1FC"
WAVE = "#7FB6F2"
BG = "#F4F6FA"
CARD = "#FFFFFF"
LINE = "#DCE3EE"
TEXT = "#1B2433"
MUTED = "#6B7689"
ORANGE = "#F08C00"

STATUS_COLORS = {
    # 판정: (배경, 글자)
    "일치": ("#E3F4E8", "#1E7B3A"),
    "수량차이": ("#FFF4CC", "#8A6100"),
    "단가차이": ("#FDE4D3", "#B4470F"),
    "동원만": ("#DDEBFB", "#0B3D91"),
    "거래처만": ("#EEE8F8", "#5B3A9E"),
}

FONT = "Malgun Gothic"

def build_qss(arrow_down: str, arrow_up: str) -> str:
    """arrow_*: 화살표 PNG 경로(앱 시작 시 그려서 넘겨준다)."""
    return f"""
* {{ font-family: '{FONT}'; font-size: 10pt; color: {TEXT}; }}
QMainWindow, #root {{ background: {BG}; }}
#card {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 12px; }}
#cardTitle {{ font-size: 11pt; font-weight: 700; color: {BLUE_DARK}; }}
#stepBadge {{ background: {BLUE}; color: white; border-radius: 11px; font-weight: 700; font-size: 9pt; }}
#muted {{ color: {MUTED}; font-size: 9pt; }}
#fileName {{ font-weight: 700; color: {TEXT}; }}

QPushButton {{
    background: white; border: 1px solid {LINE}; border-radius: 8px; padding: 6px 14px; color: {BLUE};
}}
QPushButton:hover {{ background: {SKY_LIGHT}; border-color: {SKY}; }}
QPushButton:disabled {{ color: #A9B2C1; background: #F1F3F7; }}
QPushButton#primary {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {BLUE}, stop:1 {BLUE_MID});
    color: white; border: none; font-size: 11pt; font-weight: 700; padding: 11px 18px; border-radius: 10px;
}}
QPushButton#primary:hover {{ background: {BLUE_MID}; }}
QPushButton#primary:disabled {{ background: #9FB3D6; }}
QPushButton#accent {{ background: {ORANGE}; color: white; border: none; font-weight: 700; padding: 8px 16px; }}
QPushButton#accent:hover {{ background: #D97E00; }}
QPushButton#accent:disabled {{ background: #F3D3A6; color: white; }}
QPushButton#ghost {{ border: none; background: transparent; color: rgba(255,255,255,0.92); padding: 4px 10px; }}
QPushButton#ghost:hover {{ background: rgba(255,255,255,0.15); }}
QPushButton#iconBtn {{ border: none; background: transparent; color: {MUTED}; padding: 2px 6px; font-size: 12pt; }}
QPushButton#iconBtn:hover {{ color: #C62828; }}
QPushButton#filter {{ border-radius: 14px; padding: 4px 12px; font-size: 9pt; }}
QPushButton#filter:checked {{ background: {BLUE}; color: white; border-color: {BLUE}; }}

QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {{
    background: white; border: 1px solid {LINE}; border-radius: 6px; padding: 4px 8px; min-height: 22px;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border; subcontrol-position: top right; width: 20px; border: none; background: transparent;
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border; subcontrol-position: bottom right; width: 20px; border: none; background: transparent;
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url({arrow_up}); width: 9px; height: 9px; }}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url({arrow_down}); width: 9px; height: 9px; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{ image: url({arrow_down}); width: 10px; height: 10px; }}
QComboBox QAbstractItemView {{ border: 1px solid {LINE}; selection-background-color: {SKY_LIGHT}; selection-color: {TEXT}; }}
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus {{ border-color: {SKY}; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 16px; height: 16px; }}

QTableView {{
    background: white; border: 1px solid {LINE}; border-radius: 8px; gridline-color: #EEF1F6;
    selection-background-color: #CFE0FA; selection-color: {TEXT};
}}
QHeaderView::section {{
    background: {BLUE}; color: white; border: none; border-right: 1px solid {BLUE_MID};
    padding: 6px 4px; font-weight: 700; font-size: 9pt;
}}
QTabWidget::pane {{ border: none; }}
QTabBar::tab {{
    background: transparent; color: {MUTED}; padding: 8px 16px; margin-right: 2px;
    border-bottom: 3px solid transparent; font-weight: 600;
}}
QTabBar::tab:selected {{ color: {BLUE}; border-bottom: 3px solid {BLUE}; }}
QTabBar::tab:hover {{ color: {BLUE_MID}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: #C5CFDF; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; }}
QScrollBar::handle:horizontal {{ background: #C5CFDF; border-radius: 5px; min-width: 30px; }}
QToolTip {{ background: {BLUE_DARK}; color: white; border: none; padding: 6px; }}
#updateBar {{ background: #FFF4E0; border-bottom: 1px solid #F3D19C; }}
"""
