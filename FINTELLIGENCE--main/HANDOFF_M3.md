# Handoff Document (M3)

## What is built and tested
- ✅ New dependencies integrated: `groq`, `spacy`, `sentence-transformers`, `scikit-learn`, `scipy`, `huggingface-hub`, `pandas`, `numpy`.
- ✅ Groq AI integration with a robust fallback mock system (`app/ai/groq_client.py`) that returns static string/JSON for UI testing until `GROQ_API_KEY` is provided.
- ✅ SpaCy NLP model downloaded and `en_core_web_sm` integrated for Name/Account Extraction in the Chat Investigator.
- ✅ **New Detectors:**
  - `LargeTransaction`: Detects > 3x historical 90-day rolling average using pandas and scipy z-score.
  - `DormantRevival`: Detects > 180 day gaps with sudden high-volume transactions using IsolationForest.
  - `BeneficiaryBurst`: Detects 5+ new beneficiaries in any 24-hour rolling window.
  - `HighRiskTime`: Flags transactions happening between 1:00 AM - 5:00 AM or on public holidays.
  - `Structuring`: Detects rapid sub-threshold deposits near the ₹50,000 mark and calculates description similarity.
  - `EvidenceConfidence`: Weighted engine to produce an aggregate confidence score for the entire case.
- ✅ **AI Intelligence Modules:**
  - `ChatInvestigator`: Handles natural language queries over the statement data using spaCy NER and Groq.
  - `Explainer`: Generates natural language summaries for why specific transactions are flagged.
  - `LegitimateExplainer`: Analyzes flagged transactions for potentially innocent, legitimate explanations.
  - `PatternLibrary`: Re-evaluates triggered detectors and maps them into canonical Indian AML patterns (e.g., Structuring, Layering).
  - `CaseSeverity`: Evaluates overall case context and generates an executive severity score.
- ✅ **Intelligence & Escalation:**
  - `Escalation`: Recommends investigation statuses (MONITOR, SUPERVISOR_REVIEW, etc.)
  - `Submission`: Drafts an FIU/EOW reporting form and recommendation using Groq.
- ✅ All endpoints documented in `SCHEMA.md` and mounted on `app.py`.

## Known Limitations
- AI features currently rely on the mock fallback until `GROQ_API_KEY` is added to `.env`.
- Certain dates for holidays in `HighRiskTime` are static placeholders for testing and should be dynamically sourced for production.
- `SentenceTransformer` model inside `Structuring` will be downloaded lazily the first time that detector is triggered (taking ~50-100MB RAM and bandwidth).

## Environment Setup for M4
1. If you haven't yet, run `python -m spacy download en_core_web_sm`.
2. Add your `GROQ_API_KEY` to the `.env` file to replace the mock AI responses.
3. Wire the new `api/ai/*` and `api/intelligence/*` endpoints into the React UI.
