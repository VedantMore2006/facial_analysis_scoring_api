"""Standalone scoring utilities for the scoring API repo.

These are extracted from predict_video_risk.py so the scoring service has
no dependency on mediapipe, opencv, or any extraction-side code.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd


def resolve_expected_feature_order(
    project_root: Path,
    training_report_path: Path,
    label_col: str,
) -> Tuple[List[str], Path, List[str]]:
    report = json.loads(training_report_path.read_text(encoding="utf-8"))
    report_classes = [str(c) for c in report.get("classes", [])]
    input_csv = report.get("input", "")

    if input_csv:
        input_path = Path(input_csv)
        if not input_path.is_absolute():
            input_path = (project_root / input_path).resolve()

        if input_path.exists():
            header_df = pd.read_csv(input_path, nrows=0)
            expected = [c for c in header_df.columns.tolist() if c != label_col]
            if expected:
                return expected, input_path, report_classes

    # Fallback: resolve schema from saved feature-importance artifact.
    artifacts = report.get("artifacts", {}) if isinstance(report.get("artifacts", {}), dict) else {}
    importance_csv = artifacts.get("feature_importance_csv", "")
    if importance_csv:
        importance_path = Path(str(importance_csv))
        if not importance_path.is_absolute():
            importance_path = (project_root / importance_path).resolve()
        if importance_path.exists():
            imp_df = pd.read_csv(importance_path)
            if "feature" in imp_df.columns:
                expected = [str(f) for f in imp_df["feature"].tolist()]
                if expected:
                    return expected, importance_path, report_classes

    raise FileNotFoundError(
        "Could not resolve expected feature schema. "
        "Neither training input CSV nor feature_importance CSV is available."
    )


def _probability_output(
    model: Any,
    X_row: pd.DataFrame,
    class_labels: List[str],
    pred_idx: int,
) -> Tuple[Dict[str, float], float]:
    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(X_row)
        prob_vec = np.asarray(probs[0], dtype=float)
    else:
        prob_vec = np.zeros(len(class_labels), dtype=float)
        prob_vec[pred_idx] = 1.0

    probabilities = {
        class_labels[i]: float(prob_vec[i])
        for i in range(min(len(class_labels), len(prob_vec)))
    }

    confidence = float(prob_vec[pred_idx]) if pred_idx < len(prob_vec) else 1.0
    return probabilities, confidence
