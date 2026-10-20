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


def _contexts():
    """인증서 확인 방식을 순서대로 돌려준다.

    1) 윈도우 인증서 확인(truststore) — 브라우저와 같은 방식이라 사내 보안장비 인증서,
       PC에 아직 없는 최상위·중간 인증서 자동 받기까지 된다.
    2) 파이썬 기본(윈도우 인증서 저장소 목록)  3) certifi 묶음.
    """
    try:
        import truststore

        yield truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:
        pass
    yield ssl.create_default_context()
    try:
        import certifi

        yield ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass


def _is_cert_error(e: Exception) -> bool:
    reason = getattr(e, "reason", e)
    return isinstance(reason, ssl.SSLError) or "CERTIFICATE" in str(e).upper()


def _open(url: str, accept: str = "application/vnd.github+json"):
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": f"{APP_NAME_EN}/{__version__}"})
    last: Exception | None = None
    for ctx in _contexts():
        try:
            return urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx)
        except Exception as e:  # noqa: BLE001
            if not _is_cert_error(e):
                raise
            last = e
    raise last or RuntimeError("인증서를 확인하지 못했습니다")


def releases_page() -> str:
    """브라우저로 직접 받을 때 여는 최신 릴리스 페이지."""
    return f"https://github.com/{GITHUB_REPO}/releases/latest"


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
