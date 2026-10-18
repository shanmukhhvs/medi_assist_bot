"""Hybrid search runs as ONE Qdrant query_points call (dense + sparse prefetch, RRF fusion, IDF sparse).

Uses an in-memory Qdrant and a handful of synthetic chunks so the test does not depend on ingestion.
"""
import pytest
from qdrant_client import QdrantClient, models

from app.RAG.vector_store import QdrantHybridStore

CHUNKS = [
    {"text": "Paediatric < 5 kg IV cannula size is 24G.", "source_document": "icu_nursing_procedures.pdf",
     "collection": "nursing", "access_roles": ["nurse", "doctor", "admin"], "section_title": "SOP 4", "chunk_type": "table"},
    {"text": "Insurance billing code I21.4 NSTEMI package rate.", "source_document": "billing_codes.pdf",
     "collection": "billing", "access_roles": ["billing_executive", "admin"], "section_title": "Diagnosis Codes", "chunk_type": "table"},
    {"text": "Infusion pump DriveFlow IP-200 fault code F-03 occlusion.", "source_document": "equipment_manual.pdf",
     "collection": "equipment", "access_roles": ["technician", "admin"], "section_title": "Fault codes", "chunk_type": "table"},
    {"text": "Salary is credited on the last working day of the month.", "source_document": "general_faqs.pdf",
     "collection": "general", "access_roles": ["doctor", "nurse", "billing_executive", "technician", "admin"],
     "section_title": "Q1", "chunk_type": "text"},
]


@pytest.fixture(scope="module")
def store():
    s = QdrantHybridStore(client=QdrantClient(":memory:"))
    s.recreate_collection()
    s.upsert_chunks(CHUNKS)
    return s


def test_sparse_vectors_use_idf_modifier(store):
    params = store.client.get_collection(store.collection_name).config.params
    assert params.sparse_vectors["sparse"].modifier == models.Modifier.IDF


def test_single_query_points_call_with_prefetch_and_rrf(store, monkeypatch):
    calls = []
    original = store.client.query_points

    def spy(*args, **kwargs):
        calls.append(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(store.client, "query_points", spy)
    results = store.hybrid_search("IV cannula paediatric 5kg", user_role="nurse", top_k=10)

    assert len(calls) == 1
    call = calls[0]
    assert isinstance(call["query"], models.FusionQuery)
    assert call["query"].fusion == models.Fusion.RRF
    usings = sorted(p.using for p in call["prefetch"])
    assert usings == ["dense", "sparse"]
    for p in call["prefetch"]:
        assert p.filter is not None and p.limit >= 10
    assert results and results[0]["source_document"] == "icu_nursing_procedures.pdf"


@pytest.mark.parametrize("role, forbidden", [
    ("nurse", {"billing", "equipment"}),
    ("technician", {"billing", "nursing", "clinical"}),
    ("billing_executive", {"nursing", "equipment", "clinical"}),
])
def test_rbac_filter_applies_inside_query(store, role, forbidden):
    # Query text targets the forbidden collections directly (keyword guard is bypassed here on purpose).
    results = store.hybrid_search("insurance billing code I21.4 infusion pump fault F-03 IV cannula", user_role=role, top_k=10)
    assert {r["collection"] for r in results}.isdisjoint(forbidden)


def test_dense_only_search_for_comparison(store):
    results = store.dense_search("IV cannula size", user_role="admin", top_k=2)
    assert len(results) == 2


def test_recreate_collection_does_not_duplicate(store):
    store.upsert_chunks(CHUNKS)
    assert store.client.count(store.collection_name).count == len(CHUNKS)
