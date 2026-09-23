"""
Emerging Issue Spike Alert Service for NagarSetu.
Evaluates early-warning heuristics by comparing recent complaint volume
against historical baseline volume across categories, wards, and departments.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.complaint import RawComplaint, TriagedComplaint
from app.schemas.analytics import EmergingIssueAlert, EmergingAlertsResponse

logger = logging.getLogger("nagarsetu.emerging_alerts_service")

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent.parent.parent / "config" / "alerts_config.json"


class EmergingAlertsService:
    """
    Early-warning spike detection service.
    """

    def __init__(self, config_path: Optional[Path] = None):
        cfg_file = config_path or CONFIG_PATH
        if cfg_file.exists():
            with open(cfg_file, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = {
                "min_recent_complaints": 3,
                "spike_multiplier": 2.0,
                "recent_window_hours": 72.0,
                "baseline_window_hours": 72.0,
                "disclaimer": "[PROTOTYPE_ASSUMPTION] Early-warning spike heuristic. Does not denote confirmed emergency or statistical significance."
            }

        self.min_recent = int(self.config.get("min_recent_complaints", 3))
        self.spike_mult = float(self.config.get("spike_multiplier", 2.0))
        self.recent_hours = float(self.config.get("recent_window_hours", 72.0))
        self.baseline_hours = float(self.config.get("baseline_window_hours", 72.0))
        self.disclaimer = self.config.get("disclaimer", "")

    def detect_emerging_issues(self, db: Session, **kwargs) -> EmergingAlertsResponse:
        """Alias for detect_alerts."""
        return self.detect_alerts(db, **kwargs)

    def detect_alerts(
        self,
        db: Session,
        department: Optional[str] = None,
        ward: Optional[str] = None,
        min_recent_override: Optional[int] = None,
        spike_multiplier_override: Optional[float] = None
    ) -> EmergingAlertsResponse:
        """
        Scans complaint records to identify volume spikes relative to previous baseline period.
        """
        min_recent = min_recent_override if min_recent_override is not None else self.min_recent
        spike_mult = spike_multiplier_override if spike_multiplier_override is not None else self.spike_mult

        query = db.query(TriagedComplaint, RawComplaint).join(
            RawComplaint, TriagedComplaint.complaint_id == RawComplaint.complaint_id
        )

        if department:
            query = query.filter(TriagedComplaint.department == department)
        if ward:
            query = query.filter(TriagedComplaint.ward == ward)

        records = query.all()
        if not records:
            return EmergingAlertsResponse(
                alerts=[],
                total_alerts=0,
                evaluation_timestamp=datetime.now(timezone.utc)
            )

        # Determine reference time T_now as the max timestamp among records (or current time)
        timestamps = [
            (rc.timestamp or rc.created_at) for tc, rc in records
            if (rc.timestamp or rc.created_at) is not None
        ]

        if timestamps:
            t_now = max(timestamps)
            if t_now.tzinfo is None:
                t_now = t_now.replace(tzinfo=timezone.utc)
        else:
            t_now = datetime.now(timezone.utc)

        t_recent_start = t_now - timedelta(hours=self.recent_hours)
        t_baseline_start = t_recent_start - timedelta(hours=self.baseline_hours)

        # Group into (category, locality, ward, department)
        groups: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}

        for tc, rc in records:
            cat = tc.category or "CAT_UNSPECIFIED"
            loc = tc.normalized_locality or "UNKNOWN"
            w = tc.ward or "Ward Unknown"
            dept = tc.department or "DEPT_UNASSIGNED"
            key = (cat, loc, w, dept)

            if key not in groups:
                groups[key] = {
                    "category": cat,
                    "locality": loc,
                    "ward": w,
                    "department": dept,
                    "recent_complaints": [],
                    "baseline_complaints": []
                }

            t = rc.timestamp or rc.created_at
            if t:
                if t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)

                if t >= t_recent_start:
                    groups[key]["recent_complaints"].append(tc.complaint_id)
                elif t >= t_baseline_start:
                    groups[key]["baseline_complaints"].append(tc.complaint_id)

        alerts: List[EmergingIssueAlert] = []
        alert_index = 1

        for key, data in groups.items():
            recent_cnt = len(data["recent_complaints"])
            base_cnt = len(data["baseline_complaints"])

            # Evaluate spike conditions
            is_spike = False
            ratio = 0.0

            if recent_cnt >= min_recent:
                if base_cnt == 0:
                    # Sudden emergence where prior period had zero issues
                    ratio = float(recent_cnt)
                    is_spike = True
                else:
                    ratio = round(recent_cnt / float(base_cnt), 2)
                    if ratio >= spike_mult:
                        is_spike = True

            if is_spike:
                cat_clean = data["category"].replace("CAT_", "").replace("_", " ").title()
                alert_id = f"ALERT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{alert_index:03d}"
                alert_index += 1

                explanation = (
                    f"Surge detected for {cat_clean} in {data['locality']} ({data['ward']}): "
                    f"{recent_cnt} complaints reported in the last {self.recent_hours:.0f} hours "
                    f"compared to {base_cnt} in the prior baseline window (surge factor: {ratio:.1f}x)."
                )

                alerts.append(EmergingIssueAlert(
                    alert_id=alert_id,
                    category=data["category"],
                    locality=data["locality"],
                    ward=data["ward"],
                    department=data["department"],
                    baseline_count=base_cnt,
                    recent_count=recent_cnt,
                    spike_multiplier=ratio,
                    time_window_hours=self.recent_hours,
                    contributing_complaints=data["recent_complaints"],
                    trigger_explanation=explanation,
                    heuristic_disclaimer=self.disclaimer
                ))

        # Sort alerts by highest spike multiplier, then recent count desc
        alerts.sort(key=lambda a: (a.spike_multiplier, a.recent_count), reverse=True)

        return EmergingAlertsResponse(
            alerts=alerts,
            total_alerts=len(alerts),
            evaluation_timestamp=datetime.now(timezone.utc)
        )
