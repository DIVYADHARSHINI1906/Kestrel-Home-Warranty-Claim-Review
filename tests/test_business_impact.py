"""
Automated tests for business impact, capacity constraints, and financial calculations.
"""

from pathlib import Path
import json
import pytest

from src.business_impact import compute_business_impact


def test_business_impact_report_structure():
    report_file = Path("reports/business_impact.json")
    assert report_file.exists(), "reports/business_impact.json must exist"
    
    with open(report_file, "r") as f:
        data = json.load(f)
        
    assert "parameters" in data
    assert "historical_performance_15_months" in data
    assert "projected_q3_2026_test_quarter" in data
    
    params = data["parameters"]
    assert params["monthly_desk_capacity"] == 40
    assert params["goodwill_penalty_per_genuine_delayed_inr"] == 380.0
    assert params["blended_contact_cost_inr"] == 260.0


def test_historical_financial_calculations():
    with open("reports/business_impact.json", "r") as f:
        data = json.load(f)
        
    hist = data["historical_performance_15_months"]
    assert hist["total_reviewed_by_desk"] == 600, "15 months * 40 claims/month must equal exactly 600 claims reviewed"
    assert hist["total_frauds_intercepted"] > 0
    assert hist["fraud_prevention_rate_rupees"] > 0
    
    # Verify math consistency
    expected_goodwill = hist["total_genuine_held"] * 380.0
    assert abs(hist["goodwill_costs_incurred_rupees"] - expected_goodwill) < 1.0
    
    expected_labor = hist["total_reviewed_by_desk"] * 260.0
    assert abs(hist["investigation_labor_cost_rupees"] - expected_labor) < 1.0
    
    expected_net = hist["fraud_prevention_rate_rupees"] - expected_goodwill - expected_labor
    assert abs(hist["net_financial_benefit_rupees"] - expected_net) < 1.0
    
    # Return per claim checked must be positive
    assert hist["net_benefit_per_investigated_claim_rupees"] > 0
