import hashlib
import shutil
import sqlite3

import pytest

from app.config import settings
from app.RAG import sql_rag
from app.RAG.llm import LLMUnavailableError


def _sha1(path):
    with open(path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()


def test_uses_provided_database():
    assert _sha1(settings.DB_PATH) == "f10d60e8ca5f5c9a92bf766c56af127ab53e5a41"


def test_schema_prompt_is_built_from_real_db():
    prompt = sql_rag.build_schema_prompt()
    for expected in ["claimed_amount", "approved_amount", "insurer", "submitted_date",
                     "raised_date", "'escalated'", "'approved'", "'in_progress'", "2024-12-28"]:
        assert expected in prompt, expected
    for stale in ["claim_amount REAL", "insurance_provider", "claim_date", "'Approved'", "escalated BOOLEAN"]:
        assert stale not in prompt, stale


@pytest.mark.parametrize("raw, expected", [
    ("```sql\nSELECT COUNT(*) FROM claims;\n```", "SELECT COUNT(*) FROM claims;"),
    ("Here is the query:\nSELECT 1", "SELECT 1;"),
    ("WITH x AS (SELECT 1) SELECT * FROM x;", "WITH x AS (SELECT 1) SELECT * FROM x;"),
])
def test_extract_clean_sql(raw, expected):
    assert sql_rag.extract_clean_sql(raw) == expected


def test_now_is_anchored_to_dataset_date():
    out = sql_rag.anchor_relative_dates("SELECT * FROM claims WHERE submitted_date >= date('now','-1 month')")
    assert "'now'" not in out
    assert "'2024-12-28'" in out


@pytest.fixture
def db_copy(tmp_path, monkeypatch):
    path = tmp_path / "mediassist.db"
    shutil.copy(settings.DB_PATH, path)
    monkeypatch.setattr(settings, "DB_PATH", str(path))
    return path


@pytest.mark.parametrize("sql", [
    "DELETE FROM claims;",
    "UPDATE claims SET status = 'approved';",
    "DROP TABLE claims;",
    "INSERT INTO claims (claim_id) VALUES ('x');",
    "ATTACH DATABASE '/tmp/evil.db' AS evil;",
    "PRAGMA writable_schema = 1;",
    "SELECT 1; DELETE FROM claims;",
])
def test_execute_rejects_anything_but_one_select(db_copy, sql):
    before = _sha1(db_copy)
    with pytest.raises(sql_rag.SQLExecutionError):
        sql_rag.execute_read_only(sql)
    assert _sha1(db_copy) == before


def test_execute_returns_rows_and_caps_them(db_copy):
    columns, rows, truncated = sql_rag.execute_read_only("SELECT claim_id FROM claims;")
    assert columns == ["claim_id"]
    assert len(rows) == sql_rag.MAX_RESULT_ROWS
    assert truncated is True


def test_execute_connection_is_read_only_even_without_authorizer(db_copy):
    conn = sql_rag._connect_read_only()
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("DELETE FROM claims")
    conn.close()


def test_chain_end_to_end_with_stubbed_llm(db_copy, monkeypatch):
    calls = []

    def fake_llm(prompt, system_instruction=""):
        calls.append(prompt)
        if len(calls) == 1:
            return "```sql\nSELECT COUNT(*) AS n FROM claims WHERE status = 'escalated';\n```"
        return "There are 8 escalated claims."

    monkeypatch.setattr(sql_rag, "call_llm", fake_llm)
    res = sql_rag.sql_rag_chain_with_details("How many claims are escalated?")
    assert res["executed_sql"] == "SELECT COUNT(*) AS n FROM claims WHERE status = 'escalated';"
    assert res["db_results"] == [{"n": 8}]
    assert res["answer"] == "There are 8 escalated claims."
    assert "[{'n': 8}]" in calls[1] or '"n": 8' in calls[1]


def test_plain_chain_returns_str(db_copy, monkeypatch):
    replies = iter(["SELECT COUNT(*) AS n FROM maintenance_tickets WHERE status = 'open';", "11 open tickets."])
    monkeypatch.setattr(sql_rag, "call_llm", lambda prompt, system_instruction="": next(replies))
    assert sql_rag.sql_rag_chain("How many open tickets?") == "11 open tickets."


def test_chain_reports_sql_error_without_canned_answer(db_copy, monkeypatch):
    monkeypatch.setattr(sql_rag, "call_llm", lambda prompt, system_instruction="": "SELECT nope FROM claims;")
    res = sql_rag.sql_rag_chain_with_details("anything")
    assert "could not" in res["answer"].lower()
    assert res["db_results"] == []


def test_chain_propagates_llm_unavailable(db_copy, monkeypatch):
    def down(prompt, system_instruction=""):
        raise LLMUnavailableError("no provider")
    monkeypatch.setattr(sql_rag, "call_llm", down)
    with pytest.raises(LLMUnavailableError):
        sql_rag.sql_rag_chain("How many claims?")
