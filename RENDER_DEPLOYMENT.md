# CalliQ-AI - Render Deployment Guide

## 🚀 Deploy to Render

### Prerequisites
- GitHub repository with the code (already done!)
- Render account (free tier available)
- API keys for LLM providers (Groq recommended for free tier)

### Step 1: Create Render Account
1. Go to [render.com](https://render.com)
2. Sign up using GitHub
3. Verify your email

### Step 2: Deploy via render.yaml (Recommended)

1. **Connect Render to GitHub**
   - Go to Render Dashboard
   - Click "New +"
   - Select "Blueprint"
   - Connect your GitHub account
   - Select the `CalliQ-AI` repository

2. **Review Configuration**
   - Render will read the `render.yaml` file
   - Review the services and resources
   - Click "Apply" to create all resources

3. **Add Environment Variables**
   - Go to your Backend service (`calliq-api`)
   - Add these environment variables:
     - `GROQ_API_KEY`: Your Groq API key (get from [console.groq.com](https://console.groq.com/keys))
     - `GEMINI_API_KEY`: Your Gemini API key (optional, get from [aistudio.google.com](https://aistudio.google.com/apikey))

### Step 3: Manual Deployment (Alternative)

If you prefer manual deployment:

#### Deploy PostgreSQL Database
1. Go to Render Dashboard → New → PostgreSQL
2. Name: `calliq-db`
3. Database: `calliq`
4. User: `calliq_user`
5. Region: Choose nearest to your users
6. Click "Create Database"

#### Deploy Redis
1. Go to Render Dashboard → New → Redis
2. Name: `calliq-redis`
3. Region: Same as database
4. Click "Create Redis"

#### Deploy Backend API
1. Go to Render Dashboard → New → Web Service
2. Connect GitHub → Select `CalliQ-AI` repository
3. Settings:
   - Name: `calliq-api`
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `chmod +x Backend/start.sh && ./Backend/start.sh`
4. Environment Variables:
   - `DATABASE_URL`: (From PostgreSQL connection string)
   - `REDIS_URL`: (From Redis connection string)
   - `SECRET_KEY`: (Generate secure key)
   - `ENVIRONMENT`: `production`
   - `DEBUG`: `false`
   - `LLM_PROVIDER`: `groq`
   - `GROQ_API_KEY`: Your Groq API key
   - `GROQ_MODEL`: `llama-3.3-70b-versatile`
5. Click "Create Web Service"

#### Deploy Frontend
1. Go to Render Dashboard → New → Static Site
2. Connect GitHub → Select `CalliQ-AI` repository
3. Settings:
   - Name: `calliq-frontend`
   - Build Command: `cd frontend && npm install && npm run build`
   - Publish Directory: `frontend/dist`
4. Environment Variables:
   - `VITE_API_URL`: `https://calliq-api.onrender.com`
5. Click "Create Static Site"

#### Deploy Celery Worker
1. Go to Render Dashboard → New → Worker
2. Connect GitHub → Select `CalliQ-AI` repository
3. Settings:
   - Name: `calliq-worker`
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `cd Backend && celery -A workers.celery_app worker --loglevel=info`
4. Environment Variables:
   - `DATABASE_URL`: (Same as backend)
   - `REDIS_URL`: (Same as backend)
   - `CELERY_BROKER_URL`: (Same as REDIS_URL)
   - `CELERY_RESULT_BACKEND`: (Same as REDIS_URL)
   - `SECRET_KEY`: (Same as backend)
   - `LLM_PROVIDER`: `groq`
   - `GROQ_API_KEY`: Your Groq API key
5. Click "Create Worker"

### Step 4: Configure API Keys

#### Get Groq API Key (Free)
1. Go to [console.groq.com](https://console.groq.com/keys)
2. Sign up (free)
3. Create API key
4. Copy and add to Render environment variables

#### Get Gemini API Key (Free Alternative)
1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Sign in with Google
3. Create API key
4. Copy and add to Render environment variables

### Step 5: Access Your Application

After deployment:
- **Frontend**: `https://calliq-frontend.onrender.com`
- **Backend API**: `https://calliq-api.onrender.com`
- **API Docs**: `https://calliq-api.onrender.com/api/docs`

Default login:
- Email: `demo@company.com`
- Password: `demo1234`

## 🔧 Troubleshooting

### Backend fails to start
- Check logs in Render Dashboard
- Verify environment variables are set correctly
- Ensure database connection string is correct

### Frontend can't connect to API
- Verify `VITE_API_URL` is correct
- Check if backend is running
- Verify CORS settings in backend

### Database connection issues
- Ensure PostgreSQL is running
- Check connection string format
- Verify database user permissions

### Redis connection issues
- Ensure Redis is running
- Check connection string format
- Verify Redis URL format

## 📊 Monitoring

### View Logs
- Go to service in Render Dashboard
- Click "Logs" tab
- Real-time logs are displayed

### Health Checks
- Backend: `https://calliq-api.onrender.com/health`
- API Docs: `https://calliq-api.onrender.com/api/docs`

## 💰 Cost Estimate (Render Free Tier)

- PostgreSQL: Free tier available
- Redis: ~$7/month (or use alternative)
- Web Service: Free tier (512MB RAM)
- Static Site: Free
- Worker: Free tier (512MB RAM)

**Estimated cost**: ~$7/month (mostly for Redis)

## 🔄 Updates

To update your application:
1. Push changes to GitHub
2. Render automatically detects and rebuilds
3. Monitor deployment in Render Dashboard

## 🛡️ Security

- Never commit API keys to GitHub
- Use Render's environment variables
- Enable SSL (automatic on Render)
- Use strong database passwords
- Regular security updates

## 📞 Support

- Render Docs: [docs.render.com](https://docs.render.com)
- GitHub Issues: [github.com/krymjwdh098-cmyk/CalliQ-AI/issues](https://github.com/krymjwdh098-cmyk/CalliQ-AI/issues)
