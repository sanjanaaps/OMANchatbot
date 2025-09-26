@echo off
echo Setting up Apache for Central Bank of Oman Chatbot...
echo.

REM Check if PowerShell is available
powershell -Command "Get-Host" >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: PowerShell is not available
    pause
    exit /b 1
)

REM Run the PowerShell setup script
echo Running Apache setup script...
powershell -ExecutionPolicy Bypass -File "setup_apache_windows.ps1"

if %errorlevel% equ 0 (
    echo.
    echo Setup completed successfully!
    echo.
    echo Next steps:
    echo 1. Start Apache service: net start Apache2.4
    echo 2. Start Flask backend: python run_app.py
    echo 3. Start Node.js API: node server.js
    echo 4. Or use: start_apache_services.bat
    echo.
    echo Access the application at: http://localhost
) else (
    echo.
    echo Setup failed! Please check the error messages above.
)

pause
