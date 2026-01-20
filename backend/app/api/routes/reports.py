"""Report generation routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from app.db.database import get_db
from app.db.models import Run, AnalyticsFact, Initiative as DBInitiative, Report as DBReport
from app.core.config import settings
from app.core.vertical_config import VerticalConfigManager
from app.reports.memo import MemoGenerator
from app.reports.deck import DeckGenerator
from app.reports.deck_v2 import EnhancedDeckGenerator
from app.llm.client import LLMClient

router = APIRouter()
config_manager = VerticalConfigManager()
llm_client = LLMClient()


def _calculate_months_available(analytics_facts: list) -> int:
    """Calculate months of data from analytics facts."""
    # Look for month-related facts or count unique periods
    for fact in analytics_facts:
        if fact.get('evidence_key') == 'months_analyzed':
            return int(fact.get('value', 0))

    # Count unique periods
    periods = set()
    for fact in analytics_facts:
        period = fact.get('period')
        if period:
            periods.add(period)

    return len(periods) if periods else 3  # Default to 3 if unknown

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
def generate_deck(
    run_id: int,
    enhanced: bool = Query(default=True, description="Use enhanced deck with Show Your Work"),
    db: Session = Depends(get_db)
):
    """
    Generate PowerPoint deck.

    Args:
        run_id: The run ID
        enhanced: If True, use the enhanced deck generator with "Show Your Work" slides
    """
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

    # Build initiative map from playbook for sizing methods
    playbook_initiatives = {init.id: init for init in config.initiatives}

    # Prepare analytics facts
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

    # Calculate months available
    months_available = _calculate_months_available(analytics_facts)

    # Prepare mode info
    mode_info = {
        "mode": run.mode or "DIRECTIONAL_MODE",
        "confidence": run.confidence_score or 0.5,
        "reasons": [],
        "months_available": months_available
    }

    # Prepare initiatives with full data including specificity_draft and sizing info
    initiatives_list = []
    for i in initiatives:
        init_data = {
            "initiative_id": i.initiative_id,
            "title": i.title,
            "category": i.category,
            "description": i.description,
            "rank": i.rank,
            "impact_low": i.impact_low,
            "impact_mid": i.impact_mid,
            "impact_high": i.impact_high,
            "impact_unit": i.impact_unit,
            "explanation": i.explanation,
            "assumptions": i.assumptions or [],
            "data_gaps": i.data_gaps or [],
            "specificity_draft": i.specificity_draft or {},
            "priority_score": i.priority_score
        }

        # Add sizing method info from playbook if available
        playbook_init = playbook_initiatives.get(i.initiative_id)
        if playbook_init:
            init_data["sizing_method"] = playbook_init.sizing_method
            init_data["sizing_params"] = playbook_init.sizing_params
        else:
            # Default for sandbox initiatives
            init_data["sizing_method"] = "fixed_value"
            init_data["sizing_params"] = {"low": 5000, "mid": 15000, "high": 30000}

        initiatives_list.append(init_data)

    # Generate deck
    suffix = "_enhanced" if enhanced else ""
    file_path = Path(settings.REPORTS_DIR) / f"run_{run_id}_deck{suffix}.pptx"

    if enhanced:
        generator = EnhancedDeckGenerator()
    else:
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
        report_type="deck_enhanced" if enhanced else "deck",
        file_path=str(file_path)
    )
    db.add(report)
    db.commit()

    return {
        "message": "Deck generated",
        "file_path": str(file_path),
        "report_id": report.id,
        "enhanced": enhanced
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
