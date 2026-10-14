"""
Business Impact and Operational ROI Calculator for Kestrel Home.
Calculates prevented fraud payouts, investigation costs, customer goodwill penalties,
and capacity utilization under operations policy constraints (40 claims/month).
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import joblib

from src.data_validation import load_raw_datasets, clean_and_prepare_claims


def compute_business_impact(base_dir: str = "."):
    base_path = Path(base_dir)
    train_raw, test_raw, products_raw, partners_raw = load_raw_datasets(base_path)
    
    bundle_path = base_path / "models" / "fraud_pipeline.joblib"
    if not bundle_path.exists():
        raise FileNotFoundError("Model bundle not found. Please run train.py first.")
    
    bundle = joblib.load(bundle_path)
    pipeline = bundle["feature_pipeline"]
    model = bundle["production_model"]
    operating_threshold = bundle["operating_threshold"]
    
    # 1. Historical Analysis (Train with adjudicated outcomes)
    train_clean = clean_and_prepare_claims(train_raw, partners_raw, products_raw, is_training=True)
    known = train_clean[train_clean["is_fraud"].notna()].copy()
    known["is_fraud"] = known["is_fraud"].astype(int)
    
    X_train = pipeline.transform(known)
    known["risk_score"] = model.predict_proba(X_train)[:, 1]
    
    # Simulate monthly desk capacity (40 claims / month)
    monthly_results = []
    total_reviewed = 0
    total_fraud_caught = 0
    total_genuine_held = 0
    total_fraud_loss_prevented = 0.0
    total_goodwill_cost = 0.0
    total_desk_labor_cost = 0.0
    
    BLENDED_CONTACT_COST = 260.0  # Ops policy blended contact cost
    GOODWILL_COST = 380.0         # Ops policy goodwill compensation
    
    for month_period, group in known.groupby("submitted_month"):
        # Desk reviews top 40 highest risk claims in the month
        reviewed_group = group.sort_values("risk_score", ascending=False).head(40)
        frauds_in_review = reviewed_group[reviewed_group["is_fraud"] == 1]
        genuines_in_review = reviewed_group[reviewed_group["is_fraud"] == 0]
        
        fraud_caught_cnt = len(frauds_in_review)
        genuine_held_cnt = len(genuines_in_review)
        prevented_inr = frauds_in_review["claim_amount_inr"].sum()
        goodwill_inr = genuine_held_cnt * GOODWILL_COST
        desk_labor_inr = len(reviewed_group) * BLENDED_CONTACT_COST
        
        net_inr = prevented_inr - goodwill_inr - desk_labor_inr
        
        total_reviewed += len(reviewed_group)
        total_fraud_caught += fraud_caught_cnt
        total_genuine_held += genuine_held_cnt
        total_fraud_loss_prevented += prevented_inr
        total_goodwill_cost += goodwill_inr
        total_desk_labor_cost += desk_labor_inr
        
        monthly_results.append({
            "month": str(month_period),
            "claims_submitted": len(group),
            "claims_reviewed": len(reviewed_group),
            "frauds_detected": fraud_caught_cnt,
            "genuines_held": genuine_held_cnt,
            "prevented_fraud_loss_inr": round(float(prevented_inr), 2),
            "goodwill_cost_inr": round(float(goodwill_inr), 2),
            "desk_labor_cost_inr": round(float(desk_labor_inr), 2),
            "net_monthly_benefit_inr": round(float(net_inr), 2)
        })
        
    historical_net_benefit = total_fraud_loss_prevented - total_goodwill_cost - total_desk_labor_cost
    
    # 2. Projected Test Period Analysis (Q3 2026: July, August, September)
    test_clean = clean_and_prepare_claims(test_raw, partners_raw, products_raw, is_training=False)
    X_test = pipeline.transform(test_clean)
    test_clean["risk_score"] = model.predict_proba(X_test)[:, 1]
    
    test_monthly_projections = []
    projected_fraud_prevented = 0.0
    projected_goodwill = 0.0
    projected_labor = 0.0
    projected_reviews = 0
    
    # Average precision from validation indicates ~22% of top-40 flagged claims are actual fraud in post-May regime
    estimated_precision = 0.225
    
    for month_period, group in test_clean.groupby("submitted_month"):
        top_40 = group.sort_values("risk_score", ascending=False).head(40)
        avg_top_amount = top_40["claim_amount_inr"].mean()
        
        expected_frauds = int(round(len(top_40) * estimated_precision))
        expected_genuines = len(top_40) - expected_frauds
        
        m_prevented = expected_frauds * avg_top_amount
        m_goodwill = expected_genuines * GOODWILL_COST
        m_labor = len(top_40) * BLENDED_CONTACT_COST
        m_net = m_prevented - m_goodwill - m_labor
        
        projected_reviews += len(top_40)
        projected_fraud_prevented += m_prevented
        projected_goodwill += m_goodwill
        projected_labor += m_labor
        
        test_monthly_projections.append({
            "month": str(month_period),
            "claims_submitted": len(group),
            "allocated_investigation_slots": len(top_40),
            "average_claimed_amount_inr": round(float(avg_top_amount), 2),
            "estimated_frauds_intercepted": expected_frauds,
            "estimated_prevented_loss_inr": round(float(m_prevented), 2),
            "estimated_goodwill_penalty_inr": round(float(m_goodwill), 2),
            "estimated_desk_labor_inr": round(float(m_labor), 2),
            "projected_net_benefit_inr": round(float(m_net), 2)
        })
        
    projected_quarterly_net = projected_fraud_prevented - projected_goodwill - projected_labor
    
    impact_report = {
        "parameters": {
            "monthly_desk_capacity": 40,
            "goodwill_penalty_per_genuine_delayed_inr": GOODWILL_COST,
            "blended_contact_cost_inr": BLENDED_CONTACT_COST,
            "operating_threshold": round(operating_threshold, 4),
            "realization_rate": 1.0
        },
        "historical_performance_15_months": {
            "total_claims_in_period": len(known),
            "total_reviewed_by_desk": total_reviewed,
            "total_frauds_intercepted": total_fraud_caught,
            "total_genuine_held": total_genuine_held,
            "fraud_prevention_rate_rupees": round(total_fraud_loss_prevented, 2),
            "goodwill_costs_incurred_rupees": round(total_goodwill_cost, 2),
            "investigation_labor_cost_rupees": round(total_desk_labor_cost, 2),
            "net_financial_benefit_rupees": round(historical_net_benefit, 2),
            "net_benefit_per_investigated_claim_rupees": round(historical_net_benefit / total_reviewed, 2),
            "monthly_breakdown": monthly_results
        },
        "projected_q3_2026_test_quarter": {
            "total_unlabeled_claims": len(test_clean),
            "total_investigations_allocated": projected_reviews,
            "projected_gross_prevented_fraud_rupees": round(projected_fraud_prevented, 2),
            "projected_goodwill_cost_rupees": round(projected_goodwill, 2),
            "projected_investigation_labor_rupees": round(projected_labor, 2),
            "projected_net_quarterly_benefit_rupees": round(projected_quarterly_net, 2),
            "monthly_projections": test_monthly_projections
        }
    }
    
    reports_dir = base_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    with open(reports_dir / "business_impact.json", "w") as f:
        json.dump(impact_report, f, indent=2)
        
    print("Business impact analysis computed and saved to reports/business_impact.json")
    print(f"Historical Net Benefit: INR {historical_net_benefit:,.2f}")
    print(f"Net return per claim inspected: INR {historical_net_benefit / total_reviewed:,.2f}")
    print(f"Projected Q3 2026 Quarterly Benefit: INR {projected_quarterly_net:,.2f}")
    return impact_report


if __name__ == "__main__":
    compute_business_impact(".")
