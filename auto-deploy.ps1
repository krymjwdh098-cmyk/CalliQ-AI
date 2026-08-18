# CalliQ-AI - Auto Deployment Script for Render
# This script automates the entire deployment process

param(
    [Parameter(Mandatory=$false)]
    [switch]$SkipSetup = $false
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CalliQ-AI Auto-Deployment to Render" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Git is installed
try {
    $gitVersion = git --version
    Write-Host "✓ Git is installed: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Git is not installed. Please install Git first." -ForegroundColor Red
    exit 1
}

# Check if Render CLI is installed
try {
    $renderVersion = render --version
    Write-Host "✓ Render CLI is installed: $renderVersion" -ForegroundColor Green
} catch {
    Write-Host "⚠ Render CLI is not installed. Installing..." -ForegroundColor Yellow
    try {
        Invoke-WebRequest -Uri "https://render.com/cli/install.ps1" -OutFile "install-render.ps1"
        & .\install-render.ps1
        Remove-Item "install-render.ps1"
        Write-Host "✓ Render CLI installed successfully" -ForegroundColor Green
    } catch {
        Write-Host "✗ Failed to install Render CLI" -ForegroundColor Red
        exit 1
    }
}

# Check environment variables
Write-Host ""
Write-Host "Checking environment variables..." -ForegroundColor Cyan

$renderApiKey = $env:RENDER_API_KEY
$groqApiKey = $env:GROQ_API_KEY
$geminiApiKey = $env:GEMINI_API_KEY

if (-not $renderApiKey) {
    Write-Host "✗ RENDER_API_KEY not found in environment variables" -ForegroundColor Red
    Write-Host "Please set it using: $env:RENDER_API_KEY = 'your-api-key'" -ForegroundColor Yellow
    Write-Host "Get your API key from: https://dashboard.render.com/user/settings" -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "✓ RENDER_API_KEY is set" -ForegroundColor Green
}

if (-not $groqApiKey) {
    Write-Host "⚠ GROQ_API_KEY not found. You'll need to add it manually in Render dashboard" -ForegroundColor Yellow
    Write-Host "Get your API key from: https://console.groq.com/keys" -ForegroundColor Yellow
} else {
    Write-Host "✓ GROQ_API_KEY is set" -ForegroundColor Green
}

if (-not $geminiApiKey) {
    Write-Host "⚠ GEMINI_API_KEY not found (optional)" -ForegroundColor Yellow
} else {
    Write-Host "✓ GEMINI_API_KEY is set" -ForegroundColor Green
}

# Validate render.yaml
Write-Host ""
Write-Host "Validating render.yaml..." -ForegroundColor Cyan
try {
    render blueprints validate
    Write-Host "✓ render.yaml is valid" -ForegroundColor Green
} catch {
    Write-Host "✗ render.yaml validation failed" -ForegroundColor Red
    exit 1
}

# Authenticate with Render
Write-Host ""
Write-Host "Authenticating with Render..." -ForegroundColor Cyan
try {
    render login --api-key $renderApiKey
    Write-Host "✓ Successfully authenticated with Render" -ForegroundColor Green
} catch {
    Write-Host "✗ Authentication failed. Please check your RENDER_API_KEY" -ForegroundColor Red
    exit 1
}

# Deploy services
Write-Host ""
Write-Host "Deploying services to Render..." -ForegroundColor Cyan
try {
    render blueprints apply render.yaml --skip-prompts
    Write-Host "✓ Services deployed successfully" -ForegroundColor Green
} catch {
    Write-Host "✗ Deployment failed" -ForegroundColor Red
    exit 1
}

# Wait for deployment
Write-Host ""
Write-Host "Waiting for services to be ready (this may take 5-10 minutes)..." -ForegroundColor Cyan
Start-Sleep -Seconds 60

# Get service information
Write-Host ""
Write-Host "Getting service information..." -ForegroundColor Cyan
try {
    $services = render services list --output json
    Write-Host "✓ Services retrieved" -ForegroundColor Green
    Write-Host $services
} catch {
    Write-Host "⚠ Could not retrieve service information" -ForegroundColor Yellow
}

# Display deployment summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deployment Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "🚀 Deployment completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Access your application:" -ForegroundColor Cyan
Write-Host "- Frontend: https://calliq-frontend.onrender.com" -ForegroundColor White
Write-Host "- Backend API: https://calliq-api.onrender.com" -ForegroundColor White
Write-Host "- API Docs: https://calliq-api.onrender.com/api/docs" -ForegroundColor White
Write-Host ""
Write-Host "Default login:" -ForegroundColor Cyan
Write-Host "- Email: demo@company.com" -ForegroundColor White
Write-Host "- Password: demo1234" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Add GROQ_API_KEY to calliq-api service in Render dashboard" -ForegroundColor White
Write-Host "2. Add GEMINI_API_KEY (optional) to calliq-api service" -ForegroundColor White
Write-Host "3. Trigger a manual deploy after adding API keys" -ForegroundColor White
Write-Host ""
Write-Host "To monitor deployment:" -ForegroundColor Cyan
Write-Host "- Visit: https://dashboard.render.com" -ForegroundColor White
Write-Host "- Check logs for each service" -ForegroundColor White
Write-Host ""
