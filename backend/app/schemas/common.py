"""Schémas transverses : pagination, référence de source, erreurs."""

from datetime import date
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.models.catalog import SourceDocumentType

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SourceRef(ORMModel):
    """Document officiel d'où provient l'information (traçabilité / citation RAG)."""

    id: int
    title: str
    doc_type: SourceDocumentType
    version: str
    document_date: date | None = None
    is_demo: bool


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)


class ErrorDetail(BaseModel):
    code: str = Field(examples=["not_found"])
    message: str = Field(examples=["Formation introuvable."])
    details: Any | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Non authentifié"},
    403: {"model": ErrorResponse, "description": "Rôle ou périmètre insuffisant"},
    404: {"model": ErrorResponse, "description": "Ressource introuvable"},
    409: {"model": ErrorResponse, "description": "Conflit (code déjà utilisé)"},
    422: {"model": ErrorResponse, "description": "Données invalides"},
}
