"""
FastAPI Routes for NagarSetu Duplicate & Incident Clustering.
Provides endpoints for cluster detection, listing, inspection, and operator review.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.cluster import (
    ClusterListResponse,
    ClusterDetailResponse,
    ClusterDetectionRequest,
    ClusterDetectionResponse,
    ClusterReviewRequest,
    ClusterReviewResponse
)
from app.services.clustering.cluster_service import ClusterService

router = APIRouter(prefix="/clusters", tags=["Clustering & Incident Detection"])


def get_cluster_service() -> ClusterService:
    return ClusterService()


@router.post("/detect", response_model=ClusterDetectionResponse)
def detect_clusters(
    req: ClusterDetectionRequest = ClusterDetectionRequest(),
    db: Session = Depends(get_db),
    cluster_service: ClusterService = Depends(get_cluster_service)
):
    """
    Executes multi-signal duplicate and incident cluster detection across triaged complaints.
    Clusters are persisted in `duplicate_clusters` and `cluster_members`.
    Raw complaints remain strictly immutable.
    """
    try:
        return cluster_service.detect_clusters(
            db=db,
            recluster=req.recluster,
            threshold_duplicate=req.threshold_duplicate,
            threshold_related=req.threshold_related,
            department_filter=req.department,
            ward_filter=req.ward
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cluster detection failed: {str(e)}")


@router.get("", response_model=ClusterListResponse)
def list_clusters(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    department: Optional[str] = Query(None, description="Filter by department"),
    ward: Optional[str] = Query(None, description="Filter by ward"),
    is_active: bool = Query(True, description="Filter active clusters"),
    db: Session = Depends(get_db),
    cluster_service: ClusterService = Depends(get_cluster_service)
):
    """
    Retrieves paginated list of incident clusters and overall ticket reduction analytics.
    """
    clusters, total, analytics = cluster_service.get_clusters(
        db=db,
        limit=limit,
        offset=offset,
        department=department,
        ward=ward,
        is_active=is_active
    )
    return ClusterListResponse(
        clusters=clusters,
        total_clusters=total,
        analytics=analytics
    )


@router.get("/{cluster_id}", response_model=ClusterDetailResponse)
def get_cluster_detail(
    cluster_id: str,
    db: Session = Depends(get_db),
    cluster_service: ClusterService = Depends(get_cluster_service)
):
    """
    Retrieves detailed cluster information including all linked member complaints,
    relationship classifications, and matching signal breakdowns.
    """
    detail = cluster_service.get_cluster_by_id(db, cluster_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Cluster '{cluster_id}' not found.")
    return detail


@router.post("/{cluster_id}/review", response_model=ClusterReviewResponse)
def review_cluster(
    cluster_id: str,
    req: ClusterReviewRequest,
    db: Session = Depends(get_db),
    cluster_service: ClusterService = Depends(get_cluster_service)
):
    """
    Executes operator review action on a cluster:
    - 'confirm': Confirms cluster validity
    - 'remove_member': Dissociates a complaint without modifying raw data
    - 'add_notes': Appends municipal operator observations
    """
    try:
        return cluster_service.review_cluster(
            db=db,
            cluster_id=cluster_id,
            action=req.action,
            operator_id=req.operator_id,
            complaint_id=req.complaint_id,
            notes=req.notes
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cluster review failed: {str(e)}")
