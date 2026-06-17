# FINTELLIGENCE Schemas

## Canonical Transaction JSON
All parsers normalize their output to match this schema:

```json
{
  "txn_id": "uuid-string",
  "statement_id": "uuid-string",
  "case_id": "uuid-string",
  "date": "YYYY-MM-DD",
  "amount": 50000.00,
  "type": "credit | debit",
  "sender_account": "string",
  "receiver_account": "string",
  "description": "string",
  "balance_after": 12400.00,
  "raw_text": "original unparsed line"
}
```

## Canonical Detector Output JSON
M2, M3, M4 must follow this exact output format for their detectors:

```json
{
  "detector": "DetectorName",
  "triggered": true,
  "score": 85.5,
  "reason": "High frequency of transfers observed during odd hours.",
  "transactions_involved": ["txn_id_1", "txn_id_2"],
  "severity": "high",
  "metadata": {}
}
```

## Flask API Endpoints

### Auth
- `POST /api/auth/register`
- `POST /api/auth/login` -> returns `access_token`
- `GET /api/auth/me` -> requires JWT
- `POST /api/auth/logout` -> requires JWT

### Upload
- `POST /api/upload/` -> requires JWT, accepts `file` and `case_id` via form-data.

### Transactions
- `GET /api/transactions/<statement_id>` -> requires JWT, paginated list.
- `GET /api/transactions/<statement_id>/summary` -> requires JWT.
- `GET /api/transactions/<txn_id>/detail` -> requires JWT.

### Cases
- `GET /api/cases/` -> requires JWT, list user's cases.
- `POST /api/cases/` -> requires JWT, create case.
- `GET /api/cases/<case_id>` -> requires JWT.
- `GET /api/cases/<case_id>/transactions` -> requires JWT.
- `GET /api/cases/<case_id>/beneficiaries` -> requires JWT.
- `PATCH /api/cases/<case_id>/status` -> requires JWT.

### Health Check
- `GET /api/health/`

### Graph & Detectors (M2)
- `POST /api/graph/build/<case_id>` -> requires JWT. Builds and caches the graph.
- `GET /api/graph/<case_id>` -> requires JWT. Returns graph nodes and edges.
- `POST /api/graph/reconstruct-trail` -> requires JWT. Input `case_id`.
- `POST /api/graph/cross-analysis` -> requires JWT. Input `case_id`.
- `POST /api/graph/relationships` -> requires JWT. Input `case_id`.
- `POST /api/detect/circular-flow` -> requires JWT. Input `case_id`.
- `POST /api/detect/layering-chain` -> requires JWT. Input `case_id`.
- `POST /api/detect/layering-severity` -> requires JWT. Input `case_id`, `chain`.

### New M3 Detectors & AI
- `POST /api/detect/large-transaction` -> requires JWT. Input `case_id`.
- `POST /api/detect/dormant-revival` -> requires JWT. Input `case_id`.
- `POST /api/detect/beneficiary-burst` -> requires JWT. Input `case_id`.
- `POST /api/detect/high-risk-time` -> requires JWT. Input `case_id`.
- `POST /api/detect/structuring` -> requires JWT. Input `case_id`.
- `POST /api/detect/evidence-confidence` -> requires JWT. Input `case_id`.
- `POST /api/ai/chat` -> requires JWT. Input `question`, `case_id`, `conversation_history`.
- `POST /api/ai/explain` -> requires JWT. Input `txn_id`, `case_id`.
- `POST /api/ai/legitimate-check` -> requires JWT. Input `txn_id`, `case_id`.
- `POST /api/ai/identify-patterns` -> requires JWT. Input `case_id`.
- `GET /api/ai/case-severity/<case_id>` -> requires JWT.
- `GET /api/intelligence/escalation/<case_id>` -> requires JWT.
- `GET /api/intelligence/submission-recommendation/<case_id>` -> requires JWT.

