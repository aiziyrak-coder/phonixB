#!/bin/bash

# Phoenix Scientific Platform - Backend Setup Script
# This script sets up and runs the Django backend

echo "================================================"
echo "🚀 Phoenix Scientific Platform - Backend Setup"
echo "================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install Python 3.11 or higher."
    exit 1
fi

echo "✓ Python3 found: $(python3 --version)"
echo ""

# Navigate to backend directory
cd "$(dirname "$0")"

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✓ Dependencies installed"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Using default settings."
    echo "   For production, please create .env file with proper configuration."
fi

# Run migrations
echo "🗄️  Running database migrations..."
python manage.py makemigrations
python manage.py migrate

if [ $? -ne 0 ]; then
    echo "❌ Migration failed"
    exit 1
fi

echo "✓ Database ready"
echo ""

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput --clear

echo ""

# Create superuser if needed
echo "👤 Create superuser? (y/n)"
read -r create_superuser

if [ "$create_superuser" = "y" ] || [ "$create_superuser" = "Y" ]; then
    python manage.py createsuperuser
fi

echo ""
echo "================================================"
echo "✅ Backend setup complete!"
echo "================================================"
echo ""
echo "🌐 Starting development server..."
echo "   Backend: http://127.0.0.1:8000"
echo "   Admin:   http://127.0.0.1:8000/admin"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
python manage.py runserver 0.0.0.0:8000
