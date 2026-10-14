"""
Pydantic Schemas for Kestrel Home Warranty Claim Review API.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ClaimInput(BaseModel):
    claim_id: Optional[str] = Field("WC-SIMULATED", description="Claim identification number")
    submitted_at: Optional[str] = Field("2026-08-15 14:30", description="Submission timestamp in IST")
    partner_id: str = Field(..., description="Service partner ID (e.g., SP3033)")
    sku: str = Field(..., description="Product SKU (e.g., KH-AF-01)")
    product_serial: str = Field(..., description="Product serial number entered by partner")
    days_since_purchase: int = Field(..., ge=0, description="Elapsed days between purchase and claim")
    claim_amount_inr: float = Field(..., ge=0, description="Amount claimed in INR")
    photo_attached: str = Field("Y", description="Y or N")
    partner_inspected: str = Field("Y", description="Y or N")
    claim_description: str = Field(..., description="Partner fault description")
    inspector_note: Optional[str] = Field(None, description="Inspector sign-off note if inspected")
    customer_prior_claims: int = Field(0, ge=0, description="Customer past warranty claim count")
    source: Optional[str] = Field("crm", description="Originating system: crm or legacy_zoho")


class PolicyCheckResult(BaseModel):
    rule_name: str
    passed: bool
    details: str
    severity: str  # "INFO", "WARNING", "VIOLATION"


class ClaimPredictionResponse(BaseModel):
    claim_id: str
    risk_score: float
    risk_tier: str  # "Low", "Moderate", "High", "Critical"
    evidence_factors: List[str]
    policy_checks: List[PolicyCheckResult]
    data_quality_flags: List[str]
    recommended_action: str
    recommended_action_rationale: str
    operational_context: Dict[str, Any]


class ClaimSummaryItem(BaseModel):
    claim_id: str
    submitted_at: str
    partner_id: str
    partner_city: str
    partner_type: str
    sku: str
    product_family: str
    claim_amount_inr: float
    photo_attached: str
    partner_inspected: str
    risk_score: float
    risk_tier: str
    recommendation: str
    source: str
    is_historical: bool
    historical_fraud_label: Optional[int] = None


class PaginatedClaimsResponse(BaseModel):
    total_count: int
    page: int
    page_size: int
    total_pages: int
    claims: List[ClaimSummaryItem]


class BusinessImpactRequest(BaseModel):
    monthly_capacity: int = Field(40, ge=5, le=200)
    goodwill_cost_inr: float = Field(380.0, ge=0)
    contact_cost_inr: float = Field(260.0, ge=0)
    realization_rate: float = Field(1.0, ge=0.1, le=1.0)


class AdjudicationRequest(BaseModel):
    action: str = Field(..., description="APPROVE, HOLD, or REJECT")
    reviewer: Optional[str] = Field("Kabir Nanda", description="Name/role of reviewer")
    notes: Optional[str] = Field("", description="Audit notes or rationale")


class AdjudicationResponse(BaseModel):
    claim_id: str
    action: str
    status_label: str
    reviewer: str
    timestamp: str
    notes: str
    success: bool
