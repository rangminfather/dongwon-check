"""GitHub Releases 로 새 버전을 확인하고 설치 파일을 받아 실행한다.

릴리스 규칙: 태그 vX.Y.Z, 첨부 파일 이름은 *Setup*.exe (GitHub Actions 가 자동으로 만든다).
"""

from __future__ import annotations

import json
import os
import re
import ssl
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass

from .version import APP_NAME_EN, GITHUB_REPO, __version__

API = "https://api.github.com/repos/{repo}/releases/latest"
TIMEOUT = 8


@dataclass
class Release:
    version: str
    notes: str
    asset_url: str
    asset_name: str
    size: int
    page_url: str


def parse_version(v: str) -> tuple[int, ...]:
    nums = re.findall(r"\d+", v)
    return tuple(int(n) for n in nums[:3]) or (0,)


def is_newer(remote: str, local: str = __version__) -> bool:
    return parse_version(remote) > parse_version(local)


def _context():
    # 사내망 SSL 검사 장비가 있으면 윈도우 인증서 저장소를 써야 통과된다.
    ctx = ssl.create_default_context()
    try:
        ctx.load_default_certs()
    except Exception:
        pass
    return ctx


def _open(url: str, accept: str = "application/vnd.github+json"):
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": f"{APP_NAME_EN}/{__version__}"})
    return urllib.request.urlopen(req, timeout=TIMEOUT, context=_context())


def configured() -> bool:
    return "/" in GITHUB_REPO and not GITHUB_REPO.startswith("OWNER/")


def latest_release() -> Release | None:
    """최신 릴리스 정보. 저장소가 설정되지 않았거나 설치 파일이 없으면 None."""
    if not configured():
        return None
    with _open(API.format(repo=GITHUB_REPO)) as resp:
        data = json.load(resp)
    asset = next(
        (a for a in data.get("assets", []) if a["name"].lower().endswith(".exe") and "setup" in a["name"].lower()),
        None,
    )
    if asset is None:
        return None
    return Release(
        version=data.get("tag_name", "").lstrip("v"),
        notes=data.get("body") or "",
        asset_url=asset["browser_download_url"],
        asset_name=asset["name"],
        size=asset.get("size", 0),
        page_url=data.get("html_url", ""),
    )


def download(rel: Release, progress=None) -> str:
    """설치 파일을 임시 폴더에 받는다. progress(받은 바이트, 전체 바이트)."""
    dest = os.path.join(tempfile.gettempdir(), rel.asset_name)
    with _open(rel.asset_url, accept="application/octet-stream") as resp, open(dest + ".part", "wb") as f:
        total = int(resp.headers.get("Content-Length") or rel.size or 0)
        got = 0
        while chunk := resp.read(256 * 1024):
            f.write(chunk)
            got += len(chunk)
            if progress:
                progress(got, total)
    os.replace(dest + ".part", dest)
    return dest


def run_installer(path: str):
    """조용히 설치하고 끝나면 앱을 다시 띄운다(installer.iss 의 [Run] 항목)."""
    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([path, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"],
                     creationflags=flags if sys.platform == "win32" else 0, close_fds=True)
