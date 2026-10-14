"""
Test suite validating predictions.csv against sample_submission.csv.
"""

from pathlib import Path
import pandas as pd
import numpy as np
import pytest


def test_predictions_file_exists():
    path = Path("predictions.csv")
    assert path.exists(), "predictions.csv must exist in the repository root"


def test_predictions_schema_and_row_count():
    preds = pd.read_csv("predictions.csv")
    sample = pd.read_csv("sample_submission.csv")
    
    assert list(preds.columns) == ["claim_id", "score"], "Columns must be exactly ['claim_id', 'score']"
    assert len(preds) == len(sample), f"Row count must be {len(sample)}, found {len(preds)}"
    assert len(preds) == 2252, "Row count must be 2,252"


def test_predictions_claim_id_alignment():
    preds = pd.read_csv("predictions.csv")
    sample = pd.read_csv("sample_submission.csv")
    
    assert (preds["claim_id"] == sample["claim_id"]).all(), (
        "Claim IDs in predictions.csv must strictly match sample_submission.csv order"
    )
    assert not preds["claim_id"].duplicated().any(), "predictions.csv must not have duplicate claim_ids"


def test_predictions_valid_numeric_scores():
    preds = pd.read_csv("predictions.csv")
    
    assert not preds["score"].isna().any(), "Scores must not contain NaN"
    assert np.issubdtype(preds["score"].dtype, np.floating), "Scores must be numeric floating point numbers"
    assert (preds["score"] >= 0.0).all(), "Scores must be >= 0.0"
    assert (preds["score"] <= 1.0).all(), "Scores must be <= 1.0"
    assert preds["score"].nunique() > 10, "Scores must have meaningful distribution, not constant"
