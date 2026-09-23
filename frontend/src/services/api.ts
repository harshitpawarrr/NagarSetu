/**
 * API Service Client for NagarSetu Operator Desk
 * Handles communication with FastAPI backend endpoints.
 */

// @ts-ignore
const API_BASE = import.meta.env.VITE_API_URL || (typeof window !== 'undefined' ? '/api/v1' : 'http://localhost:8000/api/v1');

export async function fetchComplaints(params: {
  page?: number;
  page_size?: number;
  skip?: number;
  limit?: number;
  department?: string;
  category?: string;
  urgency?: string;
  status?: string;
  ward?: string;
  zone?: string;
  search?: string;
  search_query?: string;
} = {}) {
  const query = new URLSearchParams();
  const page = params.page || (params.skip !== undefined && params.limit ? Math.floor(params.skip / params.limit) + 1 : 1);
  const pageSize = params.page_size || params.limit || 100;
  query.append('page', String(page));
  query.append('page_size', String(pageSize));

  if (params.department) query.append('department', params.department);
  if (params.category) query.append('category', params.category);
  if (params.urgency) query.append('urgency', params.urgency);
  if (params.status) query.append('status', params.status);
  if (params.ward) query.append('ward', params.ward);
  if (params.zone) query.append('zone', params.zone);

  const search = params.search_query || params.search;
  if (search) query.append('search_query', search);

  const res = await fetch(`${API_BASE}/complaints?${query.toString()}`);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const errBody = await res.json();
      detail = JSON.stringify(errBody);
    } catch (e) {}
    throw new Error(`Failed to fetch complaints: ${detail}`);
  }
  return res.json();
}

export async function fetchComplaint(complaintId: string) {
  const res = await fetch(`${API_BASE}/complaints/${encodeURIComponent(complaintId)}`);
  if (!res.ok) throw new Error(`Failed to fetch complaint '${complaintId}': ${res.statusText}`);
  return res.json();
}

export async function fetchTriage(complaintId: string) {
  const res = await fetch(`${API_BASE}/complaints/${encodeURIComponent(complaintId)}/triage`);
  if (!res.ok) throw new Error(`Failed to fetch triage for '${complaintId}': ${res.statusText}`);
  return res.json();
}

