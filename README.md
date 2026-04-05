# API User Guide

This guide explains how to run and call the two production APIs.

Architecture is intentionally split into two services:

1. **Extraction API**: video → single ML-ready session vector
2. **Scoring API**: session vector → dominant risk + other probabilities

Both APIs require **API Key authentication** via the `X-API-Key` header.

## Swagger UI Documentation
```
Extraction API: http://127.0.0.1:8001/docs
Scoring API: http://127.0.0.1:8002/docs
```

## 1. Prerequisites

From project root, install API dependencies:

```bash
pip install -r requirements.txt
```

## 2. Set Up API Authentication

Before starting the APIs, configure your API key:

### Step 1: Create `.env` file from template

```bash
cp .env.example .env
```

### Step 2: Generate a secure API key

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 3: Edit `.env` and update the key

```bash
# .env
SCORING_API_KEY=<paste_your_generated_key_here>
```

**Important:** Never commit `.env` to version control. The file is automatically ignored by `.gitignore`.

## 3. Start Services

Start Extraction API on port 8001:

```bash
uvicorn extraction_api:app --host 0.0.0.0 --port 8001 --reload
```

Start Scoring API on port 8002:

```bash
uvicorn scoring_api:app --host 0.0.0.0 --port 8002 --reload
```

Both APIs will validate the `SCORING_API_KEY` environment variable on startup and fail if it's missing or still set to the placeholder value `CHANGE_ME`.

## 4. Extraction API

Source file: extraction_api.py

### Endpoint A: Upload Video And Process Session

Method and route:

- POST /extract/video

Input:

- multipart form-data with field name: video

Query parameters:

- mode: accurate | balanced | fast
- frame_stride: optional override (0 means use mode default)
- min_duration_seconds: default 150.0
- allow_short: default false
- model_dir: default reports/model_training/run_20260324_171117
- training_report: optional
- label_col: default condition_label

Example call:

```bash
API_KEY="<your_api_key>"  # Load from .env

curl -X POST "http://127.0.0.1:8001/extract/video?mode=balanced&allow_short=true" \
  -H "X-API-Key: $API_KEY" \
  -F "video=@assets/stress.mp4"
```

Example response:

```json
{
  "session_id": "8d0c5f7e62d14e2cbe64b70842d4f4da",
  "vector_feature_count": 63
}
```

### Endpoint B: Fetch ML-Ready Vector

Method and route:

- GET /extract/session/{session_id}/vector

Example call:

```bash
API_KEY="<your_api_key>"  # Load from .env

curl -s "http://127.0.0.1:8001/extract/session/8d0c5f7e62d14e2cbe64b70842d4f4da/vector" \
  -H "X-API-Key: $API_KEY"
```

Save vector to file:

```bash
API_KEY="<your_api_key>"  # Load from .env

curl -s "http://127.0.0.1:8001/extract/session/8cadd316226f4d4b9aee328aab0186f9/vector" \
  -H "X-API-Key: $API_KEY" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps({'vector': d['vector']}))" \
  > score_input.json
```

Example response shape:

```json
{
  "session_id": "8d0c5f7e62d14e2cbe64b70842d4f4da",
  "vector": {
    "au12_mean_amplitude__slope": 0.000123,
    "au12_variance__min": 0.000045
  }
}
```

## 5. Scoring API

Source file: scoring_api.py

### Endpoint: Score Vector

Method and route:

- POST /score

**Authentication:** Required via `X-API-Key` header

Request body:

```json
{
  "vector": {
    "au12_mean_amplitude__slope": 0.000123,
    "au12_variance__min": 0.000045
  }
}
```

Example call:

```bash
API_KEY="<your_api_key>"  # Load from .env

curl -X POST "http://127.0.0.1:8002/score" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d @score_input.json
```

Response (only required outputs):

```json
{
  "dominant_risk": {
    "label": "stress",
    "probability": 0.9475
  },
  "other_risks": [
    {"label": "suicidal_tendency", "probability": 0.0506},
    {"label": "depression", "probability": 0.0006}
  ]
}
```

## 6. End-To-End Calling Process

### Option A — Python test script (recommended)

With both APIs running, from project root:

```bash
conda activate project_env
python3 api/test_pipeline.py assets/test.mp4
```

Optional flags:

```bash
python3 api/test_pipeline.py assets/test.mp4 \
  --extract-port 8001 \
  --score-port 8002 \
  --mode balanced
```

The script automatically loads the API key from environment variables.

Example output:

```
[1/3] Uploading test.mp4 → http://127.0.0.1:8001/extract/video
      session_id=b99baf61...  features=63
[2/3] Fetching vector → http://127.0.0.1:8001/extract/session/b99baf61.../vector
      63 features retrieved
[3/3] Scoring vector → http://127.0.0.1:8002/score
=============================================
  DOMINANT RISK: STRESS                98.0%
---------------------------------------------
  bipolar                               0.1%
  anxiety                               0.1%
  suicidal_tendency                     0.0%
  depression                            0.0%
  phobia                                0.0%
=============================================
```

### Option B — Bash with API key (manual, for debugging individual steps)

First, load your API key:

```bash
export API_KEY=$(grep "^SCORING_API_KEY=" .env | cut -d'=' -f2)
```

Step 1: upload video, capture session_id:

```bash
SESSION=$(curl -s -X POST "http://127.0.0.1:8001/extract/video?mode=balanced&allow_short=true" \
  -H "X-API-Key: $API_KEY" \
  -F "video=@assets/test.mp4" | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")
echo "session_id: $SESSION"
```

Step 2: fetch vector and save to file:

```bash
curl -s "http://127.0.0.1:8001/extract/session/$SESSION/vector" \
  -H "X-API-Key: $API_KEY" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps({'vector': d['vector']}))" \
  > /tmp/score_input.json
```

Step 3: score:

```bash
curl -X POST "http://127.0.0.1:8002/score" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d @/tmp/score_input.json
```

## 7. Common Errors

### Authentication Errors (Both APIs)

- **401 Unauthorized**: Missing or invalid `X-API-Key` header
  - Solution: Add `X-API-Key: <your_api_key>` header to all requests
  - Verify your API key matches the value in `.env`

- **RuntimeError on startup**: "Missing required environment variable SCORING_API_KEY"
  - Solution: Create `.env` file and set `SCORING_API_KEY=<your_key>`

- **RuntimeError on startup**: "Invalid SCORING_API_KEY value. Replace placeholder..."
  - Solution: Edit `.env` and replace `CHANGE_ME` with a real API key

### Extraction API

- 400: video too short and allow_short is false
- 404: training_report or model artifacts not found
- 500: extraction pipeline failure

### Scoring API

- 400: missing vector features or unknown extra features
- 404: model or training_report not found
- 500: model inference failure

## 8. Using Swagger UI with Authentication

Both APIs include interactive Swagger UI documentation with built-in API key support:

1. **Extraction API Docs**: http://127.0.0.1:8001/docs
2. **Scoring API Docs**: http://127.0.0.1:8002/docs

To use Swagger UI:

1. Open the docs endpoint URL in your browser
2. Click the green **"Authorize"** button at the top right
3. Enter your API key in the popup dialog
4. Click **"Authorize"**
5. All subsequent requests will automatically include the `X-API-Key` header

This is useful for testing and debugging without manually adding headers to curl commands.
