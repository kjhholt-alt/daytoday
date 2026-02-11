# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for DayToDay application.

Bundles:
- Django backend (with all services)
- React frontend (pre-built static files)
- SQLite database support
- win32com for Outlook/OneNote COM automation
- python-docx for Word document parsing

Build with:
    pyinstaller daytoday.spec
"""

import os
from pathlib import Path

# Project paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(SPEC))
BACKEND_DIR = os.path.join(PROJECT_ROOT, 'backend')
FRONTEND_BUILD = os.path.join(PROJECT_ROOT, 'frontend', 'build')
CONFIG_DIR = os.path.join(PROJECT_ROOT, 'config')

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'launcher.py')],
    pathex=[BACKEND_DIR],
    binaries=[],
    datas=[
        # Django backend code
        (os.path.join(BACKEND_DIR, 'core'), os.path.join('backend', 'core')),
        (os.path.join(BACKEND_DIR, 'daytoday_project'), os.path.join('backend', 'daytoday_project')),
        # React frontend build
        (FRONTEND_BUILD, os.path.join('frontend', 'build')),
        # Config template
        (os.path.join(CONFIG_DIR, 'config.template.json'), 'config'),
    ],
    hiddenimports=[
        # Django
        'django',
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'django.contrib.staticfiles.handlers',
        'django.db.backends.sqlite3',
        # DRF
        'rest_framework',
        'rest_framework.routers',
        'rest_framework.pagination',
        'rest_framework.filters',
        # CORS
        'corsheaders',
        # Our app
        'core',
        'core.models',
        'core.views',
        'core.serializers',
        'core.urls',
        'core.middleware',
        'core.services',
        'core.services.config_service',
        'core.services.summary_service',
        'core.services.win32_outlook_service',
        'core.services.win32_onenote_service',
        'core.services.word_service',
        'core.services.recording_service',
        'core.services.auth_service',
        'core.services.graph_client',
        'core.services.graph_calendar_service',
        'core.services.graph_onenote_service',
        'core.services.calendar_service',
        'core.services.onenote_service',
        'core.management',
        'core.management.commands',
        'core.management.commands.collect_today',
        # timezone
        'zoneinfo',
        # win32com
        'win32com',
        'win32com.client',
        'win32com.client.gencache',
        'pythoncom',
        'pywintypes',
        'win32api',
        # python-docx
        'docx',
        'docx.opc',
        # dateutil
        'dateutil',
        'dateutil.parser',
        # dotenv
        'dotenv',
        # MSAL (Graph API auth)
        'msal',
        'msal_extensions',
        # PyPDF2
        'PyPDF2',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'PIL',
        'cv2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DayToDay',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Keep console for logging output
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Can add an .ico file later
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DayToDay',
)
