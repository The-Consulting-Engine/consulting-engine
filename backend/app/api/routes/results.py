from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import (
    Cycle, CategoryScore, Initiative, InitiativeKind,
    CompetitorAnalysis, CompetitorAnalysisStatus
)
import uuid

router = APIRouter()


@router.get("/cycles/{cycle_id}/results")
def get_results(cycle_id: str, db: Session = Depends(get_db)):
    """Get generation results for a cycle."""
    try:
        cycle_uuid = uuid.UUID(cycle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid cycle_id format")
    
    cycle = db.query(Cycle).filter(Cycle.id == cycle_uuid).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")
    
    # Get category scores
    category_scores = db.query(CategoryScore).filter(
        CategoryScore.cycle_id == cycle_uuid
    ).first()
    
    # Get initiatives
    initiatives = db.query(Initiative).filter(
        Initiative.cycle_id == cycle_uuid
    ).order_by(Initiative.rank).all()
    
    core_initiatives = [
        {
            "id": str(init.id),
            "title": init.title or f"Core Initiative {init.rank or idx}",
            "body": init.body if isinstance(init.body, dict) else {},
            "rank": init.rank or idx
        }
        for idx, init in enumerate(initiatives, 1)
        if init.kind == InitiativeKind.CORE
    ]
    
    sandbox_initiatives = [
        {
            "id": str(init.id),
            "title": init.title or f"Sandbox Experiment {init.rank or idx}",
            "body": init.body if isinstance(init.body, dict) else {},
            "rank": init.rank or idx
        }
        for idx, init in enumerate(initiatives, 1)
        if init.kind == InitiativeKind.SANDBOX
    ]

    # Check for competitor analysis
    competitor_analysis = db.query(CompetitorAnalysis).filter(
        CompetitorAnalysis.cycle_id == cycle_uuid
    ).first()

    competitor_context = None
    if competitor_analysis and competitor_analysis.status == CompetitorAnalysisStatus.COMPLETED:
        competitor_context = {
            "status": "completed",
            "competitor_count": competitor_analysis.competitor_count,
            "positioning_summary": competitor_analysis.positioning_summary,
            "positioning": competitor_analysis.positioning,
            "premium_validation": competitor_analysis.premium_validation,
            "competitive_gaps": competitor_analysis.competitive_gaps,
            "strategic_initiatives": competitor_analysis.strategic_initiatives,
            "analyzed_at": competitor_analysis.analyzed_at.isoformat() if competitor_analysis.analyzed_at else None,
        }
    elif competitor_analysis:
        competitor_context = {
            "status": competitor_analysis.status.value if hasattr(competitor_analysis.status, 'value') else str(competitor_analysis.status),
            "error_message": competitor_analysis.error_message,
        }

    return {
        "cycle_id": cycle_id,
        "status": cycle.status.value if cycle.status and hasattr(cycle.status, 'value') else str(cycle.status) if cycle.status else "unknown",
        "category_scores": category_scores.scores if category_scores and hasattr(category_scores, 'scores') else [],
        "core_initiatives": core_initiatives if core_initiatives else [],
        "sandbox_initiatives": sandbox_initiatives if sandbox_initiatives else [],
        "competitor_context": competitor_context,
    }
