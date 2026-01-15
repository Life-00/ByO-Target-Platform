import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Float, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    user_email = Column(String, nullable=False, index=True)

    original_name = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)
    mime_type = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=True)

    # uploaded / failed / parsed ... 등
    status = Column(String, default="uploaded", nullable=False)
    summary = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class StagedPaper(Base):
    __tablename__ = "staged_papers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    user_email = Column(String, nullable=False, index=True)

    # arxiv / semantic_scholar / internal ...
    source = Column(String, nullable=False)

    title = Column(String, nullable=False)
    authors = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    url = Column(String, nullable=True)

    abstract = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    pdf_storage_path = Column(String, nullable=True)  # PDF 저장 시 경로

    # retrieval 점수(없으면 null)
    score = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Selection(Base):
    __tablename__ = "selections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    user_email = Column(String, nullable=False, index=True)

    # uploaded_file / staged_paper
    item_type = Column(String, nullable=False)
    item_id = Column(UUID(as_uuid=True), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class VectorIndexRecord(Base):
    __tablename__ = "vector_index_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    user_email = Column(String, nullable=False, index=True)

    item_type = Column(String, nullable=False)
    item_id = Column(UUID(as_uuid=True), nullable=False)

    chroma_collection = Column(String, nullable=False)
    embedding_model = Column(String, nullable=True)

    # queued / running / success / fail
    status = Column(String, default="queued", nullable=False)

    # chunk_count, error, timings... 자유롭게
    stats = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    user_email = Column(String, nullable=False, index=True)

    # research / extract / report
    job_type = Column(String, nullable=False)

    # queued / running / success / fail
    status = Column(String, default="queued", nullable=False)

    request_payload = Column(JSONB, nullable=True)
    result_payload = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
