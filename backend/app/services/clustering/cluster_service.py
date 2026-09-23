"""
Duplicate and Incident Cluster Detection Service for NagarSetu.
Coordinates pairwise multi-signal similarity evaluation, connected-component clustering,
deterministic representative synthesis, and ticket count reduction analytics.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple, Set
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_

from app.models.complaint import RawComplaint, TriagedComplaint, StatusHistory
from app.models.cluster import DuplicateCluster, ClusterMember
from app.models.audit import ComplaintAudit
from app.schemas.cluster import (
    ClusterSummary,
    ClusterDetailResponse,
    ClusterMemberDetail,
    ClusterAnalytics,
    ClusterDetectionResponse,
    ClusterReviewResponse
)
from app.services.clustering.similarity_engine import SimilarityEngine

logger = logging.getLogger("nagarsetu.cluster_service")


class UnionFind:
    """Disjoint Set Union (DSU) with path compression for connected components."""
    def __init__(self):
        self.parent = {}

    def find(self, x: str) -> str:
        if x not in self.parent:
            self.parent[x] = x
            return x
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: str, y: str):
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x != root_y:
            self.parent[root_x] = root_y


class ClusterService:
    """
    Manages detection, retrieval, and operator review of complaint clusters.
    """

    def __init__(self, similarity_engine: Optional[SimilarityEngine] = None):
        self.similarity_engine = similarity_engine or SimilarityEngine()

    def detect_clusters(
        self,
        db: Session,
        recluster: bool = False,
        threshold_duplicate: Optional[float] = None,
        threshold_related: Optional[float] = None,
        department_filter: Optional[str] = None,
        ward_filter: Optional[str] = None
    ) -> ClusterDetectionResponse:
        """
        Executes multi-signal cluster detection on triaged complaints.
        Creates DuplicateCluster and ClusterMember records while preserving raw complaints.
        """
        if recluster:
            # Clear existing active cluster links on triaged complaints and delete clusters
            db.query(ClusterMember).delete()
            db.query(DuplicateCluster).delete()
            db.query(TriagedComplaint).update(
                {TriagedComplaint.duplicate_cluster_id: None, TriagedComplaint.duplicate_confidence: None},
                synchronize_session=False
            )
            db.commit()

        # Query triaged complaints with their linked raw complaints
        query = db.query(TriagedComplaint, RawComplaint).join(
            RawComplaint, TriagedComplaint.complaint_id == RawComplaint.complaint_id
        )
        if department_filter:
            query = query.filter(TriagedComplaint.department == department_filter)
        if ward_filter:
            query = query.filter(TriagedComplaint.ward == ward_filter)

        results = query.all()
        if not results:
            analytics = self.compute_analytics(db)
            return ClusterDetectionResponse(
                success=True,
                clusters_created=0,
                total_complaints_clustered=0,
                analytics=analytics
            )

        # Convert records to dictionary format for similarity evaluation
        complaint_records = []
        record_map = {}
        for tc, rc in results:
            triage_meta = tc.triage_metadata or {}
            routing_meta = triage_meta.get("routing", {})
            routing_terms = []
            if routing_meta and "routing_evidence" in routing_meta:
                routing_terms = routing_meta.get("routing_evidence", [])

            rec = {
                "complaint_id": tc.complaint_id,
                "text": (rc.text or "") + " " + (rc.image_caption or ""),
                "summary": tc.summary or "",
                "department": tc.department,
                "category": tc.category,
                "normalized_locality": tc.normalized_locality,
                "ward": tc.ward,
                "zone": tc.zone,
                "timestamp": rc.timestamp or rc.created_at,
                "channel": rc.channel,
                "routing_terms": routing_terms,
                "confidence": tc.routing_confidence or 0.80,
                "urgency": tc.urgency or "MEDIUM",
                "tc_obj": tc,
                "rc_obj": rc
            }
            complaint_records.append(rec)
            record_map[tc.complaint_id] = rec

        # Override thresholds if requested
        if threshold_duplicate is not None:
            self.similarity_engine.thresholds["likely_duplicate"] = threshold_duplicate
        if threshold_related is not None:
            self.similarity_engine.thresholds["related_incident"] = threshold_related

        th_rel = self.similarity_engine.thresholds.get("related_incident", 0.48)
        th_dup = self.similarity_engine.thresholds.get("likely_duplicate", 0.72)

        # Evaluate pairwise similarities & build graph edges
        dsu = UnionFind()
        pair_data: Dict[Tuple[str, str], Tuple[float, Dict[str, float], str]] = {}

        n = len(complaint_records)
        for i in range(n):
            for j in range(i + 1, n):
                c1 = complaint_records[i]
                c2 = complaint_records[j]
                sim_score, signals, rel_type = self.similarity_engine.compute_similarity(c1, c2)
                if rel_type != "NO_MATCH" and sim_score >= th_rel:
                    dsu.union(c1["complaint_id"], c2["complaint_id"])
                    pair_data[(c1["complaint_id"], c2["complaint_id"])] = (sim_score, signals, rel_type)
                    pair_data[(c2["complaint_id"], c1["complaint_id"])] = (sim_score, signals, rel_type)

        # Group into clusters
        groups: Dict[str, List[str]] = {}
        for rec in complaint_records:
            cid = rec["complaint_id"]
            root = dsu.find(cid)
            groups.setdefault(root, []).append(cid)

        # Only form clusters for groups with 2 or more complaints
        clusters_created = 0
        total_complaints_clustered = 0
        existing_cluster_count = db.query(func.count(DuplicateCluster.cluster_id)).scalar() or 0

        for root, member_ids in groups.items():
            if len(member_ids) < 2:
                continue  # Singleton, not an incident cluster

            clusters_created += 1
            cluster_num = existing_cluster_count + clusters_created
            cluster_id = f"CL-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{cluster_num:04d}"

            # Pick representative complaint deterministically:
            # 1. Earliest reported timestamp
            # 2. Most descriptive summary length
            member_recs = [record_map[mid] for mid in member_ids]
            member_recs.sort(
                key=lambda r: (
                    r["timestamp"] or datetime.max.replace(tzinfo=timezone.utc),
                    -len(r["summary"] or r["text"])
                )
            )
            rep = member_recs[0]

            # Representative attributes
            channels = sorted(list({r["channel"] for r in member_recs if r["channel"]}))
            first_seen = min((r["timestamp"] for r in member_recs if r["timestamp"]), default=None)
            last_seen = max((r["timestamp"] for r in member_recs if r["timestamp"]), default=None)

            # Cluster cohesion confidence: average similarity to representative
            member_sims = []
            for mid in member_ids:
                if mid == rep["complaint_id"]:
                    member_sims.append(1.0)
                elif (rep["complaint_id"], mid) in pair_data:
                    member_sims.append(pair_data[(rep["complaint_id"], mid)][0])
                else:
                    member_sims.append(th_rel)

            cluster_confidence = round(sum(member_sims) / len(member_sims), 3)

            cluster_obj = DuplicateCluster(
                cluster_id=cluster_id,
                summary=rep["summary"] or rep["text"][:160],
                confidence=cluster_confidence,
                detection_method="multi_signal_weighted",
                category=rep["category"],
                department=rep["department"],
                canonical_locality=rep["normalized_locality"],
                ward=rep["ward"],
                first_reported_at=first_seen,
                latest_reported_at=last_seen,
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            db.add(cluster_obj)

            for rec in member_recs:
                mid = rec["complaint_id"]
                if mid == rep["complaint_id"]:
                    sim = 1.0
                    signals = {"self_representative": 1.0}
                    rel_type = "LIKELY_DUPLICATE"
                else:
                    p_info = pair_data.get((rep["complaint_id"], mid))
                    if p_info:
                        sim, signals, rel_type = p_info
                    else:
                        sim, signals, rel_type = th_rel, {"default": th_rel}, "RELATED_INCIDENT"

                mem_obj = ClusterMember(
                    cluster_id=cluster_id,
                    complaint_id=mid,
                    similarity_score=sim,
                    relationship_type=rel_type,
                    matching_signals=signals,
                    is_confirmed=True,
                    added_at=datetime.now(timezone.utc)
                )
                db.add(mem_obj)

                # Update triaged complaint record with audit linkage
                tc = rec["tc_obj"]
                tc.duplicate_cluster_id = cluster_id
                tc.duplicate_confidence = sim

                total_complaints_clustered += 1

        db.commit()
        analytics = self.compute_analytics(db)
        return ClusterDetectionResponse(
            success=True,
            clusters_created=clusters_created,
            total_complaints_clustered=total_complaints_clustered,
            analytics=analytics
        )

    def compute_analytics(self, db: Session) -> ClusterAnalytics:
        """
        Computes the ticket count reduction analytics according to the formula:
        (raw_complaint_count - unique_issue_count) / raw_complaint_count * 100
        """
        raw_count = db.query(func.count(RawComplaint.complaint_id)).scalar() or 0
        active_clusters_count = db.query(func.count(DuplicateCluster.cluster_id)).filter(
            DuplicateCluster.is_active.is_(True)
        ).scalar() or 0

        clustered_complaints_count = db.query(func.count(ClusterMember.id)).join(
            DuplicateCluster, ClusterMember.cluster_id == DuplicateCluster.cluster_id
        ).filter(DuplicateCluster.is_active.is_(True)).scalar() or 0

        unclustered_count = max(0, raw_count - clustered_complaints_count)
        unique_issue_count = active_clusters_count + unclustered_count
        duplicate_or_related = max(0, raw_count - unique_issue_count)

        if raw_count > 0:
            reduction_pct = round(((raw_count - unique_issue_count) / raw_count) * 100.0, 2)
        else:
            reduction_pct = 0.0

        return ClusterAnalytics(
            raw_complaint_count=raw_count,
            unique_cluster_count=active_clusters_count,
            unclustered_complaint_count=unclustered_count,
            unique_issue_count=unique_issue_count,
            duplicate_or_related_count=duplicate_or_related,
            ticket_reduction_percentage=reduction_pct
        )

    def get_clusters(
        self,
        db: Session,
        limit: int = 50,
        offset: int = 0,
        department: Optional[str] = None,
        ward: Optional[str] = None,
        is_active: bool = True
    ) -> Tuple[List[ClusterSummary], int, ClusterAnalytics]:
        """Returns paginated cluster summaries and overall analytics."""
        query = db.query(DuplicateCluster).filter(DuplicateCluster.is_active == is_active)
        if department:
            query = query.filter(DuplicateCluster.department == department)
        if ward:
            query = query.filter(DuplicateCluster.ward == ward)

        total = query.count()
        clusters = query.order_by(DuplicateCluster.created_at.desc()).offset(offset).limit(limit).all()

        summaries = []
        for cl in clusters:
            # Query channels and member count
            members = db.query(ClusterMember, RawComplaint).join(
                RawComplaint, ClusterMember.complaint_id == RawComplaint.complaint_id
            ).filter(ClusterMember.cluster_id == cl.cluster_id).all()

            channels = sorted(list({rc.channel for _, rc in members if rc.channel}))
            count = len(members)

            summaries.append(ClusterSummary(
                cluster_id=cl.cluster_id,
                representative_summary=cl.summary,
                category=cl.category,
                department=cl.department,
                canonical_locality=cl.canonical_locality,
                ward=cl.ward,
                complaint_count=count,
                channels=channels,
                first_reported_at=cl.first_reported_at,
                latest_reported_at=cl.latest_reported_at,
                confidence=cl.confidence,
                is_active=cl.is_active,
                created_at=cl.created_at
            ))

        analytics = self.compute_analytics(db)
        return summaries, total, analytics

    def get_cluster_by_id(self, db: Session, cluster_id: str) -> Optional[ClusterDetailResponse]:
        """Returns cluster details with member complaint listings."""
        cl = db.query(DuplicateCluster).filter(DuplicateCluster.cluster_id == cluster_id).first()
        if not cl:
            return None

        member_rows = db.query(ClusterMember, RawComplaint, TriagedComplaint).join(
            RawComplaint, ClusterMember.complaint_id == RawComplaint.complaint_id
        ).outerjoin(
            TriagedComplaint, ClusterMember.complaint_id == TriagedComplaint.complaint_id
        ).filter(ClusterMember.cluster_id == cluster_id).all()

        members = []
        channels_set = set()
        for cm, rc, tc in member_rows:
            if rc.channel:
                channels_set.add(rc.channel)
            members.append(ClusterMemberDetail(
                complaint_id=cm.complaint_id,
                similarity_score=cm.similarity_score,
                relationship_type=cm.relationship_type,
                matching_signals=cm.matching_signals,
                is_confirmed=cm.is_confirmed,
                notes=cm.notes,
                added_at=cm.added_at,
                channel=rc.channel,
                text_snippet=(rc.text or rc.image_caption or "")[:120],
                summary=tc.summary if tc else None,
                urgency=tc.urgency if tc else None,
                canonical_locality=tc.normalized_locality if tc else None,
                ward=tc.ward if tc else None
            ))

        return ClusterDetailResponse(
            cluster_id=cl.cluster_id,
            representative_summary=cl.summary,
            category=cl.category,
            department=cl.department,
            canonical_locality=cl.canonical_locality,
            ward=cl.ward,
            complaint_count=len(members),
            channels=sorted(list(channels_set)),
            first_reported_at=cl.first_reported_at,
            latest_reported_at=cl.latest_reported_at,
            confidence=cl.confidence,
            is_active=cl.is_active,
            created_at=cl.created_at,
            members=members,
            operator_notes=cl.operator_notes
        )

    def review_cluster(
        self,
        db: Session,
        cluster_id: str,
        action: str,
        operator_id: str,
        complaint_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> ClusterReviewResponse:
        """
        Executes operator action on a cluster: 'confirm', 'remove_member', or 'add_notes'.
        Audits all changes without mutating raw complaints.
        """
        cl = db.query(DuplicateCluster).filter(DuplicateCluster.cluster_id == cluster_id).first()
        if not cl:
            raise ValueError(f"Cluster '{cluster_id}' not found.")

        if action == "remove_member":
            if not complaint_id:
                raise ValueError("complaint_id is required to remove a member from cluster.")

            mem = db.query(ClusterMember).filter(
                ClusterMember.cluster_id == cluster_id,
                ClusterMember.complaint_id == complaint_id
            ).first()
            if not mem:
                raise ValueError(f"Complaint '{complaint_id}' is not a member of cluster '{cluster_id}'.")

            # Remove member linkage
            db.delete(mem)

            # Clear cluster id in triaged complaint
            tc = db.query(TriagedComplaint).filter(TriagedComplaint.complaint_id == complaint_id).first()
            if tc:
                tc.duplicate_cluster_id = None
                tc.duplicate_confidence = None

            # Record audit entry
            audit = ComplaintAudit(
                complaint_id=complaint_id,
                operator_id=operator_id,
                field_changed="cluster_membership",
                original_value=cluster_id,
                new_value="UNCLUSTERED",
                reason=notes or f"Removed from cluster {cluster_id} by operator",
                created_at=datetime.now(timezone.utc)
            )
            db.add(audit)

            # Check remaining member count; if less than 2, deactivate cluster
            remaining_count = db.query(func.count(ClusterMember.id)).filter(
                ClusterMember.cluster_id == cluster_id
            ).scalar() or 0
            if remaining_count < 2:
                cl.is_active = False

            db.commit()
            return ClusterReviewResponse(
                success=True,
                cluster_id=cluster_id,
                action_taken="remove_member",
                message=f"Complaint '{complaint_id}' removed from cluster '{cluster_id}'."
            )

        elif action == "confirm":
            if complaint_id:
                mem = db.query(ClusterMember).filter(
                    ClusterMember.cluster_id == cluster_id,
                    ClusterMember.complaint_id == complaint_id
                ).first()
                if mem:
                    mem.is_confirmed = True
                    mem.notes = notes
                    db.add(ComplaintAudit(
                        complaint_id=complaint_id,
                        operator_id=operator_id,
                        field_changed="cluster_membership",
                        original_value="PENDING_CONFIRMATION",
                        new_value=f"CONFIRMED_IN_{cluster_id}",
                        reason=notes or "Cluster membership confirmed by operator",
                        created_at=datetime.now(timezone.utc)
                    ))
            else:
                # Confirm all members
                db.query(ClusterMember).filter(ClusterMember.cluster_id == cluster_id).update(
                    {ClusterMember.is_confirmed: True}, synchronize_session=False
                )

            db.commit()
            return ClusterReviewResponse(
                success=True,
                cluster_id=cluster_id,
                action_taken="confirm",
                message=f"Cluster '{cluster_id}' membership confirmed by operator."
            )

        elif action == "add_notes":
            cl.operator_notes = notes
            db.commit()
            return ClusterReviewResponse(
                success=True,
                cluster_id=cluster_id,
                action_taken="add_notes",
                message=f"Operator notes saved for cluster '{cluster_id}'."
            )
        else:
            raise ValueError(f"Unsupported cluster review action: '{action}'")
