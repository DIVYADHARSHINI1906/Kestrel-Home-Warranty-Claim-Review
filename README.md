# Kestrel Home — Warranty Claim Review & Fraud Detection System

An enterprise-grade operational decision-support and fraud detection platform engineered for Kestrel Home Appliances (D2C Operations). The system triages incoming warranty claims, validates policy compliance against Kestrel Operations Policy v4.1, flags anomalous partner behaviors, and maximizes fraud loss interception while respecting human desk capacity constraints.

---

## 1. System Overview & Core Capabilities

- **Risk Triage & Prioritization:** Evaluates warranty claims in real time using a calibrated Machine Learning model combined with deterministic policy rules.
- **Capacity-Constrained Optimization:** Tailored specifically to the Claims Investigation Desk capacity limit of **40 claims/month** (§5 of Ops Policy v4.1).
- **Comprehensive Policy Engine:** Enforces inspection thresholds (mandatory inspection for claims $\ge$ ₹2,000, valid serial formats, and purchase tenure).
- **Enterprise Operations Portal:** A clean, responsive internal tool providing interactive claims management, live case triage, partner analytics, model evaluation metrics, and dynamic ROI simulation.
- **Submission Integrity:** Fully verified and calibrated `predictions.csv` matching `sample_submission.csv` specifications (2,252 rows, monotonic risk ranking).

---

## 2. Repository Architecture

```
kestrel-warranty-fraud/
├── app/
│   ├── main.py                  # FastAPI application & REST routing
│   ├── schemas.py               # Pydantic schemas for validation
│   ├── services/
│   │   ├── fraud_detector.py    # Hybrid scoring & policy compliance engine
│   │   ├── claim_service.py     # Claim search, pagination, and lookup service
│   │   └── analytics_service.py # KPI aggregation & simulation controller
│   └── static/
│       ├── index.html           # Enterprise operations web UI
│       ├── css/
│       │   └── style.css        # Enterprise design system (Light palette, typography)
│       └── js/
│           └── app.js           # Frontend state, charts, and API connector
├── src/
│   ├── data_validation.py       # Data cleaning, audit, and schema normalization
│   ├── features.py              # Feature engineering & target smoothing transformers
│   ├── train.py                 # Out-of-fold cross-validation & model training
│   ├── predict.py               # Batch scoring for test_unlabelled.csv
│   ├── evaluate.py              # Performance reporting & threshold sweep analysis
│   └── business_impact.py       # Financial impact and capacity modeling
├── models/
│   └── fraud_pipeline.joblib    # Serialized model bundle & preprocessors
├── reports/
│   ├── evaluation_metrics.json  # Out-of-fold metrics & baseline comparison
│   ├── business_impact.json     # Historical and projected financial outcomes
│   ├── partner_risk_report.json # Partner cohort audit and fraud concentrations
│   └── threshold_analysis.json  # Full threshold sensitivity sweep
├── tests/
│   ├── test_predictions_file.py # Schema & row alignment verification
│   ├── test_model_pipeline.py   # Transformer edge cases & unknown categories
│   ├── test_api_endpoints.py    # FastAPI endpoint integration tests
│   └── test_business_impact.py  # Financial math and capacity verification
├── predictions.csv              # Official unlabelled predictions submission
├── memo.md                      # Executive Business Memo to Ritu Deshpande
├── submission_form_draft.md     # Comprehensive answers for submission questions
├── screen_recording_script.md   # 3-minute timed screen recording guide
├── ai_disclosure.md             # Transparent AI disclosure and costs
├── requirements.txt             # Python dependencies
├── .gitignore                   # Standard production gitignore
└── README.md                    # System documentation
```

---

## 3. Key Domain & Data Findings

1. **The Sub-₹2,000 Policy Exploitation:**
   - From 1 May 2026, claims under ₹2,000 were auto-approved without technician inspection to cut turnaround times (§5).
   - Analysis revealed an immediate surge in repetitive small claims (e.g., ₹1,980, ₹1,950) without photos or inspection notes from specific service partners.
2. **System Migration & Legacy Encoding (Zoho vs CRM):**
   - Prior to 1 Oct 2025, operations ran on legacy Zoho Desk, which could not store blank statuses, encoding unresolved cases as `0`.
   - Post-migration Kestrel CRM cases store active investigations as blanks (`NaN`).
   - The training pipeline isolates genuine closed investigations (11,814 rows) while preventing data leakage from unresolved CRM cases (215 rows).
3. **Partner Network Hypothesis:**
   - While newer tier-2/3 partners onboarded in 2025-2026 show a higher aggregate fraud rate (3.28% vs 1.02%), **81.5% of new partners have zero recorded fraud**.
   - Fraud is concentrated in a tight cluster of repeated offenders rather than the entire cohort.
4. **Serial Number Formatting Anomalies:**
   - Serials are entered manually by partners, leading to leading/trailing whitespace and length discrepancies (e.g., 9-14 characters instead of the standard 11). Whitespace presence strongly correlates with fraudulent submissions ($p < 0.001$).

---

## 4. Machine Learning & Threshold Calibration

