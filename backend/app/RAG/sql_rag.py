import re
import sqlite3
import time
from functools import lru_cache
from typing import Any, Dict, List, Tuple

from app.config import settings
from app.RAG.llm import call_llm

# Rows passed back to the LLM for the natural-language answer. The provided DB has 85 claims and 78 tickets,
# so a full-table SELECT is truncated; aggregates (the normal case) are 1-20 rows.
MAX_RESULT_ROWS = 50
QUERY_TIMEOUT_SECONDS = 5.0
# Text columns with at most this many distinct values have the values listed in the prompt (status, insurer, ...).
MAX_ENUM_VALUES = 15
DATE_COLUMN_SUFFIX = "_date"


class SQLExecutionError(Exception):
    pass


def _connect_read_only() -> sqlite3.Connection:
    """Read-only at the SQLite level (mode=ro): writes fail even if the authorizer below were bypassed."""
    return sqlite3.connect(f"file:{settings.DB_PATH}?mode=ro", uri=True, check_same_thread=False)


# Only reading actions are allowed; everything else (writes, ATTACH, PRAGMA, temp tables) is denied.
_ALLOWED_ACTIONS = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}


def _authorizer(action, arg1, arg2, db_name, trigger):
    return sqlite3.SQLITE_OK if action in _ALLOWED_ACTIONS else sqlite3.SQLITE_DENY


@lru_cache(maxsize=1)
def _introspect() -> Dict[str, Any]:
    """Read the real schema, low-cardinality values and date range straight from mediassist.db."""
    conn = _connect_read_only()
    try:
        tables = {}
        max_dates = []
        for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            columns = []
            for _, name, col_type, _, _, pk in conn.execute(f'PRAGMA table_info("{table}")'):
                info = {"name": name, "type": col_type, "pk": bool(pk), "values": None, "range": None}
                if col_type.upper() == "TEXT" and not pk:
                    distinct = [r[0] for r in conn.execute(
                        f'SELECT DISTINCT "{name}" FROM "{table}" WHERE "{name}" IS NOT NULL '
                        f'ORDER BY 1 LIMIT {MAX_ENUM_VALUES + 1}')]
                    if name.endswith(DATE_COLUMN_SUFFIX):
                        lo, hi = conn.execute(f'SELECT MIN("{name}"), MAX("{name}") FROM "{table}"').fetchone()
                        info["range"] = (lo, hi)
                        if hi:
                            max_dates.append(hi)
                    elif len(distinct) <= MAX_ENUM_VALUES:
                        info["values"] = distinct
                columns.append(info)
            row_count = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            tables[table] = {"columns": columns, "row_count": row_count}
        return {"tables": tables, "anchor_date": max(max_dates) if max_dates else None}
    finally:
        conn.close()


def dataset_anchor_date() -> str:
    """Latest date present in the data. Relative dates ("last month") are resolved against it, because the
    provided dataset ends in Dec 2024 and the wall clock would make every relative question return 0 rows."""
    return _introspect()["anchor_date"]


def build_schema_prompt() -> str:
    meta = _introspect()
    lines = [
        "You are a SQLite expert for MediAssist Health Network.",
        "Translate the question into ONE valid SQLite SELECT statement for the schema below.",
        "",
        "Database schema (read from mediassist.db):",
    ]
    for table, t in meta["tables"].items():
        lines.append(f"Table `{table}` ({t['row_count']} rows):")
        for c in t["columns"]:
            desc = f"  - `{c['name']}` {c['type']}"
            if c["pk"]:
                desc += " PRIMARY KEY"
            if c["values"] is not None:
                desc += " -- values: " + ", ".join(f"'{v}'" for v in c["values"])
            if c["range"]:
                desc += f" -- 'YYYY-MM-DD' text, from {c['range'][0]} to {c['range'][1]}, NULL if not set"
            lines.append(desc)
    lines += [
        "",
        "Rules:",
        "- Output ONLY the SQL statement. No markdown fences, no explanation.",
        "- Use only SELECT (or WITH ... SELECT). Never modify data.",
        "- Text comparisons are case-sensitive: use the listed values exactly. `status`, `department`, `category`,",
        "  `claim_type` and `issue_type` are lowercase (snake_case, e.g. 'general_medicine', 'in_progress').",
        "- 'escalated' is a value of `status` in both tables, not a separate column.",
        "- claims: `claimed_amount` is what was billed; `approved_amount` is NULL unless status = 'approved'.",
        f"- Today's date for this dataset is '{meta['anchor_date']}'. Use date('{meta['anchor_date']}') instead of "
        "date('now'). 'Last month' means the previous calendar month relative to that date.",
        "- Give aggregate columns readable aliases.",
    ]
    return "\n".join(lines)


