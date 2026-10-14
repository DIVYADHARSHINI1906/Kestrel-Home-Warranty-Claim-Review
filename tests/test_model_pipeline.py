"""
Automated tests for the machine learning feature pipeline and fraud detector.
Covers missing values, unknown categories, serial anomalies, and edge cases.
"""

from pathlib import Path
import pytest
import pandas as pd
import numpy as np
import joblib

from src.features import ClaimFeaturePipeline, extract_claim_evidence_factors
from app.schemas import ClaimInput
from app.services.fraud_detector import FraudDetector


@pytest.fixture(scope="module")
def model_bundle():
    bundle_path = Path("models/fraud_pipeline.joblib")
    assert bundle_path.exists(), "Model bundle must exist"
    return joblib.load(bundle_path)


@pytest.fixture(scope="module")
def fraud_detector():
    return FraudDetector(".")


@pytest.fixture(scope="module")
def reference_data():
    products = pd.read_csv("products.csv")
    partners = pd.read_csv("partners.csv")
    return products, partners


def test_model_bundle_contents(model_bundle):
    assert "feature_pipeline" in model_bundle
    assert "production_model" in model_bundle
    assert "baseline_model" in model_bundle
    assert "operating_threshold" in model_bundle
    assert 0.0 < model_bundle["operating_threshold"] < 1.0


def test_pipeline_unknown_category_handling(model_bundle):
    pipeline = model_bundle["feature_pipeline"]
    model = model_bundle["production_model"]
    
    # Claim with completely unknown partner and SKU
    unknown_df = pd.DataFrame([{
        "claim_id": "WC-UNKNOWN",
        "submitted_at": "2026-08-01 10:00",
        "partner_id": "SP_NONEXISTENT_9999",
        "sku": "KH-UNKNOWN-99",
        "product_serial": "KH000000000",
        "days_since_purchase": 50,
        "claim_amount_inr": 1500.0,
        "photo_attached": "Y",
        "partner_inspected": "Y",
        "claim_description": "unknown fault",
        "inspector_note": None,
        "customer_prior_claims": 0,
        "source": "crm",
        "list_price_inr": 5000.0,
        "warranty_months": 12,
        "family": "Unknown",
        "city": "UnknownCity",
        "partner_type": "unknown_type",
        "onboarded_date": "2025-01-01"
    }])
    
    X = pipeline.transform(unknown_df)
    assert not X.isna().any().any(), "Features must not contain NaNs even for unknown categories"
    
    score = model.predict_proba(X)[0, 1]
    assert 0.0 <= score <= 1.0, "Prediction must be a valid probability"


def test_pipeline_missing_values_and_serials(model_bundle):
    pipeline = model_bundle["feature_pipeline"]
    model = model_bundle["production_model"]
    
    # Claim with missing optional fields and whitespace in serial
    messy_df = pd.DataFrame([{
        "claim_id": "WC-MESSY",
        "submitted_at": "2026-08-01 10:00",
        "partner_id": "SP3033",
        "sku": "KH-AF-01",
        "product_serial": "  KH123456789  ",  # leading and trailing whitespace
        "days_since_purchase": None,          # Missing days
        "claim_amount_inr": None,             # Missing amount
        "photo_attached": "N",
        "partner_inspected": "N",
        "claim_description": "broken",
        "inspector_note": None,
        "customer_prior_claims": None,        # Missing priors
        "source": "crm",
        "list_price_inr": 5199.0,
        "warranty_months": 12,
        "family": "Air Fryer",
        "city": "Bhopal",
        "partner_type": "authorised_service_centre",
        "onboarded_date": "2023-08-18"
    }])
    
    X = pipeline.transform(messy_df)
    assert not X.isna().any().any(), "Missing numeric fields must impute safely"
    assert X["serial_has_whitespace"].iloc[0] == 1, "Must detect serial whitespace anomaly"
    
    score = model.predict_proba(X)[0, 1]
    assert 0.0 <= score <= 1.0


def test_fraud_detector_policy_checks(fraud_detector, reference_data):
    products, partners = reference_data
    
    # 1. Test uninspected claim >= 2000 (Must trigger VIOLATION of Ops Policy §5)
    violation_claim = ClaimInput(
        claim_id="WC-TEST-VIOL",
        submitted_at="2026-08-01 12:00",
        partner_id="SP3033",
        sku="KH-AF-01",
        product_serial="KH123456789",
        days_since_purchase=60,
        claim_amount_inr=3500.00,  # >= 2000
        photo_attached="Y",
        partner_inspected="N",      # Uninspected!
        claim_description="not heating",
        customer_prior_claims=0
    )
    
    res = fraud_detector.evaluate_claim(violation_claim, products, partners)
    violations = [c for c in res.policy_checks if c.severity == "VIOLATION"]
    assert len(violations) > 0, "Must flag violation for uninspected claim >= ₹2,000"
    assert "Policy Rejection" in res.recommended_action
    
    # 2. Test auto-approval eligible claim < 2000
    eligible_claim = ClaimInput(
        claim_id="WC-TEST-ELIGIBLE",
        submitted_at="2026-08-01 12:00",
        partner_id="SP3033",
        sku="KH-MG-01",
        product_serial="KH123456789",
        days_since_purchase=60,
        claim_amount_inr=950.00,   # < 2000
        photo_attached="Y",
        partner_inspected="N",      # Under 2000, allowed uninspected
        claim_description="blade jammed",
        customer_prior_claims=0
    )
    
    res2 = fraud_detector.evaluate_claim(eligible_claim, products, partners)
    violations2 = [c for c in res2.policy_checks if c.severity == "VIOLATION"]
    assert len(violations2) == 0, "Compliant sub-₹2,000 claim must have no violations"
