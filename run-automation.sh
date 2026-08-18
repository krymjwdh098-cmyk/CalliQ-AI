#!/bin/bash
# CalliQ-AI - Automation Runner for Linux/Mac
# This script sets up environment and runs the automation

echo "========================================"
echo "CalliQ-AI Automation Setup"
echo "========================================"
echo ""

# Check if shell script exists
if [ ! -f "auto-deploy.sh" ]; then
    echo "ERROR: auto-deploy.sh not found"
    exit 1
fi

# Ask for API keys
echo "Please enter your API keys:"
echo ""
read -p "Enter Render API Key: " RENDER_KEY
read -p "Enter Groq API Key (optional, press Enter to skip): " GROQ_KEY
read -p "Enter Gemini API Key (optional, press Enter to skip): " GEMINI_KEY

# Set environment variables
export RENDER_API_KEY="$RENDER_KEY"
export GROQ_API_KEY="$GROQ_KEY"
export GEMINI_API_KEY="$GEMINI_KEY"

echo ""
echo "Starting automation..."
echo ""

# Make script executable and run
chmod +x auto-deploy.sh
./auto-deploy.sh
