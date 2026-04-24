# Docker Deployment Guide

This guide explains how to deploy the Facial Risk Scoring API using Docker and Docker Compose.

## Prerequisites

- Docker installed (version 20.10+)
- Docker Compose installed (version 1.29+)
- Your API key generated
- Port 8011 available on your server

## Quick Start

### 1. Prepare Environment

Copy and configure the `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and set your API key:

```bash
# Generate a secure key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Edit .env and paste the key
SCORING_API_KEY=<your_generated_key>
```

### 2. Build and Run Locally

Build the Docker image:

```bash
docker-compose build
```

Start the service:

```bash
docker-compose up -d
```

Verify it's running:

```bash
docker-compose ps
```

Check logs:

```bash
docker-compose logs -f scoring-api
```

### 3. Test the API

Health check:

```bash
curl http://localhost:8011/health
```

Swagger UI documentation:

```
http://localhost:8011/docs
```

Score an example vector:

```bash
API_KEY=$(grep "^SCORING_API_KEY=" .env | cut -d'=' -f2)

# Option 1: Direct flat vector
curl -X POST "http://localhost:8011/score" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
      "nod_onset_latency__mean": 0.987,
      "head_motion_energy__slope": 0.476
  }'

# Option 2: Using a session report file (like payload.json)
curl -X POST "http://localhost:8011/score" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d @payload.json
```

### 4. Use the Test Client

A Python test client is provided for convenience:

```bash
python run.py
```

### 5. Stop the Service

```bash
docker-compose down
```

## Hostinger VPS Deployment

To deploy on Hostinger's Docker Manager:

### Step 1: Push to GitHub

1. Create a GitHub repository
2. Commit and push all files to the `main` branch:

```bash
git init
git add .
git commit -m "Add Docker configuration for Scoring API"
git branch -M main
git remote add origin https://github.com/yourusername/your-repo.git
git push -u origin main
```

### Step 2: Add to Hostinger Docker Manager

1. Log in to Hostinger VPS panel
2. Go to **Docker Manager** > **Compose**
3. Click **+ New Compose** or **Deploy**
4. Paste your GitHub URL in the URL field:
   ```
   https://github.com/yourusername/your-repo/raw/main/docker-compose.yml
   ```
5. Click **Deploy**
6. The Docker Manager will:
   - Pull the `docker-compose.yml` from GitHub
   - Build the Docker image
   - Start the container
   - Expose port 8011

### Step 3: Configure Environment Variables

In Hostinger Docker Manager:

1. Go to **Environment Variables** or **Config**
2. Add these variables:
   ```
   SCORING_API_KEY=<your_secure_key>
   MODEL_DIR=reports/model_training/run_20260324_171117
   LABEL_COL=condition_label
   ```
3. Save and restart container

### Step 4: Access Your API

Your API will be accessible at:

```
http://<your-vps-ip>:8011/docs
```

Replace `<your-vps-ip>` with your actual VPS IP address.

## Docker Compose Configuration

### What the `docker-compose.yml` does:

- **build**: Builds the image using the Dockerfile
- **image**: Tags the image as `facial-scoring-api:latest`
- **ports**: Maps container port 8011 to host port 8011
- **environment**: Loads variables from `.env` file
- **restart**: Automatically restarts if container crashes
- **healthcheck**: Monitors container health every 30 seconds
- **networks**: Creates isolated network for the service
- **logging**: Limits log file size to prevent disk filling

### Dockerfile Features:

- **Multi-stage build**: Reduces final image size
- **Minimal base image**: Uses `python:3.10-slim` for smaller footprint
- **Health check**: Built-in health endpoint monitoring
- **Security**: Non-root user, minimal dependencies

## Troubleshooting

### Port already in use

If port 8011 is already in use:

```bash
# Find process using port 8011
lsof -i :8011

# Or change port in docker-compose.yml:
ports:
  - "8011:8011"  # Change first 8011 to another port
```

### API key validation fails

Ensure `.env` file exists and `SCORING_API_KEY` is set:

```bash
# Check .env
cat .env

# Verify it's not CHANGE_ME
grep SCORING_API_KEY .env

# Restart container
docker-compose restart scoring-api
```

### Model files not found

Ensure `reports/` directory exists with model artifacts:

```bash
ls -la reports/model_training/run_20260324_171117/
```

If missing, either:
1. Copy model files to the correct path
2. Update `MODEL_DIR` environment variable

### Container won't start

Check logs:

```bash
docker-compose logs -f scoring-api
```

Common issues:
- Missing dependencies: Rebuild image with `docker-compose build`
- Port conflict: Change port mapping
- API key not set: Add to `.env`

## Production Recommendations

For production deployment on Hostinger VPS:

1. **Use environment variables** - Never commit `.env` to Git
2. **Enable HTTPS** - Use a reverse proxy (nginx) in front of Docker
3. **Add monitoring** - Use Hostinger's monitoring tools
4. **Regular backups** - Backup model files and data
5. **Update regularly** - Rebuild image after code changes
6. **Resource limits** - Set CPU and memory limits in docker-compose.yml:

```yaml
services:
  scoring-api:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G
```

## Scaling on Multiple Ports

To run multiple instances on different ports:

```bash
# Edit docker-compose.yml to add multiple services
services:
  scoring-api-1:
    build: .
    ports:
      - "8011:8011"
    environment:
      - SCORING_API_KEY=${SCORING_API_KEY}

  scoring-api-2:
    build: .
    ports:
      - "8012:8011"
    environment:
      - SCORING_API_KEY=${SCORING_API_KEY}
```

Then run:

```bash
docker-compose up -d
```

## Updating the Deployment

After code changes:

```bash
# Commit changes
git add .
git commit -m "Update API code"
git push -u origin main

# In Hostinger Docker Manager:
# Click "Redeploy" or "Update"
# Or manually:
docker-compose down
docker-compose build
docker-compose up -d
```

## Testing with run.py

The standalone `run.py` script makes it easy to verify your deployment:

1. Ensure `.env` is configured on the host.
2. Run the script:
   ```bash
  python run.py
   ```
  It will automatically load the key, submit `payload.json`, and write `output.json`.

## Useful Commands

```bash
# View running containers
docker-compose ps

# View logs
docker-compose logs -f scoring-api

# Stop services
docker-compose stop

# Remove stopped containers
docker-compose rm

# Execute command in container
docker-compose exec scoring-api bash

# Update image
docker-compose pull

# Restart service
docker-compose restart scoring-api

# Remove everything (including volumes)
docker-compose down -v
```
