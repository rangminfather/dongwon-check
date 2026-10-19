"""대사 결과를 엑셀로 내보낸다.

수식(단가·차이·비고)은 엑셀에서 값을 고쳐도 다시 계산되도록 수식으로 쓰되,
카카오톡·모바일 미리보기처럼 계산을 안 하는 뷰어에서도 보이도록 계산값을 함께 저장한다.
"""

from __future__ import annotations

import datetime as dt
import os
import re

import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell

from .engine import STATUSES, CompareResult, ParseResult
from .version import APP_NAME, ORG_NAME, __version__

BLUE = "#0B3D91"  # 동원 블루(헤더)
BLUE_LIGHT = "#E8EEF8"
SKY = "#2E7BD6"
GRAY = "#595959"

STATUS_FILL = {
    "일치": "#E2EFDA",
    "수량차이": "#FFF2CC",
    "단가차이": "#FCE4D6",
    "동원만": "#DDEBF7",
    "거래처만": "#EDE7F6",
}

CRITERIA = (
    "기준: 공급가(액) 기준, 단가=금액÷총수량. 바코드는 앞 12자리로 매칭(박스코드 14자리 앞 1·체크숫자 제외). "
    "같은 일자+바코드는 합산, 합산 결과 수량·금액이 모두 0인 건은 제외. 금액차 ±{tol:g}원 이내는 일치."
)
CRITERIA2 = "※ 일자가 다르지만 바코드가 같은 건(±{win}일, 양쪽 한쪽에만 있던 건)은 한 줄로 묶고 거래처 일자 열에 표시"


def safe_sheet_name(name: str, used: set[str]) -> str:
    name = re.sub(r"[\[\]:*?/\\]", "_", name).strip("'") or "Sheet"
    base = name[:31]
    out, n = base, 2
    while out.lower() in {u.lower() for u in used}:
        suffix = f"({n})"
        out = base[: 31 - len(suffix)] + suffix
        n += 1
    used.add(out)
    return out


class _Formats:
    def __init__(self, wb: xlsxwriter.Workbook):
        f = lambda **kw: wb.add_format({"font_name": "맑은 고딕", "font_size": 10, **kw})  # noqa: E731
        self.title = f(bold=True, font_size=14, font_color=BLUE)
        self.subtitle = f(font_color=GRAY)
        self.note = f(font_color=GRAY, italic=True)
        self.head = f(bold=True, font_color="white", bg_color=BLUE, align="center", valign="vcenter",
                      text_wrap=True, border=1, border_color="#C9D3E6")
        self.label = f(bold=True, bg_color=BLUE_LIGHT, border=1, border_color="#C9D3E6")
        self.cell = f(border=1, border_color="#E1E6EF")
        self.text = f()
        self.date = f(num_format="yyyy-mm-dd", align="center")
        self.int = f(num_format="#,##0;[Red]-#,##0;-")
        self.money = f(num_format="#,##0;[Red]-#,##0;-")
        self.unit = f(num_format="#,##0.0")
        self.pct = f(num_format="0.0%")
        self.center = f(align="center")
        self.rows = f(font_color="#8C8C8C", font_size=9)
        self.sum_int = f(num_format="#,##0;[Red]-#,##0;-", border=1, border_color="#E1E6EF")
        self.link = f(font_color=SKY, underline=1)
        self.status = {s: wb.add_format({"bg_color": c}) for s, c in STATUS_FILL.items()}
        self.chip = {s: f(bg_color=c, bold=True, align="center", border=1, border_color="#E1E6EF")
                     for s, c in STATUS_FILL.items()}


def _write_raw(ws, fmts: _Formats, rows: list[list], header_row: int | None = None):
    """원본 시트를 행 위치 그대로 복사한다(원본행 번호로 추적할 수 있게)."""
    widths: dict[int, int] = {}
    for r, row in enumerate(rows):
        for c, v in enumerate(row):
            if v is None or v == "":
                continue
            if isinstance(v, (dt.datetime, dt.date)):
                ws.write_datetime(r, c, v if isinstance(v, dt.datetime) else dt.datetime(v.year, v.month, v.day), fmts.date)
                w = 11
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                ws.write_number(r, c, v)
                w = len(f"{v:,.0f}") + 2
            else:
                s = str(v)
                ws.write_string(r, c, s, fmts.head if header_row is not None and r == header_row else None)
                w = min(40, sum(2 if ord(ch) > 127 else 1 for ch in s) + 2)
            widths[c] = max(widths.get(c, 6), w)
    for c, w in widths.items():
        ws.set_column(c, c, w)
    if header_row is not None:
        ws.freeze_panes(header_row + 1, 0)


