#!/bin/bash
# CalliQ-AI - Auto Deployment Script for Render
# This script automates the entire deployment process

set -e

echo "========================================"
echo "CalliQ-AI Auto-Deployment to Render"
echo "========================================"
echo ""

# Check if Git is installed
if ! command -v git &> /dev/null; then
    echo "✗ Git is not installed. Please install Git first."
    exit 1
fi
echo "✓ Git is installed: $(git --version)"

# Check if Render CLI is installed
if ! command -v render &> /dev/null; then
    echo "⚠ Render CLI is not installed. Installing..."
    curl -fsSL https://render.com/cli/install.sh | bash
    export PATH="$HOME/.render/bin:$PATH"
    echo "✓ Render CLI installed successfully"
else
    echo "✓ Render CLI is installed: $(render --version)"
fi

# Check environment variables
echo ""
echo "Checking environment variables..."

if [ -z "$RENDER_API_KEY" ]; then
    echo "✗ RENDER_API_KEY not found in environment variables"
    echo "Please set it using: export RENDER_API_KEY='your-api-key'"
    echo "Get your API key from: https://dashboard.render.com/user/settings"
    exit 1
else
    echo "✓ RENDER_API_KEY is set"
fi

if [ -z "$GROQ_API_KEY" ]; then
    echo "⚠ GROQ_API_KEY not found. You'll need to add it manually in Render dashboard"
    echo "Get your API key from: https://console.groq.com/keys"
else
    echo "✓ GROQ_API_KEY is set"
fi

if [ -z "$GEMINI_API_KEY" ]; then
    echo "⚠ GEMINI_API_KEY not found (optional)"
else
    echo "✓ GEMINI_API_KEY is set"
fi

# Validate render.yaml
echo ""
echo "Validating render.yaml..."
render blueprints validate
echo "✓ render.yaml is valid"

# Authenticate with Render
echo ""
echo "Authenticating with Render..."
render login --api-key "$RENDER_API_KEY"
echo "✓ Successfully authenticated with Render"

# Deploy services
echo ""
echo "Deploying services to Render..."
render blueprints apply render.yaml --skip-prompts
echo "✓ Services deployed successfully"

# Wait for deployment
echo ""
echo "Waiting for services to be ready (this may take 5-10 minutes)..."
sleep 60

# Get service information
echo ""
echo "Getting service information..."
render services list

# Display deployment summary
echo ""
echo "========================================"
echo "Deployment Summary"
echo "========================================"
echo ""
echo "🚀 Deployment completed successfully!"
echo ""
echo "Access your application:"
echo "- Frontend: https://calliq-frontend.onrender.com"
echo "- Backend API: https://calliq-api.onrender.com"
echo "- API Docs: https://calliq-api.onrender.com/api/docs"
echo ""
echo "Default login:"
echo "- Email: demo@company.com"
echo "- Password: demo1234"
echo ""
echo "Next steps:"
echo "1. Add GROQ_API_KEY to calliq-api service in Render dashboard"
echo "2. Add GEMINI_API_KEY (optional) to calliq-api service"
echo "3. Trigger a manual deploy after adding API keys"
echo ""
echo "To monitor deployment:"
echo "- Visit: https://dashboard.render.com"
echo "- Check logs for each service"
echo ""
