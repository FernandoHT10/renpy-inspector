# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller standalone Windows specification for Ren'Py Inspector."""

from pathlib import Path

# Collect submodules and hidden imports
hiddenimports = [
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "renpy_inspector.cli.main",
    "renpy_inspector.gui.app",
    "renpy_inspector.gui.main_window",
    "renpy_inspector.gui.theme",
    "renpy_inspector.gui.worker",
    "renpy_inspector.gui.components.filter_bar",
    "renpy_inspector.gui.components.issue_details",
    "renpy_inspector.gui.components.issues_table",
    "renpy_inspector.gui.components.metric_cards",
    "renpy_inspector.gui.components.project_selector",
    "renpy_inspector.core.license.manager",
    "renpy_inspector.core.license.tier",
    "renpy_inspector.core.plugins.loader",
    "renpy_inspector.core.reporting.html_reporter",
    "renpy_inspector.core.reporting.json_reporter",
    "renpy_inspector.core.rules.assets.case_mismatch",
    "renpy_inspector.core.rules.assets.invalid_audio_channel",
    "renpy_inspector.core.rules.assets.missing_audio",
    "renpy_inspector.core.rules.assets.missing_font",
    "renpy_inspector.core.rules.assets.missing_image",
    "renpy_inspector.core.rules.assets.unused_asset",
    "renpy_inspector.core.rules.code.broken_call",
    "renpy_inspector.core.rules.code.broken_jump",
    "renpy_inspector.core.rules.code.conflicting_define_default",
    "renpy_inspector.core.rules.code.duplicate_label",
    "renpy_inspector.core.rules.code.shadow_builtin",
    "renpy_inspector.core.rules.code.undefined_screen",
    "renpy_inspector.core.rules.code.unused_label",
    "renpy_inspector.core.rules.translation.missing_translation",
]

block_cipher = None

a = Analysis(
    ["renpy_inspector/gui/app.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    [],
    name="RenPyInspector",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
