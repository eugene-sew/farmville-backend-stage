#!/bin/bash

# Exit on any error
set -e

echo "Starting FarmVile Backend..."

# Download model from S3 if not exists
if [ ! -d "/app/models/plantdisease_savedmodel" ]; then
    echo "Downloading ML model from S3..."
    MODEL_S3_URL=${MODEL_S3_URL:-"https://models-bucket-eudev.s3.eu-north-1.amazonaws.com/plantdisease_savedmodel.zip"}
    mkdir -p /app/models
    curl -L "$MODEL_S3_URL" -o /tmp/model.zip && unzip -q /tmp/model.zip -d /app/models/ && rm /tmp/model.zip
    echo "Model downloaded successfully"
fi

# Wait for any dependencies (not needed for SQLite, but good practice)
echo "Checking system readiness..."

# Run database migrations
echo "Running database migrations..."
python manage.py migrate

# Create superuser if it doesn't exist
echo "Creating superuser if needed..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@farmville.com', 'admin123', role='admin')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
EOF

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the Django development server
echo "Starting Django server on 0.0.0.0:8000..."
exec python manage.py runserver 0.0.0.0:8000
