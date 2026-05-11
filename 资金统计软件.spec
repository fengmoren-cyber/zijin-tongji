# -*- mode: python ; coding: utf-8 -*-
# =============================================================================
# 资金统计软件.spec  —  PyInstaller 打包配置
# 玉玄道·资金管理部
# =============================================================================
#
# 用法（本地调试打包）：
#   pyinstaller 资金统计软件.spec
#
# 产物：dist/资金统计软件.exe  （Windows）
#
# 注意：
#   · 通常不需要手动运行，由 GitHub Actions 自动执行
#   · 确保已安装：pip install pyinstaller customtkinter pillow openpyxl xlrd
# =============================================================================

import sys
from pathlib import Path

block_cipher = None
ROOT = Path(SPECPATH)   # project root（.spec 文件所在目录）

a = Analysis(
    # 入口脚本
    [str(ROOT / 'src' / '界面.py')],

    pathex=[str(ROOT / 'src')],

    binaries=[],

    # 需要打包进去的非 Python 数据文件
    datas=[
        # assets 目录（Logo + ICO）
        (str(ROOT / 'assets'), 'assets'),
        # 核心脚本（供 subprocess 调用）
        (str(ROOT / 'src' / '_核心库.py'),    '.'),
        (str(ROOT / 'src' / '生成报表.py'),   '.'),
        (str(ROOT / 'src' / '修正补录.py'),   '.'),
        # customtkinter 主题文件（必须打包）
        ('customtkinter', 'customtkinter'),
    ],

    hiddenimports=[
        'customtkinter',
        'PIL',
        'PIL._imaging',
        'PIL.Image',
        'PIL.ImageTk',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'xlrd',
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        '_tkinter',
        'packaging',
        'packaging.version',
        'packaging.specifiers',
        'packaging.requirements',
    ],

    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],

    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PyQt5',
        'PyQt6',
        'wx',
        'test',
        'unittest',
    ],

    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,

    # ── EXE 基本设置 ──────────────────────────────────
    name='资金统计软件',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                           # 启用 UPX 压缩（减小体积）
    upx_exclude=[],
    runtime_tmpdir=None,

    # ── 窗口模式（无控制台窗口） ─────────────────────
    console=False,
    windowed=True,

    # ── 图标 ─────────────────────────────────────────
    icon=str(ROOT / 'assets' / 'logo.ico'),

    # ── 单文件模式 ────────────────────────────────────
    onefile=True,

    # ── Windows 版本信息 ─────────────────────────────
    version=None,                       # 可补充 version_info 文件

    # ── DPI 感知（Windows 高分屏） ───────────────────
    uac_admin=False,
    uac_uiaccess=False,
)
