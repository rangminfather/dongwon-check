"""메인 화면."""

from __future__ import annotations

import datetime as dt
import os
import threading
import traceback
from dataclasses import dataclass

from PySide6.QtCore import QObject, QSettings, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFrame,
    QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressDialog, QPushButton,
    QRadioButton, QScrollArea, QSizePolicy, QSpinBox, QSplitter, QTableView, QTabWidget, QVBoxLayout, QWidget,
)

from . import engine as E
from . import exporter, theme, updater
from .version import APP_NAME, ORG_NAME, __version__
from .widgets import Card, DropZone, Emblem, HeaderBar, Kpi, ResultFilter, ResultModel

FILE_FILTER = "엑셀 파일 (*.xlsx *.xlsm *.xls)"


@dataclass
class VendorItem:
    path: str
    label: str
    candidates: list[dict]
    sheet: str
    parsed: E.ParseResult | None = None
    customer: str = "auto"  # "auto" | "" (원장 전체) | 판매처명
    error: str = ""
    aff: E.Affiliation | None = None


def busy(fn):
    """오래 걸릴 수 있는 작업 동안 모래시계 커서."""

    def wrapper(self, *a, **kw):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            return fn(self, *a, **kw)
        finally:
            QApplication.restoreOverrideCursor()

    return wrapper


class _Bridge(QObject):
    update_found = Signal(object)
    update_failed = Signal(str)
    progress = Signal(int, int)
    downloaded = Signal(str)
    download_failed = Signal(str)


# ---------------------------------------------------------------------------
# 거래처 파일 한 줄
# ---------------------------------------------------------------------------


class VendorRow(QFrame):
    removed = Signal(object)
    changed = Signal(object)

    def __init__(self, item: VendorItem, customers: list[str], parent=None):
        super().__init__(parent)
        self.item = item
        self.setStyleSheet(f"VendorRow {{ background:#F8FAFE; border:1px solid {theme.LINE}; border-radius:10px; }}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 8, 10)
        lay.setSpacing(6)

        top = QHBoxLayout()
        name = QLabel(os.path.basename(item.path))
        name.setObjectName("fileName")
        name.setToolTip(item.path)
        top.addWidget(name, 1)
        rm = QPushButton("✕")
        rm.setObjectName("iconBtn")
        rm.setToolTip("목록에서 빼기")
        rm.setCursor(Qt.PointingHandCursor)
        rm.clicked.connect(lambda: self.removed.emit(self.item))
        top.addWidget(rm)
        lay.addLayout(top)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)
        grid.addWidget(self._muted("시트"), 0, 0)
        self.sheet = QComboBox()
        self.sheet.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.sheet.setMinimumContentsLength(12)
        for c in item.candidates:
            self.sheet.addItem(f"{c['sheet']}  ({c['count']:,}행)", c["sheet"])
        self.sheet.setCurrentIndex(max(0, self.sheet.findData(item.sheet)))
        self.sheet.currentIndexChanged.connect(self._on_sheet)
        grid.addWidget(self.sheet, 0, 1)
        grid.addWidget(self._muted("원장 판매처"), 1, 0)
        self.customer = QComboBox()
        self.customer.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.customer.setMinimumContentsLength(12)
        self.customer.currentIndexChanged.connect(self._on_customer)
        grid.addWidget(self.customer, 1, 1)
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)

        self.info = QLabel()
        self.info.setObjectName("muted")
        self.info.setWordWrap(True)
        lay.addWidget(self.info)
        self.set_customers(customers)
        self.refresh()
        self.setMinimumHeight(self.sizeHint().height())  # 목록이 길어져도 줄이 눌려 찌그러지지 않게

    @staticmethod
    def _muted(t):
        lb = QLabel(t)
        lb.setObjectName("muted")
        return lb

    def set_customers(self, customers: list[str], suggested: str | None = None):
        self.customer.blockSignals(True)
        self.customer.clear()
        self.customer.addItem(f"자동 선택{f' (추천: {suggested})' if suggested else ''}", "auto")
        self.customer.addItem("원장 전체", "")
        for c in customers:
            self.customer.addItem(c, c)
        self.customer.setCurrentIndex(max(0, self.customer.findData(self.item.customer)))
        self.customer.setEnabled(len(customers) > 1)
        self.customer.blockSignals(False)

    def refresh(self):
        it = self.item
        if it.error:
            self.info.setText(f"<span style='color:#C62828'>⚠ {it.error}</span>")
            return
        p = it.parsed
        if not p:
            self.info.setText("")
            return
        dates = [r.date for r in p.records if r.date]
        span = f" · {min(dates):%m/%d}~{max(dates):%m/%d}" if dates else " · 날짜 없음(기간 합계)"
        aff = it.aff or E.Affiliation()
        supplier = aff.supplier or E.supplier_of(p)
        who = []
        if aff.store:
            who.append(f"🏪 <b style='color:{theme.BLUE}'>{aff.store}</b> <span style='color:#98A2B3'>({aff.store_source})</span>")
        if supplier:
            who.append(f"공급처 {supplier}")
        head = (" · ".join(who) + "<br>") if who else ""
        self.info.setText(head + f"{len(p.records):,}행 인식{span}<br>"
                          + " · ".join(p.notes[1:] or [p.notes[0].split('·')[-1].strip()]))

    def _on_sheet(self):
        self.item.sheet = self.sheet.currentData()
        self.changed.emit(self.item)

    def _on_customer(self):
        self.item.customer = self.customer.currentData()
        self.changed.emit(self.item)


