# SpendiZO - Expense Tracker

A comprehensive expense tracking application built with Flask that allows users to track expenses, set budgets, and generate reports.

## Features

- User authentication (local and Google OAuth)
- Expense tracking with receipt uploads
- Budget planning and monitoring
- Monthly expense reports
- Data visualization with charts

## Deployment Guide

### Prerequisites

- Python 3.9+
- pip package manager
- Git (optional)

### Local Deployment

1. Clone or download the repository
2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Set up environment variables by creating a `.env` file with the following:
   ```
   FLASK_ENV=production
   FLASK_APP=app.py
   SECRET_KEY=your-secure-secret-key
   DATABASE_URL=sqlite:///database.db
   GOOGLE_CLIENT_ID=your-google-client-id  # Optional for Google OAuth
   GOOGLE_CLIENT_SECRET=your-google-client-secret  # Optional for Google OAuth
   ```
5. Run the application:
   ```
   flask run
   ```
   or
   ```
   gunicorn app:app
   ```

### Heroku Deployment

1. Create a Heroku account and install the Heroku CLI
2. Login to Heroku CLI:
   ```
   heroku login
   ```
3. Create a new Heroku app:
   ```
   heroku create your-app-name
   ```
4. Set environment variables in Heroku:
   ```
   heroku config:set SECRET_KEY=your-secure-secret-key
   heroku config:set FLASK_ENV=production
   ```
5. If using Google OAuth, set the Google credentials:
   ```
   heroku config:set GOOGLE_CLIENT_ID=your-google-client-id
   heroku config:set GOOGLE_CLIENT_SECRET=your-google-client-secret
   ```
6. Deploy to Heroku:
   ```
   git push heroku main
   ```

### Database Configuration

For production, you may want to use a more robust database like PostgreSQL:

1. For Heroku, add the PostgreSQL addon:
   ```
   heroku addons:create heroku-postgresql:hobby-dev
   ```
2. Update the `DATABASE_URL` environment variable to use the PostgreSQL connection string
3. Modify the database connection code in `app.py` to support PostgreSQL

### File Storage

For production deployment, consider using cloud storage services like AWS S3 or Google Cloud Storage for storing receipt images instead of local file storage.

## Security Considerations

1. Always use HTTPS in production
2. Generate a strong SECRET_KEY for production
3. Never commit sensitive information to version control
4. Regularly update dependencies to patch security vulnerabilities

## Maintenance

- Regularly backup your database
- Monitor application logs for errors
- Keep dependencies updated

## License

This project is licensed under the MIT License - see the LICENSE file for details.