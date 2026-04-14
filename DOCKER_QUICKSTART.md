# Docker Deployment Quick Reference

## Files Created

1. **docker-compose.yml** - Main Docker Compose configuration
2. **Dockerfile** - Multi-stage optimized Docker build
3. **DOCKER_DEPLOYMENT.md** - Comprehensive deployment guide
4. **.env.docker** - Example environment variables
5. **.dockerignore** - Files to exclude from Docker image

## For Hostinger Docker Manager

### URL to Use

```
https://github.com/yourusername/your-repo/raw/main/docker-compose.yml
```

### What Happens Automatically

✅ Builds `facial-scoring-api:latest` image  
✅ Starts container on port 8011  
✅ Mounts network: scoring-network  
✅ Enables health checks every 30 seconds  
✅ Auto-restarts on failure  
✅ Loads environment variables from .env  

## Setup Steps

### 1. Local Testing

```bash
cp .env.example .env
# Edit .env and set SCORING_API_KEY

docker-compose up -d
curl http://localhost:8011/health

# Run test client
python3 test_scoring.py example.json
```

### 2. Push to GitHub

```bash
git init
git add .
git commit -m "Add Docker configuration"
git branch -M main
git remote add origin https://github.com/yourusername/repo.git
git push -u origin main
```

### 3. Hostinger VPS Deployment

- Go to **Docker Manager** → **Compose**
- Click **+ New Compose** or **Deploy**
- Paste your GitHub URL
- Set environment variables:
  - `SCORING_API_KEY=<your_key>`
  - `MODEL_DIR=reports/model_training/run_20260324_171117`
  - `LABEL_COL=condition_label`
- Click **Deploy**

### 4. Access API

```
http://<your-vps-ip>:8011/docs
```

## Important Notes

- **Port**: 8011 (ensure it's open on firewall)
- **Environment**: Load from `.env` file (never commit to Git)
- **Images**: Must include `reports/` directory with model artifacts
- **Health Check**: Runs every 30s, container auto-restarts if unhealthy
- **Memory**: Consider setting resource limits for production

## Docker Commands Reference

```bash
# Build image locally
docker-compose build

# Start container
docker-compose up -d

# View logs
docker-compose logs -f scoring-api

# Stop container
docker-compose stop

# Restart container
docker-compose restart scoring-api

# Remove everything
docker-compose down

# Check container status
docker-compose ps
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port already in use | Change port mapping in docker-compose.yml |
| API key validation fails | Verify .env file has SCORING_API_KEY set |
| Container won't start | Check logs: `docker-compose logs -f scoring-api` |
| Model not found | Ensure reports/ directory exists with model files |

## Production Deployment Best Practices

1. ✅ Use environment-specific `.env` files
2. ✅ Never commit `.env` to version control
3. ✅ Enable HTTPS with reverse proxy (nginx)
4. ✅ Set resource limits (CPU, memory)
5. ✅ Enable monitoring and logging
6. ✅ Regular backups of model files
7. ✅ Use managed container registry (optional)

For detailed instructions, see **DOCKER_DEPLOYMENT.md**
