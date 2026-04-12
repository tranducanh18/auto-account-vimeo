@echo off
:: ══════════════════════════════════════════════════════════════
::  Build vimeo_auto_tool_wg.exe  (yeu cau Admin tu dong qua UAC)
::  Chay file nay 1 lan de build .exe, sau do dung .exe binh thuong
:: ══════════════════════════════════════════════════════════════

:: Cai PyInstaller neu chua co
pip show pyinstaller >nul 2>&1 || pip install pyinstaller

:: Build
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "VimeoAutoTool" ^
    --manifest admin.manifest ^
    vimeo_auto_tool_wg.py

echo.
echo ═══════════════════════════════════════
echo  Build xong! File exe o: dist\VimeoAutoTool.exe
echo  Chay file nay se tu dong xin quyen Admin qua UAC.
echo ═══════════════════════════════════════
pause