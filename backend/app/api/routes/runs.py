"""Run management routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.db.database import get_db
from app.db.models import Run
from app.core.vertical_config import VerticalConfigManager

router = APIRouter()
config_manager = VerticalConfigManager()


class RunCreate(BaseModel):
    vertical_id: str = "restaurant_v1"
    company_name: Optional[str] = None
    notes: Optional[str] = None


class RunResponse(BaseModel):
    id: int
    vertical_id: str
    company_name: Optional[str]
    notes: Optional[str]
    mode: Optional[str]
    confidence_score: Optional[float]
    status: str
    created_at: str
    
    class Config:
        from_attributes = True


@router.post("/", response_model=RunResponse)
def create_run(run_data: RunCreate, db: Session = Depends(get_db)):
    """Create a new diagnostic run."""
    # Validate vertical
    if run_data.vertical_id not in config_manager.list_verticals():
        raise HTTPException(status_code=400, detail=f"Invalid vertical_id: {run_data.vertical_id}")
    
    run = Run(
        vertical_id=run_data.vertical_id,
        company_name=run_data.company_name,
        notes=run_data.notes,
        status="created"
    )
    
    db.add(run)
    db.commit()
    db.refresh(run)
    
    return RunResponse(
        id=run.id,
        vertical_id=run.vertical_id,
        company_name=run.company_name,
        notes=run.notes,
        mode=run.mode,
        confidence_score=run.confidence_score,
        status=run.status,
        created_at=run.created_at.isoformat() if run.created_at else ""
    )


@router.get("/", response_model=List[RunResponse])
def list_runs(db: Session = Depends(get_db)):
    """List all runs."""
    runs = db.query(Run).order_by(Run.created_at.desc()).all()
    
    return [
        RunResponse(
            id=run.id,
            vertical_id=run.vertical_id,
            company_name=run.company_name,
            notes=run.notes,
            mode=run.mode,
            confidence_score=run.confidence_score,
            status=run.status,
            created_at=run.created_at.isoformat() if run.created_at else ""
        )
        for run in runs
    ]


@router.get("/{run_id}", response_model=RunResponse)
def get_run(run_id: int, db: Session = Depends(get_db)):
    """Get run details."""
    run = db.query(Run).filter(Run.id == run_id).first()
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return RunResponse(
        id=run.id,
        vertical_id=run.vertical_id,
        company_name=run.company_name,
        notes=run.notes,
        mode=run.mode,
        confidence_score=run.confidence_score,
        status=run.status,
        created_at=run.created_at.isoformat() if run.created_at else ""
    )


@router.delete("/{run_id}")
def delete_run(run_id: int, db: Session = Depends(get_db)):
    """Delete a run and all associated data."""
    run = db.query(Run).filter(Run.id == run_id).first()
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    db.delete(run)
    db.commit()
    
    return {"message": "Run deleted successfully"}


@router.get("/verticals/list")
def list_verticals():
    """List available verticals."""
    verticals = []
    for vertical_id in config_manager.list_verticals():
        config = config_manager.get_config(vertical_id)
        verticals.append({
            "vertical_id": vertical_id,
            "vertical_name": config.vertical_name
        })
    
    return {"verticals": verticals}
