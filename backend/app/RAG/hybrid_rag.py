from typing import Dict, Any, List
from app.auth import ROLE_ACCESSIBLE_COLLECTIONS, ROLE_SQL_RAG_ALLOWED
from app.RAG.vector_store import QdrantHybridStore
from app.RAG.reranker import CrossEncoderReranker
from app.RAG.sql_rag import sql_rag_chain
from app.RAG.llm import call_llm

# Initialize vector store and reranker singletons
vector_store = QdrantHybridStore()
reranker = CrossEncoderReranker()

def is_analytical_question(question: str) -> bool:
    """
    Detects whether a natural language question requires relational database SQL analytics.
    """
    q_lower = question.lower()
    sql_keywords = [
        "how many", "total amount", "total sum", "average amount", "count of",
        "escalated claims", "escalated last month", "open tickets", "maintenance tickets",
        "billing claims", "rejected claims", "approved claims", "ticket count", "most open"
    ]
    return any(kw in q_lower for kw in sql_keywords)

def is_asking_for_restricted_collection(question: str, role: str) -> tuple[bool, str]:
    """
    Checks if query explicitly requests documents from a collection restricted for the role.
    """
    q_lower = question.lower()
    permitted = ROLE_ACCESSIBLE_COLLECTIONS.get(role, [])
    
    collection_keywords = {
        "billing": ["billing code", "claim submission", "icd-10", "cpt code", "bed rate", "procurement pricing"],
        "clinical": ["treatment protocol", "drug formulary", "anaphylaxis dose", "sepsis antibiotic", "paracetamol dose"],
        "equipment": ["maintenance schedule", "calibration", "ventilator ventmax", "syringe pump sp-500", "error code e-04"],
        "nursing": ["nursing procedure", "cvc dressing", "visual infusion phlebitis", "vip score"]
    }
    
    for col, keywords in collection_keywords.items():
        if col not in permitted:
            if any(kw in q_lower for kw in keywords):
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
            res = sql_rag_chain(question)
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
