@echo off
REM ============================================================================
REM Debug build script for STM32 PC Control App
REM Creates an executable WITH console window, useful if the normal build fails.
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
if exist STM32_PC_Control_Debug.spec del STM32_PC_Control_Debug.spec

echo.
echo Building debug executable...
py -m PyInstaller ^
  --onefile ^
  --console ^
  --name STM32_PC_Control_Debug ^
  --hidden-import matplotlib.backends.backend_tkagg ^
  pc_control_app.py

echo.
echo Build completed.
echo The executable should be here:
echo %cd%\dist\STM32_PC_Control_Debug.exe
echo.
pause
