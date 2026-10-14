# Kestrel Home — Warranty Claim Review: Submission Form Answers

### 1. Executive Summary & Solution Architecture
**Question: Provide a high-level overview of your solution, methodology, and operational architecture.**
*Response:*
We developed an end-to-end, capacity-constrained warranty fraud triage system for Kestrel Home Appliances. The platform pairs a calibrated Scikit-learn Random Forest classifier with a deterministic policy compliance engine and a lightweight FastAPI/HTML5 enterprise operations portal. Rather than deploying an unconstrained classifier that overwhelms the investigation desk, the system uses an empirically calibrated decision threshold of **0.4615**, aligning referral volume directly with Kestrel's operational limit of **40 claims/month** (§5 of Ops Policy v4.1). Across 15 historical months, this approach prevented ₹4,94,826 in fraudulent payouts and delivered **₹3,16,226 in net financial benefit** (₹527.04 net return per claim checked after accounting for ₹380 goodwill delay penalties and ₹260 contact costs).

---

### 2. Handling Class Imbalance & Metric Selection
**Question: How did you address the extreme class imbalance, and why was accuracy deemed inappropriate as the primary KPI?**
*Response:*
Confirmed fraud represents only **1.23% (145 cases out of 11,814 adjudicated claims)**. A trivial model predicting non-fraud for all claims achieves **98.77% accuracy** while intercepting zero fraud. We addressed imbalance through:
1. **Balanced class weights** in the Random Forest ensemble to penalize false negatives.
2. **Precision-Recall AUC (PR-AUC / Average Precision)** as the primary optimization metric, achieving **0.6137** (a 3.17x improvement over the 0.1937 logistic baseline).
3. **Threshold tuning based on operational capacity** rather than a default 0.50 cutoff, capturing **72.4% recall** among referrals sent to the 40-claims/month desk.

---

### 3. Data Cleansing: Legacy Zoho vs Kestrel CRM Blanks
**Question: How did you reconcile system migration artifacts between legacy Zoho Desk and Kestrel CRM?**
*Response:*
Per Tanmay Kulkarni's IT export notes and Ops Policy §9:
- **Zoho Legacy Records (pre-1 Oct 2025):** Zoho could not store blanks; ongoing or undecided cases migrated as `0`. These rows had closed adjudication outcomes in historical data.
- **Kestrel CRM Records (post-1 Oct 2025):** The CRM stores active, unadjudicated claims as blank (`NaN`).
- **Data Hygiene Action:** We filtered out the 215 blank CRM claims from the training set to prevent label noise and data leakage, training strictly on the 11,814 closed claims. We also verified timestamps, noting that Zoho resolution events were UTC while CRM timestamps are IST.

---

### 4. Preventing Data Leakage & Feature Engineering
**Question: What features were engineered, and how did you prevent target leakage?**
*Response:*
All features use information strictly available at the moment of claim submission:
- **Policy & Gaming Signals:** `is_under_2k` and `uninspected_under_2k` flag exploitation of the May 2026 auto-approval rule.
- **Financial Ratios:** `amount_to_list_ratio` (claimed amount vs catalog list price) and `warranty_consumed_ratio` (days since purchase divided by SKU warranty duration).
- **Partner Risk Smoothing:** Target-encoded partner fraud rates smoothed via Empirical Bayes with global fraud priors, preventing overfitting on small-sample tier-2/3 outlets.
- **Serial Anomalies:** Detected partner transcription anomalies, including leading/trailing whitespace (`serial_has_whitespace`) and irregular character counts (`serial_len`).
- **Strict Leakage Prevention:** Neither future investigation outcomes nor inspector notes were used as inputs for model prediction.

---

### 5. Service Partner Hypothesis Evaluation
**Question: Did the data support the executive hypothesis that newer partners are responsible for warranty fraud?**
*Response:*
The hypothesis is **only partially true and misleading if acted upon broadly**:
- Newer partners (onboarded $\ge$ 2025) exhibited an aggregate fraud rate of **3.28%** compared to **1.02%** for established partners.
- However, **81.5% of newer partners had zero fraudulent claims**.
- Fraud among newer partners is heavily concentrated in 5 specific outlets (`SP3160`, `SP3232`, `SP3318`, `SP3129`, and `SP3319`) gaming the uninspected sub-₹2,000 policy.
- High-value frauds (exceeding ₹10,000) were perpetrated by established partners onboarded before 2025. Blanket sanctions against new partners would harm tier-2/3 market expansion without eliminating fraud.

---

### 6. Root Cause of Post-May Small Claim Surge
**Question: What caused the surge in small warranty claims after 1 May 2026?**
*Response:*
Operations Policy §5 auto-approved claims under ₹2,000 without technician inspection starting 1 May 2026. Unscrupulous partners rapidly discovered this cutoff, resulting in repeated claims clustered between ₹1,800 and ₹1,999 with missing photos, no inspection notes, and fabricated serials.

---

### 7. Financial Model & Goodwill Protection
**Question: How are operational costs and goodwill penalties modeled?**
*Response:*
Per Ops Policy §4 and §5:
$$\text{Net Benefit} = \sum (\text{Prevented Fraud INR}) - (\text{Genuine Held} \times 380) - (\text{Total Reviews} \times 260)$$
- **Goodwill Penalty:** ₹380 for every genuine customer whose claim is delayed.
- **Blended Labor:** ₹260 per desk contact.
- **Desk Capacity:** Fixed at 40 claims/month (120/quarter).
At threshold `0.4615`, the historical net financial benefit was **₹3,16,226** (an average net yield of **₹527.04 per claim investigated**).

---

### 8. Predictions File Validation
**Question: Confirm the specifications and integrity of `predictions.csv`.**
*Response:*
- File path: `predictions.csv` (repository root)
- Row count: Exactly **2,252 rows**, perfectly aligned with `sample_submission.csv`
- Header: `claim_id,score`
- Score distribution: Continuous float probabilities between `0.0000` and `0.9799`, with higher scores reflecting higher fraud risk.
- Verification: Validated by automated tests in `tests/test_predictions_file.py`.

---

### 9. Technology Stack & Enterprise UI
**Question: What technologies were used and how does the UI support enterprise operations?**
*Response:*
- **Backend:** Python 3.14, FastAPI, Pandas, NumPy, Scikit-learn, Joblib.
- **Frontend:** Vanilla HTML5, CSS3, JavaScript, Chart.js.
- **UI Design:** Understated enterprise design system using a light slate/off-white theme, clean typography (Inter and JetBrains Mono), responsive tables, live triage forms, case study presets, partner risk tables, and interactive ROI simulation sliders.
