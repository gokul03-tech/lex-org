"""SQLAlchemy ORM models for LexOrch-KG.

Models: User, Case, Document, Analysis, Report, Feedback.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    """Registered user of the LexOrch-KG platform."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="advocate", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    cases: Mapped[list["Case"]] = relationship("Case", back_populates="user", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


class Case(Base, UUIDMixin, TimestampMixin):
    """A legal case managed by an advocate."""

    __tablename__ = "cases"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    case_type: Mapped[str | None] = mapped_column(String(200), nullable=True)
    court_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    case_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    filing_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="cases")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="case", lazy="selectin")
    analyses: Mapped[list["Analysis"]] = relationship("Analysis", back_populates="case", lazy="selectin")
    reports: Mapped[list["Report"]] = relationship("Report", back_populates="case", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Case(id={self.id}, title={self.title}, status={self.status})>"


class Document(Base, UUIDMixin, TimestampMixin):
    """An uploaded legal document associated with a case."""

    __tablename__ = "documents"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), default="other", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="uploaded", nullable=False)

    # Parsed content
    parsed_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Metadata
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Processing info
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    case: Mapped["Case"] = relationship("Case", back_populates="documents")

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename={self.filename}, status={self.status})>"


class Analysis(Base, UUIDMixin, TimestampMixin):
    """Results of multi-agent legal analysis for a case."""

    __tablename__ = "analyses"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    query: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Agent outputs
    agent_results: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    confidence_scores: Mapped[dict[str, float]] = mapped_column(JSON, default=dict, nullable=False)
    trust_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Extracted knowledge
    entities: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    legal_issues: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    applicable_acts: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    applicable_sections: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    precedents: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)

    # Analysis outputs
    contradictions: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    procedural_status: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    risk_assessment: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    strategy_options: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)

    # Explanation graph (for rendering)
    explanation_graph: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Errors during analysis
    errors: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    case: Mapped["Case"] = relationship("Case", back_populates="analyses")

    def __repr__(self) -> str:
        return f"<Analysis(id={self.id}, case_id={self.case_id}, status={self.status})>"


class Report(Base, UUIDMixin, TimestampMixin):
    """Generated legal advisory report for a case."""

    __tablename__ = "reports"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True, nullable=False)
    analysis_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)

    # Report sections as ordered JSON
    sections: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    # Scores
    trust_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_scores: Mapped[dict[str, float]] = mapped_column(JSON, default=dict, nullable=False)

    # Graph data for visualization
    explanation_graph: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    knowledge_graph: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Export paths
    pdf_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    json_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Relationships
    case: Mapped["Case"] = relationship("Case", back_populates="reports")

    def __repr__(self) -> str:
        return f"<Report(id={self.id}, case_id={self.case_id}, title={self.title})>"


class Feedback(Base, UUIDMixin, TimestampMixin):
    """User feedback on a generated report."""

    __tablename__ = "feedback"

    report_id: Mapped[str] = mapped_column(ForeignKey("reports.id"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_accurate: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    corrections: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<Feedback(id={self.id}, report_id={self.report_id}, rating={self.rating})>"


class AuditLog(Base, UUIDMixin, TimestampMixin):
    """Security audit log for sandbox executions and system events."""

    __tablename__ = "audit_logs"

    event_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    case_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    agent_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    output_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="success", nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, event_type={self.event_type}, status={self.status})>"
