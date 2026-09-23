"""
Evaluation Results and Weekly Report Analytics Relational Models for NagarSetu.
Enforces ground-truth auditability of performance benchmarks and aggregates weekly zone digests.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, Integer, Boolean, Date, DateTime, JSON

from app.db.base import Base


class EvaluationResult(Base):
    """
    Stores benchmark performance metrics evaluated against a held-out labelled test set.
    CRITICAL CONSTRAINT: Never store fabricated evaluation values as verified real results.
    """
    __tablename__ = "evaluation_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_set_version = Column(String(64), nullable=False, index=True)
    total_samples = Column(Integer, nullable=False)
    department_accuracy = Column(Float, nullable=False)
    category_accuracy = Column(Float, nullable=False)
    urgency_accuracy = Column(Float, nullable=False)
    locality_normalization_accuracy = Column(Float, nullable=False)
    duplicate_reduction = Column(Float, nullable=False)
    confusion_matrix = Column(JSON, nullable=True)
    per_class_metrics = Column(JSON, nullable=True)
    is_synthetic_benchmark = Column(Boolean, default=False, nullable=False)
    detailed_results = Column(JSON, nullable=True)  # Detailed per-sample predictions & misclassifications
    evaluated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    notes = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<EvaluationResult(test_set='{self.test_set_version}', dept_acc={self.department_accuracy:.2f})>"


class WeeklyReport(Base):
    """
    Persisted weekly accountability digests summarizing departmental workload,
    resolution times, recurring complaints by locality, and incident clusters.
    """
    __tablename__ = "weekly_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_period_start = Column(Date, nullable=False, index=True)
    report_period_end = Column(Date, nullable=False, index=True)
    department = Column(String(128), nullable=False, index=True)
    complaints_received = Column(Integer, default=0, nullable=False)
    complaints_resolved = Column(Integer, default=0, nullable=False)
    complaints_pending = Column(Integer, default=0, nullable=False)
    median_resolution_time = Column(Float, nullable=True)  # in hours
    repeat_complaints = Column(Integer, default=0, nullable=False)
    top_categories = Column(JSON, nullable=True)
    major_clusters = Column(JSON, nullable=True)
    generated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return f"<WeeklyReport(period='{self.report_period_start} to {self.report_period_end}', dept='{self.department}')>"
