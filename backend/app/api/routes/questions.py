"""Question and response management routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel
from app.db.database import get_db
from app.db.models import Run, QuestionResponse, RunContext
from app.questions.processor import QuestionProcessor

router = APIRouter()


class QuestionResponseData(BaseModel):
    question_id: str
    response_value: Any  # Can be string, list, etc.


class QuestionResponseBatch(BaseModel):
    responses: List[QuestionResponseData]


@router.get("/{run_id}/questions")
def get_questions(run_id: int, db: Session = Depends(get_db)):
    """Get intake questions for a run's vertical."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    processor = QuestionProcessor(run.vertical_id)
    questions = processor.get_questions()
    default_responses = processor.get_default_responses()
    
    return {
        "questions": questions,
        "default_responses": default_responses
    }


@router.post("/{run_id}/responses")
def save_responses(
    run_id: int,
    batch: QuestionResponseBatch,
    db: Session = Depends(get_db)
):
    """Save question responses and derive context."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    processor = QuestionProcessor(run.vertical_id)
    
    # Validate responses
    validation = processor.validate_responses([r.dict() for r in batch.responses])
    if not validation["valid"]:
        raise HTTPException(
            status_code=400,
            detail=f"Validation failed: {', '.join(validation['errors'])}"
        )
    
    # Delete existing responses
    db.query(QuestionResponse).filter(QuestionResponse.run_id == run_id).delete()
    
    # Create question map for section lookup
    questions = processor.get_questions()
    question_map = {q["question_id"]: q for q in questions}
    
    # Save new responses
    for response in batch.responses:
        question = question_map.get(response.question_id)
        section = question.get("section") if question else None
        
        db_response = QuestionResponse(
            run_id=run_id,
            question_id=response.question_id,
            section=section,
            response_value=response.response_value
        )
        db.add(db_response)
    
    # Derive context
    context_data = processor.derive_context([r.dict() for r in batch.responses])
    
    # Delete existing context
    db.query(RunContext).filter(RunContext.run_id == run_id).delete()
    
    # Save new context
    run_context = RunContext(
        run_id=run_id,
        constraints=context_data["constraints"],
        operations=context_data["operations"],
        marketing=context_data["marketing"],
        goals=context_data["goals"],
        risk=context_data["risk"],
        derived=context_data["derived"]
    )
    db.add(run_context)
    
    db.commit()
    
    return {
        "message": "Responses saved successfully",
        "context": context_data
    }


@router.get("/{run_id}/responses")
def get_responses(run_id: int, db: Session = Depends(get_db)):
    """Get saved responses for a run."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    responses = db.query(QuestionResponse).filter(QuestionResponse.run_id == run_id).all()
    
    return {
        "responses": [
            {
                "question_id": r.question_id,
                "section": r.section,
                "response_value": r.response_value
            }
            for r in responses
        ]
    }


@router.get("/{run_id}/context")
def get_context(run_id: int, db: Session = Depends(get_db)):
    """Get derived context for a run."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    context = db.query(RunContext).filter(RunContext.run_id == run_id).first()
    
    if not context:
        return {"context": None, "message": "No context available - questions not answered yet"}
    
    return {
        "context": {
            "constraints": context.constraints,
            "operations": context.operations,
            "marketing": context.marketing,
            "goals": context.goals,
            "risk": context.risk,
            "derived": context.derived
        }
    }
