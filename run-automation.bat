@echo off
REM CalliQ-AI - Automation Runner for Windows
REM This script sets up environment and runs the automation

echo ========================================
echo CalliQ-AI Automation Setup
echo ========================================
echo.

REM Check if PowerShell script exists
if not exist auto-deploy.ps1 (
    echo ERROR: auto-deploy.ps1 not found
    pause
    exit /b 1
)

REM Ask for API keys
echo Please enter your API keys:
echo.
set /p RENDER_KEY="Enter Render API Key: "
set /p GROQ_KEY="Enter Groq API Key (optional, press Enter to skip): "
set /p GEMINI_KEY="Enter Gemini API Key (optional, press Enter to skip): "

REM Set environment variables
set RENDER_API_KEY=%RENDER_KEY%
set GROQ_API_KEY=%GROQ_KEY%
set GEMINI_API_KEY=%GEMINI_KEY%

echo.
echo Starting automation...
echo.

REM Run PowerShell script
powershell -ExecutionPolicy Bypass -File auto-deploy.ps1

pause
