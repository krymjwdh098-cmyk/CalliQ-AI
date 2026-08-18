# TalentAI - Quick Start Guide

## Fastest Way to Start (Windows)

```bash
# Run the deployment script
deploy.bat
```

## Fastest Way to Start (Linux/Mac)

```bash
# Make script executable
chmod +x deploy.sh

# Run the deployment script
./deploy.sh
```

## Manual Setup

### 1. Install Docker
- Windows: https://www.docker.com/products/docker-desktop
- Mac: https://docs.docker.com/desktop/install/mac-install/
- Linux: https://docs.docker.com/engine/install/

### 2. Configure Environment
```bash
# Copy production environment
cp .env.production .env

# Generate secure secret key
python -c "import secrets; print(secrets.token_urlsafe(64))"

# Edit .env with your settings
# - Replace SECRET_KEY with generated key
# - Add your API keys (GROQ_API_KEY, etc.)
# - Update database password
```

### 3. Deploy
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Access Points

- **Frontend**: http://localhost
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs
- **Default User**: demo@company.com / demo1234

## Troubleshooting

### Docker not starting
- Make sure Docker Desktop is running
- Check if port 80, 8000, 5432, 6379 are available

### Backend errors
```bash
# Check backend logs
docker-compose logs backend

# Restart backend
docker-compose restart backend
```

### Database issues
```bash
# Restart database
docker-compose restart postgres

# Check database logs
docker-compose logs postgres
```

## Next Steps

- Configure your LLM API keys (Groq is recommended for free tier)
- Set up SSL certificates for production
- Configure domain name
- Set up regular backups

For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md)
