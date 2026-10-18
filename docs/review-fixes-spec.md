# MediBot – fixes for the review round

Reviewer feedback (5 points) → design decision → how it is verified.

## 1. Provided dataset + Docling/HybridChunker
- `data/raw_documents/` holds the 12 provided documents (11 PDF + 1 Markdown) and `data/mediassist.db` is the
  provided database (sha1 `f10d60e8…`, claims=85, maintenance_tickets=78). The generator script is deleted.
- Parsing: Docling `DocumentConverter` (PDF: layout + TableFormer, OCR off because the PDFs carry a text layer).
- Chunking: Docling `HybridChunker` with the embedding model's own tokenizer (`all-MiniLM-L6-v2`), `max_tokens=256`
  (= the embedder's `max_seq_length`, so no chunk is silently truncated at embed time), `merge_peers=True`.
- The provided PDFs come out of Docling with every heading at level 1. A heading-level pass restores
  document title (1) → numbered section `A.` / `1.` / `SOP 1` (2) → unnumbered sub-heading (3) so that the
  chunk headings read `Equipment … Manual > B. Infusion Pump - DriveFlow IP-200 > Fault codes` instead of only
  `Fault codes` (which appears four times in that manual). Markdown already has real levels and is left as is.
- Embedded text = `HybridChunker.contextualize(chunk)` (heading path + body). Payload carries
  `source_document, collection, access_roles, section_title, chunk_type, text`.
- Verify: parser test on the real `equipment_manual.pdf` (schema, chunk_type set, table chunks, section path,
  token bound); no PyPDF2 import anywhere.

## 2. Hybrid search = one `query_points` call
- Collection: named `dense` (384, cosine) + `sparse` with `Modifier.IDF` (BM25 term weights from fastembed
  `Qdrant/bm25`, IDF computed by Qdrant). `query_embed` is used for the query side.
- One call: `prefetch=[dense(limit 20, RBAC filter), sparse(limit 20, RBAC filter)]`,
  `query=FusionQuery(fusion=RRF)`, `query_filter=RBAC`, `limit=10` → reranker → top 3 to the LLM.
- Ingestion recreates the collection (no duplicate points on re-run; deterministic uuid5 ids).
- Verify: test spies on the client – exactly one `query_points` with two prefetches and RRF; collection config
  has IDF; nurse query for billing terms returns no billing chunk even with the keyword guard bypassed.
  `scripts/eval_retrieval.py` produces the dense-vs-hybrid table in the README from a real run.

## 3. SQL RAG on the real schema, read-only, no canned fallback
- Prompt schema is generated from `mediassist.db` (`PRAGMA table_info` + distinct values for text columns with
  ≤ 15 values + date ranges), so it always matches the file: `claimed_amount`, `approved_amount`, `insurer`,
  `submitted_date`, lowercase `status` (`escalated` is a status, not a column).
- Relative dates ("last month") are anchored to the latest date in the data (2024-12-28): the data ends in
  2024, so the wall clock would make every relative question return 0 rows. `'now'` in generated SQL is
  rewritten to the anchor date, and the answer states the anchor.
- Execution: `file:…?mode=ro` URI connection + SQLite authorizer allowing only SELECT/READ/FUNCTION/RECURSIVE
  (blocks ATTACH, PRAGMA, writes), single statement, 5 s deadline, at most 50 rows passed to the LLM (DB has 85 claims / 78 tickets).
- `call_llm` raises `LLMUnavailableError` when no provider is configured or every provider fails; `/chat`
  returns HTTP 503 with that message. The rule-based canned synthesizer is deleted.
- Verify: tests for prompt contents, write/ATTACH rejection with DB unchanged, `'now'` rewrite, row cap,
  LLM-unavailable path; `scripts/run_sql_examples.py` runs ≥ 4 questions and checks each against a hand-written
  reference query.

## 4. JWT secret + protected `/collections`
- `JWT_SECRET_KEY` is read from `backend/.env` (absolute path, independent of the working directory). The auth
  module refuses to import – so the API refuses to start – when it is missing, shorter than 32 chars, or equal to
  the old hard-coded default. `backend/.env.example` documents it.
- `GET /collections/{role}` requires a bearer token; a user may only read their own role (admin may read any).
  `/chat` takes the role from the token; a `role` field in the body that disagrees is rejected (403).
- Verify: tests for 401/403/200 paths and for start-up refusal in a subprocess.

## 5. README / lockfile
- Screenshots of 3+ adversarial prompts captured from the running app (Playwright, headless Chrome).
- Dense-vs-hybrid table and SQL results pasted from the actual script outputs (also saved under `docs/eval/`).
- Setup uses relative paths. `package-lock.json` regenerated against `https://registry.npmjs.org/` (pinned by
  `frontend/.npmrc`), verified with a clean `npm ci` + `npm run build`.
