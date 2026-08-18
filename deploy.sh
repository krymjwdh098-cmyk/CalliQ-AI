#!/bin/bash
# TalentAI Deployment Script for Linux/Mac

set -e

echo "======================================"
echo "TalentAI Deployment Script"
echo "======================================"
echo ""

# Check if Docker is running
if ! docker --version > /dev/null 2>&1; then
    echo "ERROR: Docker is not installed or not running"
    echo "Please install Docker from https://docs.docker.com/get-docker/"
    exit 1
fi

echo "Docker is running..."
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Creating .env file from .env.production..."
    cp .env.production .env
    echo ""
    echo "IMPORTANT: Please edit .env file with your configuration:"
    echo "- Change SECRET_KEY"
    echo "- Update DATABASE_URL with secure password"
    echo "- Add your API keys (GROQ_API_KEY, etc.)"
    echo ""
    read -p "Press Enter to continue after editing .env file..."
fi

# Create uploads directory if it doesn't exist
mkdir -p Backend/uploads

echo "Building Docker images..."
docker-compose build

echo ""
echo "Starting services..."
docker-compose up -d

echo ""
echo "======================================"
echo "Deployment successful!"
echo "======================================"
echo ""
echo "Access the application:"
echo "- Frontend: http://localhost"
echo "- Backend API: http://localhost:8000"
echo "- API Documentation: http://localhost:8000/api/docs"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop services: docker-compose down"
echo ""
