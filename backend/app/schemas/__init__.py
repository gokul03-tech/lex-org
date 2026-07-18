"""Core Pydantic schemas for LexOrch-KG.

All request/response models used across the API are defined here.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, EmailStr, Field


# ── User Schemas ─────────────────────────────────────────────
class UserRole(str, Enum):
    ADVOCATE = "advocate"
    RESEARCHER = "researcher"
    STUDENT = "student"
    ADMIN = "admin"


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=200)
    role: UserRole = UserRole.ADVOCATE


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None


class UserResponse(UserBase):
    id: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    email: EmailStr
    password: str


# ── Auth Schemas ─────────────────────────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


# ── Case Schemas ─────────────────────────────────────────────
class CaseStatus(str, Enum):
    DRAFT = "draft"
    DOCUMENTS_UPLOADED = "documents_uploaded"
    ANALYZING = "analyzing"
    ANALYSIS_COMPLETE = "analysis_complete"
    REPORT_GENERATED = "report_generated"
    ARCHIVED = "archived"


class CaseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(None, max_length=10000)
    case_type: str | None = Field(None, max_length=200)
    court_name: str | None = Field(None, max_length=500)
    case_number: str | None = Field(None, max_length=100)
    filing_date: datetime | None = None


class CaseUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    description: str | None = Field(None, max_length=10000)
    case_type: str | None = Field(None, max_length=200)
    status: CaseStatus | None = None


class CaseResponse(CaseCreate):
    id: str
    user_id: str
    status: CaseStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Document Schemas ─────────────────────────────────────────
class DocumentType(str, Enum):
    PETITION = "petition"
    EVIDENCE = "evidence"
    JUDGMENT = "judgment"
    CONTRACT = "contract"
    AFFIDAVIT = "affidavit"
    OTHER = "other"


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    OCR_PROCESSING = "ocr_processing"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    COMPLETE = "complete"
    FAILED = "failed"


class DocumentCreate(BaseModel):
    case_id: str
    document_type: DocumentType = DocumentType.OTHER
    description: str | None = Field(None, max_length=1000)


class DocumentResponse(BaseModel):
    id: str
    case_id: str
    filename: str
    document_type: DocumentType
    status: DocumentStatus
    parsed_text: str | None
    chunk_count: int
    page_count: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Analysis Schemas ─────────────────────────────────────────
class AnalysisRequest(BaseModel):
    case_id: str
    query: str | None = Field(None, description="Optional specific question about the case")
    agents: list[str] | None = Field(
        None,
        description="List of agent names to run; runs all if None",
    )


class AgentResult(BaseModel):
    agent_name: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    output: dict[str, Any]
    execution_time_ms: float
    error: str | None = None


class AnalysisResponse(BaseModel):
    id: str
    case_id: str
    status: str
    agent_results: list[AgentResult]
    confidence_scores: dict[str, float]
    trust_score: float
    created_at: datetime

    model_config = {"from_attributes": True}


# ── RAG Schemas ──────────────────────────────────────────────
class RAGQuery(BaseModel):
    query: str
    top_k: int = Field(default=10, ge=1, le=100)
    intent: str | None = None
    filters: dict[str, Any] | None = None


class RAGResult(BaseModel):
    chunk_id: str
    text: str
    score: float
    source: str  # vector, kg, citation, keyword
    metadata: dict[str, Any] = Field(default_factory=dict)


class RAGResponse(BaseModel):
    query: str
    detected_intent: str
    results: list[RAGResult]
    retrieval_time_ms: float


# ── Report Schemas ───────────────────────────────────────────
class ReportSection(BaseModel):
    title: str
    content: str | dict[str, Any]
    order: int


class ReportCreate(BaseModel):
    case_id: str


class ReportResponse(BaseModel):
    id: str
    case_id: str
    sections: list[ReportSection]
    trust_score: float
    confidence_scores: dict[str, float]
    explanation_graph: dict[str, Any] | None
    knowledge_graph: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── KG Schemas ───────────────────────────────────────────────
class KGEntity(BaseModel):
    name: str
    entity_type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class KGRelationship(BaseModel):
    source: str
    target: str
    relationship_type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class KGCaseGraphResponse(BaseModel):
    nodes: list[KGEntity]
    edges: list[KGRelationship]


# ── Generic / Utility Schemas ────────────────────────────────
class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageResponse(BaseModel):
    message: str
    detail: str | None = None


class ErrorResponse(BaseModel):
    detail: str
    error_type: str | None = None
