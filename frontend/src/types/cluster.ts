/**
 * TypeScript Type Definitions for NagarSetu Incident Clusters and Analytics
 * Mirrors backend/app/schemas/cluster.py
 */

export interface ClusterMemberDetail {
  complaint_id: string;
  similarity_score?: number;
  relationship_type: 'LIKELY_DUPLICATE' | 'RELATED_INCIDENT' | 'NO_MATCH';
  matching_signals?: Record<string, number>;
  is_confirmed: boolean;
  notes?: string;
  added_at: string;
  channel?: string;
  text_snippet?: string;
  summary?: string;
  urgency?: string;
  canonical_locality?: string;
  ward?: string;
}

export interface ClusterSummary {
  cluster_id: string;
  representative_summary: string;
  category?: string;
  department?: string;
  canonical_locality?: string;
  ward?: string;
  complaint_count: number;
  channels: string[];
  first_reported_at?: string;
  latest_reported_at?: string;
  confidence: number;
  is_active: boolean;
  created_at: string;
}

export interface ClusterDetailResponse extends ClusterSummary {
  members: ClusterMemberDetail[];
  operator_notes?: string;
}

export interface ClusterAnalytics {
  raw_complaint_count: number;
  unique_cluster_count: number;
  unclustered_complaint_count: number;
  unique_issue_count: number;
  duplicate_or_related_count: number;
  ticket_reduction_percentage: number;
  formula_explanation: string;
  disclaimer: string;
}

export interface ClusterListResponse {
  clusters: ClusterSummary[];
  total_clusters: number;
  analytics: ClusterAnalytics;
}

export interface ClusterReviewRequest {
  action: 'confirm' | 'remove_member' | 'add_notes';
  complaint_id?: string;
  notes?: string;
  operator_id: string;
}

export interface ClusterReviewResponse {
  success: boolean;
  cluster_id: string;
  action_taken: string;
  message: string;
  updated_cluster?: ClusterSummary;
}
