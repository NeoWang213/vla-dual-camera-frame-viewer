@echo off
cd /d "%~dp0"
set "PYTHON="
if exist "G:\miniconda\envs\lerobot\python.exe" set "PYTHON=G:\miniconda\envs\lerobot\python.exe"
if not defined PYTHON for /f "delims=" %%P in ('where py 2^>nul') do if not defined PYTHON set "PYTHON=%%P"
if not defined PYTHON for /f "delims=" %%P in ('where python 2^>nul') do if not defined PYTHON set "PYTHON=%%P"
if not defined PYTHON goto no_python

"%PYTHON%" -c "import cv2, PIL" >nul 2>nul
if errorlevel 1 (
  echo OpenCV/Pillow are missing. Installing required packages...
  "%PYTHON%" -m pip install -r requirements_sync_video_viewer.txt
  if errorlevel 1 goto install_failed
)

"%PYTHON%" sync_video_viewer.py
if errorlevel 1 goto viewer_failed
exit /b 0

:no_python
echo Python 3 is not installed or not on PATH.
goto wait_exit

:install_failed
echo Dependency installation failed. Check network access and run this command manually:
echo "%PYTHON%" -m pip install -r requirements_sync_video_viewer.txt
goto wait_exit

:viewer_failed
echo The viewer exited with an error.

:wait_exit
echo.
echo Press Enter to close this window.
set /p "dummy="
