# Kestrel Home — Warranty Claim Review: Screen Recording Script

**Target Duration:** Exactly 3 Minutes (180 Seconds)  
**Presenter:** Kabir Nanda / Lead Risk Analytics Engineer  
**Audience:** Executive Review Panel & D2C Operations Leadership  

---

### [0:00 – 0:30] Introduction & Operations Overview
* **Screen View:** `http://localhost:8000` (Overview Tab)
* **Visual Actions:**
  1. Mouse hovers over the KPI cards: Total Historical Claims (12,029), Queue Size (2,252), Historical Fraud Rate (1.23%), and Recall at Capacity (72.4%).
  2. Scroll down to showcase the interactive charts: Monthly Claim Volume stacked bar (highlighting the orange surge of uninspected claims post-May), Product Family Breakdown, and Risk Score Distribution.
  3. Briefly point to the "High-Priority Queue" table at the bottom.
* **Voiceover Script:**
  > *"Hello everyone. Today I'm presenting the Kestrel Home Warranty Fraud Detection & Triage System. As requested by operations leadership and the board, we've built a production-ready internal tool tailored specifically to Kestrel Operations Policy v4.1. Here on the Overview dashboard, we display live operational telemetry: our 15-month historical baseline of 12,029 claims, our active queue of 2,252 incoming unlabelled claims, and our calibrated model recall of 72.4%. Crucially, our volume trend chart visibly illustrates the post-May explosion of uninspected sub-₹2,000 claims that prompted this investigation."*

---

### [0:30 – 1:05] Claims Register & Real-Time Filtering
* **Screen View:** Switch to the **Claims Register** Tab
* **Visual Actions:**
  1. Click the "Claims Register" button in the sidebar. Show the high-density table loading test claims.
  2. Type `WC711348` into the instant search bar. Watch the table filter instantly.
  3. Clear search. Change Risk Tier filter to "Critical", then change Product Family filter to "Water Purifiers".
  4. Click on row `WC711412` to trigger the smooth slide-out **Claim Details Drawer**.
  5. Show the complete claim telemetry: purchase tenure, serial number, partner details, and risk rating.
* **Voiceover Script:**
  > *"Moving to the Claims Register, operations staff have immediate access to all 2,252 incoming claims with instant fuzzy search, multi-factor filtering, and responsive sorting. Clicking any claim row opens a comprehensive telemetry drawer. Here, technicians can review every piece of evidence—including product serial numbers, partner tenure, and originating CRM sources—with zero lag. From this drawer, reviewers can seamlessly push any claim directly into our triage engine."*

---

### [1:05 – 1:45] Live Triage Engine & Case Studies
* **Screen View:** Switch to the **Claim Review & Triage** Tab
* **Visual Actions:**
  1. Click the case study preset: **'Post-May Small Claim Fraud' (Claim WC711412)**.
  2. Note how all form inputs auto-populate: ₹1,980 amount, missing inspection, missing photo, whitespace in serial (` KH762701250`).
  3. Click **"Run Fraud Scoring & Policy Check"**.
  4. Highlight the output: 96.6% Fraud Risk Score, Critical Tier badge, Red Recommendation Banner ("Desk Review & Physical Verification Required"), and Warranty Policy §5 compliance check failure.
  5. Next, click preset **'Clean Genuine Claim' (WC711350)** and click evaluate. Show the green 1.3% risk score and "Auto-Approve for Payment" recommendation.
* **Voiceover Script:**
  > *"In the Claim Review tab, operations officers can triage custom claims or select preloaded case studies. Let's load the 'Post-May Small Claim' preset. Notice the hallmarks: ₹1,980 claimed amount, uninspected, no photo, and serial formatting whitespace. When we run the evaluation, our decision engine outputs a 96.6% risk probability, flags §5 auto-approval gaming, and issues an immediate hold for desk review. In contrast, evaluating a genuine claim like WC711350 returns a 1.3% risk score and safely recommends instant approval, ensuring genuine customer repairs are never delayed."*

---

### [1:45 – 2:15] Partner Analysis & Hypothesis Audit
* **Screen View:** Switch to the **Partner Analysis** Tab
* **Visual Actions:**
  1. Scroll down through the Executive Inquiry card comparing Ritu's hypothesis with Meenal's service desk observations.
  2. Highlight the Cohort Table: Newer Partners (3.28% fraud) vs Established Partners (1.02% fraud).
  3. Cursor highlights the key insight: **81.5% of new tier-2/3 partners have zero fraud**.
  4. Point to the Top Repeat Offender table below showing specific outlets (`SP3160`, `SP3232`).
* **Voiceover Script:**
  > *"In the Partner Analysis tab, we tested the hypothesis that newer partners drive warranty fraud. The data reveals a nuanced truth: while newer partners show a higher overall fraud rate of 3.28%, over 81% of new partners have never submitted a single fraudulent claim. The problem is not tier-2 expansion—it is a concentrated ring of 5 specific partner outlets exploiting the sub-₹2,000 loophole. Blanket onboarding freezes would harm Kestrel's growth; instead, our system enables surgical, outlet-specific audits."*

---

### [2:15 – 2:40] Model Evaluation & Threshold Calibration
* **Screen View:** Switch to the **Model Evaluation** Tab
* **Visual Actions:**
  1. Highlight the "Accuracy Trap" callout explaining why 98.77% raw accuracy is trivial on imbalanced data.
  2. Point out the balanced Random Forest metrics: ROC-AUC of 0.8763 and PR-AUC of 0.6137 (a 3.17x lift over the logistic baseline).
  3. Scroll down to the Threshold Sensitivity Table and highlight the calibrated operating threshold of **0.4615**.
* **Voiceover Script:**
  > *"Under Model Evaluation, we directly address the board's 97% accuracy request. With a 1.2% fraud prevalence, an empty model predicting zero achieves 98.7% accuracy while stopping no fraud. Instead, our Random Forest achieves a 0.6137 PR-AUC. Most importantly, we calibrated the operating threshold to 0.4615, precisely matching the Investigation Desk's capacity limit of 40 claims per month."*

---

### [2:40 – 3:00] Operations Settings, ROI Simulator & Conclusion
* **Screen View:** Switch to the **Operations & Capacity** Tab
* **Visual Actions:**
  1. Adjust the monthly capacity slider from 40 to 50 claims, or tweak the Goodwill Penalty cost.
  2. Click **"Recalculate Net Impact"**.
  3. Highlight the live KPI cards: ₹4,94,000+ fraud prevented, ₹3,16,226 historical net benefit, and ₹527 net return per claim checked.
  4. Conclude on the clean interface.
* **Voiceover Script:**
  > *"Finally, the Operations & Capacity tab contains our interactive ROI simulator. By embedding Ops Policy §4 costs—₹380 goodwill penalty for delayed genuine claims and ₹260 contact labor—Farhan's team can simulate staffing changes in real time. Over 15 months, our system generated ₹3,16,226 in net financial benefit, returning ₹527 in net savings for every claim reviewed. The application is completely tested, documented, and ready for production deployment. Thank you."*
