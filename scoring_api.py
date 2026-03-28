from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from scoring_utils import _probability_output, resolve_expected_feature_order


APP_TITLE = "Facial Risk Scoring API"
DEFAULT_LABEL_COL = os.environ.get("LABEL_COL", "condition_label")

project_root = Path(__file__).resolve().parent

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


app = FastAPI(title=APP_TITLE, version="1.0.0", lifespan=lifespan)


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
def score_vector(req: ScoreRequest) -> ScoreResponse:
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
