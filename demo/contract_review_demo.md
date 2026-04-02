# Contract Review Demo

## Goal

Show RagForge as a contract review assistant for law firms in under 3 minutes.

## Demo Asset

Use this sample file:
- [`demo/sample_vendor_msa.txt`](/Users/dakshyadav/ragforge-v2/demo/sample_vendor_msa.txt)

It is intentionally designed to trigger useful findings:
- no limitation of liability clause
- no indemnity clause
- short termination notice
- weak dispute resolution specificity
- aggressive payment timing
- no late-payment remedy

## Demo Flow

1. Start backend
```bash
./venv/bin/python -m uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000
```

2. Start frontend
```bash
cd rag-ui
npm run dev -- --host 127.0.0.1 --port 5173
```

3. Open the app
- Frontend: `http://127.0.0.1:5173`

4. Upload the sample contract
- Go to Dashboard
- Upload `demo/sample_vendor_msa.txt`

5. Show the contract review story
- Contract Overview
  - document type
  - parties
  - effective date
  - governing law
- Clause Inventory
  - payment
  - termination
  - governing law
- Contract Review Findings
  - missing liability cap
  - missing indemnity
  - short termination notice
  - payment timing may be aggressive
  - dispute resolution forum mechanics could be more specific
- Contract Review Audit
  - show that findings are structured and reviewable

6. Show reviewer workflow
- Accept one finding
- Escalate one finding
- Add a reviewer note
- Filter to `Escalated`

7. Show contract-aware Q&A
Use questions like:
- `What is the governing law?`
- `Is there a termination right?`
- `What does the payment clause require?`

## 3-Minute Script

`RagForge is a contract review assistant built for legal teams.`

`I upload a commercial agreement, and the system first profiles the contract, extracts the key clauses, and builds a clause inventory.`

`Then it generates review findings like missing protections, negotiation points, and clause-specific risks, all tied back to the contract text.`

`Here we can already see there is no limitation of liability clause, no indemnity clause, the termination notice is short, and the payment language is aggressive.`

`A reviewer can accept, dismiss, or escalate findings, and leave notes directly in the workflow.`

`The Q&A layer is contract-aware, so instead of generic chat it answers against the relevant clauses first.`

`The result is a faster first-pass contract review workflow with traceable, reviewable outputs rather than black-box document summaries.`

## Recommended Screenshots

Capture these for README / portfolio / Upwork:
- Dashboard upload screen
- Contract overview
- Clause inventory
- Contract review findings
- Contract review audit
- Q&A answer with citation