def _write_compare(ws, fmts: _Formats, res: CompareResult, ledger_name: str, tol: float, win: int):
    rows = res.rows
    first, last = 11, 11 + max(len(rows), 1) - 1  # 0-based 데이터 행
    rng = lambda col: f"{col}{first + 1}:{col}{last + 1}"  # noqa: E731

    period = "기간 합계" if res.mode == "period" else "일자별"
    ws.write(0, 0, f"동원 원장 vs 거래처 매입 비교 — {res.label} ({period})", fmts.title)
    ws.write(1, 0, CRITERIA.format(tol=tol), fmts.subtitle)
    ws.write(2, 0, CRITERIA2.format(win=win) if res.mode == "daily" else "※ 날짜가 없는 양식이라 바코드별 기간 합계로 비교", fmts.subtitle)

    s = res.summary
    ws.write_row(3, 0, ["구분", "동원", "거래처", "차이"], fmts.head)
    ws.write(4, 0, "총수량", fmts.label)
    ws.write_formula(4, 1, f"=SUM({rng('D')})", fmts.sum_int, s.l_qty)
    ws.write_formula(4, 2, f"=SUM({rng('G')})", fmts.sum_int, s.v_qty)
    ws.write_formula(4, 3, "=B5-C5", fmts.sum_int, s.l_qty - s.v_qty)
    ws.write(5, 0, "금액(공급가)", fmts.label)
    ws.write_formula(5, 1, f"=SUM({rng('F')})", fmts.sum_int, s.l_amt)
    ws.write_formula(5, 2, f"=SUM({rng('I')})", fmts.sum_int, s.v_amt)
    ws.write_formula(5, 3, "=B6-C6", fmts.sum_int, s.l_amt - s.v_amt)
    ws.write_row(3, 5, ["비고", "건수"], fmts.head)
    for i, st in enumerate(STATUSES):
        ws.write(4 + i, 5, st, fmts.chip[st])
        ws.write_formula(4 + i, 6, f'=COUNTIF({rng("L")},F{5 + i})', fmts.sum_int, s.counts[st])
    ws.write(3, 8, "거래처 파일", fmts.label)
    ws.write(3, 9, f"{os.path.basename(res.vendor_file)} › {res.vendor_sheet}")
    ws.write(4, 8, "동원 원장", fmts.label)
    ws.write(4, 9, ledger_name)
    ws.write(5, 8, "원장 판매처", fmts.label)
    ws.write(5, 9, res.customer or "(전체)")
    ws.write(6, 8, "참고", fmts.label)
    ws.write(6, 9, " · ".join(n for n in res.notes), fmts.note)

    headers = ["일자", "바코드", "상품명", "동원\n총수량", "동원\n단가", "동원\n금액", "거래처\n총수량", "거래처\n단가",
               "거래처\n금액", "수량차\n(동원-거래처)", "금액차\n(동원-거래처)", "비고", "거래처\n일자", "메모",
               "동원\n원본행", "거래처\n원본행"]
    ws.write_row(10, 0, headers, fmts.head)
    ws.set_row(10, 30)

    for i, r in enumerate(rows):
        x = first + i
        n = x + 1  # 엑셀 행 번호
        if r.date:
            ws.write_datetime(x, 0, dt.datetime(r.date.year, r.date.month, r.date.day), fmts.date)
        else:
            ws.write(x, 0, "기간합계", fmts.center)
        ws.write_string(x, 1, r.barcode)
        ws.write_string(x, 2, r.name)
        if r.l_qty is not None:
            ws.write_number(x, 3, r.l_qty, fmts.int)
            ws.write_number(x, 5, r.l_amt, fmts.money)
        ws.write_formula(x, 4, f'=IF(N(D{n})=0,"",F{n}/D{n})', fmts.unit, r.l_unit if r.l_unit is not None else "")
        if r.v_qty is not None:
            ws.write_number(x, 6, r.v_qty, fmts.int)
            ws.write_number(x, 8, r.v_amt, fmts.money)
        ws.write_formula(x, 7, f'=IF(N(G{n})=0,"",I{n}/G{n})', fmts.unit, r.v_unit if r.v_unit is not None else "")
        ws.write_formula(x, 9, f"=N(D{n})-N(G{n})", fmts.int, r.qty_diff)
        ws.write_formula(x, 10, f"=N(F{n})-N(I{n})", fmts.money, round(r.amt_diff, 2))
        ws.write_formula(
            x, 11,
            f'=IF(D{n}="","거래처만",IF(G{n}="","동원만",IF(J{n}<>0,"수량차이",IF(ABS(K{n})<={tol:g},"일치","단가차이"))))',
            fmts.center, r.status,
        )
        if r.v_date:
            ws.write_datetime(x, 12, dt.datetime(r.v_date.year, r.v_date.month, r.v_date.day), fmts.date)
        if r.memo:
            ws.write_string(x, 13, r.memo)
        if r.l_rows:
            ws.write_string(x, 14, ",".join(map(str, r.l_rows)), fmts.rows)
        if r.v_rows:
            ws.write_string(x, 15, ",".join(map(str, r.v_rows)), fmts.rows)

    full = f"A{first + 1}:P{last + 1}"
    for st in STATUSES:
        if st == "일치":
            continue
        ws.conditional_format(full, {"type": "formula", "criteria": f'=$L{first + 1}="{st}"', "format": fmts.status[st]})
    ws.autofilter(10, 0, last, 15)
    ws.freeze_panes(11, 3)
    for col, w in zip("ABCDEFGHIJKLMNOP", [11, 15, 34, 8, 10, 12, 8, 10, 12, 11, 13, 10, 11, 26, 9, 9]):
        ws.set_column(f"{col}:{col}", w)


