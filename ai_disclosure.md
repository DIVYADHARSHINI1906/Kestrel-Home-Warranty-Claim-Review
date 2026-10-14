# Kestrel Home — Warranty Claim Review: AI Usage & Cost Disclosure

### 1. Architectural & Privacy Compliance (§10 Ops Policy v4.1)
Kestrel Operations Policy v4.1 strictly prohibits uploading operational data, identifiable partner information, or raw claim details to external public AI APIs or third-party web services.
- **Local Execution:** All data engineering, model training, feature extraction, evaluation metrics, and real-time inference run **100% locally** on the local Python runtime using open-source libraries (`scikit-learn`, `pandas`, `numpy`, `fastapi`, `uvicorn`).
- **No External API Dependencies:** The application does **not** make runtime calls to proprietary commercial AI APIs (such as OpenAI, Anthropic, or external cloud endpoints). It requires no paid API keys to execute.

---

### 2. Development Assistant Disclosure
During system engineering and coding:
- **Coding Assistant:** Antigravity AI IDE (Google DeepMind Advanced Agentic Coding environment) powered by Gemini 3.8 Flash.
- **Purpose of AI Assistant:** Pair-programming code generation, drafting unit and integration tests, structuring the enterprise UI design system, and documenting project reports.
- **Data Protection:** No proprietary customer or operational records were shared externally. All dataset processing pipelines operate entirely within local workspace boundaries.

---

### 3. Computational Resources & Operating Costs
- **Model Training Runtime:** ~8.5 seconds on standard CPU hardware (5-fold stratified cross-validation on 11,814 rows).
- **Batch Inference Runtime:** ~0.45 seconds to score and validate all 2,252 rows in `test_unlabelled.csv`.
- **API Latency:** Sub-10ms per individual claim inference via FastAPI (`POST /api/predict`).
- **External API Operating Costs:** **$0.00 / INR 0.00** (Zero external inference expenditure).
- **Memory Footprint:** Under 150 MB total RAM utilization for the running FastAPI server and cached dataset indexes.
