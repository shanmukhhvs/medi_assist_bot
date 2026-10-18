import os
import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from fastembed import SparseTextEmbedding
from app.config import settings

DENSE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DENSE_DIM = 384
SPARSE_MODEL = "Qdrant/bm25"
# Each prefetch (dense and sparse) fetches this many candidates before RRF fusion narrows to top_k.
PREFETCH_LIMIT = 20
UPSERT_BATCH = 128
# Stable namespace so re-ingesting the same chunk produces the same point id.
_POINT_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "medibot/chunks")

PAYLOAD_FIELDS = ["text", "source_document", "collection", "access_roles", "section_title", "chunk_type"]


class QdrantHybridStore:
    def __init__(self, client: Optional[QdrantClient] = None):
        if client is None:
            os.makedirs(settings.QDRANT_PATH, exist_ok=True)
            # Local Qdrant client (persistent on disk)
            client = QdrantClient(path=settings.QDRANT_PATH)
        self.client = client

        print(f"Loading Dense Embedding Model ({DENSE_MODEL})...")
        self.dense_model = SentenceTransformer(DENSE_MODEL)

        # BM25 term-frequency weights; IDF is applied by Qdrant via Modifier.IDF on the sparse vector config.
        print(f"Loading Sparse BM25 Embedding Model ({SPARSE_MODEL})...")
        self.sparse_model = SparseTextEmbedding(model_name=SPARSE_MODEL)

        self.collection_name = settings.COLLECTION_NAME
        if not self.client.collection_exists(self.collection_name):
            self.recreate_collection()

    def recreate_collection(self):
        if self.client.collection_exists(self.collection_name):
            self.client.delete_collection(self.collection_name)
        print(f"Creating Qdrant Hybrid Collection: {self.collection_name}")
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config={
                "dense": models.VectorParams(size=DENSE_DIM, distance=models.Distance.COSINE)
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)
            },
        )
        self.client.create_payload_index(self.collection_name, "access_roles", models.PayloadSchemaType.KEYWORD)

    def upsert_chunks(self, chunks: List[Dict[str, Any]]):
        if not chunks:
            return

        print(f"Indexing {len(chunks)} chunks into Qdrant vector store...")
        for start in range(0, len(chunks), UPSERT_BATCH):
            batch = chunks[start:start + UPSERT_BATCH]
            texts = [c["text"] for c in batch]
            dense_vecs = self.dense_model.encode(texts, show_progress_bar=False).tolist()
            sparse_vecs = list(self.sparse_model.embed(texts))

            points = []
            for chunk, dense, sparse in zip(batch, dense_vecs, sparse_vecs):
                point_id = str(uuid.uuid5(_POINT_NAMESPACE, f"{chunk['source_document']}\x00{chunk['text']}"))
                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector={
                            "dense": dense,
                            "sparse": models.SparseVector(indices=sparse.indices.tolist(), values=sparse.values.tolist()),
                        },
                        payload={k: chunk[k] for k in PAYLOAD_FIELDS},
                    )
                )
            self.client.upsert(collection_name=self.collection_name, points=points)
        print(f"Successfully indexed {len(chunks)} chunks.")

    @staticmethod
    def _rbac_filter(user_role: str) -> models.Filter:
        return models.Filter(
            must=[models.FieldCondition(key="access_roles", match=models.MatchValue(value=user_role))]
        )

    def _encode_query(self, query: str):
        dense = self.dense_model.encode(query).tolist()
        sparse = next(iter(self.sparse_model.query_embed(query)))
        return dense, models.SparseVector(indices=sparse.indices.tolist(), values=sparse.values.tolist())

    @staticmethod
    def _to_results(points) -> List[Dict[str, Any]]:
        out = []
        for p in points:
            item = {k: p.payload.get(k) for k in PAYLOAD_FIELDS}
            item["fusion_score"] = float(p.score)
            out.append(item)
        return out

    def hybrid_search(self, query: str, user_role: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Hybrid RAG search in ONE Qdrant query_points call: a dense and a sparse (BM25 + IDF) prefetch, each
        restricted by the RBAC access_roles filter, fused server-side with Reciprocal Rank Fusion.
        """
        rbac_filter = self._rbac_filter(user_role)
        dense, sparse = self._encode_query(query)
        prefetch_limit = max(PREFETCH_LIMIT, top_k)

        response = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                models.Prefetch(query=dense, using="dense", filter=rbac_filter, limit=prefetch_limit),
                models.Prefetch(query=sparse, using="sparse", filter=rbac_filter, limit=prefetch_limit),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            # Applied to the fused result as well, so RBAC holds even if a prefetch is changed later.
            query_filter=rbac_filter,
            limit=top_k,
            with_payload=True,
        )
        return self._to_results(response.points)

    def dense_search(self, query: str, user_role: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Dense-only baseline (same RBAC filter); used by scripts/eval_retrieval.py for the comparison table."""
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=self.dense_model.encode(query).tolist(),
            using="dense",
            query_filter=self._rbac_filter(user_role),
            limit=top_k,
            with_payload=True,
        )
        return self._to_results(response.points)
