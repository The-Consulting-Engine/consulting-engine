"""Analytics computation routes."""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import pandas as pd
from pathlib import Path
from app.db.database import get_db
from app.db.models import Run, Upload, Mapping, AnalyticsFact, Initiative as DBInitiative
from app.core.vertical_config import VerticalConfigManager
from app.normalization.engine import NormalizationEngine
from app.analytics.engine import AnalyticsEngine
from app.initiatives.selector import InitiativeSelector
from app.llm.client import LLMClient

router = APIRouter()
config_manager = VerticalConfigManager()
normalization_engine = NormalizationEngine()
llm_client = LLMClient()


@router.post("/{run_id}/analyze")
def analyze_run(run_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Run full analysis pipeline."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Check if mappings are confirmed
    mappings = db.query(Mapping).filter(
        Mapping.run_id == run_id,
        Mapping.is_confirmed == True
    ).all()
    
    if not mappings:
        raise HTTPException(status_code=400, detail="No confirmed mappings")
    
    # Update status
    run.status = "analyzing"
    db.commit()
    
    # Run analysis in background
    background_tasks.add_task(run_analysis_pipeline, run_id, db)
    
    return {"message": "Analysis started", "run_id": run_id}


def run_analysis_pipeline(run_id: int, db: Session):
    """Execute the full analysis pipeline."""
    try:
        run = db.query(Run).filter(Run.id == run_id).first()
        
        # Get vertical config
        config = config_manager.get_config(run.vertical_id)
        if not config:
            raise ValueError(f"Invalid vertical: {run.vertical_id}")
        
        # Get uploads and mappings
        uploads = db.query(Upload).filter(Upload.run_id == run_id).all()
        mappings = db.query(Mapping).filter(
            Mapping.run_id == run_id,
            Mapping.is_confirmed == True
        ).all()
        
        # Group mappings by upload
        mappings_by_upload = {}
        for mapping in mappings:
            if mapping.upload_id not in mappings_by_upload:
                mappings_by_upload[mapping.upload_id] = []
            mappings_by_upload[mapping.upload_id].append({
                "canonical_field": mapping.canonical_field,
                "source_columns": mapping.source_columns,
                "transform": mapping.transform
            })
        
        # Normalize each upload
        normalized_data = {}
        available_packs = []
        
        for upload in uploads:
            if upload.id not in mappings_by_upload:
                continue
            
            # Read raw data
            df = pd.read_csv(upload.file_path)
            
            # Normalize
            normalized_df, metadata = normalization_engine.normalize(
                df,
                mappings_by_upload[upload.id],
                upload.pack_type
            )
            
            normalized_data[upload.pack_type] = normalized_df
            available_packs.append(upload.pack_type)
        
        # Compute analytics
        analytics_engine = AnalyticsEngine(config)
        mode_info, analytics_facts = analytics_engine.compute_analytics(normalized_data)
        
        # Save mode info
        run.mode = mode_info['mode']
        run.confidence_score = mode_info['confidence']
        
        # Save analytics facts
        db.query(AnalyticsFact).filter(AnalyticsFact.run_id == run_id).delete()
        
        for fact in analytics_facts:
            db_fact = AnalyticsFact(
                run_id=run_id,
                evidence_key=fact['evidence_key'],
                label=fact['label'],
                value=fact.get('value'),
                value_text=fact.get('value_text'),
                unit=fact.get('unit'),
                period=fact.get('period'),
                source=fact.get('source')
            )
            db.add(db_fact)
        
        # Select and size initiatives
        selector = InitiativeSelector(config, llm_client)
        initiatives = selector.select_and_size(mode_info, analytics_facts, available_packs)
        
        # Save initiatives
        db.query(DBInitiative).filter(DBInitiative.run_id == run_id).delete()
        
        for init in initiatives:
            db_init = DBInitiative(
                run_id=run_id,
                initiative_id=init['initiative_id'],
                title=init['title'],
                category=init['category'],
                description=init.get('description', ''),
                impact_low=init.get('impact_low'),
                impact_mid=init.get('impact_mid'),
                impact_high=init.get('impact_high'),
                impact_unit=init.get('impact_unit'),
                rank=init.get('rank'),
                priority_score=init.get('priority_score'),
                explanation=init.get('explanation'),
                assumptions=init.get('assumptions'),
                data_gaps=init.get('data_gaps')
            )
            db.add(db_init)
        
        # Update status
        run.status = "complete"
        db.commit()
        
    except Exception as e:
        run = db.query(Run).filter(Run.id == run_id).first()
        run.status = "error"
        db.commit()
        raise e


@router.get("/{run_id}/results")
def get_results(run_id: int, db: Session = Depends(get_db)):
    """Get analysis results."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if run.status != "complete":
        return {
            "status": run.status,
            "message": "Analysis not complete"
        }
    
    # Get analytics facts
    facts = db.query(AnalyticsFact).filter(AnalyticsFact.run_id == run_id).all()
    
    # Get initiatives
    initiatives = db.query(DBInitiative).filter(
        DBInitiative.run_id == run_id
    ).order_by(DBInitiative.rank).all()
    
    return {
        "run_id": run_id,
        "mode": run.mode,
        "confidence_score": run.confidence_score,
        "status": run.status,
        "analytics_facts": [
            {
                "evidence_key": f.evidence_key,
                "label": f.label,
                "value": f.value,
                "value_text": f.value_text,
                "unit": f.unit,
                "period": f.period,
                "source": f.source
            }
            for f in facts
        ],
        "initiatives": [
            {
                "initiative_id": i.initiative_id,
                "title": i.title,
                "category": i.category,
                "description": i.description,
                "rank": i.rank,
                "impact_low": i.impact_low,
                "impact_mid": i.impact_mid,
                "impact_high": i.impact_high,
                "impact_unit": i.impact_unit,
                "priority_score": i.priority_score,
                "explanation": i.explanation,
                "assumptions": i.assumptions,
                "data_gaps": i.data_gaps
            }
            for i in initiatives
        ]
    }
