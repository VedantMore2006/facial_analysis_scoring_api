# Facial Risk Scoring API

This repository currently contains one FastAPI service:

1. Scoring API: session vector -> dominant risk + other risk probabilities

## Service Summary

- Framework: FastAPI
- Main app file: scoring_api.py
- Default port: 8011
- Auth: API key via X-API-Key header (required for /score)
- Public endpoint: /health

## Endpoints

### 1) Health Check

- Method: GET
- Path: /health
- Authentication: Not required

What it does:
- Confirms API process is running
- Shows whether model is loaded

Example response:

```json
{
  "status": "ok",
  "service": "Facial Risk Scoring API",
  "model_loaded": true
}
```

curl example:

```bash
curl -X GET "http://127.0.0.1:8011/health"
```

### 2) Score Session Vector

- Method: POST
- Path: /score
- Authentication: Required (X-API-Key header)
- Content-Type: application/json

What it does:
- Validates input feature vector against model feature schema
- Runs model inference
- Returns dominant risk plus all remaining risks sorted by probability

Request body:

```json
{
  "vector": {
    "feature_name_1": 0.123,
    "feature_name_2": 0.456
  }
}
```

Response body shape:

```json
{
  "dominant_risk": {
    "label": "stress",
    "probability": 0.9475
  },
  "other_risks": [
    {
      "label": "suicidal_tendency",
      "probability": 0.0506
    },
    {
      "label": "depression",
      "probability": 0.0006
    }
  ]
}
```

curl example (inline JSON):

```bash
API_KEY="<your_api_key>"

curl -X POST "http://127.0.0.1:8011/score" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "vector": {
      "au12_mean_amplitude__slope": 0.000123,
      "au12_variance__min": 0.000045
    }
  }'
```

curl example (JSON file):

```bash
API_KEY="<your_api_key>"

cat > score_input.json << 'EOF'
{
  "vector": {
    "au12_mean_amplitude__slope": 0.000123,
    "au12_variance__min": 0.000045
  }
}
EOF

curl -X POST "http://127.0.0.1:8011/score" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d @score_input.json
```

## Authentication Setup

The API key is loaded from environment variable SCORING_API_KEY at startup.

1. Create local env file:

```bash
cp .env.example .env
```

2. Generate secure key:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

3. Set key in .env:

```env
SCORING_API_KEY=<paste_generated_key_here>
```

Important:
- SCORING_API_KEY must not be empty
- SCORING_API_KEY must not be CHANGE_ME

## Run Locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Start API:

```bash
uvicorn scoring_api:app --host 0.0.0.0 --port 8011 --reload
```

Swagger docs:

- http://127.0.0.1:8011/docs

In Swagger UI:
1. Click Authorize
2. Enter your API key value
3. Run /score requests

## Error Reference

### Authentication

- 401 Unauthorized: missing or invalid X-API-Key

### Request Validation

- 400 Bad Request:
  - input vector missing required model features
  - input vector has unknown extra features
  - predicted class index validation failure

### Server/Model Errors

- 500 Internal Server Error:
  - scoring/inference failure
  - model runtime issues

### Startup Errors (before server starts)

- RuntimeError: missing SCORING_API_KEY
- RuntimeError: SCORING_API_KEY is CHANGE_ME
- RuntimeError: model artifact missing
- RuntimeError: training report missing

## Quick Verification Checklist

- /health works without API key
- /score returns 401 without API key
- /score returns 401 with wrong API key
- /score returns 200 with correct API key and valid vector
- /docs opens and Authorize button is visible
