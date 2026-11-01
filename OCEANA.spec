# PyInstaller spec for a self-contained Windows build.
from PyInstaller.utils.hooks import collect_all
from PyInstaller.building.build_main import Analysis, PYZ, EXE

pyside_datas, pyside_binaries, pyside_hidden = collect_all('PySide6')
lupa_datas, lupa_binaries, lupa_hidden = collect_all('lupa')

a = Analysis(
    ['main.pyw'],
    pathex=[],
    binaries=pyside_binaries + lupa_binaries,
    datas=pyside_datas + lupa_datas,
    hiddenimports=pyside_hidden + lupa_hidden + ['runner'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='OCEANA',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)
