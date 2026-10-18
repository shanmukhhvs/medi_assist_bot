"""Docling + HybridChunker ingestion on the provided documents."""
import os

import pytest

from app.config import settings
from app.ingestion.parser import COLLECTION_ROLE_MAP, DoclingHybridParser, MAX_CHUNK_TOKENS

REQUIRED_KEYS = {"text", "source_document", "collection", "access_roles", "section_title", "chunk_type"}


@pytest.fixture(scope="module")
def parser():
    return DoclingHybridParser()


@pytest.fixture(scope="module")
def equipment_chunks(parser):
    return parser.parse_file(os.path.join(settings.RAW_DOCS_DIR, "equipment", "equipment_manual.pdf"), "equipment")


@pytest.fixture(scope="module")
def markdown_chunks(parser):
    return parser.parse_file(os.path.join(settings.RAW_DOCS_DIR, "billing", "claim_submission_guide.md"), "billing")


def test_provided_dataset_is_present():
    files = sorted(
        os.path.join(col, f) for col in os.listdir(settings.RAW_DOCS_DIR)
        for f in os.listdir(os.path.join(settings.RAW_DOCS_DIR, col))
    )
    assert len(files) == 12
    assert sum(f.endswith(".pdf") for f in files) == 11


def test_no_pypdf2():
    import app.ingestion.parser as mod
    with open(mod.__file__) as f:
        assert "PyPDF2" not in f.read()


def test_metadata_schema_complete(equipment_chunks):
    assert len(equipment_chunks) > 10
    for c in equipment_chunks:
        assert REQUIRED_KEYS <= c.keys()
        assert c["source_document"] == "equipment_manual.pdf"
        assert c["collection"] == "equipment"
        assert c["access_roles"] == COLLECTION_ROLE_MAP["equipment"]
        assert c["chunk_type"] in {"text", "table", "heading", "code"}
        assert c["section_title"]


def test_tables_are_detected(equipment_chunks):
    tables = [c for c in equipment_chunks if c["chunk_type"] == "table"]
    assert tables
    assert any("F-09" in c["text"] and "kV generator fault" in c["text"] for c in tables)


def test_section_path_disambiguates_repeated_headings(equipment_chunks):
    fault_sections = {c["section_title"] for c in equipment_chunks if c["section_title"].endswith("Fault codes")}
    # "Fault codes" appears under four devices; each must keep its device heading as parent.
    assert len(fault_sections) >= 4
    assert any("DriveFlow IP-200" in s for s in fault_sections)


def test_embedded_text_carries_heading_context(equipment_chunks):
    for c in equipment_chunks:
        leaf = c["section_title"].split(" > ")[-1]
        assert leaf in c["text"]


def test_chunks_fit_embedding_window(parser, equipment_chunks):
    for c in equipment_chunks:
        assert parser.count_tokens(c["text"]) <= MAX_CHUNK_TOKENS


def test_markdown_keeps_native_levels_and_code_blocks(markdown_chunks):
    assert any(c["section_title"].startswith("Claim Submission & Escalation Guide > 1. Cashless Claim Process")
               for c in markdown_chunks)
    assert any(c["chunk_type"] == "code" for c in markdown_chunks)
    assert any(c["chunk_type"] == "table" for c in markdown_chunks)
