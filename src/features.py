"""
Feature Engineering Module for Kestrel Home Warranty Claim Review.
Implements leak-free feature transformations, ratio calculations, policy indicators,
and empirical Bayes target smoothing for partner & geographic risk.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

FEATURE_NAMES = [
    "claim_amount_inr",
    "days_since_purchase",
    "customer_prior_claims",
    "photo_attached_flag",
    "partner_inspected_flag",
    "has_inspector_note",
    "is_under_2k",
    "uninspected_under_2k",
    "amount_to_list_ratio",
    "warranty_consumed_ratio",
    "near_warranty_expiry",
    "early_failure",
    "partner_tenure_days",
    "is_new_partner",
    "partner_smoothed_risk",
    "city_smoothed_risk",
    "serial_has_whitespace",
    "serial_len",
    "is_franchise",
    "is_freelance",
    "submission_hour",
    "is_night_submission"
]


class ClaimFeaturePipeline(BaseEstimator, TransformerMixin):
    """
    Scikit-learn compatible transformer that converts cleaned claim DataFrames
    into numerical feature matrices.
    """

    def __init__(self, smoothing_weight: float = 10.0):
        self.smoothing_weight = smoothing_weight
        self.global_fraud_rate_: float = 0.0123
        self.partner_risk_map_: Dict[str, float] = {}
        self.city_risk_map_: Dict[str, float] = {}
        self.feature_names_: List[str] = FEATURE_NAMES

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None):
        """
        Learns empirical Bayes prior rates from the training dataset.
        """
        if y is not None:
            y_arr = np.asarray(y)
            self.global_fraud_rate_ = float(np.mean(y_arr[~np.isnan(y_arr)]))
            
            # Partner smoothed risk
            p_df = pd.DataFrame({"partner_id": X["partner_id"], "target": y_arr})
            p_agg = p_df.groupby("partner_id")["target"].agg(["count", "sum"])
            m = self.smoothing_weight
            p_smoothed = (p_agg["sum"] + m * self.global_fraud_rate_) / (p_agg["count"] + m)
            self.partner_risk_map_ = p_smoothed.to_dict()
            
            # City smoothed risk
            if "city" in X.columns:
                c_df = pd.DataFrame({"city": X["city"], "target": y_arr})
                c_agg = c_df.groupby("city")["target"].agg(["count", "sum"])
                c_smoothed = (c_agg["sum"] + m * self.global_fraud_rate_) / (c_agg["count"] + m)
                self.city_risk_map_ = c_smoothed.to_dict()

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms input DataFrame into the model feature space.
        """
        df = X.copy()
        features = pd.DataFrame(index=df.index)

        features["claim_amount_inr"] = pd.to_numeric(df["claim_amount_inr"], errors="coerce").fillna(0.0)
        features["days_since_purchase"] = pd.to_numeric(df["days_since_purchase"], errors="coerce").fillna(0.0)
        features["customer_prior_claims"] = pd.to_numeric(df["customer_prior_claims"], errors="coerce").fillna(0).astype(int)

        # Binary operational flags
        photo = df["photo_attached"] if "photo_attached" in df.columns else df.get("photo_attached_flag", 0)
        if isinstance(photo.iloc[0] if len(photo) > 0 else 0, str):
            features["photo_attached_flag"] = (photo == "Y").astype(int)
        else:
            features["photo_attached_flag"] = photo.astype(int)

        inspected = df["partner_inspected"] if "partner_inspected" in df.columns else df.get("partner_inspected_flag", 0)
        if isinstance(inspected.iloc[0] if len(inspected) > 0 else 0, str):
            features["partner_inspected_flag"] = (inspected == "Y").astype(int)
        else:
            features["partner_inspected_flag"] = inspected.astype(int)

        # Inspector note indicator
        if "inspector_note" in df.columns:
            features["has_inspector_note"] = df["inspector_note"].notna().astype(int)
        else:
            features["has_inspector_note"] = 0

        # Policy & gaming signals
        features["is_under_2k"] = (features["claim_amount_inr"] < 2000.0).astype(int)
        features["uninspected_under_2k"] = (
            (features["is_under_2k"] == 1) & (features["partner_inspected_flag"] == 0)
        ).astype(int)

        # Ratios
        list_price_series = df["list_price_inr"] if "list_price_inr" in df.columns else pd.Series(5000.0, index=df.index)
        list_price = pd.to_numeric(list_price_series, errors="coerce").fillna(5000.0).clip(lower=100.0)
        features["amount_to_list_ratio"] = (features["claim_amount_inr"] / list_price).clip(lower=0.0, upper=2.0)

        warranty_months_series = df["warranty_months"] if "warranty_months" in df.columns else pd.Series(12.0, index=df.index)
        warranty_months = pd.to_numeric(warranty_months_series, errors="coerce").fillna(12.0).clip(lower=1.0)
        warranty_days = warranty_months * 30.5
        features["warranty_consumed_ratio"] = (features["days_since_purchase"] / warranty_days).clip(lower=0.0, upper=3.0)
        features["near_warranty_expiry"] = (features["warranty_consumed_ratio"] > 0.85).astype(int)
        features["early_failure"] = (features["days_since_purchase"] < 30.0).astype(int)

        # Partner tenure & flags
        if "partner_tenure_days" in df.columns:
            features["partner_tenure_days"] = pd.to_numeric(df["partner_tenure_days"], errors="coerce").fillna(365.0).clip(lower=0.0)
        elif "submitted_dt" in df.columns and "onboarded_dt" in df.columns:
            features["partner_tenure_days"] = (df["submitted_dt"] - df["onboarded_dt"]).dt.days.fillna(365.0).clip(lower=0.0)
        elif "submitted_at" in df.columns and "onboarded_date" in df.columns:
            sub_dt = pd.to_datetime(df["submitted_at"], errors="coerce")
            onb_dt = pd.to_datetime(df["onboarded_date"], errors="coerce")
            features["partner_tenure_days"] = (sub_dt - onb_dt).dt.days.fillna(365.0).clip(lower=0.0)
        else:
            features["partner_tenure_days"] = pd.Series(365.0, index=df.index)
        features["is_new_partner"] = (features["partner_tenure_days"] < 365.0).astype(int)

        # Smoothed risks
        features["partner_smoothed_risk"] = df["partner_id"].map(self.partner_risk_map_).fillna(self.global_fraud_rate_)
        if "city" in df.columns:
            features["city_smoothed_risk"] = df["city"].map(self.city_risk_map_).fillna(self.global_fraud_rate_)
        else:
            features["city_smoothed_risk"] = pd.Series(self.global_fraud_rate_, index=df.index)

        # Serial anomalies
        if "product_serial" in df.columns:
            clean_s = df["product_serial"].astype(str).str.strip()
            features["serial_has_whitespace"] = (df["product_serial"].astype(str) != clean_s).astype(int)
            features["serial_len"] = clean_s.str.len().fillna(11).astype(int)
        else:
            features["serial_has_whitespace"] = pd.Series(0, index=df.index)
            features["serial_len"] = pd.Series(11, index=df.index)

        # Partner type
        p_type = df["partner_type"] if "partner_type" in df.columns else pd.Series("authorised_service_centre", index=df.index)
        features["is_franchise"] = (p_type == "franchise").astype(int)
        features["is_freelance"] = (p_type == "freelance_technician").astype(int)

        # Submission hour
        if "submitted_dt" in df.columns:
            dt_series = pd.to_datetime(df["submitted_dt"])
            features["submission_hour"] = dt_series.dt.hour.fillna(12).astype(int)
        elif "submitted_at" in df.columns:
            dt_series = pd.to_datetime(df["submitted_at"], errors="coerce")
            features["submission_hour"] = dt_series.dt.hour.fillna(12).astype(int)
        else:
            features["submission_hour"] = 12

        features["is_night_submission"] = features["submission_hour"].isin([22, 23, 0, 1, 2, 3, 4, 5]).astype(int)

        # Ensure all columns exist and ordered
        return features[self.feature_names_]


