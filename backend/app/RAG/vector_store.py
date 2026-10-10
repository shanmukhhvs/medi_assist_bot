import os
import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from fastembed import SparseTextEmbedding
from app.config import settings

class QdrantHybridStore:
    def __init__(self):
        os.makedirs(settings.QDRANT_PATH, exist_ok=True)
        # Initialize local Qdrant client (persistent on disk)
        self.client = QdrantClient(path=settings.QDRANT_PATH)
        
        # Dense Embedding Model (384 dimensions)
        print("Loading Dense Embedding Model (all-MiniLM-L6-v2)...")
        self.dense_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        
        # Sparse BM25 Embedding Model
        print("Loading Sparse BM25 Embedding Model (Qdrant/bm25)...")
        self.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
        
        self.collection_name = settings.COLLECTION_NAME
        self._ensure_collection()

    def _ensure_collection(self):
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in collections:
            print(f"Creating Qdrant Hybrid Collection: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    "dense": models.VectorParams(size=384, distance=models.Distance.COSINE)
                },
                sparse_vectors_config={
                    "sparse": models.SparseVectorParams(
                        index=models.SparseIndexParams(on_disk=False)
                    )
                }
            )

    def upsert_chunks(self, chunks: List[Dict[str, Any]]):
        if not chunks:
            return
        
        print(f"Indexing {len(chunks)} chunks into Qdrant vector store...")
        texts = [c["text"] for c in chunks]
        
        # Generate dense vectors
        dense_vecs = self.dense_model.encode(texts, show_progress_bar=False).tolist()
        
        # Generate sparse BM25 vectors
        sparse_embed_gen = list(self.sparse_model.embed(texts))
        
        points = []
        for idx, chunk in enumerate(chunks):
            point_id = str(uuid.uuid4())
            s_vec = sparse_embed_gen[idx]
            
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector={
                        "dense": dense_vecs[idx],
                        "sparse": models.SparseVector(
                            indices=s_vec.indices.tolist(),
                            values=s_vec.values.tolist()
                        )
                    },
                    payload=chunk
                )
            )
            
        # Batch upload to Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        print(f"Successfully indexed {len(points)} chunks.")

    def hybrid_search(self, query: str, user_role: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Executes Hybrid RAG Search (Dense + BM25) with MANDATORY RBAC Retrieval Filter.
        Filter is applied at the vector database level before returning candidates.
        """
        # 1. Enforce RBAC Metadata Filter on 'access_roles'
        rbac_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="access_roles",
                    match=models.MatchValue(value=user_role)
                )
            ]
        )
        
        # 2. Encode Dense Query Vector
        query_dense = self.dense_model.encode(query).tolist()
        
        # 3. Encode Sparse Query Vector
        sparse_gen = list(self.sparse_model.embed([query]))[0]
        query_sparse = models.SparseVector(
            indices=sparse_gen.indices.tolist(),
            values=sparse_gen.values.tolist()
        )
        
        # 4. Dense Vector Search with RBAC Filter using query_points
        dense_response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_dense,
            using="dense",
            query_filter=rbac_filter,
            limit=top_k
        )
        dense_results = dense_response.points
        
        # 5. Sparse BM25 Search with RBAC Filter using query_points
        sparse_response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_sparse,
            using="sparse",
            query_filter=rbac_filter,
            limit=top_k
        )
        sparse_results = sparse_response.points
        
        # 6. Hybrid Result Fusion (Reciprocal Rank Fusion)
        fused_candidates = {}
        
        # Process Dense Scores
        for rank, res in enumerate(dense_results):
            cid = res.id
            score = getattr(res, "score", 0.0)
            if cid not in fused_candidates:
                fused_candidates[cid] = {"hit": res, "dense_score": score, "sparse_score": 0.0, "rrf_score": 0.0}
            fused_candidates[cid]["dense_score"] = score
            fused_candidates[cid]["rrf_score"] += 1.0 / (60 + rank + 1)
            
        # Process Sparse Scores
        for rank, res in enumerate(sparse_results):
            cid = res.id
            score = getattr(res, "score", 0.0)
            if cid not in fused_candidates:
                fused_candidates[cid] = {"hit": res, "dense_score": 0.0, "sparse_score": score, "rrf_score": 0.0}
            fused_candidates[cid]["sparse_score"] = score
            fused_candidates[cid]["rrf_score"] += 1.0 / (60 + rank + 1)
            
        # Sort candidates by combined RRF score
        sorted_fused = sorted(fused_candidates.values(), key=lambda x: x["rrf_score"], reverse=True)[:top_k]
        
        output = []
        for item in sorted_fused:
            payload = item["hit"].payload
            output.append({
                "text": payload.get("text", ""),
                "source_document": payload.get("source_document", ""),
                "collection": payload.get("collection", ""),
                "access_roles": payload.get("access_roles", []),
                "section_title": payload.get("section_title", ""),
                "chunk_type": payload.get("chunk_type", "text"),
                "dense_score": float(item["dense_score"]),
                "sparse_score": float(item["sparse_score"]),
                "rrf_score": float(item["rrf_score"])
            })
            
        return output
