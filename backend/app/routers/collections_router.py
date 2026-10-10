from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.auth import ROLE_ACCESSIBLE_COLLECTIONS, ROLE_SQL_RAG_ALLOWED

router = APIRouter(tags=["Collections & Metadata"])

@router.get("/collections/{role}")
def get_accessible_collections(role: str):
    role_clean = role.strip().lower()
    collections = ROLE_ACCESSIBLE_COLLECTIONS.get(role_clean)
    if collections is None:
        raise HTTPException(status_code=404, detail=f"Role '{role}' not recognized.")
        
    return {
        "role": role_clean,
        "collections": collections,
        "sql_rag_permitted": ROLE_SQL_RAG_ALLOWED.get(role_clean, False)
    }

@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": "MediBot Enterprise RAG API",
        "version": "1.0.0"
    }
