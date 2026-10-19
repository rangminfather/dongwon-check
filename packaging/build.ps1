# 설치 파일 빌드: dist\DongwonCheck-Setup-<버전>.exe
#   powershell -ExecutionPolicy Bypass -File packaging\build.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

# 1) 가상환경과 라이브러리(모두 exe 안에 들어간다)
if (-not (Test-Path ".venv\Scripts\python.exe")) { python -m venv .venv }
$Py = Join-Path $Root ".venv\Scripts\python.exe"
& $Py -m pip install --quiet --upgrade pip
& $Py -m pip install --quiet -r requirements.txt -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw "pip install 실패" }

# 2) 버전
$Version = (& $Py -c "import sys; sys.path.insert(0,'src'); from dongwon_check.version import __version__; print(__version__)").Trim()
Write-Host "버전: $Version" -ForegroundColor Cyan

# 3) 테스트
& $Py -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "테스트 실패 — 빌드를 멈춥니다" }

# 4) 아이콘·마법사 그림, exe 버전 정보
& $Py packaging\make_assets.py
New-Item -ItemType Directory -Force build | Out-Null
$v = $Version.Split(".") + @("0", "0", "0")
$tuple = "($($v[0]), $($v[1]), $($v[2]), 0)"
@"
VSVersionInfo(
  ffi=FixedFileInfo(filevers=$tuple, prodvers=$tuple),
  kids=[
    StringFileInfo([StringTable('041204B0', [
      StringStruct('CompanyName', '동원F&B'),
      StringStruct('FileDescription', '동원 매입대사 점검'),
      StringStruct('FileVersion', '$Version'),
      StringStruct('ProductName', '동원 매입대사'),
      StringStruct('ProductVersion', '$Version'),
      StringStruct('OriginalFilename', 'DongwonCheck.exe')])]),
    VarFileInfo([VarStruct('Translation', [0x0412, 1200])])
  ]
)
"@ | Out-File -Encoding utf8 build\version_info.txt

# 릴리스 노트: CHANGELOG.md 에서 이 버전 절만 뽑는다(GitHub 릴리스 본문)
$log = Get-Content CHANGELOG.md -Encoding UTF8 -Raw
$m = [regex]::Match($log, "(?ms)^## \[$([regex]::Escape($Version))\][^\r\n]*\r?\n(.*?)(?=^## \[|\z)")
$notes = if ($m.Success) { $m.Groups[1].Value.Trim() } else { "v$Version" }
$notes | Out-File -Encoding utf8 build\release_notes.md

# 5) PyInstaller (폴더형 — 시작이 빠르다)
& $Py -m PyInstaller --noconfirm --clean --distpath dist --workpath build\pyinstaller packaging\DongwonCheck.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller 실패" }

# 6) Inno Setup
$Iscc = @(
  "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
  "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
  "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Iscc) { throw "Inno Setup 6이 없습니다: winget install JRSoftware.InnoSetup" }
& $Iscc /Qp "/DAppVersion=$Version" packaging\installer.iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup 실패" }

$Out = Join-Path $Root "dist\DongwonCheck-Setup-$Version.exe"
Write-Host "완료: $Out ($([math]::Round((Get-Item $Out).Length / 1MB, 1)) MB)" -ForegroundColor Green
