# FarmVile Backend - Docker Deployment

## Quick Start

### 1. Build and Run with Docker Compose
```bash
# Clone the repository
git clone <repository-url>
cd farmville-backend

# Build and start the container
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

### 2. Build and Run with Docker
```bash
# Build the image
docker build -t farmville-backend .

# Run the container
docker run -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/media:/app/media \
  -e GEMINI_API_KEY=your-api-key \
  farmville-backend
```

## Configuration

### Environment Variables
- `DEBUG`: Set to `False` for production
- `SECRET_KEY`: Change for production deployment
- `ALLOWED_HOSTS`: Add your domain names
- `GEMINI_API_KEY`: Your Google Gemini API key
- `DATABASE_URL`: SQLite database path (default: `sqlite:///data/farmville.db`)

### Volumes
- `./data:/app/data` - SQLite database persistence
- `./media:/app/media` - Uploaded images and media files
- `./static:/app/static` - Static files (CSS, JS, etc.)

## Default Admin Account
- **Username**: `admin`
- **Password**: `admin123`
- **Email**: `admin@farmville.com`

**⚠️ Change the default password in production!**

## API Endpoints
Once running, the API will be available at:
- Base URL: `http://localhost:8000`
- Admin Panel: `http://localhost:8000/admin/`
- API Documentation: `http://localhost:8000/api/`

## Health Check
The container includes a health check endpoint:
```bash
curl http://localhost:8000/api/health/
```

## Logs
View container logs:
```bash
# Docker Compose
docker-compose logs -f

# Docker
docker logs -f <container-name>
```

## Production Deployment

### 1. Update Environment Variables
```bash
# Create production environment file
cp .env.docker .env.production

# Edit the file with production values
nano .env.production
```

### 2. Use Production Settings
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  farmville-backend:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env.production
    volumes:
      - ./data:/app/data
      - ./media:/app/media
    restart: always
```

### 3. Deploy
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs farmville-backend

# Check if port is available
netstat -tulpn | grep :8000
```

### Database issues
```bash
# Reset database (⚠️ This will delete all data)
rm -rf data/farmville.db
docker-compose restart
```

### Permission issues
```bash
# Fix volume permissions
sudo chown -R $USER:$USER data/ media/ static/
```
