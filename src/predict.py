"""
Prediction Generator for Kestrel Home Unlabeled Test Claims.
Produces validated predictions.csv matching sample_submission.csv specifications.
"""

from pathlib import Path
import joblib
import pandas as pd
import numpy as np

from src.data_validation import load_raw_datasets, clean_and_prepare_claims


def generate_predictions(base_dir: str = "."):
    base_path = Path(base_dir)
    print("Loading test dataset and model pipeline...")
    train_raw, test_raw, products_raw, partners_raw = load_raw_datasets(base_path)
    sample_sub = pd.read_csv(base_path / "sample_submission.csv")
    
    bundle_path = base_path / "models" / "fraud_pipeline.joblib"
    if not bundle_path.exists():
        raise FileNotFoundError(f"Model bundle not found at {bundle_path}. Please run src/train.py first.")
        
    bundle = joblib.load(bundle_path)
    feature_pipeline = bundle["feature_pipeline"]
    model = bundle["production_model"]
    
    # Clean and prepare test set
    test_clean = clean_and_prepare_claims(test_raw, partners_raw, products_raw, is_training=False)
    
    # Transform features
    X_test = feature_pipeline.transform(test_clean)
    
    # Predict probabilities (higher score = greater fraud likelihood)
    scores = model.predict_proba(X_test)[:, 1]
    
    # Format submission DataFrame
    predictions_df = pd.DataFrame({
        "claim_id": test_clean["claim_id"],
        "score": np.round(scores, 4)
    })
    
    # Align strictly to sample_submission order
    predictions_df = sample_sub[["claim_id"]].merge(predictions_df, on="claim_id", how="left")
    
    # Validation checks
    assert len(predictions_df) == len(sample_sub), (
        f"Row count mismatch: {len(predictions_df)} vs expected {len(sample_sub)}"
    )
    assert list(predictions_df.columns) == ["claim_id", "score"], (
        f"Invalid columns: {list(predictions_df.columns)}"
    )
    assert not predictions_df["score"].isna().any(), "Found NaN values in scores"
    assert (predictions_df["score"] >= 0.0).all() and (predictions_df["score"] <= 1.0).all(), (
        "Scores out of valid [0, 1] probability range"
    )
    assert (predictions_df["claim_id"] == sample_sub["claim_id"]).all(), (
        "Claim IDs do not match sample_submission order"
    )
    
    # Save output to predictions.csv in repository root
    output_path = base_path / "predictions.csv"
    predictions_df.to_csv(output_path, index=False)
    print(f"Successfully generated validated predictions at {output_path}")
    print(f"Sample predictions (first 5 rows):\n{predictions_df.head()}")
    print(f"Score statistics:\n{predictions_df['score'].describe()}")
    
    return predictions_df


if __name__ == "__main__":
    generate_predictions(".")
