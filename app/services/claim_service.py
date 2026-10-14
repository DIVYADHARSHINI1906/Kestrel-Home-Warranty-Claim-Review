"""
Claims Management and Data Query Service for Kestrel Home.
Provides fast in-memory indexing, search, filtering, and detail lookups across all claims.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
import joblib

from src.data_validation import load_raw_datasets, clean_and_prepare_claims


class ClaimService:
    def __init__(self, base_dir: str = "."):
        self.base_path = Path(base_dir)
        self.claims_df: pd.DataFrame = pd.DataFrame()
        self.products_df: pd.DataFrame = pd.DataFrame()
        self.partners_df: pd.DataFrame = pd.DataFrame()
        self.model_bundle: Optional[Dict[str, Any]] = None
        self._initialize()

    def _initialize(self):
        train_raw, test_raw, self.products_df, self.partners_df = load_raw_datasets(self.base_path)
        
        bundle_path = self.base_path / "models" / "fraud_pipeline.joblib"
        if bundle_path.exists():
            self.model_bundle = joblib.load(bundle_path)
        
        # Load predictions.csv if present
        preds_map = {}
        preds_path = self.base_path / "predictions.csv"
        if preds_path.exists():
            pdf = pd.read_csv(preds_path)
            preds_map = dict(zip(pdf["claim_id"], pdf["score"]))

        # Process Test Claims
        test_clean = clean_and_prepare_claims(test_raw, self.partners_df, self.products_df, is_training=False)
        test_clean["is_historical"] = False
        test_clean["historical_fraud_label"] = None
        test_clean["risk_score"] = test_clean["claim_id"].map(preds_map)
        
        # If test risk scores weren't mapped, predict them
        if test_clean["risk_score"].isna().any() and self.model_bundle:
            pipe = self.model_bundle["feature_pipeline"]
            m = self.model_bundle["production_model"]
            missing_mask = test_clean["risk_score"].isna()
            X_miss = pipe.transform(test_clean[missing_mask])
            test_clean.loc[missing_mask, "risk_score"] = m.predict_proba(X_miss)[:, 1]

        # Process Train Claims
        train_clean = clean_and_prepare_claims(train_raw, self.partners_df, self.products_df, is_training=True)
        train_clean["is_historical"] = True
        train_clean["historical_fraud_label"] = train_clean["is_fraud"]
        
        # Predict train scores using fitted model for uniform inspection
        if self.model_bundle:
            pipe = self.model_bundle["feature_pipeline"]
            m = self.model_bundle["production_model"]
            X_train = pipe.transform(train_clean)
            train_clean["risk_score"] = np.round(m.predict_proba(X_train)[:, 1], 4)
        else:
            train_clean["risk_score"] = 0.02

        # Combine datasets (Test claims first, then train)
        combined = pd.concat([test_clean, train_clean], ignore_index=True)
        combined["risk_score"] = combined["risk_score"].fillna(0.02)
        
        # Assign risk tiers and recommendations
        def assign_tier_and_action(row):
            score = float(row["risk_score"])
            amt = float(row["claim_amount_inr"])
            insp = str(row["partner_inspected"]).upper()
            
            # Policy Rule: claim >= 2000 MUST be inspected (§5)
            if amt >= 2000.0 and insp == "N":
                tier = "Policy Non-Compliant"
                rec = "Reject: Missing Inspection"
            elif score >= 0.75:
                tier = "Critical"
                rec = "Escalate for Immediate Fraud Audit"
            elif score >= 0.46:
                tier = "High"
                rec = "Hold for Desk Review (Priority Queue)"
            elif score >= 0.20:
                tier = "Moderate"
                rec = "Hold for Secondary Technical Verification"
            else:
                tier = "Low"
                if amt < 2000.0 and row.get("submitted_dt", pd.Timestamp("2026-06-01")) >= pd.Timestamp("2026-05-01"):
                    rec = "Auto-Approve Payout (§5)"
                else:
                    rec = "Standard Approval"
            return pd.Series([tier, rec])

        combined[["risk_tier", "recommendation"]] = combined.apply(assign_tier_and_action, axis=1)
        self.claims_df = combined

    def get_claims(
        self,
        search: Optional[str] = None,
        risk_tier: Optional[str] = None,
        product_family: Optional[str] = None,
        partner_id: Optional[str] = None,
        partner_inspected: Optional[str] = None,
        photo_attached: Optional[str] = None,
        is_historical: Optional[bool] = None,
        sort_by: str = "submitted_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 25
    ) -> Tuple[List[Dict[str, Any]], int]:
        df = self.claims_df

        if is_historical is not None:
            df = df[df["is_historical"] == is_historical]

        if search:
            s = search.strip().lower()
            mask = (
                df["claim_id"].str.lower().str.contains(s) |
                df["partner_id"].str.lower().str.contains(s) |
                df["product_serial"].astype(str).str.lower().str.contains(s) |
                df["claim_description"].astype(str).str.lower().str.contains(s) |
                df["city"].astype(str).str.lower().str.contains(s) |
                df["family"].astype(str).str.lower().str.contains(s)
            )
            df = df[mask]

        if risk_tier and risk_tier.lower() != "all":
            df = df[df["risk_tier"].str.lower() == risk_tier.lower()]

        if product_family and product_family.lower() != "all":
            df = df[df["family"].str.lower() == product_family.lower()]

        if partner_id and partner_id.lower() != "all":
            df = df[df["partner_id"].str.lower() == partner_id.lower()]

        if partner_inspected and partner_inspected.lower() != "all":
            df = df[df["partner_inspected"].str.upper() == partner_inspected.upper()]

        if photo_attached and photo_attached.lower() != "all":
            df = df[df["photo_attached"].str.upper() == photo_attached.upper()]

        # Sorting
        ascending = (sort_order.lower() == "asc")
        if sort_by in df.columns:
            df = df.sort_values(by=sort_by, ascending=ascending)
        else:
            df = df.sort_values(by="submitted_at", ascending=False)

        total_count = len(df)
        start = (page - 1) * page_size
        end = start + page_size
        page_df = df.iloc[start:end]

        results = []
        for _, row in page_df.iterrows():
            results.append({
                "claim_id": str(row["claim_id"]),
                "submitted_at": str(row["submitted_at"]),
                "partner_id": str(row["partner_id"]),
                "partner_city": str(row.get("city", "Unknown")),
                "partner_type": str(row.get("partner_type", "ASC")),
                "sku": str(row["sku"]),
                "product_family": str(row.get("family", "Unknown")),
                "claim_amount_inr": float(row["claim_amount_inr"]),
                "photo_attached": str(row["photo_attached"]),
                "partner_inspected": str(row["partner_inspected"]),
                "risk_score": float(round(row["risk_score"], 4)),
                "risk_tier": str(row["risk_tier"]),
                "recommendation": str(row["recommendation"]),
                "source": str(row.get("source", "crm")),
                "is_historical": bool(row["is_historical"]),
                "historical_fraud_label": int(row["historical_fraud_label"]) if pd.notna(row.get("historical_fraud_label")) else None
            })

        return results, total_count

    def get_claim_by_id(self, claim_id: str) -> Optional[Dict[str, Any]]:
        matches = self.claims_df[self.claims_df["claim_id"].str.upper() == claim_id.strip().upper()]
        if matches.empty:
            return None
        row = matches.iloc[0]
        return {
            "claim_id": str(row["claim_id"]),
            "submitted_at": str(row["submitted_at"]),
            "partner_id": str(row["partner_id"]),
            "sku": str(row["sku"]),
            "product_serial": str(row["product_serial"]),
            "days_since_purchase": int(row["days_since_purchase"]),
            "claim_amount_inr": float(row["claim_amount_inr"]),
            "photo_attached": str(row["photo_attached"]),
            "partner_inspected": str(row["partner_inspected"]),
            "claim_description": str(row["claim_description"]),
            "inspector_note": str(row["inspector_note"]) if pd.notna(row.get("inspector_note")) else None,
            "customer_prior_claims": int(row["customer_prior_claims"]),
            "source": str(row.get("source", "crm")),
            "product_family": str(row.get("family", "Unknown")),
            "list_price_inr": float(row.get("list_price_inr", 0)),
            "warranty_months": int(row.get("warranty_months", 12)),
            "city": str(row.get("city", "Unknown")),
            "partner_type": str(row.get("partner_type", "Unknown")),
            "onboarded_date": str(row.get("onboarded_date", "Unknown")),
            "risk_score": float(round(row["risk_score"], 4)),
            "risk_tier": str(row["risk_tier"]),
            "recommendation": str(row["recommendation"]),
            "is_historical": bool(row["is_historical"]),
            "historical_fraud_label": int(row["historical_fraud_label"]) if pd.notna(row.get("historical_fraud_label")) else None,
            "adjudication": getattr(self, "adjudications", {}).get(str(row["claim_id"]))
        }

    def adjudicate_claim(
        self,
        claim_id: str,
        action: str,
        reviewer: str = "Kabir Nanda (Lead Risk Officer)",
        notes: str = ""
    ) -> Optional[Dict[str, Any]]:
        claim_id = claim_id.strip().upper()
        if not hasattr(self, "adjudications"):
            self.adjudications = {}

        matches = self.claims_df[self.claims_df["claim_id"].str.upper() == claim_id]
        if matches.empty:
            return None

        action_upper = action.upper()
        status_label_map = {
            "APPROVE": "Adjudicated: Approved for Payment",
            "HOLD": "Adjudicated: Held for Physical Audit",
            "REJECT": "Adjudicated: Rejected (Fraud / Policy Violation)"
        }
        status_label = status_label_map.get(action_upper, f"Adjudicated: {action_upper}")

        from datetime import datetime
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

        record = {
            "claim_id": claim_id,
            "action": action_upper,
            "status_label": status_label,
            "reviewer": reviewer,
            "timestamp": now_str,
            "notes": notes,
            "success": True
        }
        self.adjudications[claim_id] = record

        # Update in-memory DataFrame recommendation & risk tier display
        idx = matches.index[0]
        self.claims_df.at[idx, "recommendation"] = status_label
        if action_upper == "APPROVE":
            self.claims_df.at[idx, "risk_tier"] = "Low"
        elif action_upper == "REJECT":
            self.claims_df.at[idx, "risk_tier"] = "Critical"

        return record


_claim_service_instance: Optional[ClaimService] = None

def get_claim_service() -> ClaimService:
    global _claim_service_instance
    if _claim_service_instance is None:
        _claim_service_instance = ClaimService(".")
    return _claim_service_instance
