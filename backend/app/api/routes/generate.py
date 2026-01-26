import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import (
    Cycle, QuestionnaireResponse, CategoryScore, Initiative, CycleStatus, InitiativeKind
)
from app.generation.category_scoring import score_categories, select_top_4_categories
from app.generation.initiative_expansion import expand_core_initiatives, generate_sandbox_initiatives

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/cycles/{cycle_id}/generate")
def generate_cycle(cycle_id: str, db: Session = Depends(get_db)):
    """Generate initiatives for a cycle."""
    import sys
    print("[GENERATE] Started for cycle %s" % cycle_id, file=sys.stderr, flush=True)
    logger.info("=" * 80)
    logger.info("Generate STARTED for cycle %s", cycle_id)
    logger.info("=" * 80)
    try:
        cycle_uuid = uuid.UUID(cycle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid cycle_id format")
    
    cycle = db.query(Cycle).filter(Cycle.id == cycle_uuid).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")
    
    # Check questionnaire is complete
    qr = db.query(QuestionnaireResponse).filter(
        QuestionnaireResponse.cycle_id == cycle_uuid
    ).first()
    
    if not qr:
        raise HTTPException(
            status_code=400,
            detail="Questionnaire responses not found. Complete questionnaire first."
        )
    
    try:
        # Validate we have responses and signals
        if not qr.responses:
            raise HTTPException(status_code=400, detail="Questionnaire responses are empty")
        if not qr.derived_signals:
            raise HTTPException(status_code=400, detail="Derived signals are missing")
        
        # Step 1: Score categories
        print("[GENERATE] Step 1/4: Scoring categories (calling OpenAI)...", file=sys.stderr, flush=True)
        logger.info("Step 1/4: Scoring categories for cycle %s", cycle_id)
        try:
            category_scores = score_categories(
                qr.responses,
                qr.derived_signals,
                cycle.vertical_id
            )
            print("[GENERATE] Step 1/4 complete: %d scores" % (len(category_scores) if category_scores else 0), file=sys.stderr, flush=True)
            logger.info("Step 1/4 complete: Got %d category scores", len(category_scores) if category_scores else 0)
        except Exception as step1_err:
            logger.error("❌ Step 1/4 FAILED: Category scoring error")
            logger.exception(step1_err)
            raise
        
        if not category_scores or len(category_scores) != 10:
            raise ValueError(f"Expected 10 category scores, got {len(category_scores) if category_scores else 0}")
        
        # Save category scores
        db_category_scores = CategoryScore(
            cycle_id=cycle_uuid,
            scores=category_scores
        )
        db.add(db_category_scores)
        
        # Step 2: Select top 4
        print("[GENERATE] Step 2/4: Selecting top 4 categories...", file=sys.stderr, flush=True)
        logger.info("Step 2/4: Selecting top 4 categories for cycle %s", cycle_id)
        top_4_ids = select_top_4_categories(category_scores)
        print("[GENERATE] Step 2/4 complete: %s" % top_4_ids, file=sys.stderr, flush=True)
        logger.info("Step 2/4 complete: Selected categories %s", top_4_ids)
        
        if not top_4_ids or len(top_4_ids) != 4:
            raise ValueError(f"Expected 4 top categories, got {len(top_4_ids) if top_4_ids else 0}")
        
        # Step 3: Expand core initiatives
        print("[GENERATE] Step 3/4: Expanding core initiatives (calling OpenAI)...", file=sys.stderr, flush=True)
        logger.info("Step 3/4: Expanding core initiatives for cycle %s", cycle_id)
        try:
            core_initiatives = expand_core_initiatives(
                qr.responses,
                qr.derived_signals,
                top_4_ids,
                cycle.vertical_id
            )
            print("[GENERATE] Step 3/4 complete: %d initiatives" % (len(core_initiatives) if core_initiatives else 0), file=sys.stderr, flush=True)
            logger.info("Step 3/4 complete: Got %d core initiatives", len(core_initiatives) if core_initiatives else 0)
        except Exception as step3_err:
            logger.error("❌ Step 3/4 FAILED: Core initiative expansion error")
            logger.exception(step3_err)
            raise
        
        if not core_initiatives or len(core_initiatives) != 4:
            raise ValueError(f"Expected 4 core initiatives, got {len(core_initiatives) if core_initiatives else 0}")
        
        # Save core initiatives
        for idx, init in enumerate(core_initiatives):
            if not isinstance(init, dict):
                continue
            db_init = Initiative(
                cycle_id=cycle_uuid,
                kind=InitiativeKind.CORE,
                title=init.get("title", f"Core Initiative {idx + 1}"),
                body=init,
                rank=idx + 1
            )
            db.add(db_init)
        
        # Step 4: Generate sandbox
        print("[GENERATE] Step 4/4: Generating sandbox (calling OpenAI)...", file=sys.stderr, flush=True)
        logger.info("Step 4/4: Generating sandbox initiatives for cycle %s", cycle_id)
        try:
            sandbox_initiatives = generate_sandbox_initiatives(
                qr.responses,
                qr.derived_signals,
                top_4_ids,
                cycle.vertical_id,
            )
            print("[GENERATE] Step 4/4 complete: %d sandbox" % (len(sandbox_initiatives) if sandbox_initiatives else 0), file=sys.stderr, flush=True)
            logger.info("Step 4/4 complete: Got %d sandbox initiatives", len(sandbox_initiatives) if sandbox_initiatives else 0)
        except Exception as step4_err:
            logger.error("❌ Step 4/4 FAILED: Sandbox initiative generation error")
            logger.exception(step4_err)
            raise
        
        if not sandbox_initiatives or len(sandbox_initiatives) != 3:
            raise ValueError(f"Expected 3 sandbox initiatives, got {len(sandbox_initiatives) if sandbox_initiatives else 0}")
        
        # Save sandbox initiatives
        for idx, init in enumerate(sandbox_initiatives):
            if not isinstance(init, dict):
                continue
            db_init = Initiative(
                cycle_id=cycle_uuid,
                kind=InitiativeKind.SANDBOX,
                title=init.get("title", f"Sandbox Experiment {idx + 1}"),
                body=init,
                rank=idx + 1
            )
            db.add(db_init)
        
        # Update cycle status
        cycle.status = CycleStatus.GENERATED
        db.commit()

        # Check if any results look like placeholders (mock was used)
        has_placeholders = (
            any("placeholder" in str(init.get("title", "")).lower() for init in core_initiatives) or
            any("placeholder" in str(init.get("title", "")).lower() for init in sandbox_initiatives)
        )
        
        logger.info("")
        logger.info("=" * 80)
        if has_placeholders:
            logger.error("⚠️  GENERATION COMPLETE but used MOCK/PLACEHOLDER data")
            logger.error("   Possible causes:")
            logger.error("     1. OpenAI API failed (timeout, connection, auth) — look for ❌ OPENAI API ERROR above")
            logger.error("     2. LLM response failed JSON/schema validation — look for ⚠️ JSON validation failed above")
            logger.error("     3. LLM_PROVIDER=mock")
            logger.error("")
            logger.error("   Scroll UP in the logs for [OPENAI] ERROR or 'JSON validation failed'.")
            logger.error("   Placeholder initiatives are clearly marked in the UI.")
        else:
            logger.info("✅ GENERATION COMPLETE - All data from REAL LLM (not mock)")
            logger.info("   All initiatives were successfully generated by OpenAI")
        logger.info("=" * 80)
        logger.info("Generate completed for cycle %s", cycle_id)
        logger.info("=" * 80)
        logger.info("")
        
        return {
            "status": "generated",
            "cycle_id": cycle_id,
            "category_scores_count": len(category_scores),
            "core_initiatives_count": len(core_initiatives),
            "sandbox_initiatives_count": len(sandbox_initiatives)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Generate failed for cycle %s: %s", cycle_id, e)
        db.rollback()
        try:
            cycle.status = CycleStatus.ERROR
            db.commit()
        except Exception:
            db.rollback()
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
