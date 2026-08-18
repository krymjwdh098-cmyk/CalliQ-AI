# TalentAI - Deployment Guide

## 🚀 Production Deployment

### System Requirements
- **Backend:** Python 3.10+, 2GB RAM minimum, 4GB recommended
- **Frontend:** Node.js 18+, 1GB RAM
- **Database:** SQLite (default) or PostgreSQL (recommended for production)
- **Optional:** Redis for production rate limiting and Celery

### Load Balancing Configuration
The system now supports automatic load balancing between multiple LLM providers:
- **Groq:** Primary provider (fast, cost-effective)
- **Gemini:** Secondary provider (backup)
- **Rotation:** Automatic round-robin between available providers

### Rate Limiting (Production Optimized)
- **Public CV Upload:** 20 requests/IP per minute
- **Login Attempts:** 10 attempts/IP per minute  
- **General API:** 500 requests/IP per minute
- **Bulk Upload:** 10 requests/user per minute
- **Chat:** 60 requests/user per minute

### Batch Processing
- **Concurrent Processing:** 10 CVs simultaneously
- **Batch Size:** 20-50 CVs per batch
- **Retry Attempts:** 3 automatic retries

### Deployment Steps

#### 1. Backend Setup
```bash
cd Backend
pip install -r requirements.txt
python main.py
```

#### 2. Frontend Setup
```bash
cd frontend
npm install
npm run build
# Serve dist/ folder with nginx or similar
```

#### 3. Environment Variables
Copy `.env.example` to `.env` and configure:
- `ENVIRONMENT=production`
- `DEBUG=false`
- `SECRET_KEY` (generate strong secret)
- `DATABASE_URL` (PostgreSQL recommended)
- `LLM_PROVIDER=groq` (or leave empty for auto-rotation)
- API keys for Groq/Gemini

#### 4. Database Setup
```bash
# For PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/talentai_db

# Run migrations
python migrate.py
```

#### 5. Optional: Redis + Celery
```bash
# Start Redis
redis-server

# Start Celery worker
celery -A workers.tasks worker --loglevel=info --concurrency=4

# Update .env
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### Authentication Changes
- **Registration:** Full name + Email + Password + Organization name (all fields visible to public)
- **Login:** Password-based authentication
- **Public Access:** Registration page is accessible to anyone without authentication

### Scaling Recommendations
- **Small deployment:** SQLite + in-memory rate limiting (current setup)
- **Medium deployment:** PostgreSQL + Redis + 2 Celery workers
- **Large deployment:** PostgreSQL + Redis + 4+ Celery workers + Load balancer

### Monitoring
- Check logs for LLM provider rotation
- Monitor rate limiting hits
- Track batch processing performance
- Monitor database connection pool

### Security Notes
- Change `SECRET_KEY` before production
- Use HTTPS in production
- Configure CORS properly
- Enable firewall rules
- Regular database backups

### Troubleshooting
- **LLM Failures:** System automatically rotates providers
- **Rate Limiting:** Check Redis connection if using Redis backend
- **Slow Processing:** Increase `BATCH_MAX_CONCURRENT` or add Celery workers
- **Database Issues:** Switch to PostgreSQL for better performance