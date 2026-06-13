# Handoff Document (M1)

## What is built and tested
- ✅ Project structure established (`app/`, `models/`, `routes/`, `parsers/`, `normalizer/`).
- ✅ Database Schema (SQLAlchemy models) for all core entities: Users, Cases, Statements, Transactions, Beneficiaries, etc.
- ✅ Canonical schemas for Transactions and Detectors documented in `SCHEMA.md`.
- ✅ PDF Parser scaffolded with `pdfplumber`, `PyMuPDF`, and `camelot-py`.
- ✅ CSV/Excel Parser scaffolded with `pandas` and `openpyxl`.
- ✅ OCR Parser scaffolded with `opencv-python` and `pytesseract`.
- ✅ Normalizer stub ready to take parser outputs and map them to Canonical JSON.
- ✅ API Endpoints built with JWT Auth, Rate Limiting, and basic error handling.
- ✅ Celery Worker configured for background tasks.
- ✅ Environment setup with `requirements.txt` and `.env.example` configured for Neon PostgreSQL and local Redis.

## Known Limitations
- The Parsers currently contain generalized, robust extraction logic but require fine-tuning for specific, highly complex table structures. Bank-specific logic should be extended inside the Normalizer.
- SocketIO is configured for a global `*` origin for development but should be locked down for production.
- Redis connection strings are hardcoded to `localhost` in `.env.example` but can be overridden.

## Sample Test Files Location
Place your test files (PDFs, CSVs, scanned images) in `d:/CIDECODE/fintelligence/uploads/` (or via POST to `/api/upload/`).

## Environment Setup for M2, M3, M4
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`.
3. Set up `.env` using your Neon Postgres connection string.
4. Ensure Redis is running locally.
5. In `celery_worker.py`, fill in the `run_silent_analysis` function to loop through and execute your specific ML/AI detectors.
