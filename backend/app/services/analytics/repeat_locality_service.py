"""
Repeat Complaints by Locality Service for NagarSetu.
Aggregates civic complaints across geographic zones, wards, and localities,
clearly distinguishing between unique incident clusters and repeated reports.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.complaint import RawComplaint, TriagedComplaint
from app.schemas.analytics import LocalityRepeatStat, LocalityRepeatResponse

logger = logging.getLogger("nagarsetu.repeat_locality_service")


class RepeatLocalityService:
    """
    Computes locality and ward repetition statistics.
    """

    def get_repeat_localities(
        self,
        db: Session,
        department: Optional[str] = None,
        ward: Optional[str] = None,
        locality: Optional[str] = None,
        days_back: Optional[int] = None
    ) -> LocalityRepeatResponse:
        """
        Groups complaints by locality & ward to compute repeat complaint rates.
        """
        query = db.query(TriagedComplaint, RawComplaint).join(
            RawComplaint, TriagedComplaint.complaint_id == RawComplaint.complaint_id
        )

        if days_back:
            start_dt = datetime.now(timezone.utc) - timedelta(days=days_back)
            query = query.filter(
                (RawComplaint.timestamp >= start_dt) | (RawComplaint.created_at >= start_dt)
            )

        if department:
            query = query.filter(TriagedComplaint.department == department)
        if ward:
            query = query.filter(TriagedComplaint.ward == ward)
        if locality:
            query = query.filter(TriagedComplaint.normalized_locality.ilike(f"%{locality}%"))

        records = query.all()

        # Group by (locality, ward, department)
        groups: Dict[tuple, Dict[str, Any]] = {}
        for tc, rc in records:
            loc = tc.normalized_locality or "UNKNOWN"
            w = tc.ward or "Ward Unknown"
            d = tc.department or "Unassigned"
            key = (loc, w, d)

            if key not in groups:
                groups[key] = {
                    "locality": loc,
                    "ward": w,
                    "department": d,
                    "complaints": [],
                    "categories": {},
                    "cluster_ids": set()
                }

            groups[key]["complaints"].append(tc)
            cat = tc.category or "CAT_UNSPECIFIED"
            groups[key]["categories"][cat] = groups[key]["categories"].get(cat, 0) + 1
            if tc.duplicate_cluster_id:
                groups[key]["cluster_ids"].add(tc.duplicate_cluster_id)

        stats_list: List[LocalityRepeatStat] = []
        total_repeat_sum = 0

        for key, g in groups.items():
            total = len(g["complaints"])
            clustered_cnt = sum(1 for c in g["complaints"] if c.duplicate_cluster_id)
            unique_clusters_cnt = len(g["cluster_ids"])
            unclustered_cnt = total - clustered_cnt
            unique_issues = unique_clusters_cnt + unclustered_cnt

            # Repeat reports are tickets reporting an existing cluster issue (total - unique_issues)
            repeat_cnt = max(0, total - unique_issues)
            total_repeat_sum += repeat_cnt

            repeat_rate = round((repeat_cnt / total) * 100.0, 1) if total > 0 else 0.0

            top_cats = [
                k for k, _ in sorted(g["categories"].items(), key=lambda x: x[1], reverse=True)[:3]
            ]

            stats_list.append(LocalityRepeatStat(
                locality=g["locality"],
                ward=g["ward"],
                department=g["department"],
                total_complaints=total,
                unique_clusters=unique_issues,
                repeat_complaints=repeat_cnt,
                repeat_rate_pct=repeat_rate,
                top_categories=top_cats
            ))

        # Sort localities by repeat complaints desc, then total desc
        stats_list.sort(key=lambda s: (s.repeat_complaints, s.total_complaints), reverse=True)

        return LocalityRepeatResponse(
            localities=stats_list,
            total_repeat_complaints=total_repeat_sum
        )
