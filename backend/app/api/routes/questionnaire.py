from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any
from app.db.session import get_db
from app.db.models import Cycle, QuestionnaireResponse, CycleStatus
from app.questionnaire.loader import load_questionnaire
from app.questionnaire.evaluator import evaluate_responses
import uuid

router = APIRouter()


class QuestionnaireResponseModel(BaseModel):
    responses: Dict[str, Any]


@router.get("/cycles/{cycle_id}/questionnaire")
def get_questionnaire(cycle_id: str, db: Session = Depends(get_db)):
    """Get questionnaire JSON for a cycle."""
    try:
        cycle_uuid = uuid.UUID(cycle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid cycle_id format")
    
    cycle = db.query(Cycle).filter(Cycle.id == cycle_uuid).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")
    
    questionnaire = load_questionnaire(cycle.vertical_id)
    return questionnaire


@router.post("/cycles/{cycle_id}/questionnaire")
def save_questionnaire(
    cycle_id: str,
    data: QuestionnaireResponseModel,
    db: Session = Depends(get_db)
):
    """Save questionnaire responses and compute derived signals."""
    try:
        cycle_uuid = uuid.UUID(cycle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid cycle_id format")
    
    cycle = db.query(Cycle).filter(Cycle.id == cycle_uuid).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")
    
    if not data.responses:
        raise HTTPException(status_code=400, detail="Responses cannot be empty")
    
    try:
        derived_signals = evaluate_responses(data.responses, cycle.vertical_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate responses: {str(e)}")
    
    try:
        existing = db.query(QuestionnaireResponse).filter(
            QuestionnaireResponse.cycle_id == cycle_uuid
        ).first()
        
        if existing:
            existing.responses = data.responses
            existing.derived_signals = derived_signals
        else:
            existing = QuestionnaireResponse(
                cycle_id=cycle_uuid,
                responses=data.responses,
                derived_signals=derived_signals
            )
            db.add(existing)
        
        cycle.status = CycleStatus.QUESTIONNAIRE_COMPLETE
        db.commit()
        db.refresh(existing)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save: {str(e)}")
    
    return {
        "cycle_id": cycle_id,
        "status": "saved",
        "derived_signals": derived_signals
    }
