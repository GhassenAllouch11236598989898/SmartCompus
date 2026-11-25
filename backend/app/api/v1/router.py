"""Regroupement des routes de l'API version 1."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, formations, health, memory, sessions

router = APIRouter()
router.include_router(health.router, prefix="/health", tags=["Health"])
router.include_router(formations.router, prefix="/formations", tags=["Formations"])
router.include_router(sessions.router, prefix="/sessions", tags=["Sessions visiteurs"])
router.include_router(memory.router, prefix="/sessions/me/messages", tags=["Mémoire des conversations"])
router.include_router(auth.router, prefix="/auth", tags=["Authentification et rôles"])