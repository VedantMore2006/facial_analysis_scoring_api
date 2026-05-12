# Facial Risk Scoring API

This repository currently contains one FastAPI service:

1. Scoring API: session vector -> dominant risk + other risk probabilities

## Service Summary

- Framework: FastAPI
- Main app file: app.py
- Default port: 5200
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
curl -X GET "http://127.0.0.1:5200/health"
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

**Flexible Request Body:**
The API supports two input formats:
1. **Direct Vector**: A flat JSON object containing feature names as keys.
2. **Wrapped Object (Session Report)**: A JSON object containing a `"vector"` key (e.g., the format of `payload.json`).

The API prioritizes the `"vector"` key if present; otherwise, it treats the top-level object as the vector.

Example Request (Direct):
```json
{
  "nod_onset_latency__mean": 0.987,
  "head_motion_energy__slope": 0.476
}
```

Example Request (Wrapped/payload.json):
```json
{
  "session_id": "4bc4fabea...",
  "vector": {
    "nod_onset_latency__mean": 0.987,
    "head_motion_energy__slope": 0.476
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

curl example (Direct Vector):

```bash
API_KEY="<your_api_key>"

curl -X POST "http://127.0.0.1:5200/score" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
      "nod_onset_latency__mean": 0.987,
      "head_motion_energy__slope": 0.476
  }'
```

curl example (Using payload.json):

```bash
API_KEY="<your_api_key>"

curl -X POST "http://127.0.0.1:5200/score" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d @payload.json
```

## How To Use (Python requests)

```python
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

  url = "http://127.0.0.1:5200/score"

with open("payload.json", "r", encoding="utf-8") as f:
    payload = json.load(f)

headers = {
    "x-api-key": os.getenv("SCORING_API_KEY"),
    "content-type": "application/json"
}

response = requests.post(url, json=payload, headers=headers, timeout=120)
print(response.status_code)
print(response.json())
```

## Ready-To-Run Script

A standalone Python script `run.py` is provided for quick verification. It automatically loads your API key from `.env`, reads `payload.json`, calls the API, and prints output.

**Usage:**
```bash
python run.py
```

On success, `run.py` also writes the structured response to `output.json`.

## Submission Files

The required submission artifacts are present:

- `payload.json` (sample input)
- `output.json` (sample output from a real API call)
- `run.py` (single-command runner)
- `example.env` (environment template)

## Authentication Setup

The API key is loaded from environment variable SCORING_API_KEY at startup.

1. Create local env file:

```bash
cp example.env .env
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
uvicorn app:app --host 0.0.0.0 --port 5200 --reload
```

Swagger docs:

- http://127.0.0.1:5200/docs

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
