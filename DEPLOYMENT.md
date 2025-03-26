# SpendiZO Expense Tracker - Deployment Guide

This document provides detailed instructions for deploying the SpendiZO Expense Tracker application using different methods.

## Prerequisites

- Python 3.9+ (Python 3.13.2 is currently installed)
- pip package manager
- Virtual environment (venv)

## Method 1: Local Deployment with Gunicorn

1. **Activate the virtual environment**:
   ```
   source .venv/bin/activate  # On macOS/Linux
   # or
   .venv\Scripts\activate  # On Windows
   ```

2. **Install dependencies**:
   ```
   pip install -r requirements.txt
   ```
   
   Note: If you encounter issues with psycopg2, install the binary version:
   ```
   pip install psycopg2-binary
   ```

3. **Configure environment variables**:
   Update the `.env` file with appropriate values:
   ```
   FLASK_ENV=production
   FLASK_APP=app.py
   SECRET_KEY=your-secure-secret-key
   DATABASE_URL=sqlite:///database.db
   ```

4. **Run the application with Gunicorn**:
   ```
   gunicorn --bind 0.0.0.0:8000 app:app
   ```

5. **Access the application**:
   Open your browser and navigate to `http://localhost:8000`

## Method 2: Docker Deployment

1. **Install Docker and Docker Compose** if not already installed.

2. **Configure environment variables**:
   Update the `docker-compose.yml` file with appropriate values for:
   - SECRET_KEY
   - DATABASE_URL (SQLite or PostgreSQL)

3. **Build and start the containers**:
   ```
   docker-compose up --build
   ```

4. **Access the application**:
   Open your browser and navigate to `http://localhost:5000`

### Using PostgreSQL with Docker

To use PostgreSQL instead of SQLite:

1. Uncomment the PostgreSQL configuration in `docker-compose.yml`:
   ```yaml
   environment:
     - DATABASE_URL=postgresql://postgres:postgres@db:5432/expense_tracker
   ```

2. Ensure the database service is properly configured.

## Method 3: Heroku Deployment

1. **Install the Heroku CLI** and log in:
   ```
   brew install heroku/brew/heroku  # On macOS
   heroku login
   ```

2. **Create a new Heroku app**:
   ```
   heroku create your-app-name
   ```

3. **Set environment variables**:
   ```
   heroku config:set SECRET_KEY=your-secure-secret-key
   heroku config:set FLASK_ENV=production
   ```

4. **Add PostgreSQL database**:
   ```
   heroku addons:create heroku-postgresql:hobby-dev
   ```

5. **Deploy the application**:
   ```
   git push heroku main
   ```

6. **Open the application**:
   ```
   heroku open
   ```

## Cloud Storage Configuration

For production deployment, configure cloud storage for receipt uploads:

### Amazon S3

Add to `.env`:
```
STORAGE_TYPE=s3
S3_BUCKET=your-s3-bucket-name
S3_ACCESS_KEY=your-s3-access-key
S3_SECRET_KEY=your-s3-secret-key
```

### Google Cloud Storage

Add to `.env`:
```
STORAGE_TYPE=gcs
GCS_BUCKET=your-gcs-bucket-name
```

## Security Considerations

1. Use a strong, unique SECRET_KEY in production
2. Ensure all sensitive environment variables are properly secured
3. Use HTTPS in production environments
4. Regularly update dependencies to address security vulnerabilities

## Troubleshooting

- **Database connection issues**: Verify the DATABASE_URL is correctly configured
- **File upload problems**: Check cloud storage configuration and permissions
- **Application errors**: Check the application logs with `heroku logs --tail` or Docker logs