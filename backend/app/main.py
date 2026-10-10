from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth_router, chat_router, collections_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="MediBot - Advanced RAG, Hybrid Search, Reranking & RBAC System"
)

# Enable CORS for the Next.js dev server only
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Include Routers
app.include_router(auth_router.router)
app.include_router(chat_router.router)
app.include_router(collections_router.router)

@app.get("/")
def root():
    return {
        "message": "Welcome to MediBot RAG API. Visit /docs for OpenAPI documentation.",
        "health": "/health"
    }
