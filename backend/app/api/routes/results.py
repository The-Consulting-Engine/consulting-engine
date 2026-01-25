from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Cycle, CategoryScore, Initiative, InitiativeKind
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
    
    return {
        "cycle_id": cycle_id,
        "status": cycle.status.value if cycle.status and hasattr(cycle.status, 'value') else str(cycle.status) if cycle.status else "unknown",
        "category_scores": category_scores.scores if category_scores and hasattr(category_scores, 'scores') else [],
        "core_initiatives": core_initiatives if core_initiatives else [],
        "sandbox_initiatives": sandbox_initiatives if sandbox_initiatives else [],
    }