def _write_summary(ws, fmts: _Formats, results: list[CompareResult], ledger: ParseResult, ledger_path: str,
                   sheet_of: dict[str, str]):
    branch = next((r.extra.get("branch") for r in ledger.records if r.extra.get("branch")), "")
    ws.write(0, 0, f"{ORG_NAME} 매입대사 결과", fmts.title)
    ws.write(1, 0, f"{branch + ' · ' if branch else ''}기준 원장: {os.path.basename(ledger_path)}  ·  "
                   f"작성 {dt.datetime.now():%Y-%m-%d %H:%M}  ·  {APP_NAME} v{__version__}", fmts.subtitle)
    heads = ["거래처 파일", "시트", "원장 판매처", "방식", "총 건수", *STATUSES, "일치율",
             "동원 금액", "거래처 금액", "금액차", "참고"]
    ws.write_row(3, 0, heads, fmts.head)
    ws.set_row(3, 22)
    for i, res in enumerate(results):
        r = 4 + i
        s = res.summary
        ws.write_url(r, 0, f"internal:'{sheet_of[res.label]}'!A1", fmts.link, string=os.path.basename(res.vendor_file))
        ws.write(r, 1, res.vendor_sheet, fmts.cell)
        ws.write(r, 2, res.customer or "(전체)", fmts.cell)
        ws.write(r, 3, "기간합계" if res.mode == "period" else "일자별", fmts.cell)
        ws.write_number(r, 4, s.total, fmts.sum_int)
        for j, st in enumerate(STATUSES):
            ws.write_number(r, 5 + j, s.counts[st], fmts.sum_int)
        ws.write_formula(r, 10, f"=IF({xl_rowcol_to_cell(r, 4)}=0,0,{xl_rowcol_to_cell(r, 5)}/{xl_rowcol_to_cell(r, 4)})",
                         fmts.pct, s.match_rate)
        ws.write_number(r, 11, s.l_amt, fmts.sum_int)
        ws.write_number(r, 12, s.v_amt, fmts.sum_int)
        ws.write_number(r, 13, s.l_amt - s.v_amt, fmts.sum_int)
        ws.write(r, 14, " · ".join(res.notes), fmts.note)
    for col, w in zip(range(15), [28, 18, 22, 8, 8, 8, 9, 9, 8, 9, 8, 14, 14, 12, 70]):
        ws.set_column(col, col, w)
    ws.freeze_panes(4, 1)
    ws.write(6 + len(results), 0, "※ 파일 이름을 누르면 해당 비교 시트로 이동합니다. 행 색: "
                                  "노랑=수량차이 · 주황=단가차이 · 파랑=동원만 · 보라=거래처만", fmts.note)


def export(path: str, ledger: ParseResult, ledger_path: str, results: list[CompareResult],
           tolerance: float = 1.0, window_days: int = 3) -> str:
    """결과 통합문서를 저장하고 경로를 돌려준다.

    거래처 파일이 1개면 예시 양식과 같은 [동원 · 거래처 · 비교] 3시트,
    여러 개면 [요약 · 동원 · 비교_x · 거래처_x …] 로 만든다.
    """
    wb = xlsxwriter.Workbook(path, {"strings_to_numbers": False, "nan_inf_to_errors": True})
    wb.set_properties({"title": f"{ORG_NAME} 매입대사 결과", "company": ORG_NAME, "comments": f"{APP_NAME} v{__version__}"})
    fmts = _Formats(wb)
    used: set[str] = set()
    ledger_name = os.path.basename(ledger_path)

    if len(results) == 1:
        res = results[0]
        ws_l = wb.add_worksheet(safe_sheet_name("동원", used))
        ws_v = wb.add_worksheet(safe_sheet_name("거래처", used))
        ws_c = wb.add_worksheet(safe_sheet_name("비교", used))
        _write_raw(ws_l, fmts, ledger.raw_all, header_row=ledger.header_row - 1)
        _write_raw(ws_v, fmts, res.vendor.raw_all, header_row=res.vendor.header_row - 1)
        _write_compare(ws_c, fmts, res, ledger_name, tolerance, window_days)
        ws_c.activate()
    else:
        ws_s = wb.add_worksheet(safe_sheet_name("요약", used))
        ws_l = wb.add_worksheet(safe_sheet_name("동원", used))
        _write_raw(ws_l, fmts, ledger.raw_all, header_row=ledger.header_row - 1)
        sheet_of = {}
        for res in results:
            ws_c = wb.add_worksheet(safe_sheet_name(f"비교_{res.label}", used))
            ws_v = wb.add_worksheet(safe_sheet_name(f"거래처_{res.label}", used))
            sheet_of[res.label] = ws_c.name
            _write_compare(ws_c, fmts, res, ledger_name, tolerance, window_days)
            _write_raw(ws_v, fmts, res.vendor.raw_all, header_row=res.vendor.header_row - 1)
        _write_summary(ws_s, fmts, results, ledger, ledger_path, sheet_of)
        ws_s.activate()
    wb.close()
    return path
