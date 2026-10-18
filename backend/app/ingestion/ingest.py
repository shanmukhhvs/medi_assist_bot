import os
import sys

# Ensure backend directory is in python path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.config import settings
from app.ingestion.parser import COLLECTION_ROLE_MAP, SUPPORTED_EXTENSIONS, DoclingHybridParser
from app.RAG.vector_store import QdrantHybridStore


def run_ingestion_pipeline():
    print("=== MediBot Document Ingestion Pipeline (Docling + HybridChunker) ===")
    raw_docs_dir = settings.RAW_DOCS_DIR
    if not os.path.isdir(raw_docs_dir):
        raise SystemExit(f"Error: {raw_docs_dir} does not exist. Copy the provided mediassist_data documents there.")

    parser = DoclingHybridParser()
    all_chunks = []
    for col in COLLECTION_ROLE_MAP:
        col_dir = os.path.join(raw_docs_dir, col)
        if not os.path.isdir(col_dir):
            continue
        for fname in sorted(os.listdir(col_dir)):
            if fname.lower().endswith(SUPPORTED_EXTENSIONS):
                print(f"Parsing [{col}] document: {fname}")
                chunks = parser.parse_file(os.path.join(col_dir, fname), col)
                print(f" -> Extracted {len(chunks)} structural chunks.")
                all_chunks.extend(chunks)

    print(f"\nTotal chunks prepared across all collections: {len(all_chunks)}")
    store = QdrantHybridStore()
    # Re-ingestion replaces the index rather than appending duplicates.
    store.recreate_collection()
    store.upsert_chunks(all_chunks)
    print("Ingestion & Vector Indexing Complete!")


if __name__ == "__main__":
    run_ingestion_pipeline()
