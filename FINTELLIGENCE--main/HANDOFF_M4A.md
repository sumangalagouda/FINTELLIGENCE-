# Handoff Document (M4 - Part A Backend)

## What is built and tested
- ✅ Added ReportLab, WeasyPrint, Jinja2, python-docx, and openpyxl dependencies.
- ✅ Transaction Velocity Detector (M4) implemented and integrated.
- ✅ Pass-Through Ratio Engine (M4) implemented and integrated.
- ✅ Cash Cycling Detector (M4) implemented and integrated.
- ✅ Silent Intelligence Engine implemented in `app/intelligence/silent_engine.py` and hooked into the M1 upload endpoint to run all M2, M3, and M4 detectors.
- ✅ Suspicion Score Aggregator implemented combining all triggered detectors to calculate risk scores and risk levels.
- ✅ Governance models (`InvestigatorNote`, `EvidenceItem`) created, alongside reusing existing `Verification`, `AuditTrail`, and `SupervisorApproval` models.
- ✅ Human Verification Center endpoints implemented.
- ✅ Supervisor Approval Gate implemented.
- ✅ Audit Trail Engine integrated across endpoints.
- ✅ AI-Human Mismatch Detector built.
- ✅ Investigator Notes System and Evidence Locker CRUD built.
- ✅ FIR Readiness Assessment Engine implemented to calculate evidence, verification, and approval metrics.
- ✅ Reports Generation: Auto Investigation Report (PDF), Authority-Specific Dossier (DOCX/XLSX), and FIR Draft Generator (via Groq AI).
- ✅ Investigator Accountability Dashboard endpoint provided.

## New Endpoints for M4-Part B (Frontend)

### Intelligence & Score
- `POST /api/intelligence/run-silent`
- `GET /api/intelligence/suspicion-score/<case_id>`
- `GET /api/intelligence/fir-readiness/<case_id>`

### Governance & Verification
- `GET /api/governance/verification/<case_id>`
- `POST /api/governance/verification/<case_id>`
- `GET /api/governance/fir-gate/<case_id>`
- `POST /api/governance/supervisor-approve/<case_id>` (Supervisor only)
- `GET /api/governance/audit/<case_id>`
- `POST /api/governance/check-mismatch/<case_id>`
- `GET /api/governance/notes/<case_id>`
- `POST /api/governance/notes/<case_id>`
- `GET /api/governance/accountability-dashboard` (Supervisor only)
- `GET /api/governance/investigator-risk/<user_id>`

### Evidence Locker
- `GET /api/evidence/<case_id>`
- `POST /api/evidence/<case_id>/upload`
- `DELETE /api/evidence/<item_id>`

### Reports
- `GET /api/reports/generate/<case_id>` -> Downloads PDF
- `GET /api/reports/dossier/<case_id>?authority=<type>` -> Downloads DOCX or XLSX
- `POST /api/reports/fir-draft/<case_id>` -> Requires FIR gate open

## Known Limitations
- Background task processing for silent analysis is currently running synchronously. For production, Celery should be enabled.
- Holding duration logic for pass-through is a generic estimate based on first and last transaction.
- Generated PDF and DOCX reports use placeholder outputs for AI summaries if Groq is unavailable.

## What M4-Part B Needs to Wire Up
- Call `GET /api/intelligence/suspicion-score/<case_id>` to render the risk score dashboard.
- Create UI for the Investigator Notes and Evidence Locker.
- Build the Verification Checklist UI that posts to `POST /api/governance/verification/<case_id>`.
- Build the FIR Generation and Supervisor Review views.
- Handle file downloads correctly for the report endpoints.
