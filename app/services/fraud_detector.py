"""
Real-time Claim Fraud Detector and Policy Rule Engine for Kestrel Home.
Evaluates single claims, extracts evidence factors, checks ops policy rules,
and generates actionable triage recommendations.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
import joblib

from app.schemas import ClaimInput, ClaimPredictionResponse, PolicyCheckResult
from src.features import extract_claim_evidence_factors


class FraudDetector:
    def __init__(self, base_dir: str = "."):
        self.base_path = Path(base_dir)
        self.bundle_path = self.base_path / "models" / "fraud_pipeline.joblib"
        self.bundle: Optional[Dict[str, Any]] = None
        self._load_bundle()

    def _load_bundle(self):
        if self.bundle_path.exists():
            self.bundle = joblib.load(self.bundle_path)
        else:
            self.bundle = None

    def evaluate_claim(
        self,
        claim: ClaimInput,
        products_df: pd.DataFrame,
        partners_df: pd.DataFrame
    ) -> ClaimPredictionResponse:
        if not self.bundle:
            self._load_bundle()
            if not self.bundle:
                raise RuntimeError("Model pipeline bundle not found. Please run train.py first.")

        pipeline = self.bundle["feature_pipeline"]
        model = self.bundle["production_model"]
        operating_threshold = self.bundle.get("operating_threshold", 0.4615)

        # Lookup product and partner info
        prod_row = products_df[products_df["sku"].str.upper() == claim.sku.strip().upper()]
        if not prod_row.empty:
            list_price = float(prod_row.iloc[0]["list_price_inr"])
            warranty_months = int(prod_row.iloc[0]["warranty_months"])
            family = str(prod_row.iloc[0]["family"])
        else:
            list_price = 5000.0
            warranty_months = 12
            family = "Unknown"

        part_row = partners_df[partners_df["partner_id"].str.upper() == claim.partner_id.strip().upper()]
        if not part_row.empty:
            city = str(part_row.iloc[0]["city"])
            partner_type = str(part_row.iloc[0]["partner_type"])
            onboarded_date = str(part_row.iloc[0]["onboarded_date"])
        else:
            city = "Unknown"
            partner_type = "authorised_service_centre"
            onboarded_date = "2024-01-01"

        # Build single-row DataFrame for pipeline transformation
        claim_dict = {
            "claim_id": claim.claim_id or "WC-PREDICT",
            "submitted_at": claim.submitted_at or "2026-08-01 12:00",
            "partner_id": claim.partner_id,
            "sku": claim.sku,
            "product_serial": claim.product_serial,
            "days_since_purchase": claim.days_since_purchase,
            "claim_amount_inr": claim.claim_amount_inr,
            "photo_attached": claim.photo_attached.upper(),
            "partner_inspected": claim.partner_inspected.upper(),
            "claim_description": claim.claim_description,
            "inspector_note": claim.inspector_note,
            "customer_prior_claims": claim.customer_prior_claims,
            "source": claim.source or "crm",
            "list_price_inr": list_price,
            "warranty_months": warranty_months,
            "family": family,
            "city": city,
            "partner_type": partner_type,
            "onboarded_date": onboarded_date
        }
        
        single_df = pd.DataFrame([claim_dict])
        single_df["submitted_dt"] = pd.to_datetime(single_df["submitted_at"])
        single_df["onboarded_dt"] = pd.to_datetime(single_df["onboarded_date"])
        single_df["partner_tenure_days"] = (single_df["submitted_dt"] - single_df["onboarded_dt"]).dt.days.clip(lower=0)
        single_df["photo_attached_flag"] = (single_df["photo_attached"] == "Y").astype(int)
        single_df["partner_inspected_flag"] = (single_df["partner_inspected"] == "Y").astype(int)

        # Predict score
        X = pipeline.transform(single_df)
        score = float(model.predict_proba(X)[0, 1])
        score = round(score, 4)

        # Policy checks according to ops-policy.pdf
        policy_checks: List[PolicyCheckResult] = []

        # 1. Inspection Sign-off Check (§5)
        # "From 1 May 2026, claims under Rs 2,000 are auto-approved without inspection to cut turnaround time. Larger claims still need inspection."
        if claim.claim_amount_inr >= 2000.0:
            if claim.partner_inspected.upper() == "Y":
                policy_checks.append(PolicyCheckResult(
                    rule_name="Ops Policy §5: Mandatory Inspection Sign-off (>= ₹2,000)",
                    passed=True,
                    details=f"Claim amount ₹{claim.claim_amount_inr:,.2f} is above ₹2,000 threshold and includes verified partner inspection sign-off.",
                    severity="INFO"
                ))
            else:
                policy_checks.append(PolicyCheckResult(
                    rule_name="Ops Policy §5: Mandatory Inspection Sign-off (>= ₹2,000)",
                    passed=False,
                    details=f"Claim amount ₹{claim.claim_amount_inr:,.2f} requires mandatory partner inspection sign-off before payout.",
                    severity="VIOLATION"
                ))
        else:
            policy_checks.append(PolicyCheckResult(
                rule_name="Ops Policy §5: Auto-Approval Eligibility (< ₹2,000)",
                passed=True,
                details=f"Claim amount ₹{claim.claim_amount_inr:,.2f} is under ₹2,000; eligible for expedited turnaround without mandatory pre-approval inspection.",
                severity="INFO"
            ))

        # 2. Warranty Window Check (§1)
        max_warranty_days = warranty_months * 30.5
        if claim.days_since_purchase <= max_warranty_days:
            policy_checks.append(PolicyCheckResult(
                rule_name="Warranty Period Validity",
                passed=True,
                details=f"Claim submitted at day {claim.days_since_purchase} is within the {warranty_months}-month warranty window (~{max_warranty_days:.0f} days).",
                severity="INFO"
            ))
        else:
            policy_checks.append(PolicyCheckResult(
                rule_name="Warranty Period Validity",
                passed=False,
                details=f"Claim submitted at day {claim.days_since_purchase} exceeds product {warranty_months}-month warranty window (~{max_warranty_days:.0f} days).",
                severity="VIOLATION"
            ))

        # 3. Claim Amount vs List Price Check
        if claim.claim_amount_inr <= list_price:
            policy_checks.append(PolicyCheckResult(
                rule_name="Claim Value vs List Price",
                passed=True,
                details=f"Claim amount ₹{claim.claim_amount_inr:,.2f} is within SKU list price (₹{list_price:,.2f}).",
                severity="INFO"
            ))
        else:
            policy_checks.append(PolicyCheckResult(
                rule_name="Claim Value vs List Price",
                passed=False,
                details=f"Claim amount ₹{claim.claim_amount_inr:,.2f} exceeds product list price (₹{list_price:,.2f}).",
                severity="VIOLATION"
            ))

        # 4. Photo Evidence Check (§5)
        if claim.photo_attached.upper() == "Y":
            policy_checks.append(PolicyCheckResult(
                rule_name="Photo Verification Attachment",
                passed=True,
                details="Photographic evidence of defect was submitted.",
                severity="INFO"
            ))
        else:
            policy_checks.append(PolicyCheckResult(
                rule_name="Photo Verification Attachment",
                passed=False,
                details="No photo documentation submitted. Increases verification burden for disputed claims.",
                severity="WARNING"
            ))

        # Data quality checks
        data_quality_flags: List[str] = []
        raw_serial = claim.product_serial
        clean_serial = raw_serial.strip()
        if raw_serial != clean_serial:
            data_quality_flags.append("Serial number contains leading or trailing whitespace (partner entry typo).")
        if len(clean_serial) != 11:
            data_quality_flags.append(f"Non-standard serial length ({len(clean_serial)} chars; standard is 11 chars).")
        if claim.partner_inspected.upper() == "Y" and not claim.inspector_note:
            data_quality_flags.append("Partner marked claim as inspected, but no inspector notes were provided.")

        # Evidence factors
        evidence_factors = extract_claim_evidence_factors(single_df.iloc[0], score)

        # Determine Risk Tier and Recommendation
        violations = [c for c in policy_checks if c.severity == "VIOLATION"]
        
        if score >= 0.75:
            risk_tier = "Critical"
        elif score >= operating_threshold:
            risk_tier = "High"
        elif score >= 0.20:
            risk_tier = "Moderate"
        else:
            risk_tier = "Low"

        if violations:
            violation_names = ", ".join([v.rule_name for v in violations])
            recommended_action = f"Policy Rejection: {violation_names}"
            rationale = (
                "Claim violates operational warranty policy rules. Human verification must decline or return "
                "the claim to the service partner for corrective documentation."
            )
        elif risk_tier in ["Critical", "High"]:
            recommended_action = "Hold for Claims Investigation Desk Review"
            rationale = (
                f"Elevated fraud risk score ({score:.2%}) exceeds the calibrated operational review threshold ({operating_threshold:.2%}). "
                "Allocates 1 of 40 monthly investigation desk slots. Human review required before payout."
            )
        elif risk_tier == "Moderate":
            recommended_action = "Secondary Technical Verification / Request Photo"
            rationale = (
                f"Moderate risk score ({score:.2%}). Route for quick documentation check or request photo/invoice "
                "before releasing payment."
            )
        else:
            if claim.claim_amount_inr < 2000.0:
                recommended_action = "Auto-Approve Expedited Payout (§5)"
                rationale = "Low risk score and compliant sub-₹2,000 claim eligible for turnaround fast-tracking."
            else:
                recommended_action = "Approve Standard Payout"
                rationale = "Low risk score with valid warranty and partner inspection sign-off verified."

        return ClaimPredictionResponse(
            claim_id=claim.claim_id or "WC-SIMULATED",
            risk_score=score,
            risk_tier=risk_tier,
            evidence_factors=evidence_factors,
            policy_checks=policy_checks,
            data_quality_flags=data_quality_flags,
            recommended_action=recommended_action,
            recommended_action_rationale=rationale,
            operational_context={
                "monthly_desk_capacity": 40,
                "operating_threshold": operating_threshold,
                "goodwill_cost_if_delayed_inr": 380,
                "potential_loss_avoided_if_fraud_inr": claim.claim_amount_inr,
                "partner_city": city,
                "partner_type": partner_type,
                "product_family": family,
                "list_price_inr": list_price
            }
        )


_fraud_detector_instance: Optional[FraudDetector] = None

def get_fraud_detector() -> FraudDetector:
    global _fraud_detector_instance
    if _fraud_detector_instance is None:
        _fraud_detector_instance = FraudDetector(".")
    return _fraud_detector_instance
