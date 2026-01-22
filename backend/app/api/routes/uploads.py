"""File upload and profiling routes."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from pathlib import Path
import shutil
from app.db.database import get_db
from app.db.models import Run, Upload
from app.core.config import settings
from app.core.vertical_config import VerticalConfigManager
from app.ingestion.profiler import ColumnProfiler
from app.ingestion.mapper import ColumnMapper
from app.llm.client import LLMClient

router = APIRouter()
config_manager = VerticalConfigManager()
profiler = ColumnProfiler()
llm_client = LLMClient()
mapper = ColumnMapper(llm_client)

# Ensure upload directory exists
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


@router.post("/{run_id}/upload")
def upload_file(
    run_id: int,
    pack_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and profile a data file."""
    # Validate run
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Validate pack type
    valid_pack_types = ["PNL", "REVENUE", "LABOR"]
    if pack_type not in valid_pack_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid pack_type: {pack_type}. Must be one of: {', '.join(valid_pack_types)}"
        )
    
    # Save file
    file_path = Path(settings.UPLOAD_DIR) / f"run_{run_id}_{pack_type}_{file.filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Profile columns
    try:
        profile = profiler.profile_file(str(file_path))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to profile file: {str(e)}")
    
    # Create upload record
    upload = Upload(
        run_id=run_id,
        filename=file.filename,
        pack_type=pack_type,
        file_path=str(file_path),
        column_profile=profile,
        row_count=profile["row_count"]
    )
    
    db.add(upload)
    
    # Update run status
    run.status = "mapping"
    
    db.commit()
    db.refresh(upload)
    
    return {
        "upload_id": upload.id,
        "filename": upload.filename,
        "pack_type": upload.pack_type,
        "row_count": upload.row_count,
        "column_profile": upload.column_profile
    }


@router.get("/{run_id}/uploads")
def list_uploads(run_id: int, db: Session = Depends(get_db)):
    """List uploads for a run."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    uploads = db.query(Upload).filter(Upload.run_id == run_id).all()
    
    return {
        "uploads": [
            {
                "upload_id": u.id,
                "filename": u.filename,
                "pack_type": u.pack_type,
                "row_count": u.row_count,
                "column_profile": u.column_profile
            }
            for u in uploads
        ]
    }


@router.post("/{run_id}/uploads/{upload_id}/suggest-mappings")
def suggest_mappings(run_id: int, upload_id: int, db: Session = Depends(get_db)):
    """Suggest column mappings using LLM."""
    # Get upload
    upload = db.query(Upload).filter(
        Upload.id == upload_id,
        Upload.run_id == run_id
    ).first()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    # Get run
    run = db.query(Run).filter(Run.id == run_id).first()
    
    # Get vertical config
    data_pack = config_manager.get_data_pack(run.vertical_id, upload.pack_type)
    if not data_pack:
        raise HTTPException(status_code=400, detail=f"No data pack definition for {upload.pack_type}")
    
    # Suggest mappings
    try:
        suggested_mappings = mapper.suggest_mappings(
            upload.column_profile,
            data_pack,
            upload.pack_type
        )
        
        # Validate mappings
        if not suggested_mappings:
            # Fallback to heuristic if LLM fails
            from app.ingestion.mapper import ColumnMapper
            fallback_mapper = ColumnMapper(llm_client)
            suggested_mappings = fallback_mapper._heuristic_mappings(
                upload.column_profile,
                data_pack
            )
        
        # Ensure at least required fields are mapped
        required_fields = [f.name for f in data_pack.fields if f.required]
        mapped_fields = [m.get('canonical_field') for m in suggested_mappings]
        missing_required = [f for f in required_fields if f not in mapped_fields]
        
        if missing_required:
            # Add warnings for missing required fields
            for field_name in missing_required:
                suggested_mappings.append({
                    "canonical_field": field_name,
                    "source_columns": [],
                    "transform": "none",
                    "confidence": 0.0,
                    "reasoning": f"Required field '{field_name}' not found in source columns"
                })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Try heuristic fallback
        try:
            from app.ingestion.mapper import ColumnMapper
            fallback_mapper = ColumnMapper(llm_client)
            suggested_mappings = fallback_mapper._heuristic_mappings(
                upload.column_profile,
                data_pack
            )
        except Exception as e2:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to suggest mappings: {str(e)}. Fallback also failed: {str(e2)}"
            )
    
    return {
        "upload_id": upload_id,
        "pack_type": upload.pack_type,
        "suggested_mappings": suggested_mappings,
        "warnings": {
            "missing_required": [m for m in suggested_mappings if m.get('confidence', 1) == 0.0]
        } if any(m.get('confidence', 1) == 0.0 for m in suggested_mappings) else None
    }
