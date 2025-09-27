@echo off
echo ========================================
echo CBO Flask Application - Apache Setup
echo ========================================
echo.

echo Checking Python installation...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo.
echo Running Apache setup...
python setup_apache_windows.py setup

echo.
echo Setup completed! Press any key to continue...
pause