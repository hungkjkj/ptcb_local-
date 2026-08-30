@echo off
title AlphaQuant Local Server
color 0b
echo ===================================================
echo     ALPHA QUANT - HE THONG DINH LUONG CO PHIEU
echo ===================================================
echo.
echo Dang khoi dong may chu Cuc bo (Local Server)...
echo Vui long giu nguyen cua so nay khi su dung web!
echo.
cd /d "%~dp0"

REM Chờ 2 giây sau đó mở trình duyệt
start /b cmd /c "ping localhost -n 3 > nul & start http://localhost:8000"

python main.py

pause
