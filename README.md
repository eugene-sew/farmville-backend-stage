# FarmVille Backend - AI Crop Disease Detection & Management System

A Django REST API backend for the FarmVille agricultural platform, featuring AI-powered crop disease detection using TensorFlow and intelligent recommendations via Google's Gemini API.

## Features

- **Role-based Authentication**: JWT authentication for Farmers and Admins
- **AI Disease Detection**: TensorFlow model integration for crop disease identification
- **Smart Recommendations**: Gemini AI-powered treatment suggestions
- **Admin Dashboard**: Review and approve AI recommendations
- **Image Processing**: Support for multiple image formats with preprocessing
- **RESTful API**: Complete API for frontend integration
- **Production Ready**: Docker support, logging, and security features

## Tech Stack

- **Framework**: Django 5.0.8 + Django REST Framework
- **Database**: SQLite (default) / PostgreSQL (production)
- **ML/AI**: TensorFlow 2.17.0, Google Gemini API
- **Task Queue**: Celery + Redis
- **Authentication**: JWT (djangorestframework-simplejwt)
- **Documentation**: OpenAPI/Swagger

## Quick Start

### 1. Clone and Setup

```bash
cd farmville-backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Database Setup

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 4. Run Development Server

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/`

## API Endpoints

### Authentication
- `POST /api/auth/register/` - Register new user
- `POST /api/auth/login/` - Login and get JWT tokens
- `GET /api/auth/profile/` - Get user profile
- `POST /api/auth/token/refresh/` - Refresh JWT token

### Analysis (Farmers)
- `POST /api/analysis/upload/` - Upload images for disease detection
- `GET /api/analysis/history/` - Get analysis history with filtering
- `GET /api/analysis/{id}/` - Get detailed analysis results

### Admin Dashboard
- `GET /api/admin/pending/` - Get pending recommendations
- `POST /api/admin/review/{id}/` - Approve/reject recommendations
- `GET /api/admin/stats/` - Dashboard statistics

### Documentation
- `GET /api/docs/` - Swagger UI documentation
- `GET /api/schema/` - OpenAPI schema

## ML Model Integration

### Model Requirements
- **Format**: TensorFlow SavedModel or .keras format
- **Input**: RGB images, 224x224 pixels
- **Output**: Disease classification with confidence scores

### Model Setup
1. Place your trained model in the `models/` directory
2. Update `TF_MODEL_PATH` in settings
3. Ensure model classes match the predefined class names in `ml_service.py`

### Preprocessing Pipeline
```python
# Images are automatically:
# 1. Converted to RGB
# 2. Resized to 224x224
# 3. Normalized to [0,1] range
# 4. Batched for inference
```

## Gemini AI Integration

### Setup
1. Get Gemini API key from Google AI Studio
2. Set `GEMINI_API_KEY` in environment variables
3. The system includes fallback recommendations if Gemini is unavailable

### Recommendation Generation
- Analyzes crop type, disease, and severity
- Provides actionable treatment steps
- Includes safety warnings and prevention tips
- Supports location-based recommendations

## Frontend Integration

### Response Format
The API returns data in the exact format expected by the Next.js frontend:

```json
{
  "analysis_id": "uuid",
  "id": "uuid",
  "crop_type": "Tomato",
  "disease": "Late Blight",
  "confidence": "89%",
  "severity": "high",
  "results": [...],
  "recommendations": [...]
}
```

### CORS Configuration
- Configured for `http://localhost:3000` (Next.js default)
- Supports credentials for JWT authentication
- Easily configurable via environment variables

## Docker Deployment

### Development
```bash
docker-compose up
```

### Production
```bash
# Build and run
docker build -t farmville-backend .
docker run -p 8000:8000 farmville-backend
```

## Configuration

### Environment Variables
```bash
# Required
SECRET_KEY=your-secret-key
GEMINI_API_KEY=your-gemini-key

# Optional
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourfrontend.com
TF_MODEL_PATH=models/your_model
MAX_IMAGE_SIZE_MB=12
```

### Database Configuration
```bash
# PostgreSQL (Production)
DB_NAME=farmville
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432
```

## Testing

### Run Tests
```bash
python manage.py test
```

### API Testing
Use the included Postman collection or test via Swagger UI at `/api/docs/`

## Model Compatibility

### TensorFlow Version
- **Supported**: TensorFlow 2.15.0 - 2.17.0
- **Python**: 3.11+ recommended
- **GPU**: CUDA 11.8+ (optional)

### Model Export
Ensure your model is exported with:
```python
model.save('plantdisease_savedmodel', save_format='tf')
# or
model.save('model.keras')
```

## Security Features

- JWT authentication with refresh tokens
- CORS protection
- File upload validation
- SQL injection protection
- XSS protection
- Rate limiting ready (add django-ratelimit)

## Monitoring & Logging

- Structured logging to `farmville.log`
- ML prediction logging
- Gemini API request tracking
- Error tracking ready (add Sentry)

## Performance Optimization

- Model loaded once at startup
- Batch image processing
- Database query optimization
- Static file serving with WhiteNoise
- Ready for Redis caching

## Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Configure proper `SECRET_KEY`
- [ ] Set up PostgreSQL database
- [ ] Configure Redis for Celery
- [ ] Set up proper CORS origins
- [ ] Configure file storage (S3/CloudFront)
- [ ] Set up monitoring (Sentry, Prometheus)
- [ ] Configure SSL/TLS
- [ ] Set up backup strategy

## Support

For issues and questions:
1. Check the API documentation at `/api/docs/`
2. Review the logs in `farmville.log`
3. Ensure model and Gemini API are properly configured

## License

This project is part of the FarmVille Agricultural Platform capstone project.
