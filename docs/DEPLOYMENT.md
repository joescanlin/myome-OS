# Myome Deployment Guide

## Prerequisites

- Docker and Docker Compose
- Domain name with SSL certificate
- PostgreSQL 15+ with TimescaleDB
- Redis 7+

## Environment Variables

Create `.env.production`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/myome
DB_USER=myome
DB_PASSWORD=secure_password
DB_NAME=myome

# Redis
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=generate-with-openssl-rand-hex-32

# Application
ENVIRONMENT=production
DEBUG=false

# OAuth (Device Integrations)
WHOOP_CLIENT_ID=your_whoop_client_id
WHOOP_CLIENT_SECRET=your_whoop_client_secret
WITHINGS_CLIENT_ID=your_withings_client_id
WITHINGS_CLIENT_SECRET=your_withings_client_secret
```

## Deployment Steps

1. Clone repository:
   ```bash
   git clone https://github.com/joescanlin/myome-OS.git
   cd myome-OS/myome
   ```

2. Configure environment variables:
   ```bash
   cp .env.example .env.production
   # Edit .env.production with your values
   ```

3. Build and start services:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. Run database migrations:
   ```bash
   docker-compose exec api alembic upgrade head
   ```

5. Create initial admin user (optional):
   ```bash
   docker-compose exec api python -m myome.scripts.create_admin
   ```

6. Configure SSL certificates:
   - Place certificates in `./nginx/certs/`
   - Update nginx.conf with SSL configuration

7. Set up monitoring and logging:
   - Configure log aggregation
   - Set up health check endpoints

## Health Checks

- API: `GET /api/v1/health`
- Database: Check TimescaleDB connection
- Redis: Check cache connectivity
- Celery: Check worker status

## Scaling

For production deployments with higher load:

```bash
# Scale API workers
docker-compose -f docker-compose.prod.yml up -d --scale api=3

# Scale Celery workers
docker-compose -f docker-compose.prod.yml up -d --scale worker=2
```

## Backup Strategy

### Database Backups

Daily pg_dump with retention:
```bash
# Create backup
docker-compose exec db pg_dump -U myome myome > backup_$(date +%Y%m%d).sql

# Restore backup
docker-compose exec -T db psql -U myome myome < backup_20240101.sql
```

### Redis Backups

RDB snapshots are automatic. For manual backup:
```bash
docker-compose exec redis redis-cli BGSAVE
```

### User Data

- Encrypt all backups before storage
- Use object storage (S3, GCS) for backup retention
- Maintain 30-day rolling backups

## Monitoring

Recommended monitoring stack:
- Prometheus for metrics
- Grafana for visualization
- Sentry for error tracking

## Troubleshooting

### Common Issues

1. **Database connection errors**
   - Check DATABASE_URL environment variable
   - Verify PostgreSQL is running: `docker-compose logs db`

2. **Celery tasks not executing**
   - Check worker logs: `docker-compose logs worker`
   - Verify Redis connection: `docker-compose logs redis`

3. **CORS errors**
   - Update allowed origins in API configuration
   - Check nginx proxy settings

### Logs

View service logs:
```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f api
```

## Security Checklist

- [ ] SSL/TLS configured
- [ ] Strong SECRET_KEY generated
- [ ] Database credentials secured
- [ ] API rate limiting enabled
- [ ] CORS properly configured
- [ ] Firewall rules in place
- [ ] Regular security updates scheduled
