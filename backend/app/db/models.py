from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum

from app.db.session import Base


class CycleStatus(str, enum.Enum):
    CREATED = "created"
    QUESTIONNAIRE_COMPLETE = "questionnaire_complete"
    GENERATED = "generated"
    ERROR = "error"


class InitiativeKind(str, enum.Enum):
    CORE = "core"
    SANDBOX = "sandbox"


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Cycle(Base):
    __tablename__ = "cycles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    vertical_id = Column(Text, default="restaurant_v0_1", nullable=False)
    status = Column(
        SQLEnum(CycleStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=CycleStatus.CREATED,
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class QuestionnaireResponse(Base):
    __tablename__ = "questionnaire_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cycle_id = Column(UUID(as_uuid=True), ForeignKey("cycles.id"), nullable=False, unique=True)
    responses = Column(JSON, nullable=False)
    derived_signals = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CategoryScore(Base):
    __tablename__ = "category_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cycle_id = Column(UUID(as_uuid=True), ForeignKey("cycles.id"), nullable=False)
    scores = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Initiative(Base):
    __tablename__ = "initiatives"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cycle_id = Column(UUID(as_uuid=True), ForeignKey("cycles.id"), nullable=False)
    kind = Column(
        SQLEnum(InitiativeKind, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    title = Column(Text, nullable=False)
    body = Column(JSON, nullable=False)
    rank = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
