from __future__ import annotations

import json
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List

import joblib
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException
from fastapi.openapi.utils import get_openapi
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from scoring_utils import _probability_output, resolve_expected_feature_order


APP_TITLE = "Facial Risk Scoring API"
DEFAULT_LABEL_COL = os.environ.get("LABEL_COL", "condition_label")

project_root = Path(__file__).resolve().parent

# Load environment variables from .env file
load_dotenv(project_root / ".env")

# API key configuration
API_KEY_ENV_VAR = "SCORING_API_KEY"
API_KEY_HEADER_NAME = "X-API-Key"


def _load_api_key() -> str:
    """Load and validate API key from environment variable on startup."""
    key = os.getenv(API_KEY_ENV_VAR, "").strip()
    if not key:
        raise RuntimeError(
            f"Missing required environment variable {API_KEY_ENV_VAR}. "
            f"Set it before starting the API."
        )
    if key == "CHANGE_ME":
        raise RuntimeError(
            f"Invalid {API_KEY_ENV_VAR} value. Replace placeholder value 'CHANGE_ME' with a real key."
        )
    return key


EXPECTED_API_KEY = _load_api_key()

_DEFAULT_MODEL_DIR = os.environ.get(
    "MODEL_DIR",
    str(project_root / "reports" / "model_training" / "run_20260324_171117"),
)

# ---------------------------------------------------------------------------
# Model state — loaded once at startup, reused for every request
# ---------------------------------------------------------------------------
_model = None
_expected_features: list[str] = []
_class_labels: list[str] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _model, _expected_features, _class_labels

    model_dir = Path(_DEFAULT_MODEL_DIR)
    if not model_dir.is_absolute():
        model_dir = (project_root / model_dir).resolve()

    model_path = model_dir / "best_model.joblib"
    training_report_path = model_dir / "training_report.json"

    if not model_path.exists():
        raise RuntimeError(f"Model artifact missing at startup: {model_path}")
    if not training_report_path.exists():
        raise RuntimeError(f"Training report missing at startup: {training_report_path}")

    _model = joblib.load(model_path)

    _expected_features, _schema_csv, report_classes = resolve_expected_feature_order(
        project_root=project_root,
        training_report_path=training_report_path,
        label_col=DEFAULT_LABEL_COL,
    )

    if report_classes:
        _class_labels = report_classes
    else:
        report_payload = json.loads(training_report_path.read_text(encoding="utf-8"))
        _class_labels = [str(c) for c in report_payload.get("classes", [])]

    yield  # app runs — model stays in memory


app = FastAPI(
    title=APP_TITLE,
    version="1.0.0",
    description="Facial Risk Scoring API requiring authentication via X-API-Key header.",
    lifespan=lifespan,
)

# API Key security configuration
api_key_header = APIKeyHeader(
    name=API_KEY_HEADER_NAME,
    description="API key required for authentication. Obtain from deployment configuration.",
    auto_error=False,
)


def require_api_key(provided_key: str | None = Depends(api_key_header)) -> None:
    """Validate API key from X-API-Key header using timing-attack resistant comparison."""
    if not provided_key or not secrets.compare_digest(provided_key, EXPECTED_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def custom_openapi():
    """Add security scheme to OpenAPI spec for Swagger UI display."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Register X-API-Key as security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "api_key": {
            "type": "apiKey",
            "in": "header",
            "name": API_KEY_HEADER_NAME,
            "description": "API key for authentication. Required for all scoring endpoints.",
        }
    }

    # Apply security requirement to all endpoints except /health
    for path, path_item in openapi_schema["paths"].items():
        if path != "/health":
            for operation in path_item.values():
                if isinstance(operation, dict) and "operationId" in operation:
                    operation["security"] = [{"api_key": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": APP_TITLE, "model_loaded": _model is not None}


class ScoreRequest(BaseModel):
    vector: Dict[str, float] = Field(..., description="ML-ready session vector")


class RiskRow(BaseModel):
    label: str
    probability: float


class ScoreResponse(BaseModel):
    dominant_risk: RiskRow
    other_risks: List[RiskRow]


@app.post("/score", response_model=ScoreResponse)
def score_vector(req: ScoreRequest, _auth: None = Depends(require_api_key)) -> ScoreResponse:
    try:
        model_features = (
            [str(f) for f in _model.feature_names_in_.tolist()]
            if hasattr(_model, "feature_names_in_")
            else list(_expected_features)
        )

        missing = [f for f in model_features if f not in req.vector]
        if missing:
            raise ValueError(f"Input vector missing required features: {missing[:10]} (total {len(missing)})")

        extra = [f for f in req.vector if f not in set(model_features)]
        if extra:
            raise ValueError(f"Input vector has unknown features: {extra[:10]} (total {len(extra)})")

        X_model = pd.DataFrame(
            [{name: float(req.vector[name]) for name in model_features}],
            columns=model_features,
        )
        pred_idx = int(_model.predict(X_model)[0])

        if pred_idx < 0 or pred_idx >= len(_class_labels):
            raise ValueError(f"Predicted class index {pred_idx} out of range for {len(_class_labels)} classes")

        probabilities, _confidence = _probability_output(
            model=_model,
            X_row=X_model,
            class_labels=_class_labels,
            pred_idx=pred_idx,
        )

        ranked = sorted(probabilities.items(), key=lambda kv: kv[1], reverse=True)
        dominant_label, dominant_prob = ranked[0]
        other_rows = [RiskRow(label=label, probability=float(prob)) for label, prob in ranked[1:]]

        return ScoreResponse(
            dominant_risk=RiskRow(label=dominant_label, probability=float(dominant_prob)),
            other_risks=other_rows,
        )

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Scoring failed: {exc}") from exc
