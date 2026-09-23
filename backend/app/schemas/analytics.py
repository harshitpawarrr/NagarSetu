"""
Pydantic Schemas for NagarSetu Weekly Digest, Locality Repeats, and Emerging Alerts.
Defines contracts for departmental workload summaries, resolution times,
recurring complaints, and early-warning spike alerts.
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class CategoryVolume(BaseModel):
    category: str
    count: int


class ClusterBrief(BaseModel):
    cluster_id: str
    summary: str
    complaint_count: int
    confidence: float


class DepartmentWeeklySummary(BaseModel):
    """Departmental workload and resolution summary for the reporting period."""
    department: str
    department_name: Optional[str] = None
    complaints_received: int
    complaints_resolved: int
    complaints_pending: int
    median_resolution_hours: Optional[float] = None  # None if no resolved tickets with timestamps
    repeat_complaints: int
    top_categories: List[CategoryVolume] = Field(default_factory=list)
    major_clusters: List[ClusterBrief] = Field(default_factory=list)
    high_urgency_unresolved: int = 0


class WeeklyDigestResponse(BaseModel):
    """Full weekly accountability digest covering all municipal departments."""
    report_period_start: str
    report_period_end: str
    overall_received: int
    overall_resolved: int
    overall_pending: int
    overall_median_resolution_hours: Optional[float] = None
    departments: List[DepartmentWeeklySummary]
    operational_summary: str
    generated_at: datetime
    disclaimer: str = "[OPERATIONAL_METRIC] Median resolution times calculated strictly from database records with valid created_at and resolved_at timestamps."


class LocalityRepeatStat(BaseModel):
    """Repeat complaint statistics grouped by locality and ward."""
    locality: str
    ward: Optional[str] = None
    department: Optional[str] = None
    total_complaints: int
    unique_clusters: int
    repeat_complaints: int
    repeat_rate_pct: float
    top_categories: List[str] = Field(default_factory=list)


class LocalityRepeatResponse(BaseModel):
    """Response returning repeat complaints aggregated by municipal localities."""
    localities: List[LocalityRepeatStat]
    total_repeat_complaints: int


class EmergingIssueAlert(BaseModel):
    """Early-warning heuristic alert for sudden complaint volume spikes."""
    alert_id: str
    category: str
    locality: str
    ward: Optional[str] = None
    department: str
    baseline_count: int
    recent_count: int
    spike_multiplier: float
    time_window_hours: float
    contributing_complaints: List[str] = Field(default_factory=list)
    trigger_explanation: str
    heuristic_disclaimer: str = "[PROTOTYPE_ASSUMPTION] Early-warning spike heuristic. Does not denote confirmed emergency or statistical significance."


class EmergingAlertsResponse(BaseModel):
    """Response containing active early-warning spike alerts."""
    alerts: List[EmergingIssueAlert]
    total_alerts: int
    evaluation_timestamp: datetime
