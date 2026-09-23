"""
FastAPI Routes for NagarSetu Held-Out Test Set Formal Evaluation.
Provides endpoints to run benchmarks, retrieve scorecards, inspect confusion matrices,
and audit misclassifications.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.evaluation import (
    EvaluationRunRequest,
    EvaluationResultResponse,
    EvaluationHistoryResponse
)
from app.services.evaluation.evaluation_service import EvaluationService

router = APIRouter(prefix="/eval", tags=["Model Evaluation & Benchmarks"])


def get_evaluation_service() -> EvaluationService:
    return EvaluationService()


@router.post("/run", response_model=EvaluationResultResponse)
@router.post("/benchmark", response_model=EvaluationResultResponse)
def run_evaluation_benchmark(
    req: EvaluationRunRequest = EvaluationRunRequest(),
    db: Session = Depends(get_db),
    eval_service: EvaluationService = Depends(get_evaluation_service)
):
    """
    Executes formal benchmark evaluation against a held-out labelled test set.
    Computes department routing, category, urgency, locality accuracies, and duplicate reduction.
    Never modifies raw complaint tables.
    """
    try:
        return eval_service.run_evaluation(db, req)
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation benchmark run failed: {str(e)}")


@router.get("/latest", response_model=EvaluationResultResponse)
def get_latest_evaluation_result(
    db: Session = Depends(get_db),
    eval_service: EvaluationService = Depends(get_evaluation_service)
):
    """
    Retrieves the most recent held-out evaluation benchmark results.
    """
    latest = eval_service.get_latest_evaluation(db)
    if not latest:
        raise HTTPException(status_code=404, detail="No evaluation benchmark has been executed yet.")
    return latest


@router.get("/history", response_model=EvaluationHistoryResponse)
def get_evaluation_history(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    eval_service: EvaluationService = Depends(get_evaluation_service)
):
    """
    Retrieves chronological history of evaluation benchmark runs.
    """
    return eval_service.get_evaluation_history(db, limit=limit)
