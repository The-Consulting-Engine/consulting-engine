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


class CompetitorAnalysisStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


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


class OwnerMenuItem(Base):
    """Menu items provided directly by the restaurant owner."""
    __tablename__ = "owner_menu_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cycle_id = Column(UUID(as_uuid=True), ForeignKey("cycles.id"), nullable=False)

    # Item details
    item_name = Column(Text, nullable=False)
    price = Column(Text, nullable=False)  # Store as text, parse later (handles $12.99, 12.99, etc.)
    category = Column(Text, nullable=True)  # e.g., "Appetizers", "Mains", "Drinks"
    description = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CompetitorAnalysis(Base):
    """Stores competitor analysis results for a cycle."""
    __tablename__ = "competitor_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cycle_id = Column(UUID(as_uuid=True), ForeignKey("cycles.id"), nullable=False, unique=True)

    # Search parameters
    restaurant_name = Column(Text, nullable=False)
    address = Column(Text, nullable=False)
    search_radius_meters = Column(Integer, default=2000)
    max_competitors = Column(Integer, default=8)

    # Status tracking
    status = Column(
        SQLEnum(CompetitorAnalysisStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=CompetitorAnalysisStatus.PENDING,
        nullable=False,
    )
    error_message = Column(Text, nullable=True)

    # Results (stored as JSON)
    competitor_count = Column(Integer, nullable=True)
    positioning_summary = Column(Text, nullable=True)

    # Full analysis data
    restaurants_data = Column(JSON, nullable=True)  # List of competitor profiles
    price_analysis = Column(JSON, nullable=True)  # Price positioning metrics
    positioning = Column(JSON, nullable=True)  # PricePositioning as dict
    premium_validation = Column(JSON, nullable=True)  # Premium validation results
    menu_complexity = Column(JSON, nullable=True)  # MenuComplexity as dict
    competitive_gaps = Column(JSON, nullable=True)  # List of gaps
    strategic_initiatives = Column(JSON, nullable=True)  # Competitor-derived initiatives
    visualizations = Column(JSON, nullable=True)  # Base64 encoded charts
    executive_summary = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    analyzed_at = Column(DateTime(timezone=True), nullable=True)
