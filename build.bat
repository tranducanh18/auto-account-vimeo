@echo off
echo ========================================
echo   VIMEO AUTO TOOL - BUILD RAR
echo ========================================

:: Cài thư viện
echo [1/4] Cai dat thu vien...
pip install selenium undetected-chromedriver pyinstaller

:: Xóa thư mục cũ
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "VimeoTool.spec" del /q VimeoTool.spec

:: Build exe
echo [2/4] Build exe...
pyinstaller --noconfirm --onefile --windowed --name "VimeoTool" gui.py

:: Kiểm tra build thành công
if not exist "dist\VimeoTool.exe" (
    echo ❌ Build that bai!
    pause
    exit /b 1
)

:: Tạo thư mục tạm
echo [3/4] Chuan bi dong goi...
if exist "VimeoTool_Temp" rmdir /s /q VimeoTemp
mkdir VimeoTemp

:: Copy file exe
copy "dist\VimeoTool.exe" "VimeoTemp\"

:: Tạo file README
echo Tao file README.txt...
(
echo ========================================
echo    VIMEO AUTO TOOL
echo ========================================
echo.
echo CACH DUNG:
echo 1. Chay file VimeoTool.exe
echo 2. Nhap thong tin email
echo 3. Nhan START
echo.
echo FILE TAO RA:
echo - accounts.txt: tai khoan tao thanh cong
echo - email_failed.txt: email bi loi
) > "VimeoTemp\README.txt"

:: Đóng gói RAR
echo [4/4] Dong goi RAR...

:: Thử đường dẫn WinRAR phổ biến
if exist "C:\Program Files\WinRAR\WinRAR.exe" (
    "C:\Program Files\WinRAR\WinRAR.exe" a -ep1 -r "VimeoTool.rar" "VimeoTemp\*.*"
    echo ✅ Da tao file VimeoTool.rar
) else if exist "C:\Program Files (x86)\WinRAR\WinRAR.exe" (
    "C:\Program Files (x86)\WinRAR\WinRAR.exe" a -ep1 -r "VimeoTool.rar" "VimeoTemp\*.*"
    echo ✅ Da tao file VimeoTool.rar
) else (
    echo ⚠️ Khong tim thay WinRAR!
    echo Thu dung 7-Zip...
    if exist "C:\Program Files\7-Zip\7z.exe" (
        "C:\Program Files\7-Zip\7z.exe" a -tzip "VimeoTool.zip" "VimeoTemp\*.*"
        echo ✅ Da tao file VimeoTool.zip
    ) else (
        echo ❌ Khong tim thay WinRAR hoac 7-Zip
        echo Vui long tu nen thu muc VimeoTemp thanh VimeoTool.rar
    )
)

:: Dọn dẹp
rmdir /s /q VimeoTemp

echo.
echo ========================================
echo   HOAN TAT!
echo ========================================
if exist "VimeoTool.rar" echo File da tao: VimeoTool.rar
if exist "VimeoTool.zip" echo File da tao: VimeoTool.zip
echo.
echo Nhan phim bat ky de thoat...
pause > nul