"""
Automated tests for FastAPI endpoints and input validation.
"""

from fastapi.testclient import TestClient
import pytest

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["dataset_loaded"] is True
    assert data["indexed_claims_count"] > 10000


def test_summary_endpoint():
    response = client.get("/api/summary")
    assert response.status_code == 200
    data = response.json()
    assert "historical_observed" in data
    assert "active_operational_queue" in data
    assert "model_performance" in data
    assert data["historical_observed"]["total_historical_claims"] == 12029
    assert data["active_operational_queue"]["unlabeled_claims_in_test"] == 2252


def test_claims_list_pagination_and_search():
    # Test standard list
    response = client.get("/api/claims?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] > 2000
    assert len(data["claims"]) == 10
    
    # Test search by known claim ID
    response_search = client.get("/api/claims?search=WC711348")
    assert response_search.status_code == 200
    data_search = response_search.json()
    assert data_search["total_count"] >= 1
    assert data_search["claims"][0]["claim_id"] == "WC711348"


def test_claim_detail_lookup():
    # Valid claim
    response = client.get("/api/claims/WC711348")
    assert response.status_code == 200
    claim = response.json()
    assert claim["claim_id"] == "WC711348"
    assert "claim_amount_inr" in claim
    assert "risk_score" in claim
    
    # Non-existent claim
    response_404 = client.get("/api/claims/WC_NONEXISTENT_9999")
    assert response_404.status_code == 404


def test_predict_endpoint_valid_and_invalid():
    # Valid predict payload
    payload = {
        "claim_id": "WC-API-TEST",
        "submitted_at": "2026-08-10 12:00",
        "partner_id": "SP3033",
        "sku": "KH-AF-01",
        "product_serial": "KH123456789",
        "days_since_purchase": 45,
        "claim_amount_inr": 1800.0,
        "photo_attached": "Y",
        "partner_inspected": "N",
        "claim_description": "not heating",
        "inspector_note": None,
        "customer_prior_claims": 0
    }
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert 0.0 <= res["risk_score"] <= 1.0
    assert res["risk_tier"] in ["Low", "Moderate", "High", "Critical"]
    assert len(res["policy_checks"]) > 0
    assert "recommended_action" in res

    # Invalid payload (missing required field 'sku')
    invalid_payload = payload.copy()
    del invalid_payload["sku"]
    response_422 = client.post("/api/predict", json=invalid_payload)
    assert response_422.status_code == 422


def test_analytics_and_partners_endpoints():
    res_analytics = client.get("/api/analytics")
    assert res_analytics.status_code == 200
    data_an = res_analytics.json()
    assert "volume_over_time" in data_an
    assert "product_family_distribution" in data_an
    assert "risk_score_distribution" in data_an

    res_partners = client.get("/api/partners")
    assert res_partners.status_code == 200
    data_pt = res_partners.json()
    assert "findings" in data_pt
    assert "top_high_risk_partners" in data_pt


def test_business_impact_endpoint():
    res = client.get("/api/business-impact?monthly_capacity=40&goodwill_cost=380")
    assert res.status_code == 200
    data = res.json()
    assert "parameters" in data
    assert data["parameters"]["monthly_capacity"] == 40
