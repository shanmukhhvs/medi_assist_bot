from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.auth import get_current_user_role
from app.RAG.hybrid_rag import process_chat_query

router = APIRouter(tags=["Chat RAG"])

class ChatRequest(BaseModel):
    question: str

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

@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest, user_role: str = Depends(get_current_user_role)):
    print(f"\nIncoming /chat Request: '{request.question}' | Role: '{user_role}'")
    result = process_chat_query(question=request.question, user_role=user_role)
    
    return {
        "answer": result.get("answer", ""),
        "sources": result.get("sources", []),
        "retrieval_type": result.get("retrieval_type", "hybrid_rag"),
        "role": result.get("role", user_role),
        "blocked": result.get("blocked", False)
    }