# ---------------------------------------------------------------------------
# 결과 패널(탭 하나)
# ---------------------------------------------------------------------------


class ResultPanel(QWidget):
    def __init__(self, res: E.CompareResult, parent=None):
        super().__init__(parent)
        self.res = res
        s = res.summary
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(10)

        aff = res.affiliation
        if aff.store or aff.supplier:
            who = QLabel(
                (f"🏪 거래처 소속: <b>{aff.store}</b> <span style='color:#6B7689'>({aff.store_source})</span>" if aff.store
                 else "🏪 거래처 소속: <span style='color:#6B7689'>감지 안 됨</span>")
                + (f"  ·  공급처 {aff.supplier}" if aff.supplier else "")
                + f"  ·  원장 판매처 <b>{res.customer or (res.ledger_rows_used[0].customer if res.ledger_rows_used else '-')}</b>")
            who.setStyleSheet(f"color:{theme.TEXT};")
            who.setWordWrap(True)
            who.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            lay.addWidget(who)

        if res.warning:
            warn = QLabel(f"⚠  {res.warning}")
            warn.setWordWrap(True)
            warn.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)  # 긴 문장이 화면을 밀어내지 않게
            warn.setStyleSheet("background:#FFF1F0; color:#A8071A; border:1px solid #FFA39E; border-radius:10px;"
                               "padding:10px 14px; font-weight:600;")
            lay.addWidget(warn)

        kpis = QHBoxLayout()
        kpis.setSpacing(10)
        rate = Kpi("일치율", theme.BLUE, theme.SKY_LIGHT)
        rate.set(f"{s.match_rate * 100:.1f}%", f"총 {s.total:,}건 중 {s.counts['일치']:,}건")
        kpis.addWidget(rate)
        for title, lv, vv in (("총수량", s.l_qty, s.v_qty), ("공급가 금액", s.l_amt, s.v_amt)):
            k = Kpi(f"{title} 차이 (동원−거래처)", "#C62828" if abs(lv - vv) > 1 else "#1E7B3A")
            k.set(f"{lv - vv:+,.0f}", f"동원 {lv:,.0f} · 거래처 {vv:,.0f}")
            kpis.addWidget(k)
        lay.addLayout(kpis)

        bar = QHBoxLayout()
        bar.setSpacing(6)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        for st, label in [(None, "전체"), *[(x, x) for x in E.STATUSES]]:
            n = s.total if st is None else s.counts[st]
            b = QPushButton(f"{label}  {n:,}")
            b.setObjectName("filter")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            if st:
                bg, fg = theme.STATUS_COLORS[st]
                b.setStyleSheet(
                    f"QPushButton#filter {{ background:{bg}; color:{fg}; border:1px solid {bg}; }}"
                    f"QPushButton#filter:checked {{ background:{fg}; color:white; border-color:{fg}; }}"
                )
            b.clicked.connect(lambda _=False, st=st: self.proxy.set_status(st))
            self.group.addButton(b)
            bar.addWidget(b)
            if st is None:
                b.setChecked(True)
        bar.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 바코드·상품명 검색")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(220)
        bar.addWidget(self.search)
        lay.addLayout(bar)

        self.model = ResultModel(res.rows)
        self.proxy = ResultFilter()
        self.proxy.setSourceModel(self.model)
        self.search.textChanged.connect(self.proxy.set_text)
        tv = QTableView()
        tv.setModel(self.proxy)
        tv.setSortingEnabled(True)
        tv.sortByColumn(0, Qt.AscendingOrder)
        tv.setSelectionBehavior(QAbstractItemView.SelectRows)
        tv.setAlternatingRowColors(False)
        tv.verticalHeader().setVisible(False)
        tv.verticalHeader().setDefaultSectionSize(26)
        h = tv.horizontalHeader()
        h.setHighlightSections(False)
        for i, w in enumerate([86, 116, 250, 70, 80, 96, 76, 80, 96, 64, 86, 74, 86, 200]):
            tv.setColumnWidth(i, w)
        h.setSectionResizeMode(13, QHeaderView.Stretch)
        lay.addWidget(tv, 1)
        self.table = tv

        note = QLabel(" · ".join(res.notes))
        note.setObjectName("muted")
        note.setWordWrap(True)
        note.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        lay.addWidget(note)


