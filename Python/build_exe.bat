@echo off
REM ============================================================================
REM Build script for STM32 PC Control App
REM Creates a Windows executable using PyInstaller.
REM ============================================================================

cd /d "%~dp0"

echo.
echo Installing/updating Python requirements...
py -m pip install --upgrade pip
py -m pip install -r requirements.txt

echo.
echo Cleaning previous build files...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist STM32_PC_Control.spec del STM32_PC_Control.spec

echo.
echo Building executable...
py -m PyInstaller ^
  --onefile ^
  --windowed ^
  --name STM32_PC_Control ^
  --hidden-import matplotlib.backends.backend_tkagg ^
  pc_control_app.py

echo.
echo Build completed.
echo The executable should be here:
echo %cd%\dist\STM32_PC_Control.exe
echo.
pause
