"""
Model Training and Calibration Script for Kestrel Home Warranty Fraud Detection.
Trains baseline and production classifiers, calculates performance metrics,
determines optimal threshold based on business costs, and persists model artifacts.
"""

from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    precision_recall_curve,
    confusion_matrix,
    classification_report,
    roc_curve
)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.data_validation import load_raw_datasets, clean_and_prepare_claims, audit_data_integrity
from src.features import ClaimFeaturePipeline, FEATURE_NAMES


def train_and_evaluate(base_dir: str = "."):
    base_path = Path(base_dir)
    print("Loading raw datasets...")
    train_raw, test_raw, products_raw, partners_raw = load_raw_datasets(base_path)
    
    audit = audit_data_integrity(train_raw, test_raw)
    print(f"Data audit: {audit['train_rows']} train rows, {audit['undecided_crm_claims']} undecided CRM claims.")
    
    # Clean and prepare
    train_clean = clean_and_prepare_claims(train_raw, partners_raw, products_raw, is_training=True)
    
    # Filter known outcome cases for training
    known_mask = train_clean["is_fraud"].notna()
    train_adjudicated = train_clean[known_mask].copy()
    train_adjudicated["is_fraud"] = train_adjudicated["is_fraud"].astype(int)
    
    y = train_adjudicated["is_fraud"]
    print(f"Training dataset: {len(train_adjudicated)} claims. Class balance: {y.sum()} fraud ({y.mean():.2%}), {(y==0).sum()} non-fraud.")
    
    # Fit feature pipeline
    feature_pipeline = ClaimFeaturePipeline(smoothing_weight=10.0)
    feature_pipeline.fit(train_adjudicated, y)
    X = feature_pipeline.transform(train_adjudicated)
    
    # Baseline: Logistic Regression
    baseline_scaler = StandardScaler()
    X_scaled = baseline_scaler.fit_transform(X)
    baseline_model = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
    baseline_model.fit(X_scaled, y)
    
    # Production Model: Random Forest Classifier
    rf_model = RandomForestClassifier(
        n_estimators=120,
        max_depth=9,
        min_samples_leaf=8,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X, y)
    
    # Out-of-fold evaluation for unbiased metrics
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    oof_preds_rf = np.zeros(len(y))
    oof_preds_baseline = np.zeros(len(y))
    
    for tr_idx, val_idx in skf.split(train_adjudicated, y):
        tr_df, val_df = train_adjudicated.iloc[tr_idx], train_adjudicated.iloc[val_idx]
        y_tr, y_val = y.iloc[tr_idx], y.iloc[val_idx]
        
        # Fit fold pipeline
        fold_pipe = ClaimFeaturePipeline(smoothing_weight=10.0)
        fold_pipe.fit(tr_df, y_tr)
        X_tr = fold_pipe.transform(tr_df)
        X_val = fold_pipe.transform(val_df)
        
        # RF fold
        fold_rf = RandomForestClassifier(
            n_estimators=100, max_depth=9, min_samples_leaf=8,
            class_weight="balanced", random_state=42, n_jobs=-1
        )
        fold_rf.fit(X_tr, y_tr)
        oof_preds_rf[val_idx] = fold_rf.predict_proba(X_val)[:, 1]
        
        # Baseline fold
        fold_scaler = StandardScaler()
        X_tr_s = fold_scaler.fit_transform(X_tr)
        X_val_s = fold_scaler.transform(X_val)
        fold_lr = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
        fold_lr.fit(X_tr_s, y_tr)
        oof_preds_baseline[val_idx] = fold_lr.predict_proba(X_val_s)[:, 1]

    # Metrics
    auc_rf = float(roc_auc_score(y, oof_preds_rf))
    prauc_rf = float(average_precision_score(y, oof_preds_rf))
    auc_base = float(roc_auc_score(y, oof_preds_baseline))
    prauc_base = float(average_precision_score(y, oof_preds_baseline))
    
    print(f"Random Forest  -> Out-of-Fold ROC-AUC: {auc_rf:.4f}, PR-AUC: {prauc_rf:.4f}")
    print(f"Logistic Reg   -> Out-of-Fold ROC-AUC: {auc_base:.4f}, PR-AUC: {prauc_base:.4f}")
    
    # Threshold Tuning based on monthly investigation desk capacity (40 claims / month)
    # With ~787 claims/month, 40 claims is the top ~5.1% percentile of scores
    operating_threshold = float(np.percentile(oof_preds_rf, 94.9))
    print(f"Calibrated operating threshold for 40 reviews/month: {operating_threshold:.4f}")
    
    y_pred_thresh = (oof_preds_rf >= operating_threshold).astype(int)
    cm = confusion_matrix(y, y_pred_thresh).tolist()
    tn, fp, fn, tp = confusion_matrix(y, y_pred_thresh).ravel()
    
    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    accuracy = float((tp + tn) / len(y))
    
    # Feature importances
    importances = {
        name: float(round(imp, 4))
        for name, imp in zip(FEATURE_NAMES, rf_model.feature_importances_)
    }
    sorted_importances = dict(sorted(importances.items(), key=lambda item: item[1], reverse=True))

    evaluation_report = {
        "model_name": "RandomForest_Balanced_Ensemble",
        "baseline_name": "StandardScaled_LogisticRegression",
        "training_samples": len(train_adjudicated),
        "total_claims_recorded": len(train_raw),
        "undecided_crm_claims": int(audit["undecided_crm_claims"]),
        "fraud_count": int(y.sum()),
        "non_fraud_count": int((y == 0).sum()),
        "historical_fraud_rate": float(y.mean()),
        "operating_threshold": round(operating_threshold, 4),
        "metrics": {
            "roc_auc": round(auc_rf, 4),
            "pr_auc": round(prauc_rf, 4),
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "true_positives": int(tp),
            "false_positives": int(fp),
            "true_negatives": int(tn),
            "false_negatives": int(fn),
            "confusion_matrix": cm
        },
        "baseline_comparison": {
            "roc_auc": round(auc_base, 4),
            "pr_auc": round(prauc_base, 4)
        },
        "feature_importances": sorted_importances,
        "investigation_capacity_per_month": 40,
        "goodwill_cost_per_genuine_claim_inr": 380,
        "average_service_contact_cost_inr": 260
    }
    
    # Save artifacts
    models_dir = base_path / "models"
    reports_dir = base_path / "reports"
    models_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    bundle = {
        "feature_pipeline": feature_pipeline,
        "production_model": rf_model,
        "baseline_model": baseline_model,
        "baseline_scaler": baseline_scaler,
        "operating_threshold": operating_threshold,
        "feature_names": FEATURE_NAMES,
        "metadata": evaluation_report
    }
    
    joblib.dump(bundle, models_dir / "fraud_pipeline.joblib")
    with open(models_dir / "model_metadata.json", "w") as f:
        json.dump(evaluation_report, f, indent=2)
    with open(reports_dir / "evaluation_metrics.json", "w") as f:
        json.dump(evaluation_report, f, indent=2)
        
    print("Training and evaluation completed successfully. Artifacts saved.")
    return bundle, evaluation_report


if __name__ == "__main__":
    train_and_evaluate(".")
