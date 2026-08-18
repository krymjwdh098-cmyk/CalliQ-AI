#!/bin/bash
# Render startup script for Backend

# Change to Backend directory
cd Backend

# Create uploads directory
mkdir -p uploads

# Initialize database
python -c "from models.database import init_db; init_db()"

# Start the application
uvicorn main:app --host 0.0.0.0 --port $PORT
