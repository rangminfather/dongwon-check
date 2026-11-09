"""업데이트 연결: 인증서 확인이 실패하면 다음 방식으로 넘어가는지(네트워크 없이 확인)."""

import os
import ssl
import sys
import urllib.error

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dongwon_check import updater as U  # noqa: E402


def _cert_fail():
    return urllib.error.URLError(ssl.SSLCertVerificationError(1, "certificate verify failed: unable to get local issuer certificate"))


def test_falls_back_on_certificate_error(monkeypatch):
    tried = []

    def fake_urlopen(req, timeout, context):
        tried.append(context)
        if len(tried) < 3:
            raise _cert_fail()
        return "ok"

    monkeypatch.setattr(U, "_contexts", lambda: iter(["windows", "default", "certifi"]))
    monkeypatch.setattr(U.urllib.request, "urlopen", fake_urlopen)
    assert U._open("https://example") == "ok"
    assert tried == ["windows", "default", "certifi"]


def test_other_errors_are_not_retried(monkeypatch):
    tried = []

    def fake_urlopen(req, timeout, context):
        tried.append(context)
        raise urllib.error.URLError(TimeoutError("timed out"))

    monkeypatch.setattr(U, "_contexts", lambda: iter(["windows", "default"]))
    monkeypatch.setattr(U.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(urllib.error.URLError):
        U._open("https://example")
    assert tried == ["windows"]  # 망 끊김은 인증서 문제가 아니므로 바로 알린다


def test_windows_trust_comes_first():
    first = next(U._contexts())
    assert type(first).__module__.startswith("truststore")


def _rel():
    return U.Release("9.9.9", "", "https://github.com/x/releases/download/a.exe", "DongwonCheck-Setup-test.exe", 3, "",
                     api_url="https://api.github.com/x/assets/1")


class _Resp:
    headers = {"Content-Length": "3"}

    def __init__(self):
        self.data = [b"abc", b""]

    def read(self, n):
        return self.data.pop(0)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_download_uses_api_url_then_browser_url_and_retries(monkeypatch, tmp_path):
    tried = []

    def fake_open(url, accept=""):
        tried.append(url)
        if len(tried) < 4:  # 첫 바퀴 두 주소 모두 504, 둘째 바퀴 API 주소도 504
            raise urllib.error.HTTPError(url, 504, "Gateway Time-out", {}, None)
        return _Resp()

    monkeypatch.setattr(U, "_open", fake_open)
    monkeypatch.setattr(U.tempfile, "gettempdir", lambda: str(tmp_path))
    rel = _rel()
    path = U.download(rel, sleep=lambda s: None)
    assert tried == [rel.api_url, rel.asset_url, rel.api_url, rel.asset_url]
    assert open(path, "rb").read() == b"abc"


def test_download_gives_up_after_rounds(monkeypatch, tmp_path):
    def fake_open(url, accept=""):
        raise urllib.error.HTTPError(url, 504, "Gateway Time-out", {}, None)

    monkeypatch.setattr(U, "_open", fake_open)
    monkeypatch.setattr(U.tempfile, "gettempdir", lambda: str(tmp_path))
    with pytest.raises(urllib.error.HTTPError):
        U.download(_rel(), sleep=lambda s: None)
