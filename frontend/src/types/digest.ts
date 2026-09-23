/**
 * TypeScript Type Definitions for NagarSetu Weekly Digest & Reporting
 * Mirrors backend/app/schemas/digest.py
 */

export interface LocalityRepeatStat {
  locality: string;
  ward?: string;
  zone?: string;
  repeat_complaint_count: number;
  primary_department: string;
  primary_category: string;
}

export interface ClusterSummary {
  cluster_id: string;
  department: string;
  ward?: string;
  incident_count: number;
  first_reported_at: string;
  latest_reported_at: string;
  summary: string;
  is_active: boolean;
  urgency_level: string;
}

export interface EmergingClusterAlert {
  alert_id: string;
  cluster_id: string;
  locality: string;
  ward?: string;
  department: string;
  growth_rate_last_24h: number;
  complaint_count: number;
  severity: 'WARNING' | 'HIGH_ALERT' | 'CRITICAL_SPIKE';
  recommended_action: string;
}

export interface DepartmentMetric {
  department_id: string;
  department_name: string;
  received_count: number;
  resolved_count: number;
  pending_count: number;
  median_resolution_time_hours?: number;
  sla_compliance_rate?: number;
}

export interface WeeklyDepartmentDigest {
  digest_id: string;
  period_start_date: string;
  period_end_date: string;
  generated_at: string;
  zone?: string;

  total_received: number;
  total_resolved: number;
  total_pending: number;
  overall_median_resolution_hours?: number;

  departmental_metrics: DepartmentMetric[];
  repeat_complaints_by_locality: LocalityRepeatStat[];
  major_clusters: ClusterSummary[];
  emerging_cluster_alerts: EmergingClusterAlert[];
}
