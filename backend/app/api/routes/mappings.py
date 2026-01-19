"""Mapping confirmation routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.db.database import get_db
from app.db.models import Run, Upload, Mapping

router = APIRouter()


class MappingConfirm(BaseModel):
    canonical_field: str
    source_columns: List[str]
    transform: str
    confidence: float


class MappingBatchConfirm(BaseModel):
    upload_id: int
    mappings: List[MappingConfirm]


@router.post("/{run_id}/confirm")
def confirm_mappings(
    run_id: int,
    batch: MappingBatchConfirm,
    db: Session = Depends(get_db)
):
    """Confirm column mappings for an upload."""
    # Validate run and upload
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    upload = db.query(Upload).filter(
        Upload.id == batch.upload_id,
        Upload.run_id == run_id
    ).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    # Delete existing mappings for this upload
    db.query(Mapping).filter(Mapping.upload_id == batch.upload_id).delete()
    
    # Create new mappings
    for mapping_data in batch.mappings:
        mapping = Mapping(
            run_id=run_id,
            upload_id=batch.upload_id,
            canonical_field=mapping_data.canonical_field,
            source_columns=mapping_data.source_columns,
            transform=mapping_data.transform,
            confidence=mapping_data.confidence,
            is_confirmed=True
        )
        db.add(mapping)
    
    db.commit()
    
    return {"message": "Mappings confirmed", "count": len(batch.mappings)}


@router.get("/{run_id}/mappings")
def get_mappings(run_id: int, db: Session = Depends(get_db)):
    """Get all confirmed mappings for a run."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    mappings = db.query(Mapping).filter(Mapping.run_id == run_id).all()
    
    return {
        "mappings": [
            {
                "mapping_id": m.id,
                "upload_id": m.upload_id,
                "canonical_field": m.canonical_field,
                "source_columns": m.source_columns,
                "transform": m.transform,
                "confidence": m.confidence,
                "is_confirmed": m.is_confirmed
            }
            for m in mappings
        ]
    }
