# TaskPilot Deployment Checklist

## Pre-Deployment Verification

### Code Quality
- [x] All tasks (TASK-01 through TASK-08) completed
- [x] Git history clean with descriptive commits
- [x] No sensitive data in repository (.env files excluded)
- [x] All TODO comments resolved or documented
- [x] Code follows Django best practices

### Documentation
- [x] README.md updated with setup instructions
- [x] CLAUDE.md contains development rules
- [x] PROJECT_SPEC.md documents architecture
- [x] PERMISSIONS_AUDIT.md documents security model
- [x] SMOKE_TEST_GUIDE.md provides testing instructions
- [x] Individual task documentation in /task-docs/

### Environment Configuration
- [ ] `.env` file configured with production values
- [ ] `SECRET_KEY` generated (use: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
- [ ] `DEBUG=False` in production
- [ ] `ALLOWED_HOSTS` set to actual domains
- [ ] Database credentials secured
- [ ] `TELEGRAM_BOT_TOKEN` configured
- [ ] `OPENAI_API_KEY` configured (if using AI features)
- [ ] Email settings configured (for invites)

### Security
- [x] Tenant isolation verified
- [x] RBAC (Manager/Member) implemented
- [x] Permission tests written (tests/test_permissions.py)
- [x] Cross-tenant access blocked
- [x] Audit logging implemented
- [ ] SSL/TLS certificates configured (production)
- [ ] CORS settings reviewed
- [ ] Rate limiting considered (optional)

### Database
- [ ] Migrations created and tested
- [ ] Database backups configured
- [ ] Migration rollback plan documented
- [ ] Initial data fixtures prepared (optional)

### Services
- [x] Web healthz endpoint: `/healthz`
- [x] Bot healthz endpoint: `http://localhost:8001/healthz`
- [x] Worker healthz endpoint: `http://localhost:8002/healthz`
- [x] All Dockerfiles present and tested
- [x] docker-compose.yml configured
- [ ] Resource limits set in docker-compose (memory, CPU)
- [ ] Log rotation configured
- [ ] Monitoring/alerting setup (optional)

## Deployment Steps

### 1. Server Preparation
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installations
docker --version
docker-compose --version
```

### 2. Clone Repository
```bash
cd /opt
sudo git clone <repository_url> taskpilot
cd taskpilot
sudo chown -R $USER:$USER .
```

### 3. Configure Environment
```bash
# Copy and edit .env file
cp .env.example .env
nano .env

# Set permissions
chmod 600 .env
```

### 4. Build and Start Services
```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

### 5. Database Setup
```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files (if needed)
docker-compose exec web python manage.py collectstatic --noinput
```

### 6. Verify Deployment
```bash
# Check healthz endpoints
curl http://localhost:8000/healthz
curl http://localhost:8001/healthz
curl http://localhost:8002/healthz

# Check logs
docker-compose logs -f --tail=100

# Access web UI
# Navigate to http://<server_ip>:8000
```

### 7. Initial Data
```bash
# Create first tenant and admin user via Django admin
# Navigate to /admin/
```

### 8. Telegram Bot Setup
```bash
# Set webhook (if using webhooks instead of polling)
# Or verify polling is working in logs
docker-compose logs bot | grep "Bot started"
```

## Post-Deployment Verification

### Smoke Tests
- [ ] Run through SMOKE_TEST_GUIDE.md checklist
- [ ] Verify all healthz endpoints return 200
- [ ] Test login/logout flow
- [ ] Create test task and verify it appears
- [ ] Test mobile view (responsive design)
- [ ] Verify bot responds to commands
- [ ] Test permission restrictions (member vs manager)
- [ ] Check logs for errors

### Monitoring
- [ ] Set up uptime monitoring for /healthz
- [ ] Configure log aggregation (optional)
- [ ] Set up alerts for service failures
- [ ] Monitor disk space (database, logs)
- [ ] Monitor memory usage

### Backup
- [ ] Set up automated database backups
  ```bash
  # Example cron job for daily backups
  0 2 * * * docker-compose exec -T db pg_dump -U taskpilot taskpilot | gzip > /backup/taskpilot_$(date +\%Y\%m\%d).sql.gz
  ```
- [ ] Test backup restoration procedure
- [ ] Document backup retention policy

## Rollback Plan

### If Deployment Fails
1. Check logs: `docker-compose logs`
2. Check healthz endpoints
3. Verify environment variables
4. Roll back to previous version:
   ```bash
   git checkout <previous_tag>
   docker-compose down
   docker-compose up -d --build
   ```

### Database Rollback
```bash
# Restore from backup
docker-compose exec -T db psql -U taskpilot taskpilot < backup.sql

# Roll back migrations (if needed)
docker-compose exec web python manage.py migrate <app> <migration_number>
```

## Maintenance

### Regular Tasks
- [ ] Weekly: Review logs for errors
- [ ] Weekly: Check disk space
- [ ] Weekly: Verify backups are running
- [ ] Monthly: Update dependencies (security patches)
- [ ] Monthly: Review and rotate logs
- [ ] Monthly: Review audit logs for suspicious activity

### Updates
```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose up -d --build

# Run migrations
docker-compose exec web python manage.py migrate
```

## Production-Specific Configuration

### Nginx/Traefik (Reverse Proxy)
If using reverse proxy, configure:
- [ ] SSL/TLS termination
- [ ] Domain routing
- [ ] Rate limiting
- [ ] Static file serving
- [ ] WebSocket support (for bot if needed)

### Environment-Specific Settings
```bash
# Production
DEBUG=False
ALLOWED_HOSTS=taskpilot.yourdomain.com
DATABASE_URL=postgresql://user:pass@db_host:5432/taskpilot
CELERY_BROKER_URL=redis://redis_host:6379/0

# Staging (if applicable)
DEBUG=True
ALLOWED_HOSTS=staging.taskpilot.yourdomain.com
```

## Troubleshooting

### Common Issues

**Services won't start:**
- Check environment variables: `docker-compose config`
- Check logs: `docker-compose logs <service>`
- Verify ports not in use: `netstat -tulpn`

**Database connection errors:**
- Verify DB credentials in .env
- Check DB service is healthy: `docker-compose ps db`
- Check DB logs: `docker-compose logs db`

**Bot not responding:**
- Verify TELEGRAM_BOT_TOKEN is correct
- Check bot logs: `docker-compose logs bot`
- Verify webhook/polling configuration
- Test bot token with: `curl https://api.telegram.org/bot<TOKEN>/getMe`

**Web UI slow or unresponsive:**
- Check worker service is running
- Check Redis connection
- Review Django logs for slow queries
- Consider adding database indexes

**Permission errors in logs:**
- Check file ownership: `ls -la`
- Ensure user has docker group membership
- Check volume permissions

## Security Hardening (Production)

- [ ] Enable firewall (ufw/iptables)
- [ ] Configure fail2ban for SSH
- [ ] Disable root SSH login
- [ ] Use SSH keys (disable password auth)
- [ ] Keep system packages updated
- [ ] Regular security audits
- [ ] Monitor for CVEs in dependencies
- [ ] Implement rate limiting at proxy level
- [ ] Use secrets management (not .env in production)
- [ ] Enable audit logging
- [ ] Regular penetration testing

## Compliance & Legal

- [ ] Privacy policy updated
- [ ] Terms of service defined
- [ ] Data retention policy documented
- [ ] GDPR compliance reviewed (if EU users)
- [ ] User data export capability implemented
- [ ] User data deletion capability implemented

## Sign-off

### Development Team
- [x] All tasks completed: _______________
- [x] Code reviewed: _______________
- [x] Tests passing: _______________
- [x] Documentation complete: _______________

### DevOps/Infrastructure
- [ ] Server prepared: _______________
- [ ] Services deployed: _______________
- [ ] Monitoring configured: _______________
- [ ] Backups configured: _______________

### Product Owner
- [ ] Smoke tests passed: _______________
- [ ] Acceptance criteria met: _______________
- [ ] Ready for production: _______________

**Deployment Date:** _______________
**Deployed By:** _______________
**Version:** v1.0.0

---

## Notes

Additional deployment notes or issues encountered:
-
-
-
