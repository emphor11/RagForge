# RagForge Contract Review

RagForge is being refocused into a legal contract review assistant for law firms and legal ops teams.

Current v1 capabilities:
- clause-aware ingestion for legal-style documents
- contract profiling
  - document type
  - parties
  - effective date
  - governing law
  - term / renewal basics
- clause inventory with stored clause text and previews
- contract review findings
  - missing protections
  - clause-specific risks
  - negotiation points
- legal review audit
- contract-aware Q&A
- reviewer workflow
  - status updates
  - reviewer notes
  - queue filtering

## Backend Routes

Contract-focused routes currently available:
- `POST /upload`
- `GET /documents`
- `GET /insights/{document_id}`
- `GET /contracts/{document_id}/overview`
- `GET /contracts/{document_id}/clauses`
- `GET /contracts/{document_id}/risks`
- `GET /contracts/{document_id}/review-audit`
- `PATCH /contracts/{document_id}/findings/{finding_index}/status`
- `PATCH /contracts/{document_id}/findings/{finding_index}/note`
- `POST /query`

## Frontend

The current UI supports:
- contract overview
- clause inventory
- contract review findings
- legal review audit
- contract-aware Q&A

## Smoke Test

Run the current end-to-end legal smoke test:

```bash
./venv/bin/python scripts/legal_review_smoke_test.py
```

It validates:
- ingestion and chunking
- contract profiling
- clause extraction
- review findings
- legal review audit

## Current Focus

The product is intentionally narrow right now:
- contract review first
- law-firm / legal-ops workflow
- conservative, citation-backed findings

Not in scope yet:
- autonomous legal advice
- redlining automation
- multi-document deal comparison
- broad support for every legal document type
