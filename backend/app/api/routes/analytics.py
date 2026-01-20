"""Analytics computation routes."""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
import pandas as pd
import json
from pathlib import Path
from app.db.database import get_db
from app.db.models import Run, Upload, Mapping, AnalyticsFact, Initiative as DBInitiative, RunContext
from app.core.vertical_config import VerticalConfigManager
from app.normalization.engine import NormalizationEngine
from app.analytics.engine import AnalyticsEngine
from app.analytics.enhanced_engine import EnhancedAnalyticsEngine
from app.analytics.benchmarks import get_benchmarks_for_vertical, get_benchmark_details
from app.initiatives.selector import InitiativeSelector
from app.initiatives.grounded_recommender import GroundedRecommender
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
        
        # Load run context
        run_context_obj = db.query(RunContext).filter(RunContext.run_id == run_id).first()
        run_context = None
        if run_context_obj:
            run_context = {
                "constraints": run_context_obj.constraints or {},
                "operations": run_context_obj.operations or {},
                "marketing": run_context_obj.marketing or {},
                "goals": run_context_obj.goals or {},
                "risk": run_context_obj.risk or {},
                "derived": run_context_obj.derived or {}
            }
        
        # Select and size initiatives
        selector = InitiativeSelector(config, llm_client, run_context)
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
                data_gaps=init.get('data_gaps'),
                specificity_draft=init.get('specificity_draft'),
                lane=init.get('lane', 'playbook')
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
                "lane": i.lane,
                "specificity_draft": i.specificity_draft,
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


# =============================================================================
# V2 GROUNDED ANALYTICS PIPELINE
# =============================================================================

@router.post("/{run_id}/analyze-v2")
def analyze_run_v2(
    run_id: int,
    background_tasks: BackgroundTasks,
    use_llm_explanations: bool = Query(default=True, description="Use LLM for explanation writing"),
    db: Session = Depends(get_db)
):
    """
    Run grounded analysis pipeline (v2).

    This uses the new evidence-based recommender that:
    1. Computes 50+ metrics with full evidence chains
    2. Scores initiatives deterministically (no LLM selection)
    3. Produces gap-based impact estimates
    4. References specific data points (no generic advice)
    """
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
    background_tasks.add_task(
        run_grounded_analysis_pipeline,
        run_id,
        use_llm_explanations
    )

    return {"message": "Grounded analysis started (v2)", "run_id": run_id}


