"""
Competitor analysis API routes.

Provides endpoints for running competitor analysis and retrieving results.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Cycle, CompetitorAnalysis, CompetitorAnalysisStatus

router = APIRouter()
logger = logging.getLogger(__name__)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class EnrichRequest(BaseModel):
    """Request body for competitor analysis enrichment."""
    restaurant_name: str = Field(..., description="Name of the target restaurant")
    address: str = Field(..., description="Full address of the target restaurant")
    search_radius_meters: int = Field(default=2000, ge=500, le=10000)
    max_competitors: int = Field(default=8, ge=1, le=20)


class EnrichResponse(BaseModel):
    """Response from enrichment endpoint."""
    cycle_id: str
    status: str
    message: str
    competitor_analysis_id: Optional[str] = None


class CompetitorSummary(BaseModel):
    """Summary of a competitor."""
    name: str
    rating: Optional[float]
    review_count: Optional[int]
    price_level: Optional[str]
    distance_meters: Optional[float]


class CompetitorAnalysisResponse(BaseModel):
    """Full competitor analysis response."""
    cycle_id: str
    status: str
    restaurant_name: Optional[str]
    address: Optional[str]
    competitor_count: Optional[int]
    positioning_summary: Optional[str]
    positioning: Optional[dict]
    premium_validation: Optional[dict]
    menu_complexity: Optional[dict]
    competitive_gaps: Optional[list]
    strategic_initiatives: Optional[list]
    executive_summary: Optional[str]
    error_message: Optional[str]
    analyzed_at: Optional[str]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _serialize_dataclass(obj):
    """Convert dataclass to dict, handling nested dataclasses."""
    from dataclasses import asdict, is_dataclass
    if is_dataclass(obj):
        return asdict(obj)
    return obj


def _run_competitor_analysis(
    analysis_id: uuid.UUID,
    restaurant_name: str,
    address: str,
    search_radius_meters: int,
    max_competitors: int,
    db_url: str,
):
    """
    Background task to run the competitor analysis pipeline.

    This runs synchronously in a background thread so the API can return immediately.
    Uses asyncio.run() internally to execute the async pipeline.
    """
    import asyncio
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # Create a new session for background task
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Get the analysis record
        analysis = db.query(CompetitorAnalysis).filter(
            CompetitorAnalysis.id == analysis_id
        ).first()

        if not analysis:
            logger.error(f"CompetitorAnalysis {analysis_id} not found")
            return

        # Update status to running
        analysis.status = CompetitorAnalysisStatus.RUNNING
        db.commit()

        logger.info(f"Starting competitor analysis for {restaurant_name} at {address}")

        # Import and run the pipeline
        from app.competitor_analysis.pipeline import (
            CompetitorAnalysisPipeline,
            PipelineConfig,
        )

        config = PipelineConfig(
            search_radius_meters=search_radius_meters,
            max_competitors=max_competitors,
            generate_visualizations=True,
        )

        # Run the async pipeline in a new event loop
        async def run_pipeline():
            pipeline = CompetitorAnalysisPipeline()
            return await pipeline.analyze(
                restaurant_name=restaurant_name,
                address=address,
                config=config,
            )

        result = asyncio.run(run_pipeline())

        # Store results
        analysis.competitor_count = len(result.restaurants_df) - 1 if result.restaurants_df is not None else 0
        analysis.positioning_summary = result.positioning.description if result.positioning else None

        # Serialize dataframes to JSON-friendly format
        if result.restaurants_df is not None and not result.restaurants_df.empty:
            restaurants_list = result.restaurants_df.to_dict(orient='records')
            # Clean up any non-serializable values
            for r in restaurants_list:
                for k, v in list(r.items()):
                    if hasattr(v, 'tolist'):  # numpy arrays
                        r[k] = v.tolist()
                    elif str(v) == 'nan' or str(v) == 'NaN':
                        r[k] = None
            analysis.restaurants_data = restaurants_list

        # Store price analysis (convert DataFrames to dicts)
        if result.price_analysis:
            price_data = {}
            for key, value in result.price_analysis.items():
                if hasattr(value, 'to_dict'):  # DataFrame
                    price_data[key] = value.to_dict(orient='records')
                else:
                    price_data[key] = value
            analysis.price_analysis = price_data

        # Store analysis results
        analysis.positioning = _serialize_dataclass(result.positioning)
        analysis.menu_complexity = _serialize_dataclass(result.menu_complexity)
        analysis.competitive_gaps = [_serialize_dataclass(g) for g in result.competitive_gaps]
        analysis.strategic_initiatives = [_serialize_dataclass(i) for i in result.initiatives]
        analysis.visualizations = result.visualizations
        analysis.executive_summary = result.executive_summary

        # Get premium_validation from strategic analysis if available
        # (It's generated inside generate_strategic_analysis)
        from app.competitor_analysis.strategic_analyzer import validate_premium_pricing
        if result.price_analysis and result.restaurants_df is not None:
            pv = validate_premium_pricing(result.price_analysis, result.restaurants_df)
            analysis.premium_validation = _serialize_dataclass(pv)

        # Update status
        analysis.status = CompetitorAnalysisStatus.COMPLETED
        analysis.analyzed_at = datetime.utcnow()

        if result.errors:
            analysis.error_message = "; ".join(result.errors)

        db.commit()
        logger.info(f"Competitor analysis completed for {restaurant_name}")

    except Exception as e:
        logger.exception(f"Competitor analysis failed: {e}")
        try:
            analysis = db.query(CompetitorAnalysis).filter(
                CompetitorAnalysis.id == analysis_id
            ).first()
            if analysis:
                analysis.status = CompetitorAnalysisStatus.ERROR
                analysis.error_message = str(e)[:1000]
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/competitors/health")
def competitor_analysis_health():
    """
    Check if competitor analysis is properly configured.

    Returns status of required API keys and services.
    """
    import os

    google_key = os.getenv("GOOGLE_PLACES_API_KEY", "")
    apify_token = os.getenv("APIFY_API_TOKEN", "")
    openai_key = os.getenv("OPENAI_API_KEY", "") or os.getenv("LLM_API_KEY", "")

    return {
        "status": "ok" if google_key and apify_token else "degraded",
        "google_places_configured": bool(google_key),
        "apify_configured": bool(apify_token),
        "openai_configured": bool(openai_key),
        "message": (
            "All services configured" if (google_key and apify_token and openai_key)
            else "Some API keys missing - competitor analysis may fail"
        ),
    }


@router.post("/cycles/{cycle_id}/enrich", response_model=EnrichResponse)
async def enrich_with_competitors(
    cycle_id: str,
    request: EnrichRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Trigger competitor analysis for a cycle.

    This starts a background task to analyze competitors and enrich
    the cycle with competitive insights. The analysis runs asynchronously.

    Use GET /cycles/{cycle_id}/competitors to check status and retrieve results.
    """
    # Validate cycle_id
    try:
        cycle_uuid = uuid.UUID(cycle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid cycle_id format")

    # Check cycle exists
    cycle = db.query(Cycle).filter(Cycle.id == cycle_uuid).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")

    # Check if analysis already exists
    existing = db.query(CompetitorAnalysis).filter(
        CompetitorAnalysis.cycle_id == cycle_uuid
    ).first()

    if existing:
        if existing.status == CompetitorAnalysisStatus.RUNNING:
            return EnrichResponse(
                cycle_id=cycle_id,
                status="running",
                message="Competitor analysis is already in progress",
                competitor_analysis_id=str(existing.id),
            )
        elif existing.status == CompetitorAnalysisStatus.COMPLETED:
            # Allow re-running with new parameters
            existing.status = CompetitorAnalysisStatus.PENDING
            existing.restaurant_name = request.restaurant_name
            existing.address = request.address
            existing.search_radius_meters = request.search_radius_meters
            existing.max_competitors = request.max_competitors
            existing.error_message = None
            db.commit()
            analysis = existing
        else:
            # Reset and re-run
            existing.status = CompetitorAnalysisStatus.PENDING
            existing.restaurant_name = request.restaurant_name
            existing.address = request.address
            existing.search_radius_meters = request.search_radius_meters
            existing.max_competitors = request.max_competitors
            existing.error_message = None
            db.commit()
            analysis = existing
    else:
        # Create new analysis record
        analysis = CompetitorAnalysis(
            cycle_id=cycle_uuid,
            restaurant_name=request.restaurant_name,
            address=request.address,
            search_radius_meters=request.search_radius_meters,
            max_competitors=request.max_competitors,
            status=CompetitorAnalysisStatus.PENDING,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

    # Get database URL for background task
    import os
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@db:5432/consulting_engine"
    )

    # Start background task
    background_tasks.add_task(
        _run_competitor_analysis,
        analysis.id,
        request.restaurant_name,
        request.address,
        request.search_radius_meters,
        request.max_competitors,
        db_url,
    )

    return EnrichResponse(
        cycle_id=cycle_id,
        status="started",
        message="Competitor analysis started. Poll GET /cycles/{cycle_id}/competitors for results.",
        competitor_analysis_id=str(analysis.id),
    )


@router.get("/cycles/{cycle_id}/competitors", response_model=CompetitorAnalysisResponse)
def get_competitor_analysis(
    cycle_id: str,
    db: Session = Depends(get_db),
):
    """
    Get competitor analysis results for a cycle.

    Returns the current status and any available results.
    If analysis is still running, status will be "running".
    """
    # Validate cycle_id
    try:
        cycle_uuid = uuid.UUID(cycle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid cycle_id format")

    # Check cycle exists
    cycle = db.query(Cycle).filter(Cycle.id == cycle_uuid).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")

    # Get analysis
    analysis = db.query(CompetitorAnalysis).filter(
        CompetitorAnalysis.cycle_id == cycle_uuid
    ).first()

    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="No competitor analysis found. Use POST /cycles/{cycle_id}/enrich to start one."
        )

    return CompetitorAnalysisResponse(
        cycle_id=cycle_id,
        status=analysis.status.value if hasattr(analysis.status, 'value') else str(analysis.status),
        restaurant_name=analysis.restaurant_name,
        address=analysis.address,
        competitor_count=analysis.competitor_count,
        positioning_summary=analysis.positioning_summary,
        positioning=analysis.positioning,
        premium_validation=analysis.premium_validation,
        menu_complexity=analysis.menu_complexity,
        competitive_gaps=analysis.competitive_gaps,
        strategic_initiatives=analysis.strategic_initiatives,
        executive_summary=analysis.executive_summary,
        error_message=analysis.error_message,
        analyzed_at=analysis.analyzed_at.isoformat() if analysis.analyzed_at else None,
    )


@router.get("/cycles/{cycle_id}/competitors/visualizations")
def get_competitor_visualizations(
    cycle_id: str,
    db: Session = Depends(get_db),
):
    """
    Get competitor analysis visualizations (base64 encoded PNGs).

    Returns a dict of visualization name -> base64 PNG data.
    """
    # Validate cycle_id
    try:
        cycle_uuid = uuid.UUID(cycle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid cycle_id format")

    # Get analysis
    analysis = db.query(CompetitorAnalysis).filter(
        CompetitorAnalysis.cycle_id == cycle_uuid
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="No competitor analysis found")

    if analysis.status != CompetitorAnalysisStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Analysis not complete. Current status: {analysis.status.value}"
        )

    return {
        "cycle_id": cycle_id,
        "visualizations": analysis.visualizations or {},
    }
