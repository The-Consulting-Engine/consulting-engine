from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.session import get_db
from app.db.models import Cycle, CycleStatus
from datetime import datetime
import uuid

router = APIRouter()


class CycleCreate(BaseModel):
    org_id: str


class CycleResponse(BaseModel):
    id: str
    org_id: str
    vertical_id: str
    status: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.post("/cycles", response_model=CycleResponse)
def create_cycle(cycle: CycleCreate, db: Session = Depends(get_db)):
    try:
        org_uuid = uuid.UUID(cycle.org_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid org_id format")
    
    db_cycle = Cycle(org_id=org_uuid)
    db.add(db_cycle)
    db.commit()
    db.refresh(db_cycle)
    
    # Ensure updated_at is set (fallback to created_at or current time)
    updated_at = db_cycle.updated_at or db_cycle.created_at or datetime.now()
    created_at = db_cycle.created_at or datetime.now()
    
    return CycleResponse(
        id=str(db_cycle.id),
        org_id=str(db_cycle.org_id),
        vertical_id=db_cycle.vertical_id,
        status=db_cycle.status.value,
        created_at=created_at.isoformat(),
        updated_at=updated_at.isoformat()
    )


@router.get("/cycles/{cycle_id}", response_model=CycleResponse)
def get_cycle(cycle_id: str, db: Session = Depends(get_db)):
    try:
        cycle_uuid = uuid.UUID(cycle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid cycle_id format")
    
    cycle = db.query(Cycle).filter(Cycle.id == cycle_uuid).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")
    
    # Ensure updated_at is set (fallback to created_at or current time)
    updated_at = cycle.updated_at or cycle.created_at or datetime.now()
    created_at = cycle.created_at or datetime.now()
    
    return CycleResponse(
        id=str(cycle.id),
        org_id=str(cycle.org_id),
        vertical_id=cycle.vertical_id,
        status=cycle.status.value,
        created_at=created_at.isoformat(),
        updated_at=updated_at.isoformat()
    )