def run_grounded_analysis_pipeline(
    run_id: int,
    use_llm_explanations: bool = True
):
    """Execute the grounded analysis pipeline."""
    from app.db.database import SessionLocal

    db = SessionLocal()

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

        # Load run context
        run_context_obj = db.query(RunContext).filter(RunContext.run_id == run_id).first()
        run_context = None
        if run_context_obj:
            run_context = {
                "constraints": run_context_obj.constraints or {},
                "operations": run_context_obj.operations or {},
                "marketing": run_context_obj.marketing or {},
                "goals": run_context_obj.goals or {},
                "risk": run_context_obj.risk or {},
                "derived": run_context_obj.derived or {}
            }

        # Run grounded recommender
        recommender = GroundedRecommender(
            config,
            llm_client if use_llm_explanations else None
        )

        results = recommender.generate_recommendations(
            normalized_data,
            run_context
        )

        # Save mode info
        mode_info = results['mode_info']
        run.mode = mode_info['mode']
        run.confidence_score = mode_info['confidence']

        # Save analytics facts (from enhanced engine)
        db.query(AnalyticsFact).filter(AnalyticsFact.run_id == run_id).delete()

        analytics_summary = results.get('analytics_summary', {})
        key_metrics = analytics_summary.get('key_metrics', {})

        for metric_id, metric_data in key_metrics.items():
            db_fact = AnalyticsFact(
                run_id=run_id,
                evidence_key=metric_id,
                label=metric_id.replace('_', ' ').title(),
                value=metric_data.get('value'),
                value_text=str(metric_data.get('value')),
                unit=metric_data.get('unit'),
                period="analysis_period",
                source="enhanced_analytics"
            )
            db.add(db_fact)

        # Save recommendations as initiatives
        db.query(DBInitiative).filter(DBInitiative.run_id == run_id).delete()

        for rec in results['recommendations']:
            # Build specificity draft from grounded data
            specificity_draft = {
                "what": rec['recommendation_text'],
                "where": rec['data_specifics'].get('analysis_period', ''),
                "how_much": f"${rec['impact_range']['low']:,.0f} - ${rec['impact_range']['high']:,.0f}",
                "timing": "Based on data analysis",
                "next_steps": [],
                "assumptions": rec['assumptions'],
                "data_needed": rec['data_gaps'],
                "confidence": "HIGH" if rec['confidence'] >= 0.7 else ("MEDIUM" if rec['confidence'] >= 0.5 else "LOW"),
                "specificity_level": "DETAILED" if not rec['is_assumption_based'] else "DIRECTIONAL",
                # V2 additions
                "evidence_chain": rec['evidence_chain'],
                "scoring_breakdown": rec['scoring_breakdown'],
                "data_specifics": rec['data_specifics'],
                "is_assumption_based": rec['is_assumption_based'],
                "sensitivity": rec.get('sensitivity')
            }

            db_init = DBInitiative(
                run_id=run_id,
                initiative_id=rec['initiative_id'],
                title=rec['title'],
                category=rec['category'],
                description=rec['detailed_rationale'],
                impact_low=rec['impact_range']['low'],
                impact_mid=rec['impact_range']['mid'],
                impact_high=rec['impact_range']['high'],
                impact_unit="annual_savings",
                rank=rec['rank'],
                priority_score=rec['priority_score'],
                explanation=rec['recommendation_text'],
                assumptions=rec['assumptions'],
                data_gaps=rec['data_gaps'],
                specificity_draft=specificity_draft,
                lane="grounded_v2"
            )
            db.add(db_init)

        # Store full results as JSON for the results endpoint
        # (We'll add a new field or use a separate table for full results)

        # Update status
        run.status = "complete"
        db.commit()

    except Exception as e:
        run = db.query(Run).filter(Run.id == run_id).first()
        if run:
            run.status = "error"
            db.commit()
        raise e

    finally:
        db.close()


@router.get("/{run_id}/results-v2")
def get_results_v2(run_id: int, db: Session = Depends(get_db)):
    """
    Get grounded analysis results (v2).

    Returns full evidence chains, scoring breakdowns, and data specifics.
    """
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

    # Get benchmarks for this vertical
    benchmarks = get_benchmark_details(run.vertical_id)

    # Build response with full v2 data
    recommendations = []
    for i in initiatives:
        spec = i.specificity_draft or {}

        recommendations.append({
            # Identity
            "rank": i.rank,
            "initiative_id": i.initiative_id,
            "title": i.title,
            "category": i.category,

            # The recommendation
            "recommendation_text": i.explanation,
            "detailed_rationale": i.description,

            # Ranking components (all required per spec)
            "impact_range": {
                "low": i.impact_low,
                "mid": i.impact_mid,
                "high": i.impact_high
            },
            "confidence": round(i.priority_score / 1.0, 2) if i.priority_score else 0.5,  # Approximate
            "effort": spec.get('scoring_breakdown', {}).get('effort_score', 0.5),
            "priority_score": i.priority_score,

            # Evidence chain (full traceability)
            "evidence_chain": spec.get('evidence_chain', []),

            # Assumptions (explicit)
            "assumptions": i.assumptions or [],
            "is_assumption_based": spec.get('is_assumption_based', False),

            # Sensitivity
            "sensitivity": spec.get('sensitivity'),

            # Data specifics (no generic advice)
            "data_specifics": spec.get('data_specifics', {}),

            # What would improve this
            "data_gaps": i.data_gaps or [],

            # Scoring breakdown (transparency)
            "scoring_breakdown": spec.get('scoring_breakdown', {})
        })

    return {
        "run_id": run_id,
        "mode": run.mode,
        "confidence_score": run.confidence_score,
        "status": run.status,
        "pipeline_version": "v2_grounded",

        # Analytics
        "analytics_facts": [
            {
                "evidence_key": f.evidence_key,
                "label": f.label,
                "value": f.value,
                "unit": f.unit,
                "source": f.source
            }
            for f in facts
        ],

        # Grounded recommendations
        "recommendations": recommendations,

        # Benchmarks used (transparency)
        "benchmarks_used": benchmarks
    }
