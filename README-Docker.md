# Docker Setup for AI Todo List Backend

## Quick Start

1. **Copy environment variables:**
   ```bash
   cp .env.docker .env
   # Edit .env with your actual API keys and credentials
   ```

2. **Start the services:**
   ```bash
   docker-compose up -d
   ```

3. **Access the backend:**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## Services

### Backend API
- **URL**: http://localhost:8000
- **Container**: todolist_backend
- **Network**: backend-network + frontend-network

### PostgreSQL Database
- **Host**: localhost:5432
- **Database**: ai_todo
- **User**: todouser
- **Password**: todopass
- **Container**: todolist_postgres
- **Network**: backend-network (isolated)

### Redis Cache
- **Host**: localhost:6379
- **Password**: redispass
- **Container**: todolist_redis
- **Network**: backend-network (isolated)

## Network Architecture

```
┌─────────────────┐    ┌──────────────────┐
│   Frontend      │    │    External      │
│   (Port 3000)   │────│   Access         │
└─────────────────┘    └──────────────────┘
         │                       │
         └───────────────────────┼──────────┐
                                 │          │
                    ┌────────────▼────────────▼─┐
                    │   frontend-network       │
                    │  (Public Network)        │
                    └────────────┬─────────────┘
                                 │
                         ┌───────▼──────┐
                         │   Backend    │
                         │ (Port 8000)  │
                         └───────┬──────┘
                                 │
                    ┌────────────▼─────────────┐
                    │   backend-network        │
                    │  (Isolated Network)      │
                    │                          │
                    │  ┌──────────────────┐    │
                    │  │   PostgreSQL     │    │
                    │  │   (Port 5432)    │    │
                    │  └──────────────────┘    │
                    │                          │
                    │  ┌──────────────────┐    │
                    │  │     Redis        │    │
                    │  │   (Port 6379)    │    │
                    │  └──────────────────┘    │
                    └──────────────────────────┘
```

## Commands

### Development
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down

# Rebuild backend
docker-compose build backend
docker-compose up -d backend
```

### Database Management
```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Access PostgreSQL
docker-compose exec postgres psql -U todouser -d ai_todo

# Backup database
docker-compose exec postgres pg_dump -U todouser ai_todo > backup.sql
```

### Monitoring
```bash
# Check service health
docker-compose ps

# View backend logs
docker-compose logs backend

# Monitor resource usage
docker stats
```

## Environment Variables

Edit `.env` file with your configuration:

```bash
# Required API Keys
CLERK_SECRET_KEY=your_clerk_secret_key
GEMINI_API_KEY=your_gemini_api_key

# AWS Credentials (for file storage)
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
S3_BUCKET_NAME=your_bucket_name
```

## Network Security

- **Backend Network**: Isolated internal network for database and cache
- **Frontend Network**: Public network for API access
- **Database**: Only accessible from backend service
- **Redis**: Only accessible from backend service
- **API**: Exposed on port 8000 for external access

## Postman Configuration

**Base URL**: `http://localhost:8000`

**Common Endpoints**:
- GET `/health` - Health check
- GET `/docs` - API documentation
- POST `/api/auth/login` - Authentication
- GET `/api/todos` - List todos
- POST `/api/todos` - Create todo

## Production Deployment

For production, use the nginx profile:

```bash
docker-compose --profile production up -d
```

This adds an Nginx reverse proxy for better performance and security.