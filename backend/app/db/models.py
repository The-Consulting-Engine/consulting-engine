"""SQLAlchemy models."""
from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Run(Base):
    """Diagnostic run."""
    __tablename__ = "runs"
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    vertical_id = Column(String, nullable=False, default="restaurant_v1")
    company_name = Column(String)
    notes = Column(Text)
    
    # Operating mode
    mode = Column(String)  # PNL_MODE, OPS_MODE, DIRECTIONAL_MODE
    confidence_score = Column(Float)
    
    # Status
    status = Column(String, default="created")  # created, mapping, analyzing, complete, error
    
    # Relationships
    uploads = relationship("Upload", back_populates="run", cascade="all, delete-orphan")
    mappings = relationship("Mapping", back_populates="run", cascade="all, delete-orphan")
    analytics_facts = relationship("AnalyticsFact", back_populates="run", cascade="all, delete-orphan")
    initiatives = relationship("Initiative", back_populates="run", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="run", cascade="all, delete-orphan")


class Upload(Base):
    """Uploaded data file."""
    __tablename__ = "uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    filename = Column(String, nullable=False)
    pack_type = Column(String, nullable=False)  # PNL, REVENUE, LABOR
    file_path = Column(String, nullable=False)
    
    # Column profiling
    column_profile = Column(JSON)  # {col_name: {type, null_pct, samples, stats}}
    row_count = Column(Integer)
    
    run = relationship("Run", back_populates="uploads")
    mappings = relationship("Mapping", back_populates="upload")


class Mapping(Base):
    """Column mapping from source to canonical."""
    __tablename__ = "mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    canonical_field = Column(String, nullable=False)
    source_columns = Column(JSON)  # List of source column names
    transform = Column(String)  # parse_date, to_number, sum_columns, etc.
    confidence = Column(Float)
    is_confirmed = Column(Boolean, default=False)
    
    run = relationship("Run", back_populates="mappings")
    upload = relationship("Upload", back_populates="mappings")


class AnalyticsFact(Base):
    """Analytics fact with evidence key."""
    __tablename__ = "analytics_facts"
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    evidence_key = Column(String, nullable=False, index=True)
    label = Column(String, nullable=False)
    value = Column(Float)
    value_text = Column(String)  # For non-numeric values
    unit = Column(String)
    period = Column(String)  # e.g., "2024-01" or "2024-Q1"
    source = Column(String)  # Which data pack
    
    run = relationship("Run", back_populates="analytics_facts")


class Initiative(Base):
    """Selected initiative with sizing."""
    __tablename__ = "initiatives"
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    initiative_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    category = Column(String)
    description = Column(Text)
    
    # Sizing
    impact_low = Column(Float)
    impact_mid = Column(Float)
    impact_high = Column(Float)
    impact_unit = Column(String)
    
    # Ranking
    rank = Column(Integer)
    priority_score = Column(Float)
    
    # LLM explanation
    explanation = Column(Text)
    assumptions = Column(JSON)
    data_gaps = Column(JSON)
    
    run = relationship("Run", back_populates="initiatives")


class Report(Base):
    """Generated report."""
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    report_type = Column(String, nullable=False)  # memo, deck
    file_path = Column(String, nullable=False)
    
    run = relationship("Run", back_populates="reports")
