"""
SQLAlchemy Base class and model registry for NagarSetu.
All models inherit from this Base so metadata is registered for migrations and schema creation.
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Register all domain models with Base.metadata so create_all works dynamically
from app.models.taxonomy import Department, Category  # noqa: E402, F401
from app.models.complaint import RawComplaint, TriagedComplaint, StatusHistory  # noqa: E402, F401
from app.models.audit import ComplaintAudit  # noqa: E402, F401
from app.models.gazetteer import LocalityGazetteer, LocalityAlias  # noqa: E402, F401
from app.models.cluster import DuplicateCluster, ClusterMember  # noqa: E402, F401
from app.models.acknowledgement import Acknowledgement  # noqa: E402, F401
from app.models.analytics import WeeklyReport, EvaluationResult  # noqa: E402, F401
