/**
 * TypeScript Type Definitions for NagarSetu API Requests & Responses
 * Mirrors backend/app/schemas/api_contracts.py
 */

import { CanonicalComplaint, ComplaintChannel, ProcessingStatus, UrgencyLevel, MultimodalAttachment } from './complaint';

export interface PaginationMeta {
  total_records: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ComplaintIngestItem {
  source_reference_id?: string;
  original_channel: ComplaintChannel;
  raw_text: string;
  reported_at?: string;
  raw_locality_hint?: string;
  attachments?: MultimodalAttachment[];
}

export interface BatchIngestRequest {
  batch_source_name: string;
  items: ComplaintIngestItem[];
}

export interface BatchIngestResponse {
  batch_id: string;
  total_submitted: number;
  successfully_queued: number;
  failed_count: number;
  message: string;
}

export interface ComplaintFilterParams {
  department?: string;
  category?: string;
  urgency?: UrgencyLevel;
  status?: ProcessingStatus;
  ward?: string;
  zone?: string;
  search_query?: string;
  cluster_id?: string;
  page?: number;
  page_size?: number;
}

export interface PaginatedComplaintList {
  data: CanonicalComplaint[];
  pagination: PaginationMeta;
}

export interface OperatorReviewRequest {
  operator_id: string;
  status: ProcessingStatus;
  department_override?: string;
  urgency_override?: UrgencyLevel;
  ward_override?: string;
  approved_acknowledgement: string;
  operator_notes?: string;
}

export interface ClusterDetailResponse {
  cluster_id: string;
  summary: string;
  department: string;
  ward?: string;
  complaints_count: number;
  complaints: CanonicalComplaint[];
  root_incident_id?: string;
}

export interface EvaluationMetricSummary {
  total_test_samples: number;
  department_routing_accuracy: number;
  category_accuracy: number;
  urgency_agreement_score: number;
  locality_normalization_accuracy: number;
  duplicate_reduction_percentage: number;
  evaluation_run_at: string;
  test_dataset_name: string;
  disclaimer: string;
}
