# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 설정 — packaging/build.ps1 에서 호출한다.
import os

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

# 쓰지 않는 Qt 모듈은 빼서 설치 파일 크기를 줄인다.
EXCLUDES = [
    "tkinter", "unittest", "pydoc", "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtPdf",
    "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets", "PySide6.QtDBus",
    "PySide6.QtConcurrent", "PySide6.QtXml", "PySide6.QtHelp", "PySide6.QtDesigner", "PySide6.QtUiTools",
]

a = Analysis(
    [os.path.join(ROOT, "run.py")],
    pathex=[os.path.join(ROOT, "src")],
    hiddenimports=["xlrd"],
    excludes=EXCLUDES,
    noarchive=False,
)

# Qt 번역·불필요 플러그인 제거(용량)
a.datas = [d for d in a.datas if "translations" not in d[0].replace("\\", "/")]
a.binaries = [
    b for b in a.binaries
    if not any(x in b[0] for x in ("Qt6Pdf", "Qt6Qml", "Qt6Quick", "Qt6Network", "Qt6OpenGL", "opengl32sw", "Qt6VirtualKeyboard"))
]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DongwonCheck",
    console=False,
    icon=os.path.join(ROOT, "assets", "app.ico"),
    version=os.path.join(ROOT, "build", "version_info.txt"),
    upx=False,
)

coll = COLLECT(exe, a.binaries, a.datas, name="DongwonCheck", upx=False)
