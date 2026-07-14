@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONLEGACYWINDOWSSTDIO=utf-8
cd /d "%~dp0"
python main.py --accounts 1 --headless 2>&1