export async function processComplaint(complaintId: string) {
  const res = await fetch(`${API_BASE}/complaints/${encodeURIComponent(complaintId)}/process`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error(`Failed to process complaint '${complaintId}': ${res.statusText}`);
  return res.json();
}

export async function reviewComplaint(complaintId: string, payload: {
  action: 'approve' | 'override' | 'flag_manual_review';
  department?: string;
  category?: string;
  urgency?: string;
  normalized_locality?: string;
  ward?: string;
  summary?: string;
  reason?: string;
  notes?: string;
  operator_id: string;
}) {
  const res = await fetch(`${API_BASE}/complaints/${encodeURIComponent(complaintId)}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Review failed: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchAuditTrail(complaintId: string) {
  const res = await fetch(`${API_BASE}/complaints/${encodeURIComponent(complaintId)}/audit`);
  if (!res.ok) throw new Error(`Failed to fetch audit trail: ${res.statusText}`);
  return res.json();
}

export async function fetchAcknowledgement(complaintId: string) {
  const res = await fetch(`${API_BASE}/complaints/${encodeURIComponent(complaintId)}/acknowledgement`);
  if (!res.ok) throw new Error(`Failed to fetch acknowledgement: ${res.statusText}`);
  return res.json();
}

export async function editAcknowledgement(complaintId: string, payload: {
  draft_text: string;
  language: string;
  operator_id: string;
}) {
  const res = await fetch(`${API_BASE}/complaints/${encodeURIComponent(complaintId)}/acknowledgement`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error(`Failed to update acknowledgement: ${res.statusText}`);
  return res.json();
}

export async function approveAcknowledgement(complaintId: string, payload: {
  operator_id: string;
  notes?: string;
}) {
  const res = await fetch(`${API_BASE}/complaints/${encodeURIComponent(complaintId)}/acknowledgement/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error(`Failed to approve acknowledgement: ${res.statusText}`);
  return res.json();
}

export async function fetchClusters(params: {
  limit?: number;
  offset?: number;
  department?: string;
  ward?: string;
  is_active?: boolean;
} = {}) {
  const query = new URLSearchParams();
  if (params.limit !== undefined) query.append('limit', String(params.limit));
  if (params.offset !== undefined) query.append('offset', String(params.offset));
  if (params.department) query.append('department', params.department);
  if (params.ward) query.append('ward', params.ward);
  if (params.is_active !== undefined) query.append('is_active', String(params.is_active));

  const res = await fetch(`${API_BASE}/clusters?${query.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch clusters: ${res.statusText}`);
  return res.json();
}

export async function fetchClusterDetail(clusterId: string) {
  const res = await fetch(`${API_BASE}/clusters/${encodeURIComponent(clusterId)}`);
  if (!res.ok) throw new Error(`Failed to fetch cluster detail: ${res.statusText}`);
  return res.json();
}

export async function detectClusters(payload: {
  recluster?: boolean;
  threshold_duplicate?: number;
  threshold_related?: number;
  department?: string;
  ward?: string;
} = {}) {
  const res = await fetch(`${API_BASE}/clusters/detect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error(`Cluster detection failed: ${res.statusText}`);
  return res.json();
}

export async function reviewCluster(clusterId: string, payload: {
  action: 'confirm' | 'remove_member' | 'add_notes';
  complaint_id?: string;
  notes?: string;
  operator_id: string;
}) {
  const res = await fetch(`${API_BASE}/clusters/${encodeURIComponent(clusterId)}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Cluster review failed: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDepartments() {
  const res = await fetch(`${API_BASE}/config/departments`);
  if (!res.ok) return { departments: [] };
  return res.json();
}

export async function fetchCategories() {
  const res = await fetch(`${API_BASE}/config/categories`);
  if (!res.ok) return { categories: [] };
  return res.json();
}

export async function fetchWeeklyDigest(startDate?: string, endDate?: string) {
  const query = new URLSearchParams();
  if (startDate) query.append('start_date', startDate);
  if (endDate) query.append('end_date', endDate);
  const res = await fetch(`${API_BASE}/analytics/weekly-digest?${query.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch weekly digest: ${res.statusText}`);
  return res.json();
}

export async function fetchLocalityRepeats(params: {
  department?: string;
  ward?: string;
  locality?: string;
} = {}) {
  const query = new URLSearchParams();
  if (params.department) query.append('department', params.department);
  if (params.ward) query.append('ward', params.ward);
  if (params.locality) query.append('locality', params.locality);
  const res = await fetch(`${API_BASE}/analytics/localities?${query.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch locality repeats: ${res.statusText}`);
  return res.json();
}

export async function fetchEmergingAlerts(params: {
  department?: string;
  ward?: string;
  min_recent?: number;
  spike_multiplier?: number;
} = {}) {
  const query = new URLSearchParams();
  if (params.department) query.append('department', params.department);
  if (params.ward) query.append('ward', params.ward);
  if (params.min_recent) query.append('min_recent', String(params.min_recent));
  if (params.spike_multiplier) query.append('spike_multiplier', String(params.spike_multiplier));
  const res = await fetch(`${API_BASE}/analytics/emerging-alerts?${query.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch emerging alerts: ${res.statusText}`);
  return res.json();
}

export async function runEvaluation(payload: any) {
  const res = await fetch(`${API_BASE}/eval/benchmark`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error(`Failed to run evaluation: ${res.statusText}`);
  return res.json();
}

export async function fetchLatestEvaluation() {
  const res = await fetch(`${API_BASE}/eval/latest`);
  if (!res.ok) {
    if (res.status === 404) return null;
    throw new Error(`Failed to fetch latest evaluation: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchEvaluationHistory() {
  const res = await fetch(`${API_BASE}/eval/history`);
  if (!res.ok) throw new Error(`Failed to fetch evaluation history: ${res.statusText}`);
  return res.json();
}
