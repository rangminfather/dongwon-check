# 새 버전 배포: 버전 올리기 → 커밋 → 태그 → 푸시 (GitHub Actions 가 설치 파일을 만들어 릴리스에 올린다)
#   powershell -ExecutionPolicy Bypass -File packaging\release.ps1 -Version 1.0.1 -Note "단가 반올림 오차 수정"
param(
  [Parameter(Mandatory = $true)][string]$Version,
  [Parameter(Mandatory = $true)][string]$Note
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw "버전은 1.2.3 형식이어야 합니다" }
if (git status --porcelain) { throw "커밋하지 않은 변경이 있습니다. 먼저 커밋하세요." }

$vf = "src\dongwon_check\version.py"
$text = [IO.File]::ReadAllText($vf, [Text.Encoding]::UTF8)
$text = [regex]::Replace($text, '__version__ = "[^"]+"', "__version__ = `"$Version`"")
[IO.File]::WriteAllText($vf, $text, (New-Object Text.UTF8Encoding $false))

$log = [IO.File]::ReadAllText("CHANGELOG.md", [Text.Encoding]::UTF8)
$entry = "## [$Version] - $(Get-Date -Format yyyy-MM-dd)`n" + (($Note -split ';') | ForEach-Object { "- $($_.Trim())" }) -join "`n"
$i = $log.IndexOf("## [")
$log = $log.Substring(0, $i) + $entry + "`n`n" + $log.Substring($i)
[IO.File]::WriteAllText("CHANGELOG.md", $log, (New-Object Text.UTF8Encoding $false))

git add $vf CHANGELOG.md
git commit -m "v$Version: $Note"
git tag "v$Version"
git push origin HEAD
git push origin "v$Version"
Write-Host "푸시 완료 — GitHub Actions 에서 빌드가 끝나면(약 5분) 사용자 PC에 업데이트 알림이 뜹니다." -ForegroundColor Green
