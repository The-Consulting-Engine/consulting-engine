"""
Competitor analysis API routes.

Provides endpoints for running competitor analysis and retrieving results.
Integrates with questionnaire data for restaurant info and owner-provided menus.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import (
    Cycle, CompetitorAnalysis, CompetitorAnalysisStatus,
    QuestionnaireResponse, OwnerMenuItem
)

router = APIRouter()
logger = logging.getLogger(__name__)


# =============================================================================
# CUISINE WEIGHTS
# =============================================================================

# How much to weight competitors of different cuisines when target is X
# 1.0 = same cuisine, lower = less relevant
CUISINE_WEIGHTS = {
    "Thai": {
        "Thai": 1.0, "Vietnamese": 0.7, "Chinese": 0.6, "Asian Fusion": 0.7,
        "Japanese": 0.5, "Korean": 0.5, "Indian": 0.4, "default": 0.3
    },
    "Chinese": {
        "Chinese": 1.0, "Asian Fusion": 0.7, "Japanese": 0.6, "Korean": 0.6,
        "Thai": 0.6, "Vietnamese": 0.6, "default": 0.3
    },
    "Japanese": {
        "Japanese": 1.0, "Korean": 0.7, "Asian Fusion": 0.7, "Chinese": 0.5,
        "default": 0.3
    },
    "Italian": {
        "Italian": 1.0, "Mediterranean": 0.7, "French": 0.6, "Greek": 0.5,
        "American": 0.4, "default": 0.3
    },
    "Mexican": {
        "Mexican": 1.0, "American": 0.5, "default": 0.3
    },
    "American": {
        "American": 1.0, "default": 0.5  # American competes with everyone
    },
    "default": {
        "default": 0.5  # Fallback: moderate weight for all
    }
}


def get_cuisine_weight(target_cuisine: str, competitor_cuisine: str) -> float:
    """Get the weight for a competitor based on cuisine similarity."""
    cuisine_map = CUISINE_WEIGHTS.get(target_cuisine, CUISINE_WEIGHTS["default"])
    return cuisine_map.get(competitor_cuisine, cuisine_map.get("default", 0.3))


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ManualCompetitor(BaseModel):
    """A manually specified competitor."""
    name: str
    address: str


class EnrichRequest(BaseModel):
    """Request body for competitor analysis enrichment."""
    # These can override questionnaire data if provided
    restaurant_name: Optional[str] = Field(None, description="Override restaurant name from questionnaire")
    address: Optional[str] = Field(None, description="Override address from questionnaire")
    search_radius_meters: int = Field(default=2000, ge=500, le=10000)
    max_competitors: int = Field(default=8, ge=1, le=20)


class EnrichResponse(BaseModel):
    """Response from enrichment endpoint."""
    cycle_id: str
    status: str
    message: str
    competitor_analysis_id: Optional[str] = None
    restaurant_name: Optional[str] = None
    cuisine_type: Optional[str] = None
    menu_source: Optional[str] = None  # "owner_provided" or "scraped"


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
    cuisine_type: Optional[str]
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


def _extract_restaurant_info(responses: dict) -> dict:
    """Extract restaurant info from questionnaire responses."""
    return {
        "restaurant_name": responses.get("R0_1_restaurant_name"),
        "address": responses.get("R0_2_address"),
        "cuisine_type": responses.get("R0_3_cuisine_type"),
        "service_type": responses.get("R0_4_service_type"),
        "price_tier": responses.get("R0_5_price_tier"),
        "menu_input_method": responses.get("R0_6_menu_input_method"),
        "manual_competitors": [
            {"name": responses.get("R0_7_competitor_1_name"), "address": responses.get("R0_8_competitor_1_address")},
            {"name": responses.get("R0_9_competitor_2_name"), "address": responses.get("R0_10_competitor_2_address")},
            {"name": responses.get("R0_11_competitor_3_name"), "address": responses.get("R0_12_competitor_3_address")},
        ]
    }


def _get_owner_menu_as_dataframe(db_url: str, cycle_id: uuid.UUID):
    """Fetch owner-provided menu items and convert to DataFrame format."""
    import pandas as pd
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        items = db.query(OwnerMenuItem).filter(OwnerMenuItem.cycle_id == cycle_id).all()

        if not items:
            return None

        # Convert to DataFrame matching the expected format
        data = []
        for item in items:
            # Parse price to numeric
            price_str = item.price.replace("$", "").replace(",", "").strip()
            try:
                price_numeric = float(price_str)
            except ValueError:
                price_numeric = None

            data.append({
                "restaurant_id": "target",
                "item_name": item.item_name,
                "item_name_clean": item.item_name.lower().strip(),
                "category": item.category or "Uncategorized",
                "category_normalized": (item.category or "mains").lower(),
                "description": item.description or "",
                "description_clean": (item.description or "").lower(),
                "price_raw": item.price,
                "price_numeric": price_numeric,
                "source": "owner_provided",
                "is_available": True,
            })

        return pd.DataFrame(data)

    finally:
        db.close()


def _run_competitor_analysis(
    analysis_id: uuid.UUID,
    cycle_id: uuid.UUID,
    restaurant_name: str,
    address: str,
    cuisine_type: Optional[str],
    service_type: Optional[str],
    manual_competitors: list[dict],
    use_owner_menu: bool,
    search_radius_meters: int,
    max_competitors: int,
    db_url: str,
):
    """
    Background task to run the competitor analysis pipeline.

    This runs synchronously in a background thread so the API can return immediately.
    Uses asyncio.run() internally to execute the async pipeline.

    Args:
        analysis_id: The CompetitorAnalysis record ID
        cycle_id: The Cycle ID (for fetching owner menu)
        restaurant_name: Target restaurant name
        address: Target restaurant address
        cuisine_type: e.g., "Thai", "Italian" - used for weighting
        service_type: e.g., "Casual Sit-down", "Fast Casual"
        manual_competitors: List of {"name": str, "address": str} dicts
        use_owner_menu: If True, use owner-provided menu instead of scraping
        search_radius_meters: Radius for competitor search
        max_competitors: Max competitors to analyze
        db_url: Database connection URL
    """
    import asyncio
    import pandas as pd
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
        logger.info(f"  Cuisine: {cuisine_type}, Service: {service_type}")
        logger.info(f"  Manual competitors: {len([c for c in manual_competitors if c.get('name')])}")
        logger.info(f"  Use owner menu: {use_owner_menu}")

        # Fetch owner menu if requested
        owner_menu_df = None
        if use_owner_menu:
            owner_menu_df = _get_owner_menu_as_dataframe(db_url, cycle_id)
            if owner_menu_df is not None:
                logger.info(f"  Owner menu: {len(owner_menu_df)} items")
            else:
                logger.warning("  Owner menu requested but no items found - will scrape")

        # Filter valid manual competitors
        valid_manual_competitors = [
            c for c in manual_competitors
            if c.get("name") and c.get("address")
        ]

        # Import and run the pipeline
        from app.competitor_analysis.pipeline import (
            CompetitorAnalysisPipeline,
            PipelineConfig,
        )

        config = PipelineConfig(
            search_radius_meters=search_radius_meters,
            max_competitors=max_competitors,
            cuisine_override=[cuisine_type] if cuisine_type else None,
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

    Extracts restaurant info from questionnaire responses (Section R0).
    Request body can optionally override restaurant_name and address.

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

    # Get questionnaire responses to extract restaurant info
    qr = db.query(QuestionnaireResponse).filter(
        QuestionnaireResponse.cycle_id == cycle_uuid
    ).first()

    if not qr or not qr.responses:
        raise HTTPException(
            status_code=400,
            detail="Questionnaire not completed. Please complete the questionnaire first."
        )

    # Extract restaurant info from questionnaire
    restaurant_info = _extract_restaurant_info(qr.responses)

    # Use questionnaire data, with optional overrides from request
    restaurant_name = request.restaurant_name or restaurant_info.get("restaurant_name")
    address = request.address or restaurant_info.get("address")
    cuisine_type = restaurant_info.get("cuisine_type")
    service_type = restaurant_info.get("service_type")
    menu_input_method = restaurant_info.get("menu_input_method")
    manual_competitors = restaurant_info.get("manual_competitors", [])

    # Validate required fields
    if not restaurant_name:
        raise HTTPException(
            status_code=400,
            detail="Restaurant name not found. Please complete Section R0 of the questionnaire."
        )
    if not address:
        raise HTTPException(
            status_code=400,
            detail="Address not found. Please complete Section R0 of the questionnaire."
        )

    # Determine if we should use owner-provided menu
    use_owner_menu = menu_input_method in ["I'll upload a CSV file", "I'll enter items manually"]

    # Check if owner menu exists (if they said they'd provide it)
    if use_owner_menu:
        menu_count = db.query(OwnerMenuItem).filter(
            OwnerMenuItem.cycle_id == cycle_uuid
        ).count()
        if menu_count == 0:
            # They haven't uploaded yet - we'll fall back to scraping
            logger.warning(f"Owner menu expected but not found for cycle {cycle_id}")
            use_owner_menu = False

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
                restaurant_name=restaurant_name,
                cuisine_type=cuisine_type,
            )
        else:
            # Reset and re-run
            existing.status = CompetitorAnalysisStatus.PENDING
            existing.restaurant_name = restaurant_name
            existing.address = address
            existing.search_radius_meters = request.search_radius_meters
            existing.max_competitors = request.max_competitors
            existing.error_message = None
            db.commit()
            analysis = existing
    else:
        # Create new analysis record
        analysis = CompetitorAnalysis(
            cycle_id=cycle_uuid,
            restaurant_name=restaurant_name,
            address=address,
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

    # Start background task with all the extracted info
    background_tasks.add_task(
        _run_competitor_analysis,
        analysis.id,
        cycle_uuid,
        restaurant_name,
        address,
        cuisine_type,
        service_type,
        manual_competitors,
        use_owner_menu,
        request.search_radius_meters,
        request.max_competitors,
        db_url,
    )

    menu_source = "owner_provided" if use_owner_menu else "will_scrape"

    return EnrichResponse(
        cycle_id=cycle_id,
        status="started",
        message="Competitor analysis started. Poll GET /cycles/{cycle_id}/competitors for results.",
        competitor_analysis_id=str(analysis.id),
        restaurant_name=restaurant_name,
        cuisine_type=cuisine_type,
        menu_source=menu_source,
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

    # Get cuisine_type from questionnaire
    cuisine_type = None
    qr = db.query(QuestionnaireResponse).filter(
        QuestionnaireResponse.cycle_id == cycle_uuid
    ).first()
    if qr and qr.responses:
        cuisine_type = qr.responses.get("R0_3_cuisine_type")

    return CompetitorAnalysisResponse(
        cycle_id=cycle_id,
        status=analysis.status.value if hasattr(analysis.status, 'value') else str(analysis.status),
        restaurant_name=analysis.restaurant_name,
        address=analysis.address,
        cuisine_type=cuisine_type,
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
