"""
Weekly Digest & Analytics Schemas for NagarSetu
Adheres to reporting requirements:
- complaints received
- complaints resolved
- pending complaints
- median resolution time
- repeat complaints by locality
- major complaint clusters
- emerging cluster alerts as an extension
"""

from datetime import datetime, date, timezone
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class LocalityRepeatStat(BaseModel):
    locality: str
    ward: Optional[str] = None
    zone: Optional[str] = None
    repeat_complaint_count: int
    primary_department: str
    primary_category: str


class ClusterSummary(BaseModel):
    cluster_id: str
    department: str
    ward: Optional[str] = None
    incident_count: int
    first_reported_at: datetime
    latest_reported_at: datetime
    summary: str
    is_active: bool = True
    urgency_level: str


class EmergingClusterAlert(BaseModel):
    """Extension: Early-warning detection for rapidly rising complaint spikes."""
    alert_id: str
    cluster_id: str
    locality: str
    ward: Optional[str] = None
    department: str
    growth_rate_last_24h: float = Field(..., description="Percentage or multiplier increase in reports")
    complaint_count: int
    severity: str = Field(..., description="E.g., WARNING, HIGH_ALERT, CRITICAL_SPIKE")
    recommended_action: str


class DepartmentMetric(BaseModel):
    department_id: str
    department_name: str
    received_count: int
    resolved_count: int
    pending_count: int
    median_resolution_time_hours: Optional[float] = None
    sla_compliance_rate: Optional[float] = None


class WeeklyDepartmentDigest(BaseModel):
    digest_id: str
    period_start_date: date
    period_end_date: date
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    zone: Optional[str] = None

    # Core Headline Metrics
    total_received: int
    total_resolved: int
    total_pending: int
    overall_median_resolution_hours: Optional[float] = None

    # Granular Breakdown
    departmental_metrics: List[DepartmentMetric]
    repeat_complaints_by_locality: List[LocalityRepeatStat]
    major_clusters: List[ClusterSummary]
    emerging_cluster_alerts: List[EmergingClusterAlert] = Field(default_factory=list)
