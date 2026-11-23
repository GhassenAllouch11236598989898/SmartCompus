"""Regroupement des routes de l'API version 1."""

from fastapi import APIRouter
from app.api.v1.endpoints import health

router = APIRouter()
router.include_router(health.router, prefix="/health", tags=["Health"])
