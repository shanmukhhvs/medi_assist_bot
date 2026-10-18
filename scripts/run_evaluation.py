"""Real runs for the README: dense-only vs hybrid retrieval, and SQL RAG answers checked against reference SQL.

Usage (from the repo root, after ingestion):  backend/venv/bin/python scripts/run_evaluation.py
Writes docs/eval/retrieval_comparison.md and docs/eval/sql_rag_results.md.
"""
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from app.config import settings  # noqa: E402
from app.RAG.vector_store import QdrantHybridStore  # noqa: E402
from app.RAG.reranker import CrossEncoderReranker  # noqa: E402
from app.RAG.sql_rag import sql_rag_chain_with_details  # noqa: E402

# (role, query, expected source document, text that must appear in the right chunk)
RETRIEVAL_CASES = [
    ("nurse", "What is the correct IV cannula size for a paediatric patient under 5kg?", "icu_nursing_procedures.pdf", "24G"),
    ("technician", "What does fault code F-09 mean on the RadiPro MX-150?", "equipment_manual.pdf", "kV generator fault"),
    ("technician", "DriveFlow IP-200 fault F-03", "equipment_manual.pdf", "Occlusion"),
    ("billing_executive", "Package rate for ICD-10 I21.4", "billing_codes.pdf", "I21.4"),
    ("billing_executive", "J44.1 typical length of stay", "billing_codes.pdf", "J44.1"),
    ("doctor", "CURB-65 score disposition", "treatment_protocols.pdf", "CURB-65"),
    ("doctor", "Ceftriaxone standard dose and tier", "drug_formulary.pdf", "Ceftriaxone"),
    ("doctor", "aPTT critical value heparin", "diagnostic_reference.pdf", "aPTT"),
    ("technician", "Bowie-Dick test frequency SterilPro 3000", "equipment_manual.pdf", "Bowie-Dick"),
    ("nurse", "VIP score cannula change", "icu_nursing_procedures.pdf", "VIP"),
    ("nurse", "Provident Fund PF contribution rate", "general_faqs.pdf", "12%"),
    ("billing_executive", "EXCL-03 exclusion", "billing_codes.pdf", "EXCL-03"),
]

# (question, reference SQL written by hand against the real schema; "last month" = Nov 2024, see sql_rag.py)
SQL_CASES = [
    ("How many billing claims were escalated last month?",
     "SELECT COUNT(*) FROM claims WHERE status='escalated' AND submitted_date >= '2024-11-01' AND submitted_date < '2024-12-01'"),
    ("How many claims are escalated in total?", "SELECT COUNT(*) FROM claims WHERE status='escalated'"),
    ("What is the total approved amount for approved claims?", "SELECT SUM(approved_amount) FROM claims WHERE status='approved'"),
    ("Which insurer has the highest total claimed amount?",
     "SELECT insurer, SUM(claimed_amount) s FROM claims GROUP BY insurer ORDER BY s DESC LIMIT 1"),
    ("Which equipment category has the most open maintenance tickets?",
     "SELECT category, COUNT(*) c FROM maintenance_tickets WHERE status='open' GROUP BY category ORDER BY c DESC LIMIT 1"),
    ("How many maintenance tickets are escalated for the RadiPro MX-150?",
     "SELECT COUNT(*) FROM maintenance_tickets WHERE status='escalated' AND equipment_name='RadiPro MX-150'"),
]


def _hit_rank(results, doc, needle):
    for i, r in enumerate(results, 1):
        if r["source_document"] == doc and needle.lower() in r["text"].lower():
            return i
    return None


def retrieval_comparison(store, reranker):
    rows, totals = [], {"dense": 0, "hybrid": 0, "rerank": 0}
    for role, query, doc, needle in RETRIEVAL_CASES:
        dense = _hit_rank(store.dense_search(query, role, top_k=10), doc, needle)
        candidates = store.hybrid_search(query, role, top_k=10)
        hybrid = _hit_rank(candidates, doc, needle)
        rerank = _hit_rank(reranker.rerank(query, [dict(c) for c in candidates], top_n=3), doc, needle)
        totals["dense"] += bool(dense and dense <= 3)
        totals["hybrid"] += bool(hybrid and hybrid <= 3)
        totals["rerank"] += bool(rerank)
        fmt = lambda r: str(r) if r else "miss"  # noqa: E731
        rows.append(f"| `{query}` | {role} | {fmt(dense)} | {fmt(hybrid)} | {fmt(rerank)} |")
    n = len(RETRIEVAL_CASES)
    return "\n".join([
        "Rank of the first chunk from the expected document that contains the answer (top-10 candidates; "
        "\"miss\" = not retrieved). Same RBAC filter for both.",
        "",
        "| Query | Role | Dense only | Hybrid (dense+BM25, RRF) | Hybrid + rerank (top-3) |",
        "|---|---|---|---|---|",
        *rows,
        f"| **Answer in top-3** | | **{totals['dense']}/{n}** | **{totals['hybrid']}/{n}** | **{totals['rerank']}/{n}** |",
    ])


def _norm(rows):
    return [tuple(round(v, 2) if isinstance(v, float) else v for v in r) for r in rows]


def sql_results():
    conn = sqlite3.connect(f"file:{settings.DB_PATH}?mode=ro", uri=True)
    out, ok = [], 0
    for question, ref_sql in SQL_CASES:
        expected = conn.execute(ref_sql).fetchall()
        res = sql_rag_chain_with_details(question)
        match = _norm(tuple(r.values()) for r in res["db_results"]) == _norm(expected)
        ok += match
        out += [f"### {question}", "", f"- Generated SQL: `{res['executed_sql']}`", f"- Rows: `{res['db_results']}`",
                f"- Reference result: `{expected}` → {'✅ match' if match else '❌ differs'}",
                f"- Answer: {res['answer'].strip()}", ""]
    conn.close()
    return f"{ok}/{len(SQL_CASES)} questions match the hand-written reference SQL.\n\n" + "\n".join(out)


if __name__ == "__main__":
    os.makedirs(os.path.join(ROOT, "docs", "eval"), exist_ok=True)
    store, reranker = QdrantHybridStore(), CrossEncoderReranker()
    table = retrieval_comparison(store, reranker)
    with open(os.path.join(ROOT, "docs", "eval", "retrieval_comparison.md"), "w") as f:
        f.write(table + "\n")
    print(table)
    sql = sql_results()
    with open(os.path.join(ROOT, "docs", "eval", "sql_rag_results.md"), "w") as f:
        f.write(sql)
    print(sql)
