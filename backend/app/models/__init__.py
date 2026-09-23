"""
NagarSetu Relational Models Package.
Exports all 11 core domain models, tables, and immutability error classes.
"""

from app.models.taxonomy import Department, Category
from app.models.complaint import RawComplaint, TriagedComplaint, StatusHistory, ImmutableDataError
from app.models.audit import ComplaintAudit
from app.models.gazetteer import LocalityGazetteer, LocalityAlias
from app.models.cluster import DuplicateCluster, ClusterMember
from app.models.acknowledgement import Acknowledgement
from app.models.analytics import WeeklyReport, EvaluationResult

__all__ = [
    "Department",
    "Category",
    "RawComplaint",
    "TriagedComplaint",
    "StatusHistory",
    "ComplaintAudit",
    "ImmutableDataError",
    "LocalityGazetteer",
    "LocalityAlias",
    "DuplicateCluster",
    "ClusterMember",
    "Acknowledgement",
    "WeeklyReport",
    "EvaluationResult",
]
