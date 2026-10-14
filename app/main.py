"""
Main FastAPI Application for Kestrel Home Warranty Claim Review & Fraud Detection System.
Provides RESTful endpoints for dashboard metrics, claims triage, real-time prediction,
policy validation, and financial impact simulation.
"""

from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.schemas import (
    ClaimInput,
    ClaimPredictionResponse,
    PaginatedClaimsResponse,
    BusinessImpactRequest
)
from app.services.claim_service import get_claim_service
from app.services.fraud_detector import get_fraud_detector
from app.services.analytics_service import get_analytics_service

app = FastAPI(
    title="Kestrel Home — Warranty Claim Review & Fraud Detection",
    description="Operational Risk Management & Fraud Detection System for Home Appliance Claims",
    version="1.0.0"
)

# Enable CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_path = Path(__file__).parent / "static"


@app.get("/health")
def health_check():
    claim_service = get_claim_service()
    total_claims = len(claim_service.claims_df) if not claim_service.claims_df.empty else 0
    return {
        "status": "HEALTHY",
        "service": "kestrel-warranty-fraud-detection",
        "version": "1.0.0",
        "dataset_loaded": total_claims > 0,
        "indexed_claims_count": total_claims,
        "model_loaded": claim_service.model_bundle is not None
    }


@app.get("/api/summary")
def get_summary():
    analytics = get_analytics_service()
    return analytics.get_summary()


@app.get("/api/claims", response_model=PaginatedClaimsResponse)
def list_claims(
    search: Optional[str] = Query(None, description="Search claim ID, partner, product, or fault"),
    risk_tier: Optional[str] = Query(None, description="Filter by risk tier: Low, Moderate, High, Critical"),
    product_family: Optional[str] = Query(None, description="Filter by product family"),
    partner_id: Optional[str] = Query(None, description="Filter by partner ID"),
    partner_inspected: Optional[str] = Query(None, description="Filter Y or N"),
    photo_attached: Optional[str] = Query(None, description="Filter Y or N"),
    is_historical: Optional[bool] = Query(None, description="Filter historical vs test claims"),
    sort_by: str = Query("submitted_at", description="Sort column"),
    sort_order: str = Query("desc", description="asc or desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100)
):
    claim_service = get_claim_service()
    claims, total_count = claim_service.get_claims(
        search=search,
        risk_tier=risk_tier,
        product_family=product_family,
        partner_id=partner_id,
        partner_inspected=partner_inspected,
        photo_attached=photo_attached,
        is_historical=is_historical,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size
    )
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
    return {
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "claims": claims
    }


@app.get("/api/claims/{claim_id}")
def get_claim_details(claim_id: str):
    claim_service = get_claim_service()
    claim = claim_service.get_claim_by_id(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found.")
    return claim


@app.post("/api/claims/{claim_id}/adjudicate")
def adjudicate_claim(claim_id: str, payload: dict):
    claim_service = get_claim_service()
    action = payload.get("action", "HOLD")
    reviewer = payload.get("reviewer", "Kabir Nanda (Lead Risk Officer)")
    notes = payload.get("notes", "")
    res = claim_service.adjudicate_claim(claim_id, action, reviewer, notes)
    if not res:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found.")
    return res


@app.post("/api/predict", response_model=ClaimPredictionResponse)
def predict_claim(claim_input: ClaimInput):
    claim_service = get_claim_service()
    fraud_detector = get_fraud_detector()
    result = fraud_detector.evaluate_claim(
        claim=claim_input,
        products_df=claim_service.products_df,
        partners_df=claim_service.partners_df
    )
    return result


@app.get("/api/model-metrics")
def get_model_metrics():
    analytics = get_analytics_service()
    return analytics.get_model_evaluation()


@app.get("/api/analytics")
def get_analytics():
    analytics = get_analytics_service()
    return analytics.get_analytics()


@app.get("/api/partners")
def get_partners_analysis():
    analytics = get_analytics_service()
    return analytics.get_partner_analysis()


@app.get("/api/business-impact")
def get_business_impact(
    monthly_capacity: int = Query(40, ge=5, le=200),
    goodwill_cost: float = Query(380.0, ge=0.0),
    contact_cost: float = Query(260.0, ge=0.0),
    realization_rate: float = Query(1.0, ge=0.1, le=1.0)
):
    analytics = get_analytics_service()
    return analytics.get_business_impact(
        monthly_capacity=monthly_capacity,
        goodwill_cost=goodwill_cost,
        contact_cost=contact_cost,
        realization_rate=realization_rate
    )


# Serve frontend single page app
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    @app.get("/")
    def serve_frontend():
        return FileResponse(static_path / "index.html")
