@echo off
REM TalentAI Deployment Script for Windows

echo ======================================
echo TalentAI Deployment Script
echo ======================================
echo.

REM Check if Docker is running
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not running
    echo Please install Docker Desktop from https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

echo Docker is running...
echo.

REM Check if .env file exists
if not exist .env (
    echo Creating .env file from .env.production...
    copy .env.production .env
    echo.
    echo IMPORTANT: Please edit .env file with your configuration:
    echo - Change SECRET_KEY
    echo - Update DATABASE_URL with secure password
    echo - Add your API keys (GROQ_API_KEY, etc.)
    echo.
    pause
)

REM Create uploads directory if it doesn't exist
if not exist Backend\uploads mkdir Backend\uploads

echo Building Docker images...
docker-compose build

if %errorlevel% neq 0 (
    echo ERROR: Docker build failed
    pause
    exit /b 1
)

echo.
echo Starting services...
docker-compose up -d

if %errorlevel% neq 0 (
    echo ERROR: Failed to start services
    pause
    exit /b 1
)

echo.
echo ======================================
echo Deployment successful!
echo ======================================
echo.
echo Access the application:
echo - Frontend: http://localhost
echo - Backend API: http://localhost:8000
echo - API Documentation: http://localhost:8000/api/docs
echo.
echo To view logs: docker-compose logs -f
echo To stop services: docker-compose down
echo.
pause
