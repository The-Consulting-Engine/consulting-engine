"""Report generation routes."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from app.db.database import get_db
from app.db.models import Run, AnalyticsFact, Initiative as DBInitiative, Report as DBReport
from app.core.config import settings
from app.core.vertical_config import VerticalConfigManager
from app.reports.memo import MemoGenerator
from app.reports.deck import DeckGenerator
from app.llm.client import LLMClient

router = APIRouter()
config_manager = VerticalConfigManager()
llm_client = LLMClient()

# Ensure reports directory exists
Path(settings.REPORTS_DIR).mkdir(parents=True, exist_ok=True)


@router.post("/{run_id}/generate-memo")
def generate_memo(run_id: int, db: Session = Depends(get_db)):
    """Generate Markdown memo."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if run.status != "complete":
        raise HTTPException(status_code=400, detail="Analysis not complete")
    
    # Get data
    facts = db.query(AnalyticsFact).filter(AnalyticsFact.run_id == run_id).all()
    initiatives = db.query(DBInitiative).filter(
        DBInitiative.run_id == run_id
    ).order_by(DBInitiative.rank).all()
    
    # Get vertical config
    config = config_manager.get_config(run.vertical_id)
    
    # Prepare data
    mode_info = {
        "mode": run.mode,
        "confidence": run.confidence_score,
        "reasons": [],
        "months_available": 0  # TODO: Calculate from facts
    }
    
    analytics_facts = [
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
    ]
    
    initiatives_list = [
        {
            "initiative_id": i.initiative_id,
            "title": i.title,
            "category": i.category,
            "description": i.description,
            "rank": i.rank,
            "impact_low": i.impact_low,
            "impact_mid": i.impact_mid,
            "impact_high": i.impact_high,
            "explanation": i.explanation,
            "assumptions": i.assumptions,
            "data_gaps": i.data_gaps
        }
        for i in initiatives
    ]
    
    # Generate memo
    generator = MemoGenerator(llm_client)
    memo_content = generator.generate(
        run.company_name or "Company",
        mode_info,
        analytics_facts,
        initiatives_list,
        config.vertical_name
    )
    
    # Save to file
    file_path = Path(settings.REPORTS_DIR) / f"run_{run_id}_memo.md"
    with open(file_path, 'w') as f:
        f.write(memo_content)
    
    # Save report record
    report = DBReport(
        run_id=run_id,
        report_type="memo",
        file_path=str(file_path)
    )
    db.add(report)
    db.commit()
    
    return {
        "message": "Memo generated",
        "file_path": str(file_path),
        "report_id": report.id
    }


@router.post("/{run_id}/generate-deck")
def generate_deck(run_id: int, db: Session = Depends(get_db)):
    """Generate PowerPoint deck."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if run.status != "complete":
        raise HTTPException(status_code=400, detail="Analysis not complete")
    
    # Get data
    facts = db.query(AnalyticsFact).filter(AnalyticsFact.run_id == run_id).all()
    initiatives = db.query(DBInitiative).filter(
        DBInitiative.run_id == run_id
    ).order_by(DBInitiative.rank).all()
    
    # Get vertical config
    config = config_manager.get_config(run.vertical_id)
    
    # Prepare data
    mode_info = {
        "mode": run.mode,
        "confidence": run.confidence_score,
        "reasons": [],
        "months_available": 0
    }
    
    analytics_facts = [
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
    ]
    
    initiatives_list = [
        {
            "initiative_id": i.initiative_id,
            "title": i.title,
            "category": i.category,
            "description": i.description,
            "rank": i.rank,
            "impact_low": i.impact_low,
            "impact_mid": i.impact_mid,
            "impact_high": i.impact_high,
            "explanation": i.explanation,
            "assumptions": i.assumptions,
            "data_gaps": i.data_gaps
        }
        for i in initiatives
    ]
    
    # Generate deck
    file_path = Path(settings.REPORTS_DIR) / f"run_{run_id}_deck.pptx"
    
    generator = DeckGenerator()
    generator.generate(
        run.company_name or "Company",
        mode_info,
        analytics_facts,
        initiatives_list,
        config.vertical_name,
        str(file_path)
    )
    
    # Save report record
    report = DBReport(
        run_id=run_id,
        report_type="deck",
        file_path=str(file_path)
    )
    db.add(report)
    db.commit()
    
    return {
        "message": "Deck generated",
        "file_path": str(file_path),
        "report_id": report.id
    }


@router.get("/{run_id}/reports")
def list_reports(run_id: int, db: Session = Depends(get_db)):
    """List all reports for a run."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    reports = db.query(DBReport).filter(DBReport.run_id == run_id).all()
    
    return {
        "reports": [
            {
                "report_id": r.id,
                "report_type": r.report_type,
                "file_path": r.file_path,
                "created_at": r.created_at.isoformat() if r.created_at else ""
            }
            for r in reports
        ]
    }


@router.get("/download/{report_id}")
def download_report(report_id: int, db: Session = Depends(get_db)):
    """Download a report file."""
    report = db.query(DBReport).filter(DBReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    file_path = Path(report.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found")
    
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream"
    )
