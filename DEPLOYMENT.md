# C-TRUST Deployment Guide

This guide covers deploying C-TRUST to various environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Production Deployment](#production-deployment)
4. [Docker Deployment](#docker-deployment)
5. [Cloud Deployment](#cloud-deployment)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 10GB minimum
- **OS**: Linux, macOS, or Windows

### Software Requirements

- Python 3.9+
- Node.js 16+
- PostgreSQL 13+ (for production)
- Redis (optional, for caching)
- Nginx (for production)

## Local Development

See [SETUP.md](SETUP.md) for local development setup.

## Production Deployment

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.9 python3-pip nodejs npm nginx postgresql redis-server

# Create application user
sudo useradd -m -s /bin/bash ctrust
sudo su - ctrust
```

### 2. Application Setup

```bash
# Clone repository
git clone <repository-url>
cd c-trust

# Setup backend
cd c_trust
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Setup frontend
cd frontend
npm install
npm run build
```

### 3. Environment Configuration

```bash
# Backend configuration
cp c_trust/.env.example c_trust/.env
nano c_trust/.env
```

Update production values:

```env
OPENAI_API_KEY=your_production_key
API_HOST=0.0.0.0
API_PORT=8000
DATABASE_URL=postgresql://user:pass@localhost/ctrust
LOG_LEVEL=WARNING
API_DEBUG=false
```

### 4. Database Setup

```bash
# Create database
sudo -u postgres psql
CREATE DATABASE ctrust;
CREATE USER ctrust_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE ctrust TO ctrust_user;
\q

# Run migrations
cd c_trust
alembic upgrade head
```

### 5. Systemd Service

Create `/etc/systemd/system/ctrust-api.service`:

```ini
[Unit]
Description=C-TRUST API Service
After=network.target postgresql.service

[Service]
Type=simple
User=ctrust
WorkingDirectory=/home/ctrust/c-trust/c_trust
Environment="PATH=/home/ctrust/c-trust/c_trust/.venv/bin"
ExecStart=/home/ctrust/c-trust/c_trust/.venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 src.api.main:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ctrust-api
sudo systemctl start ctrust-api
sudo systemctl status ctrust-api
```

### 6. Nginx Configuration

Create `/etc/nginx/sites-available/ctrust`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        root /home/ctrust/c-trust/c_trust/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support (if needed)
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/ctrust /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7. SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
sudo systemctl reload nginx
```

## Docker Deployment

### 1. Create Dockerfile

Create `c_trust/Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create `c_trust/frontend/Dockerfile`:

```dockerfile
FROM node:16-alpine as build

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Build application
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 2. Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: ctrust
      POSTGRES_USER: ctrust_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

  backend:
    build: ./c_trust
    environment:
      DATABASE_URL: postgresql://ctrust_user:secure_password@postgres/ctrust
      REDIS_URL: redis://redis:6379
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    volumes:
      - ./c_trust:/app
      - ./norvatas:/norvatas

  frontend:
    build: ./c_trust/frontend
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  postgres_data:
```

### 3. Run with Docker Compose

```bash
docker-compose up -d
docker-compose logs -f
```

## Cloud Deployment

### AWS Deployment

#### 1. EC2 Instance

```bash
# Launch EC2 instance (t3.medium recommended)
# Configure security groups (ports 80, 443, 8000)
# SSH into instance
ssh -i key.pem ubuntu@ec2-instance-ip

# Follow production deployment steps
```

#### 2. RDS Database

```bash
# Create RDS PostgreSQL instance
# Update DATABASE_URL in .env
DATABASE_URL=postgresql://user:pass@rds-endpoint:5432/ctrust
```

#### 3. S3 for Static Files

```bash
# Create S3 bucket
aws s3 mb s3://ctrust-static

# Upload frontend build
aws s3 sync c_trust/frontend/dist s3://ctrust-static --acl public-read
```

### Azure Deployment

```bash
# Create App Service
az webapp create --resource-group ctrust-rg --plan ctrust-plan --name ctrust-app --runtime "PYTHON|3.9"

# Deploy backend
az webapp deployment source config-zip --resource-group ctrust-rg --name ctrust-app --src backend.zip

# Create Azure Database for PostgreSQL
az postgres server create --resource-group ctrust-rg --name ctrust-db --admin-user ctrust --admin-password SecurePass123
```

### Google Cloud Platform

```bash
# Create App Engine app
gcloud app create --region=us-central

# Deploy backend
gcloud app deploy c_trust/app.yaml

# Create Cloud SQL instance
gcloud sql instances create ctrust-db --database-version=POSTGRES_13 --tier=db-f1-micro --region=us-central1
```

## Monitoring

### 1. Application Monitoring

```bash
# Install monitoring tools
pip install prometheus-client
pip install sentry-sdk
```

### 2. Log Aggregation

```bash
# Configure log shipping
# Use ELK stack, Splunk, or cloud-native solutions
```

### 3. Health Checks

```bash
# API health check
curl http://localhost:8000/health

# Database health check
curl http://localhost:8000/health/db
```

### 4. Metrics

```bash
# Prometheus metrics endpoint
curl http://localhost:8000/metrics
```

## Backup and Recovery

### Database Backup

```bash
# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -U ctrust_user ctrust > $BACKUP_DIR/ctrust_$DATE.sql
gzip $BACKUP_DIR/ctrust_$DATE.sql

# Keep only last 7 days
find $BACKUP_DIR -name "ctrust_*.sql.gz" -mtime +7 -delete
```

### Application Backup

```bash
# Backup application files
tar -czf ctrust_backup_$(date +%Y%m%d).tar.gz c-trust/

# Backup to S3
aws s3 cp ctrust_backup_$(date +%Y%m%d).tar.gz s3://ctrust-backups/
```

## Scaling

### Horizontal Scaling

```bash
# Add more API workers
gunicorn -w 8 -k uvicorn.workers.UvicornWorker src.api.main:app

# Use load balancer (Nginx, HAProxy, or cloud LB)
```

### Vertical Scaling

```bash
# Increase server resources
# Optimize database queries
# Add caching layer (Redis)
```

## Security Checklist

- [ ] Use HTTPS/SSL certificates
- [ ] Secure API keys and secrets
- [ ] Enable firewall rules
- [ ] Regular security updates
- [ ] Database encryption
- [ ] API rate limiting
- [ ] Input validation
- [ ] CORS configuration
- [ ] Regular backups
- [ ] Monitoring and alerts

## Troubleshooting

### Common Issues

#### 1. API Not Responding

```bash
# Check service status
sudo systemctl status ctrust-api

# Check logs
sudo journalctl -u ctrust-api -f

# Check port
sudo netstat -tulpn | grep 8000
```

#### 2. Database Connection Error

```bash
# Test database connection
psql -U ctrust_user -d ctrust -h localhost

# Check PostgreSQL status
sudo systemctl status postgresql
```

#### 3. Frontend Not Loading

```bash
# Check Nginx status
sudo systemctl status nginx

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log

# Verify build files
ls -la /home/ctrust/c-trust/c_trust/frontend/dist
```

## Maintenance

### Regular Tasks

- Update dependencies monthly
- Review logs weekly
- Test backups monthly
- Security patches immediately
- Performance monitoring daily
- Database optimization quarterly

### Update Procedure

```bash
# Backup current version
tar -czf ctrust_backup_$(date +%Y%m%d).tar.gz c-trust/

# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt
npm install

# Run migrations
alembic upgrade head

# Rebuild frontend
npm run build

# Restart services
sudo systemctl restart ctrust-api
sudo systemctl reload nginx
```

## Support

For deployment issues:
- Check logs first
- Review documentation
- Consult troubleshooting section
- Contact support team