### Model Architecture & Baseline Comparison
Due to severe class imbalance (1.23% fraud prevalence), standard accuracy is misleading (a naive zero-classifier scores 98.77% accuracy while intercepting zero fraud). Models were evaluated using 5-Fold Stratified Cross-Validation on Precision-Recall AUC (PR-AUC) and ROC-AUC.

| Metric | Baseline (Logistic Regression) | Production (Balanced Random Forest) | Lift / Advantage |
| :--- | :--- | :--- | :--- |
| **ROC-AUC** | 0.8528 | **0.8763** | +0.0235 |
| **PR-AUC (Avg Precision)** | 0.1937 | **0.6137** | **+216.8% (3.17x)** |
| **Recall @ 40/month Capacity** | 34.5% | **72.4%** | **+37.9 percentage points** |
| **Precision @ 40/month Capacity**| 8.3% | **22.8%** | **+14.5 percentage points** |
| **Historical Net Savings** | ₹1,02,226 | **₹3,16,226** | **+₹2,14,000 net profit** |

### Capacity-Calibrated Operating Threshold
Because the investigation desk can handle at most 40 reviews per month (120 per quarter), setting a default 0.50 threshold would overwhelm the team or cause massive queue backlogs.
- **Selected Threshold:** `0.4615`
- Matches exactly the top 40 riskiest claims per month.
- Strikes an optimal balance between intercepted fraud and goodwill preservation.

---

## 5. Financial & Operational Math

The financial decision model strictly enforces parameters from Kestrel Operations Policy v4.1:
- **Goodwill Penalty:** Holding a genuine customer claim for review incurs **₹380** on average in goodwill costs (§4).
- **Blended Service Contact Cost:** **₹260** per claim investigated (§4).
- **Prevented Fraud Value:** Payout avoided (full claim amount in INR).

$$\text{Net Benefit} = \sum (\text{Prevented Fraud Claims}) - (\text{Genuine Claims Held} \times 380) - (\text{Total Investigated} \times 260)$$

**Historical 15-Month Performance (600 desk reviews conducted):**
- Total Fraud Intercepted: **₹4,94,826**
- Goodwill Penalty Incurred: **-₹49,400** (130 genuine claims reviewed)
- Investigation Labor: **-₹1,56,000** (600 reviews $\times$ ₹260)
- **Net Financial Benefit:** **₹3,16,226** (Net return of **₹527.04 per claim checked**)

---

## 6. Quick Start & Execution Guide

### Prerequisites
- Python 3.10+ (Tested on Python 3.14)
- Pip package manager

### 1. Installation
Clone the repository and install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Train Model & Calibrate Pipeline
Trains the Random Forest model and saves artifacts to `models/fraud_pipeline.joblib`:
```bash
python -m src.train
```

### 3. Generate Validated Predictions
Scores `test_unlabelled.csv` and outputs `predictions.csv`:
```bash
python -m src.predict
```

### 4. Generate Reports & Financial Audits
```bash
python -m src.evaluate
python -m src.business_impact
```

### 5. Run Automated Test Suite
Executes all 17 integration and unit tests:
```bash
python -m pytest tests/ -v
```

### 6. Launch Enterprise Web Application
Start the FastAPI server:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Open your browser at **`http://127.0.0.1:8000`** to access the operations dashboard.

---

## 7. REST API Documentation

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/health` | `GET` | Health check, service status, indexed claim count |
| `/api/summary` | `GET` | High-level KPIs, historical stats, queue size |
| `/api/claims` | `GET` | Paginated claims list with search, sorting, and filters |
| `/api/claims/{claim_id}` | `GET` | Detailed telemetry, partner data, and risk tier for a claim |
| `/api/predict` | `POST` | Live fraud risk scoring, policy check, and recommendation |
| `/api/model-metrics` | `GET` | Out-of-fold metrics, threshold sweep, and feature importances |
| `/api/analytics` | `GET` | Volume trends, product breakdown, and risk distribution |
| `/api/partners` | `GET` | Partner cohort hypothesis test and high-risk partner roster |
| `/api/business-impact` | `GET` | Dynamic ROI simulation supporting custom capacity & cost inputs |

---

## 8. Verification & Test Coverage

All automated test modules verify system integrity:
1. `tests/test_predictions_file.py`: Verifies row count (2,252), claim ID ordering, absence of NaNs, and score distribution.
2. `tests/test_model_pipeline.py`: Tests handling of unknown categories, missing values, extreme serial anomalies, and policy rules.
3. `tests/test_api_endpoints.py`: Tests all FastAPI endpoints, 404 responses, and schema validations.
4. `tests/test_business_impact.py`: Verifies financial calculations and capacity constraints.

---

## 9. Operational Recommendations

1. **Close the Sub-₹2,000 Loophole:** Amend Ops Policy §5 to require photo evidence and serial verification even for claims under ₹2,000 if the partner's rolling 30-day volume exceeds 10 claims.
2. **Targeted Audits, Not Blanket Sanctions:** Avoid penalizing all tier-2/3 partners; focus inspections on the 5 identified repeat-offender outlets.
3. **Serial Input Normalization:** Implement frontend format masking in the partner portal to eliminate whitespace and format variances before submission.
