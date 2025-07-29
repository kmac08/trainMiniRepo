@echo off
echo ============================================================
echo TRAIN CONTROLLER SYSTEM - REMOTE GPIO STARTUP
echo ============================================================
echo.
echo This script will start the Train Controller System with
echo remote GPIO communication to Raspberry Pi.
echo.
echo Make sure:
echo 1. Raspberry Pi is connected via USB serial cable
echo 2. Pi GPIO handler is running: python3 pi_gpio_handler.py
echo 3. Physical GPIO buttons are connected to Pi
echo.
echo ============================================================
echo.

cd /d "%~dp0"

python start_with_remote_gpio.py

echo.
echo Press any key to exit...
pause > nul