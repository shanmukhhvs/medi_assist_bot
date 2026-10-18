from fastapi import APIRouter, Depends, HTTPException, status
from app.auth import ROLE_ACCESSIBLE_COLLECTIONS, ROLE_SQL_RAG_ALLOWED, get_current_user_role

router = APIRouter(tags=["Collections & Metadata"])

@router.get("/collections/{role}")
def get_accessible_collections(role: str, user_role: str = Depends(get_current_user_role)):
    role_clean = role.strip().lower()
    # A user may only read their own role's access; admin may inspect any role.
    if user_role != "admin" and role_clean != user_role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only view your own role's collections.")

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
        "version": "1.1.0"
    }
