from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from app.auth import get_current_user_role
from app.RAG.hybrid_rag import process_chat_query
from app.RAG.llm import LLMUnavailableError

router = APIRouter(tags=["Chat RAG"])

class ChatRequest(BaseModel):
    question: str
    # Optional and informational only: the authoritative role always comes from the JWT.
    role: Optional[str] = None

class SourceCitation(BaseModel):
    source_document: str
    section_title: str
    collection: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceCitation]
    retrieval_type: str
    role: str
    blocked: bool = False
    executed_sql: Optional[str] = None

@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest, user_role: str = Depends(get_current_user_role)):
    if request.role is not None and request.role != user_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requested role '{request.role}' does not match your authenticated role '{user_role}'.",
        )

    print(f"\nIncoming /chat Request: '{request.question}' | Role: '{user_role}'")
    try:
        result = process_chat_query(question=request.question, user_role=user_role)
    except LLMUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    return {
        "answer": result.get("answer", ""),
        "sources": result.get("sources", []),
        "retrieval_type": result.get("retrieval_type", "hybrid_rag"),
        "role": user_role,
        "blocked": result.get("blocked", False),
        "executed_sql": result.get("executed_sql"),
    }
