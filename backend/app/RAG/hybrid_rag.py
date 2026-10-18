from typing import Dict, Any, List
from app.auth import ROLE_ACCESSIBLE_COLLECTIONS, ROLE_SQL_RAG_ALLOWED
from app.RAG.vector_store import QdrantHybridStore
from app.RAG.reranker import CrossEncoderReranker
from app.RAG.sql_rag import sql_rag_chain_with_details
from app.RAG.llm import call_llm

# Initialize vector store and reranker singletons
vector_store = QdrantHybridStore()
reranker = CrossEncoderReranker()

# Analytical = an aggregate/count word AND a database entity. "How many hours is a night shift?" stays document RAG.
_ANALYTIC_WORDS = ["how many", "number of", "count", "total", "sum of", "average", "most", "least", "highest",
                   "lowest", "per month", "by month", "breakdown", "trend", "percentage"]
_DB_ENTITIES = ["claim", "ticket", "insurer"]


def is_analytical_question(question: str) -> bool:
    """Detects whether a question needs SQL analytics over mediassist.db (claims / maintenance_tickets)."""
    q_lower = question.lower()
    return any(w in q_lower for w in _ANALYTIC_WORDS) and any(e in q_lower for e in _DB_ENTITIES)


# Terms that only occur in one restricted collection of the provided documents (checked against the general
# collection so that permitted HR/FAQ questions are not blocked). This only produces the friendly refusal
# message; the access_roles filter inside the Qdrant query is the actual enforcement.
COLLECTION_KEYWORDS = {
    "billing": ["billing code", "insurance billing", "claim submission", "pre-authorisation", "pre-authorization",
                "empanelled insurer", "procedure code", "room rent", "co-pay", "package rate"],
    "clinical": ["drug formulary", "formulary", "diagnostic reference", "reference range", "dosage", "dosing",
                 "curb-65", "high-alert medication"],
    "equipment": ["equipment manual", "fault code", "calibration", "maintenance schedule", "bm-500", "driveflow",
                  "ip-200", "sterilpro", "radipro", "mx-150", "bowie-dick"],
    "nursing": ["nursing procedure", "icu nursing", "cvc", "central venous catheter", "cannula", "nasogastric",
                "endotracheal suctioning"],
}


def is_asking_for_restricted_collection(question: str, role: str) -> tuple[bool, str]:
    """Checks if the query explicitly targets a collection the role may not read."""
    q_lower = question.lower()
    permitted = ROLE_ACCESSIBLE_COLLECTIONS.get(role, [])
    for col, keywords in COLLECTION_KEYWORDS.items():
        if col not in permitted and any(kw in q_lower for kw in keywords):
            return True, col
    return False, ""

def process_chat_query(question: str, user_role: str) -> Dict[str, Any]:
    """
    Main RAG Routing Engine enforcing RBAC at the retrieval layer.
    """
    permitted_cols = ROLE_ACCESSIBLE_COLLECTIONS.get(user_role, ["general"])
    
    # 1. Check if query is an analytical/database question
    if is_analytical_question(question):
        if ROLE_SQL_RAG_ALLOWED.get(user_role, False):
            print(f"[RAG Router] Routing analytical question to SQL RAG for role '{user_role}'")
            res = sql_rag_chain_with_details(question)
            res["role"] = user_role
            res["sources"] = []
            return res
        else:
            print(f"[RAG Router] SQL RAG blocked by RBAC for role '{user_role}'")
            cols_str = ", ".join(permitted_cols)
            return {
                "answer": f"As a {user_role}, you do not have access to database analytics or financial claims records. I can only answer document questions from the {cols_str} collections.",
                "sources": [],
                "retrieval_type": "hybrid_rag",
                "blocked": True,
                "role": user_role
            }

    # 2. Check for explicit adversarial / out-of-bounds collection requests
    is_blocked, restricted_col = is_asking_for_restricted_collection(question, user_role)
    if is_blocked:
        print(f"[RAG Router] Explicit collection restriction detected for role '{user_role}' requesting '{restricted_col}'")
        cols_str = ", ".join(permitted_cols)
        return {
            "answer": f"As a {user_role}, you do not have access to {restricted_col} documents. I can only answer questions from the {cols_str} collections.",
            "sources": [],
            "retrieval_type": "hybrid_rag",
            "blocked": True,
            "role": user_role
        }

    # 3. Perform Vector-Level Hybrid Retrieval with MANDATORY Qdrant RBAC Filter
    print(f"[RAG Router] Executing Hybrid Search for role '{user_role}' with filter access_roles CONTAINS '{user_role}'")
    candidates = vector_store.hybrid_search(query=question, user_role=user_role, top_k=10)
    
    # If no documents pass the retrieval-level RBAC filter
    if not candidates:
        cols_str = ", ".join(permitted_cols)
        return {
            "answer": f"No accessible documents were found for your query. As a {user_role}, your document access is scoped to the following collections: {cols_str}.",
            "sources": [],
            "retrieval_type": "hybrid_rag",
            "role": user_role
        }

    # 4. Cross-Encoder Reranking (narrow top 10 down to top 3)
    top_chunks = reranker.rerank(query=question, candidates=candidates, top_n=3)
    
    # 5. Build Grounded Prompt for LLM Synthesis
    context_blocks = []
    sources = []
    
    for idx, chunk in enumerate(top_chunks):
        context_blocks.append(f"Context {idx+1}:\n{chunk['text']}")
        sources.append({
            "source_document": chunk.get("source_document", "Unknown"),
            "section_title": chunk.get("section_title", "General"),
            "collection": chunk.get("collection", "general")
        })
        
    combined_context = "\n\n".join(context_blocks)
    
    system_instruction = (
        "You are MediBot, an internal AI assistant for MediAssist Health Network. "
        "Answer the user's question strictly based on the provided context passages below. "
        "Do not invent facts outside the context. Maintain a professional medical and administrative tone."
    )
    
    user_prompt = f"Context Passages:\n{combined_context}\n\nQuestion: {question}\n\nDetailed Answer:"
    answer = call_llm(prompt=user_prompt, system_instruction=system_instruction)
    
    return {
        "answer": answer,
        "sources": sources,
        "retrieval_type": "hybrid_rag",
        "role": user_role
    }
