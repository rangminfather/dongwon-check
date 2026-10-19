# 동원F&B 매입대사 점검

동원 원장(SAP 내려받기) 1개와 거래처가 보내 준 매입 양식 n개를 넣으면
**일자 / 바코드 / 매입수량 / 단가 / 금액** 일치 여부를 한 번에 점검하고 결과를 엑셀로 내보내는 PC 프로그램입니다.

## 쓰는 법

1. **동원 원장** 엑셀을 ① 영역에 끌어놓습니다.
2. **거래처 매입자료**를 ② 영역에 여러 개 한꺼번에 끌어놓습니다. 거래처마다 양식이 달라도 자동으로 읽습니다.
   - 시트가 여러 개면 가장 알맞은 시트를 고르고, 목록에서 바꿀 수 있습니다.
   - 원장에 판매처가 여러 곳이면 거래처 자료와 가장 많이 겹치는 판매처를 자동으로 고릅니다.
3. **비교 실행** → 표에서 판정별로 걸러 보고 → **엑셀로 내보내기**.

### 판정 규칙

| 항목 | 규칙 |
|---|---|
| 금액 | 공급가(부가세 제외). 거래처 양식에 공급가액이 없으면 `매입금액 − 부가세액` |
| 단가 | 금액 ÷ 총수량 |
| 바코드 | 체크숫자를 뺀 앞 12자리로 매칭 — 박스코드(14자리)도 낱개 바코드와 맞춰짐 |
| 합산 | 같은 일자+바코드는 합산, 합산 결과 수량·금액이 모두 0이면 제외 |
| 날짜 어긋남 | 한쪽에만 있는 같은 바코드 건은 ±3일(조정 가능) 안에서 한 줄로 묶고 '거래처 일자'에 표시 |
| 판정 | 수량이 다르면 **수량차이**, 수량은 같고 금액이 ±1원 넘게 다르면 **단가차이**, 한쪽에만 있으면 **동원만/거래처만** |

### 인식하는 거래처 양식

| 양식 | 날짜를 찾는 방법 | 예 |
|---|---|---|
| 전표별 매입현황 | 품목 아래 `[09월 02일 13:53 합계]` 행 | 양식2 |
| 매입상세내역(묶음형) | 품목 위 `매입일자 : 2026-09-01` 행 | 양식1, 양식4 |
| 행마다 일자 열 | `매입일자`·`입고일자` 등 열 | — |
| 날짜 없는 상품별 합계 | 없음 → 바코드별 **기간 합계**로 비교 | 양식3 첫 시트 |

열 이름은 `바코드/상품코드`, `수량/매입수량/매입량`, `공급가액/공급가`, `매입금액/매입액`, `부가세액/부가세` 등을 알아봅니다.
새 양식이 안 읽히면 그 파일을 개발 담당에게 보내 주세요(`engine.py`의 `ALIASES`에 열 이름을 추가하면 됩니다).

## 개발

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt -r requirements-dev.txt
.venv\Scripts\python run.py          # 실행
.venv\Scripts\python -m pytest -q    # 테스트
```

실제 자료로 기존 수작업 결과(동원원장_비교.xlsx)와 대조하려면 `DONGWON_SAMPLES` 환경변수에 자료 폴더를 지정하고 테스트를 돌립니다.
**원장·거래처 엑셀은 저장소에 올리지 않습니다**(`.gitignore`에서 막아 둠).

| 파일 | 역할 |
|---|---|
| `src/dongwon_check/engine.py` | 양식 인식 · 대사 규칙 (화면과 분리) |
| `src/dongwon_check/exporter.py` | 결과 엑셀 만들기 |
| `src/dongwon_check/main_window.py` | 화면 |
| `src/dongwon_check/updater.py` | GitHub Releases 자동 업데이트 |
| `packaging/build.ps1` | 설치 파일 빌드 (`dist\DongwonCheck-Setup-x.y.z.exe`) |
| `packaging/release.ps1` | 버전 올리고 배포 |

## 설치 파일 만들기

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build.ps1
```

라이브러리(PySide6·openpyxl·xlrd·XlsxWriter)와 파이썬은 모두 설치 파일 안에 들어갑니다.
설치는 관리자 권한 없이 사용자 폴더(`%LOCALAPPDATA%\Programs\DongwonCheck`)에 됩니다.

## 업데이트 배포 (피드백 → 수정 → 배포)

1. 코드를 고치고 커밋합니다.
2. 버전을 올려 배포합니다.
   ```powershell
   powershell -ExecutionPolicy Bypass -File packaging\release.ps1 -Version 1.0.1 -Note "단가 반올림 수정; 양식5 인식 추가"
   ```
3. GitHub Actions가 설치 파일을 빌드해 Releases에 올립니다(약 5분).
4. 사용자가 프로그램을 켜면 상단에 **"새 버전이 나왔습니다 [지금 업데이트]"** 알림이 뜨고, 누르면 받아서 설치 후 다시 실행됩니다.

업데이트 확인 주소는 `src/dongwon_check/version.py`의 `GITHUB_REPO`입니다.
저장소가 **공개(public)** 여야 로그인 없이 업데이트를 받을 수 있습니다(코드만 올라가고 자료는 올라가지 않습니다).