# ---------------------------------------------------------------------------
# 메인 창
# ---------------------------------------------------------------------------


class MainWindow(QMainWindow):
    def __init__(self, icon: QIcon | None = None):
        super().__init__()
        self.settings = QSettings("DongwonFNB", "DongwonCheck")
        self.setWindowTitle(f"{ORG_NAME} 매입대사 점검  v{__version__}")
        if icon:
            self.setWindowIcon(icon)
        self.resize(1360, 860)
        self.setMinimumSize(1080, 680)

        self.ledger: E.ParseResult | None = None
        self.ledger_path = ""
        self.vendors: list[VendorItem] = []
        self.results: list[E.CompareResult] = []
        self.bridge = _Bridge()
        self.bridge.update_found.connect(self._on_update_found)
        self.bridge.update_failed.connect(self._on_update_failed)
        self._manual_check = False
        self._release = None

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_header())
        outer.addWidget(self._build_update_bar())

        split = QSplitter(Qt.Horizontal)
        split.setHandleWidth(1)
        split.addWidget(self._build_left())
        split.addWidget(self._build_right())
        split.setStretchFactor(1, 1)
        split.setSizes([420, 940])
        outer.addWidget(split, 1)

        self._restore()
        QTimer.singleShot(1500, lambda: self.check_update(manual=False))

    # ----- 화면 구성 -------------------------------------------------------

    def _build_header(self):
        bar = HeaderBar()
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(22, 0, 18, 0)
        lay.setSpacing(14)
        lay.addWidget(Emblem(44, on_dark=True))
        titles = QVBoxLayout()
        titles.setSpacing(0)
        t = QLabel(f"{ORG_NAME}  <span style='font-weight:400'>매입대사 점검</span>")
        t.setStyleSheet("color:white; font-size:17pt; font-weight:800; background:transparent;")
        s = QLabel("동원 원장 ↔ 거래처 매입자료 자동 비교 · 일자 / 바코드 / 수량 / 단가 / 금액")
        s.setStyleSheet("color:rgba(255,255,255,0.78); font-size:9pt; background:transparent;")
        titles.addWidget(t)
        titles.addWidget(s)
        lay.addLayout(titles)
        lay.addStretch()
        self.branch_chip = QLabel("")
        self.branch_chip.setStyleSheet(
            "color:white; background:rgba(255,255,255,0.16); border-radius:12px; padding:4px 12px; font-weight:700;")
        self.branch_chip.hide()
        lay.addWidget(self.branch_chip, 0, Qt.AlignVCenter)
        ver = QLabel(f"v{__version__}")
        ver.setStyleSheet("color:rgba(255,255,255,0.7); background:transparent;")
        lay.addWidget(ver)
        upd = QPushButton("업데이트 확인")
        upd.setObjectName("ghost")
        upd.setCursor(Qt.PointingHandCursor)
        upd.clicked.connect(lambda: self.check_update(manual=True))
        lay.addWidget(upd)
        hlp = QPushButton("도움말")
        hlp.setObjectName("ghost")
        hlp.setCursor(Qt.PointingHandCursor)
        hlp.clicked.connect(self.show_help)
        lay.addWidget(hlp)
        return bar

    def _build_update_bar(self):
        self.update_bar = QFrame()
        self.update_bar.setObjectName("updateBar")
        lay = QHBoxLayout(self.update_bar)
        lay.setContentsMargins(22, 8, 18, 8)
        self.update_label = QLabel()
        lay.addWidget(self.update_label, 1)
        go = QPushButton("지금 업데이트")
        go.setObjectName("accent")
        go.clicked.connect(self.install_update)
        later = QPushButton("나중에")
        later.clicked.connect(self.update_bar.hide)
        lay.addWidget(go)
        lay.addWidget(later)
        self.update_bar.hide()
        return self.update_bar

    def _build_left(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(380)
        scroll.setMaximumWidth(520)
        w = QWidget()
        w.setObjectName("root")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(18, 18, 10, 18)
        lay.setSpacing(14)

        c1 = Card("동원 원장", "1")
        self.ledger_zone = DropZone("원장 파일을 끌어놓거나 클릭", "동원 원장 엑셀 (납품요청일·바코드·총 수량·공급가)")
        self.ledger_zone.clicked.connect(self.pick_ledger)
        self.ledger_zone.files_dropped.connect(lambda ps: self.load_ledger(ps[0]))
        c1.body.addWidget(self.ledger_zone)
        lay.addWidget(c1)

        c2 = Card("거래처 매입자료", "2")
        self.vendor_count = QLabel("")
        self.vendor_count.setObjectName("muted")
        c2.header.addWidget(self.vendor_count)
        self.vendor_zone = DropZone("양식 파일 여러 개를 한꺼번에 끌어놓기", "거래처마다 양식이 달라도 자동 인식")
        self.vendor_zone.clicked.connect(self.pick_vendors)
        self.vendor_zone.files_dropped.connect(self.add_vendors)
        c2.body.addWidget(self.vendor_zone)
        self.vendor_list = QVBoxLayout()
        self.vendor_list.setSpacing(8)
        c2.body.addLayout(self.vendor_list)
        lay.addWidget(c2)

        c3 = Card("비교 기준", "3")
        g = QGridLayout()
        g.setVerticalSpacing(8)
        g.addWidget(QLabel("일자 허용 범위"), 0, 0)
        self.win = QSpinBox()
        self.win.setRange(0, 10)
        self.win.setPrefix("± ")
        self.win.setSuffix(" 일")
        self.win.setValue(3)
        self.win.setToolTip("일자가 달라도 같은 바코드면 이 범위 안에서 한 줄로 묶습니다.")
        g.addWidget(self.win, 0, 1)
        g.addWidget(QLabel("금액 일치 허용"), 1, 0)
        self.tol = QDoubleSpinBox()
        self.tol.setRange(0, 1000)
        self.tol.setDecimals(0)
        self.tol.setPrefix("± ")
        self.tol.setSuffix(" 원")
        self.tol.setValue(1)
        self.tol.setToolTip("수량이 같고 금액 차이가 이 값 이하이면 '일치'로 봅니다(원 단위 반올림 오차).")
        g.addWidget(self.tol, 1, 1)
        self.clip = QCheckBox("원장 기간 밖의 거래처 행은 제외")
        self.clip.setChecked(True)
        g.addWidget(self.clip, 2, 0, 1, 2)
        g.addWidget(QLabel("저장 방식"), 3, 0)
        save_row = QHBoxLayout()
        save_row.setSpacing(14)
        self.save_one = QRadioButton("한 파일로")
        self.save_each = QRadioButton("거래처별 파일로")
        self.save_one.setChecked(True)
        save_row.addWidget(self.save_one)
        save_row.addWidget(self.save_each)
        save_row.addStretch()
        g.addLayout(save_row, 3, 1)
        g.setColumnStretch(1, 1)
        c3.body.addLayout(g)
        lay.addWidget(c3)

        self.run_btn = QPushButton("▶  비교 실행")
        self.run_btn.setObjectName("primary")
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.clicked.connect(self.run)
        lay.addWidget(self.run_btn)
        self.export_btn = QPushButton("⬇  엑셀로 내보내기")
        self.export_btn.setObjectName("accent")
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.clicked.connect(self.export)
        lay.addWidget(self.export_btn)
        lay.addStretch()
        scroll.setWidget(w)
        self._update_buttons()
        return scroll

    def _build_right(self):
        w = QWidget()
        w.setObjectName("root")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 14, 20, 16)

        self.empty = QWidget()
        el = QVBoxLayout(self.empty)
        el.setAlignment(Qt.AlignCenter)
        em = Emblem(84)
        el.addWidget(em, 0, Qt.AlignCenter)
        h = QLabel("원장과 거래처 자료를 넣고 [비교 실행]을 누르세요")
        h.setStyleSheet(f"font-size:14pt; font-weight:700; color:{theme.BLUE_DARK}; margin-top:14px;")
        el.addWidget(h, 0, Qt.AlignCenter)
        steps = QLabel(
            "① 동원 원장 엑셀 1개  →  ② 거래처 매입 양식 n개(양식이 달라도 OK)  →  ③ 비교 실행  →  ④ 엑셀로 내보내기<br>"
            "<span style='color:#6B7689'>판정: 일치 · 수량차이 · 단가차이 · 동원만 · 거래처만 — 날짜가 ±3일 어긋난 건도 짝지어 보여줍니다.</span>"
        )
        steps.setAlignment(Qt.AlignCenter)
        steps.setStyleSheet(f"color:{theme.TEXT}; margin-top:6px;")
        el.addWidget(steps, 0, Qt.AlignCenter)
        lay.addWidget(self.empty, 1)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.hide()
        lay.addWidget(self.tabs, 1)
        return w

    # ----- 원장 ------------------------------------------------------------

    def _last_dir(self):
        return self.settings.value("last_dir", os.path.expanduser("~/Documents"))

    def pick_ledger(self):
        path, _ = QFileDialog.getOpenFileName(self, "동원 원장 선택", self._last_dir(), FILE_FILTER)
        if path:
            self.load_ledger(path)

    @busy
    def load_ledger(self, path: str):
        try:
            cands = E.inspect_workbook(path)
        except Exception as e:  # noqa: BLE001
            return self._error("원장 파일을 열 수 없습니다", e)
        ledgers = [c for c in cands if c["kind"] == "ledger"]
        if not ledgers:
            QMessageBox.warning(self, "원장 형식이 아닙니다",
                                "이 파일에서 동원 원장 형식(납품요청일 · 바코드 · 총 수량 · 공급가 열)을 찾지 못했습니다.\n"
                                "거래처 매입자료라면 ② 영역에 넣어 주세요.")
            return
        c = ledgers[0]
        self.ledger = E.parse_ledger(c["rows"], c["sheet"])
        self.ledger_path = path
        self.settings.setValue("last_dir", os.path.dirname(path))
        recs = self.ledger.records
        dates = [r.date for r in recs if r.date]
        customers = sorted({r.customer for r in recs if r.customer})
        branch = next((r.extra.get("branch") for r in recs if r.extra.get("branch")), "")
        self.ledger_zone.title.setText(f"📗  {os.path.basename(path)}")
        span = f"{min(dates):%Y-%m-%d} ~ {max(dates):%m-%d}" if dates else "날짜 없음"
        self.ledger_zone.sub.setText(f"{c['sheet']} 시트 · {len(recs):,}행 · {span}\n"
                                     f"판매처 {len(customers)}곳" + (f" · {branch}" if branch else "") + " · 클릭하면 변경")
        if branch:
            self.branch_chip.setText(f"📍 {branch}")
            self.branch_chip.show()
        for it in self.vendors:
            self._parse_vendor(it)
        self._rebuild_vendor_rows()
        self._clear_results()

    # ----- 거래처 ----------------------------------------------------------

    def pick_vendors(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "거래처 매입자료 선택 (여러 개 가능)", self._last_dir(), FILE_FILTER)
        if paths:
            self.add_vendors(paths)

    @busy
    def add_vendors(self, paths: list[str]):
        problems = []
        for path in paths:
            if any(os.path.normcase(v.path) == os.path.normcase(path) for v in self.vendors):
                continue
            try:
                cands = E.inspect_workbook(path)
            except Exception as e:  # noqa: BLE001
                problems.append(f"{os.path.basename(path)}: 열 수 없음 ({e})")
                continue
            vend = [c for c in cands if c["kind"] == "vendor"]
            if not vend:
                if any(c["kind"] == "ledger" for c in cands) and self.ledger is None:
                    self.load_ledger(path)
                    continue
                problems.append(f"{os.path.basename(path)}: 바코드·수량·금액 열을 찾지 못했습니다")
                continue
            label = self._unique_label(os.path.splitext(os.path.basename(path))[0])
            item = VendorItem(path, label, vend, vend[0]["sheet"], aff=vend[0].get("aff"))
            self._parse_vendor(item)
            self.vendors.append(item)
            self.settings.setValue("last_dir", os.path.dirname(path))
        self._rebuild_vendor_rows()
        self._clear_results()
        if problems:
            QMessageBox.warning(self, "일부 파일을 넣지 못했습니다", "\n".join(problems))

    def _unique_label(self, base: str) -> str:
        labels = {v.label for v in self.vendors}
        out, n = base, 2
        while out in labels:
            out = f"{base}({n})"
            n += 1
        return out

    def _parse_vendor(self, it: VendorItem):
        cand = next((c for c in it.candidates if c["sheet"] == it.sheet), it.candidates[0])
        period = E.ledger_period(self.ledger.records) if self.ledger else None
        try:
            it.parsed = E.parse_vendor(cand["rows"], cand["sheet"], period=period)
            it.error = ""
        except Exception as e:  # noqa: BLE001
            it.parsed, it.error = None, str(e)

    def _customers(self) -> list[str]:
        return sorted({r.customer for r in self.ledger.records if r.customer}) if self.ledger else []

    def _rebuild_vendor_rows(self):
        while self.vendor_list.count():
            w = self.vendor_list.takeAt(0).widget()
            if w:
                w.deleteLater()
        customers = self._customers()
        for it in self.vendors:
            row = VendorRow(it, customers)
            if self.ledger and it.parsed and len(customers) > 1:
                row.set_customers(customers, E.best_customer(self.ledger.records, it.parsed.records))
            row.removed.connect(self._remove_vendor)
            row.changed.connect(self._vendor_changed)
            self.vendor_list.addWidget(row)
        self.vendor_count.setText(f"{len(self.vendors)}개" if self.vendors else "")
        self._update_buttons()

    def _remove_vendor(self, it: VendorItem):
        self.vendors.remove(it)
        self._rebuild_vendor_rows()
        self._clear_results()

    @busy
    def _vendor_changed(self, it: VendorItem):
        self._parse_vendor(it)
        for i in range(self.vendor_list.count()):
            w = self.vendor_list.itemAt(i).widget()
            if isinstance(w, VendorRow) and w.item is it:
                w.refresh()
        self._clear_results()

    # ----- 실행 · 내보내기 ---------------------------------------------------

    def _update_buttons(self):
        ready = self.ledger is not None and any(v.parsed for v in self.vendors)
        self.run_btn.setEnabled(ready)
        self.export_btn.setEnabled(bool(self.results))

    def _clear_results(self):
        self.results = []
        self.tabs.clear()
        self.tabs.hide()
        self.empty.show()
        self._update_buttons()

    @busy
    def run(self):
        if not self.ledger:
            return
        try:
            self.results = [
                E.compare(self.ledger, it.parsed, label=it.label, vendor_file=it.path,
                          customer=it.customer if it.customer != "" else None,
                          window_days=self.win.value(), tolerance=self.tol.value(), clip_to_ledger=self.clip.isChecked(),
                          affiliation=it.aff)
                for it in self.vendors if it.parsed
            ]
        except Exception as e:  # noqa: BLE001
            return self._error("비교 중 오류가 났습니다", e)
        self.tabs.clear()
        for res in self.results:
            s = res.summary
            self.tabs.addTab(ResultPanel(res), f"{'⚠ ' if res.warning else ''}{res.label}   {s.match_rate * 100:.1f}%")
        self.empty.hide()
        self.tabs.show()
        self._save_options()
        self._update_buttons()

    def export(self):
        if not self.results:
            return
        stem = os.path.splitext(os.path.basename(self.ledger_path))[0]
        base_dir = self.settings.value("export_dir", os.path.dirname(self.ledger_path))
        try:
            if self.save_each.isChecked() and len(self.results) > 1:
                folder = QFileDialog.getExistingDirectory(self, "저장할 폴더 선택", base_dir)
                if not folder:
                    return
                QApplication.setOverrideCursor(Qt.WaitCursor)
                saved = [
                    exporter.export(os.path.join(folder, f"{stem}_비교_{res.label}.xlsx"), self.ledger, self.ledger_path,
                                    [res], self.tol.value(), self.win.value())
                    for res in self.results
                ]
                target = folder
            else:
                name = f"{stem}_비교.xlsx" if len(self.results) == 1 else f"{stem}_비교_{dt.date.today():%Y%m%d}.xlsx"
                path, _ = QFileDialog.getSaveFileName(self, "결과 저장", os.path.join(base_dir, name), "엑셀 파일 (*.xlsx)")
                if not path:
                    return
                QApplication.setOverrideCursor(Qt.WaitCursor)
                saved = [exporter.export(path, self.ledger, self.ledger_path, self.results, self.tol.value(), self.win.value())]
                target = path
        except PermissionError:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "저장할 수 없습니다", "같은 이름의 파일이 엑셀에서 열려 있습니다. 닫고 다시 시도해 주세요.")
            return
        except Exception as e:  # noqa: BLE001
            QApplication.restoreOverrideCursor()
            return self._error("저장 중 오류가 났습니다", e)
        QApplication.restoreOverrideCursor()
        self.settings.setValue("export_dir", os.path.dirname(saved[0]))

        box = QMessageBox(self)
        box.setWindowTitle("저장 완료")
        box.setIcon(QMessageBox.Information)
        box.setText(f"결과 파일 {len(saved)}개를 저장했습니다.")
        box.setInformativeText("\n".join(os.path.basename(p) for p in saved))
        open_btn = box.addButton("파일 열기" if len(saved) == 1 else "폴더 열기", QMessageBox.AcceptRole)
        folder_btn = box.addButton("폴더 열기", QMessageBox.ActionRole) if len(saved) == 1 else None
        box.addButton("닫기", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is open_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(target))
        elif folder_btn is not None and box.clickedButton() is folder_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(saved[0])))

    # ----- 업데이트 --------------------------------------------------------

    def check_update(self, manual: bool):
        if not updater.configured():
            if manual:
                QMessageBox.information(self, "업데이트", "업데이트 저장소가 아직 설정되지 않았습니다.")
            return
        self._manual_check = manual

        def work():
            try:
                rel = updater.latest_release()
                self.bridge.update_found.emit(rel)
            except Exception as e:  # noqa: BLE001
                self.bridge.update_failed.emit(str(e))

        threading.Thread(target=work, daemon=True).start()

    def _on_update_found(self, rel):
        if rel and updater.is_newer(rel.version):
            self._release = rel
            self.update_label.setText(f"🎉  새 버전 <b>v{rel.version}</b>이 나왔습니다. "
                                      f"<span style='color:#6B7689'>(현재 v{__version__})</span>")
            self.update_bar.show()
        elif self._manual_check:
            QMessageBox.information(self, "업데이트", f"최신 버전을 사용하고 있습니다. (v{__version__})")

    def _on_update_failed(self, msg: str):
        if self._manual_check:
            QMessageBox.warning(self, "업데이트 확인 실패", f"GitHub에 연결하지 못했습니다.\n사내망 차단 여부를 확인해 주세요.\n\n{msg}")

    def install_update(self):
        rel = self._release
        if not rel:
            return
        dlg = QProgressDialog(f"v{rel.version} 내려받는 중…", "취소", 0, 100, self)
        dlg.setWindowTitle("업데이트")
        dlg.setWindowModality(Qt.WindowModal)
        dlg.setMinimumDuration(0)
        dlg.setValue(0)
        b = self._dl_bridge = _Bridge()  # 다운로드마다 새 연결(재시도 시 중복 연결 방지)
        b.progress.connect(lambda got, total: dlg.setValue(int(got * 100 / total)) if total else None)

        def finished(path):
            dlg.close()
            if QMessageBox.question(self, "업데이트 설치",
                                    "내려받기를 마쳤습니다. 프로그램을 닫고 설치할까요?\n(설치가 끝나면 자동으로 다시 열립니다)"
                                    ) == QMessageBox.Yes:
                updater.run_installer(path)
                QApplication.quit()

        b.downloaded.connect(finished)
        b.download_failed.connect(lambda m: (dlg.close(), QMessageBox.warning(self, "업데이트 실패", m)))

        def work():
            try:
                b.downloaded.emit(updater.download(rel, lambda g, t: b.progress.emit(g, t)))
            except Exception as e:  # noqa: BLE001
                b.download_failed.emit(str(e))

        threading.Thread(target=work, daemon=True).start()

    # ----- 기타 ------------------------------------------------------------

    def show_help(self):
        QMessageBox.about(
            self, "도움말",
            f"<h3>{ORG_NAME} 매입대사 점검 v{__version__}</h3>"
            "<p><b>① 동원 원장</b> — SAP에서 내려받은 원장 엑셀(납품요청일·바코드·총 수량·공급가).<br>"
            "<b>② 거래처 매입자료</b> — 거래처가 보내준 매입 양식. 여러 개를 한 번에 넣을 수 있고, "
            "열 위치·날짜 표기가 달라도 자동으로 읽습니다.<br>"
            "<b>③ 비교 실행</b> → 표에서 확인 → <b>엑셀로 내보내기</b></p>"
            "<p><b>판정 규칙</b><br>"
            "· 공급가(부가세 제외) 기준, 단가 = 금액 ÷ 총수량<br>"
            "· 바코드는 앞 12자리로 매칭(박스코드 14자리도 낱개 바코드와 맞춤)<br>"
            "· 같은 일자+바코드는 합산, 일자가 달라도 ±N일 안이면 한 줄로 묶음<br>"
            "· 수량이 다르면 <b>수량차이</b>, 수량은 같고 금액이 다르면 <b>단가차이</b><br>"
            "· 한쪽에만 있으면 <b>동원만 / 거래처만</b></p>"
            "<p>문의·개선 요청은 개발 담당자에게 알려 주세요.</p>",
        )

    def _error(self, title: str, e: Exception):
        detail = "".join(traceback.format_exception(e))[-1500:]
        box = QMessageBox(QMessageBox.Critical, title, f"{title}.\n\n{e}", parent=self)
        box.setDetailedText(detail)
        box.exec()

    def _save_options(self):
        s = self.settings
        s.setValue("win", self.win.value())
        s.setValue("tol", self.tol.value())
        s.setValue("clip", self.clip.isChecked())
        s.setValue("save_each", self.save_each.isChecked())

    def _restore(self):
        s = self.settings
        self.win.setValue(int(s.value("win", 3)))
        self.tol.setValue(float(s.value("tol", 1)))
        self.clip.setChecked(str(s.value("clip", "true")).lower() == "true")
        (self.save_each if str(s.value("save_each", "false")).lower() == "true" else self.save_one).setChecked(True)
        geo = s.value("geometry")
        if geo is not None:
            self.restoreGeometry(geo)

    def closeEvent(self, e):
        self.settings.setValue("geometry", self.saveGeometry())
        self._save_options()
        super().closeEvent(e)
