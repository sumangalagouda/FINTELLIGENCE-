# FINTELLIGENCE Backend

This is the foundational backend for FINTELLIGENCE, an AI-powered forensic bank statement analysis platform.

## Setup Instructions

### 1. PostgreSQL (Neon Database)
We use a shared Neon PostgreSQL database. 
You must replace the placeholder in `.env` with your actual Neon connection string.
```env
DATABASE_URL=postgresql://<NEON_USERNAME>:<NEON_PASSWORD>@<NEON_HOST>/<DATABASE_NAME>?sslmode=require
```

### 2. Redis Setup Locally
Redis is required for Celery and Rate Limiting.
- On Ubuntu/Debian: `sudo apt install redis-server`
- On Mac (Homebrew): `brew install redis`
- On Windows: Use WSL2 or Docker (`docker run -p 6379:6379 -d redis`)
Ensure it runs on `localhost:6379`.

### 3. Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Update all required secrets.

### 4. Database Migrations
Initialize and upgrade your database schema:
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 5. Running the Flask Server
```bash
python run.py
```
Server runs on `http://localhost:5000`.

### 6. Running the Celery Worker
In a separate terminal, start the Celery worker:
```bash
celery -A celery_worker.celery worker --loglevel=info
```

## Documentation
- See `SCHEMA.md` for JSON structures and API endpoints.

## Adding a New Bank PDF Format
1. Open `app/parsers/pdf_parser.py`.
2. Update the `detect_bank` function to include new header keywords.
3. If the standard extraction fails, add specific table extraction rules in `parse_pdf` using `pdfplumber` or `camelot`.
4. Update `app/normalizer/normalizer.py` if the new bank introduces new column variations not currently handled.
