from typing import List, Dict, Any
from sentence_transformers import CrossEncoder

class CrossEncoderReranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        print(f"Loading Cross-Encoder Reranker ({model_name})...")
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_n: int = 3) -> List[Dict[str, Any]]:
        if not candidates:
            return []
        
        # Prepare (query, passage) pairs
        pairs = [(query, cand["text"]) for cand in candidates]
        scores = self.model.predict(pairs)
        
        # Attach scores to candidates
        for idx, cand in enumerate(candidates):
            cand["rerank_score"] = float(scores[idx])
            
        # Sort candidates descending by rerank score
        reranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)
        
        print("\n--- Reranker Score Logging ---")
        for rank, item in enumerate(reranked):
            doc = item.get("source_document", "doc")
            sec = item.get("section_title", "section")
            score = item.get("rerank_score", 0.0)
            print(f"Rank {rank+1}: Score {score:.4f} | Document: {doc} | Section: {sec}")
        print("------------------------------\n")
        
        return reranked[:top_n]
