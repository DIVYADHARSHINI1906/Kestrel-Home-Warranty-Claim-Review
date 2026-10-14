"""
Data Validation and Ingestion Module for Kestrel Home Warranty System.
Handles schema validation, missing data triage, deduplication, and legacy format handling.
"""

from pathlib import Path
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np

REQUIRED_TRAIN_COLUMNS = [
    "claim_id", "submitted_at", "partner_id", "sku", "product_serial",
    "days_since_purchase", "claim_amount_inr", "photo_attached",
    "partner_inspected", "claim_description", "customer_prior_claims", "source"
]

REQUIRED_PRODUCT_COLUMNS = ["sku", "family", "list_price_inr", "warranty_months"]
REQUIRED_PARTNER_COLUMNS = ["partner_id", "city", "onboarded_date", "partner_type"]


def load_raw_datasets(base_dir: Path | str = ".") -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Loads raw CSV files from the base directory.
    """
    base_path = Path(base_dir)
    train_df = pd.read_csv(base_path / "train.csv")
    test_df = pd.read_csv(base_path / "test_unlabelled.csv")
    products_df = pd.read_csv(base_path / "products.csv")
    partners_df = pd.read_csv(base_path / "partners.csv")
    return train_df, test_df, products_df, partners_df


def validate_schema(df: pd.DataFrame, required_columns: list, dataset_name: str = "Dataset") -> Dict[str, Any]:
    """
    Validates that a DataFrame contains all required columns and checks null distributions.
    """
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        raise ValueError(f"[{dataset_name}] Missing required columns: {missing_cols}")

    null_counts = df[required_columns].isnull().sum().to_dict()
    total_rows = len(df)

    return {
        "status": "VALID",
        "dataset_name": dataset_name,
        "total_rows": total_rows,
        "columns_checked": len(required_columns),
        "null_counts": null_counts,
    }


def clean_and_prepare_claims(
    claims_df: pd.DataFrame,
    partners_df: pd.DataFrame,
    products_df: pd.DataFrame,
    is_training: bool = True
) -> pd.DataFrame:
    """
    Cleans claim records, joins reference tables (partners and products),
    standardizes timestamps, and tags data quality flags.
    """
    df = claims_df.copy()

    # Standardize serials (strip leading/trailing whitespaces)
    df["product_serial_clean"] = df["product_serial"].astype(str).str.strip()
    df["serial_has_whitespace"] = (df["product_serial"].astype(str) != df["product_serial_clean"]).astype(int)
    df["serial_length"] = df["product_serial_clean"].str.len()

    # Parse timestamps
    df["submitted_dt"] = pd.to_datetime(df["submitted_at"])
    df["submitted_date"] = df["submitted_dt"].dt.date
    df["submitted_month"] = df["submitted_dt"].dt.to_period("M").astype(str)

    # Join Products
    df = df.merge(products_df, on="sku", how="left")
    # If any unknown sku in inference, provide sensible fallbacks
    df["list_price_inr"] = df["list_price_inr"].fillna(5000.0)
    df["warranty_months"] = df["warranty_months"].fillna(12.0)
    df["family"] = df["family"].fillna("Other")

    # Join Partners
    df = df.merge(partners_df, on="partner_id", how="left")
    df["city"] = df["city"].fillna("Unknown")
    df["partner_type"] = df["partner_type"].fillna("authorised_service_centre")
    df["onboarded_date"] = df["onboarded_date"].fillna("2024-01-01")
    df["onboarded_dt"] = pd.to_datetime(df["onboarded_date"])

    # Compute tenure
    df["partner_tenure_days"] = (df["submitted_dt"] - df["onboarded_dt"]).dt.days.clip(lower=0)

    # Normalize binary flags
    df["photo_attached_flag"] = (df["photo_attached"] == "Y").astype(int)
    df["partner_inspected_flag"] = (df["partner_inspected"] == "Y").astype(int)

    # In training, drop undecided CRM records (where is_fraud is NaN) for supervised model fitting
    if is_training and "is_fraud" in df.columns:
        df["is_fraud_numeric"] = pd.to_numeric(df["is_fraud"], errors="coerce")

    return df


def audit_data_integrity(train_df: pd.DataFrame, test_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Produces an operational data audit summarizing CRM migration quirks,
    bounced claim duplicates, serial anomalies, and undecided records.
    """
    total_train = len(train_df)
    train_duplicates = train_df["claim_id"].duplicated().sum()
    undecided_crm = train_df["is_fraud"].isna().sum()
    legacy_zoho_rows = (train_df["source"] == "legacy_zoho").sum()
    crm_rows = (train_df["source"] == "crm").sum()
    
    clean_serials = train_df["product_serial"].astype(str).str.strip()
    whitespace_serials = (train_df["product_serial"].astype(str) != clean_serials).sum()
    
    return {
        "train_rows": total_train,
        "test_rows": len(test_df),
        "train_resubmissions_duplicate_ids": int(train_duplicates),
        "undecided_crm_claims": int(undecided_crm),
        "legacy_zoho_rows": int(legacy_zoho_rows),
        "crm_rows": int(crm_rows),
        "whitespace_serials_in_train": int(whitespace_serials),
        "note": "Legacy Zoho lacked blank storage; undecided cases were recorded as 0. CRM stores open cases as blanks."
    }


if __name__ == "__main__":
    t_df, te_df, pr_df, pa_df = load_raw_datasets(".")
    audit = audit_data_integrity(t_df, te_df)
    print("Data Audit Complete:")
    for k, v in audit.items():
        print(f"  {k}: {v}")
