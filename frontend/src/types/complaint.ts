/**
 * TypeScript Type Definitions for NagarSetu Canonical Complaint Ticket
 * Mirrors backend/app/schemas/complaint.py, triage.py, and operator.py
 */

export type ComplaintChannel =
  | 'state_helpline'
  | 'municipal_app'
  | 'elected_rep_message'
  | 'social_media'
  | 'walk_in_petition';

export type UrgencyLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type ProcessingStatus =
  | 'RAW'
  | 'PREPROCESSED'
  | 'CLASSIFIED'
  | 'OPERATOR_REVIEW_PENDING'
  | 'OPERATOR_APPROVED'
  | 'MANUAL_REVIEW_FLAGGED'
  | 'RESOLVED'
  | 'REJECTED';

export type InputModality = 'text' | 'voice' | 'image_caption';

export interface MultimodalAttachment {
  modality: InputModality;
  file_uri?: string;
  caption?: string;
  audio_duration_seconds?: number;
  transcription?: string;
  extracted_ocr_text?: string;
}

export interface OperatorReview {
  operator_id: string;
  reviewed_at: string;
  department_override?: string;
  urgency_override?: UrgencyLevel;
  ward_override?: string;
  approved_acknowledgement?: string;
  operator_notes?: string;
  is_approved: boolean;
}

export interface AuditEntry {
  id: number;
  complaint_id: string;
  operator_id: string;
  field_changed: string;
  original_value?: string;
  new_value?: string;
  reason?: string;
  created_at: string;
}

export interface AcknowledgementItem {
  id: number;
  complaint_id: string;
  draft_text: string;
  language: string;
  status: 'draft' | 'edited' | 'approved';
  generated_at: string;
  edited_at?: string;
  approved_at?: string;
  approved_by?: string;
  disclaimer: string;
}

export interface CanonicalComplaint {
  // Core Identifiers & Source Details
  complaint_id: string;
  original_channel: ComplaintChannel;
  original_text: string;
  language: string;

  // Synthesis & Classification
  summary: string;
  department: string;
  category: string;
  subcategory?: string;

  // Risk & Urgency Scoring
  urgency: UrgencyLevel;
  urgency_score: number; // 0.0 to 1.0
  urgency_reason: string;

  // Geographic & Locality Normalization
  normalized_locality: string;
  ward?: string;
  zone?: string;

  // Clustering & Duplicate Detection
  duplicate_cluster_id?: string;
  duplicate_confidence?: number;

  // Explainability & Transparency
  routing_evidence: string;
  routing_confidence: number;

  // Human-in-the-Loop & Operations
  acknowledgement_draft: string;
  created_at: string; // ISO 8601
  processing_status: ProcessingStatus;

  // Optional extensions
  attachments?: MultimodalAttachment[];
  operator_review?: OperatorReview;
  metadata?: Record<string, unknown>;
  triage_metadata?: Record<string, any>;
  operator_overrides?: Record<string, any>;
  operator_decision?: Record<string, any>;
}
