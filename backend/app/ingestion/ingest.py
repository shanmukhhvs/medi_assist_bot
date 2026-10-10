import os
import sys

# Ensure backend directory is in python path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.config import settings
from app.ingestion.parser import HierarchicalDocumentParser
from app.RAG.vector_store import QdrantHybridStore

def run_ingestion_pipeline():
    print("=== MediBot Document Ingestion Pipeline ===")
    raw_docs_dir = settings.RAW_DOCS_DIR
    
    if not os.path.exists(raw_docs_dir):
        print(f"Error: {raw_docs_dir} does not exist. Run scripts/create_dataset.py first.")
        return

    parser = HierarchicalDocumentParser(max_chunk_tokens=350, overlap_tokens=40)
    all_chunks = []

    collections = ["general", "clinical", "nursing", "billing", "equipment"]
    for col in collections:
        col_dir = os.path.join(raw_docs_dir, col)
        if not os.path.exists(col_dir):
            continue
        
        files = os.listdir(col_dir)
        for fname in files:
            file_path = os.path.join(col_dir, fname)
            if os.path.isfile(file_path) and (fname.endswith(".md") or fname.endswith(".pdf")):
                print(f"Parsing [{col}] document: {fname}")
                chunks = parser.parse_file(file_path, col)
                print(f" -> Extracted {len(chunks)} structural chunks.")
                all_chunks.extend(chunks)

    print(f"\nTotal chunks prepared across all collections: {len(all_chunks)}")
    
    if all_chunks:
        store = QdrantHybridStore()
        store.upsert_chunks(all_chunks)
        print("Ingestion & Vector Indexing Complete!")

if __name__ == "__main__":
    run_ingestion_pipeline()