def extract_claim_evidence_factors(row: pd.Series, risk_score: float) -> List[str]:
    """
    Extracts human-understandable, evidence-backed reasons for a claim's fraud score.
    """
    factors = []
    
    # 1. Gaming May 1 policy change
    claim_amt = float(row.get("claim_amount_inr", 0))
    partner_insp = str(row.get("partner_inspected", "Y")).upper()
    if claim_amt < 2000.0 and partner_insp == "N":
        factors.append("Sub-₹2,000 claim submitted without partner inspection (uninspected threshold gaming).")
    
    # 2. Prior claim history
    priors = int(row.get("customer_prior_claims", 0))
    if priors >= 2:
        factors.append(f"Customer has elevated claim frequency ({priors} previous warranty claims recorded).")
        
    # 3. High claim to list price ratio
    list_price = float(row.get("list_price_inr", 5000))
    if list_price > 0:
        ratio = claim_amt / list_price
        if ratio > 0.65:
            factors.append(f"High claim-to-list-price ratio ({ratio:.1%} of product retail value of ₹{list_price:,.0f}).")
            
    # 4. Photo attached
    photo = str(row.get("photo_attached", "Y")).upper()
    if photo == "N":
        factors.append("No photographic evidence attached with the claim submission.")
        
    # 5. Serial formatting anomaly
    serial = str(row.get("product_serial", ""))
    if serial != serial.strip() or len(serial.strip()) != 11:
        factors.append("Serial number formatting anomaly (irregular length or whitespace detected).")
        
    # 6. High partner risk / surge outlet
    partner_id = str(row.get("partner_id", ""))
    surge_partners = ["SP3160", "SP3232", "SP3318", "SP3129", "SP3319", "SP3207", "SP3376", "SP3095"]
    if partner_id in surge_partners:
        factors.append(f"Partner {partner_id} associated with abnormal small-claim surge patterns.")
        
    # 7. Low risk factors if score is low
    if risk_score < 0.20 and not factors:
        factors.append("Standard claim amount with complete inspection sign-off and valid warranty window.")
        
    return factors