def extract_clean_sql(raw_output: str) -> str:
    """
    Step 2: Clean the raw LLM output to extract only the SQL statement.
    Removes markdown code fences and any preamble before the first SELECT/WITH.
    """
    cleaned = re.sub(r"```(?:sqlite|sql)?", "", raw_output, flags=re.IGNORECASE).strip()
    match = re.search(r"\b(SELECT|WITH)\b.*", cleaned, re.IGNORECASE | re.DOTALL)
    if not match:
        return cleaned
    sql = match.group(0).strip()
    # Keep only the first statement; anything after the first ';' is dropped here and re-checked at execution.
    if ";" in sql:
        sql = sql[: sql.index(";")].strip()
    return sql + ";"


def anchor_relative_dates(sql: str) -> str:
    """Replace SQLite's 'now' with the dataset anchor date (see dataset_anchor_date)."""
    return re.sub(r"'now'", f"'{dataset_anchor_date()}'", sql, flags=re.IGNORECASE)


def execute_read_only(sql: str) -> Tuple[List[str], List[tuple], bool]:
    """Execute one SELECT on a read-only connection. Returns (columns, rows[:MAX_RESULT_ROWS], truncated)."""
    if not sqlite3.complete_statement(sql) or sql.strip().rstrip(";").count(";"):
        raise SQLExecutionError("Only a single SQL statement is allowed.")
    if not re.match(r"^\s*(SELECT|WITH)\b", sql, re.IGNORECASE):
        raise SQLExecutionError("Only SELECT queries are allowed.")

    conn = _connect_read_only()
    deadline = time.monotonic() + QUERY_TIMEOUT_SECONDS
    conn.set_authorizer(_authorizer)
    # Abort runaway queries (e.g. accidental cross joins) once the deadline passes.
    conn.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 10_000)
    try:
        cursor = conn.execute(sql)
        columns = [d[0] for d in cursor.description] if cursor.description else []
        rows = cursor.fetchmany(MAX_RESULT_ROWS + 1)
        return columns, rows[:MAX_RESULT_ROWS], len(rows) > MAX_RESULT_ROWS
    except sqlite3.Error as e:
        raise SQLExecutionError(str(e)) from e
    finally:
        conn.close()


def sql_rag_chain_with_details(question: str) -> Dict[str, Any]:
    """
    Step 1: Translate the NL question into SQL using the LLM (prompt built from the real schema).
    Step 2: Clean the raw LLM output to extract only the SQL statement.
    Step 3: Execute it read-only against mediassist.db and pass the rows back to the LLM for the answer.
    Raises LLMUnavailableError if the LLM cannot be reached.
    """
    prompt = f"{build_schema_prompt()}\n\nQuestion: {question}\nSQL:"
    raw_sql_response = call_llm(prompt=prompt)

    clean_sql = anchor_relative_dates(extract_clean_sql(raw_sql_response))
    print(f"\n[SQL RAG Step 1 & 2] Question: '{question}' -> Cleaned SQL: '{clean_sql}'")

    try:
        columns, rows, truncated = execute_read_only(clean_sql)
    except SQLExecutionError as e:
        print(f"[SQL RAG Execution Error]: {e}")
        return {
            "answer": f"I could not answer this from the database: the generated SQL failed ({e}). "
                      "Please rephrase the question.",
            "executed_sql": clean_sql,
            "db_results": [],
            "retrieval_type": "sql_rag",
        }

    db_results = [dict(zip(columns, row)) for row in rows]
    truncation_note = f" (first {MAX_RESULT_ROWS} rows only)" if truncated else ""
    synthesis_prompt = (
        "Answer the question using only the SQL results below from the MediAssist Health Network database. "
        "Give exact numbers; amounts are in INR. A count of 0 is an answer (say '0'); only say no records were found "
        "when the result list itself is empty. State the period used when the question is relative (e.g. last month).\n\n"
        f"Question: {question}\n"
        f"Reference date for relative periods: {dataset_anchor_date()}\n"
        f"Executed SQL: {clean_sql}\n"
        f"Results{truncation_note}: {db_results}\n"
    )
    answer = call_llm(prompt=synthesis_prompt, system_instruction="You are a healthcare analytics assistant.")

    return {
        "answer": answer,
        "executed_sql": clean_sql,
        "db_results": db_results,
        "retrieval_type": "sql_rag",
    }


def sql_rag_chain(question: str) -> str:
    """Plain-function SQL RAG chain: question in, natural-language answer out."""
    return sql_rag_chain_with_details(question)["answer"]
