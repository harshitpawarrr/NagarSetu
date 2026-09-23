"""
FastAPI Routes for NagarSetu Analytics, Weekly Digest, and Emerging Alerts.
Provides reporting endpoints for municipal zone officers and triage supervisors.
"""

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.analytics import (
    WeeklyDigestResponse,
    DepartmentWeeklySummary,
    LocalityRepeatResponse,
    EmergingAlertsResponse
)
from app.schemas.cluster import ClusterListResponse
from app.services.analytics.weekly_digest_service import WeeklyDigestService
from app.services.analytics.repeat_locality_service import RepeatLocalityService
from app.services.analytics.emerging_alerts_service import EmergingAlertsService
from app.services.clustering.cluster_service import ClusterService

router = APIRouter(prefix="/analytics", tags=["Analytics & Weekly Digests"])


def get_digest_service() -> WeeklyDigestService:
    return WeeklyDigestService()


def get_repeat_service() -> RepeatLocalityService:
    return RepeatLocalityService()


def get_alerts_service() -> EmergingAlertsService:
    return EmergingAlertsService()


def get_cluster_service() -> ClusterService:
    return ClusterService()


@router.get("/weekly-digest", response_model=WeeklyDigestResponse)
def get_weekly_digest(
    start_date: Optional[date] = Query(None, description="Start date of digest period (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date of digest period (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    digest_service: WeeklyDigestService = Depends(get_digest_service)
):
    """
    Computes or retrieves weekly accountability digest across all municipal departments.
    Calculates median resolution time strictly from verified database records.
    """
    try:
        return digest_service.generate_digest(db, start_date=start_date, end_date=end_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate weekly digest: {str(e)}")


@router.get("/departments/{department_id}", response_model=DepartmentWeeklySummary)
def get_department_analytics(
    department_id: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    digest_service: WeeklyDigestService = Depends(get_digest_service)
):
    """
    Retrieves workload and performance summary for a specific municipal department.
    """
    digest = digest_service.generate_digest(db, start_date=start_date, end_date=end_date, persist=False)
    for dept_sum in digest.departments:
        if dept_sum.department == department_id:
            return dept_sum
    raise HTTPException(status_code=404, detail=f"Department '{department_id}' not found in current digest.")


@router.get("/localities", response_model=LocalityRepeatResponse)
@router.get("/repeat-localities", response_model=LocalityRepeatResponse)
def get_locality_repeat_analytics(
    department: Optional[str] = Query(None, description="Filter by department"),
    ward: Optional[str] = Query(None, description="Filter by ward"),
    locality: Optional[str] = Query(None, description="Filter by locality name substring"),
    days_back: Optional[int] = Query(None, description="Filter by past N days"),
    db: Session = Depends(get_db),
    repeat_service: RepeatLocalityService = Depends(get_repeat_service)
):
    """
    Aggregates complaints by locality and ward, distinguishing unique issues from repeated complaints.
    """
    return repeat_service.get_repeat_localities(
        db, department=department, ward=ward, locality=locality, days_back=days_back
    )


@router.get("/clusters", response_model=ClusterListResponse)
def get_cluster_analytics(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    department: Optional[str] = Query(None),
    ward: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    cluster_service: ClusterService = Depends(get_cluster_service)
):
    """
    Lists major incident clusters ranked by complaint volume and recency.
    """
    clusters, total, analytics = cluster_service.get_clusters(
        db=db, limit=limit, offset=offset, department=department, ward=ward
    )
    return ClusterListResponse(
        clusters=clusters,
        total_clusters=total,
        analytics=analytics
    )


@router.get("/emerging-alerts", response_model=EmergingAlertsResponse)
def get_emerging_issue_alerts(
    department: Optional[str] = Query(None),
    ward: Optional[str] = Query(None),
    min_recent: Optional[int] = Query(None, description="Override minimum recent complaint volume threshold"),
    spike_multiplier: Optional[float] = Query(None, description="Override spike multiplier threshold"),
    db: Session = Depends(get_db),
    alerts_service: EmergingAlertsService = Depends(get_alerts_service)
):
    """
    Early-warning heuristic detecting emerging complaint volume spikes across wards and categories.
    """
    return alerts_service.detect_alerts(
        db,
        department=department,
        ward=ward,
        min_recent_override=min_recent,
        spike_multiplier_override=spike_multiplier
    )
