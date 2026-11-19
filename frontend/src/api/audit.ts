import { request } from './client';

export type AuditSeverity = 'info' | 'warning' | 'error' | 'critical';

export interface AuditEventSummary {
  id: string;
  timestamp: string;
  actor_user_id: string | null;
  actor_username: string | null;
  actor_display_name: string | null;
  actor_type: string;
  source_ip: string | null;
  user_agent: string | null;
  action: string;
  category: string;
  severity: AuditSeverity;
  object_type: string | null;
  object_id: string | null;
  object_name: string | null;
  summary: string;
  request_id: string | null;
  correlation_id: string | null;
  event_id: string | null;
  queue_item_id: string | null;
  package_id: string | null;
  created_at: string;
}

export interface AuditEvent extends AuditEventSummary {
  details_json: Record<string, unknown> | null;
  before_json: Record<string, unknown> | null;
  after_json: Record<string, unknown> | null;
  diff_json: AuditDiff | null;
}

export interface AuditDiffEntry {
  path: string;
  before?: unknown;
  after?: unknown;
}

export interface AuditDiff {
  added?: AuditDiffEntry[];
  removed?: AuditDiffEntry[];
  changed?: AuditDiffEntry[];
}

export interface AuditListResponse {
  items: AuditEventSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface AuditStats {
  total: number;
  by_category: Record<string, number>;
  by_severity: Record<string, number>;
  oldest_timestamp: string | null;
  newest_timestamp: string | null;
}

export interface AuditFilters {
  date_from?: string;
  date_to?: string;
  actor_username?: string;
  category?: string;
  action?: string;
  object_type?: string;
  object_id?: string;
  severity?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

function query(filters: AuditFilters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && String(value).trim() !== '') params.set(key, String(value));
  });
  const suffix = params.toString();
  return suffix ? `?${suffix}` : '';
}

export const auditApi = {
  list: (filters: AuditFilters = {}) => request<AuditListResponse>(`/api/audit${query(filters)}`),
  get: (id: string) => request<AuditEvent>(`/api/audit/${id}`),
  objectHistory: (objectType: string, objectId: string) => request<AuditListResponse>(`/api/audit/object/${encodeURIComponent(objectType)}/${encodeURIComponent(objectId)}`),
  stats: () => request<AuditStats>('/api/audit/stats'),
  cleanup: (retention_days?: number, dry_run = true) => request<{ retention_days: number; cutoff: string; deleted: number; dry_run: boolean }>('/api/audit/cleanup', { method: 'POST', body: JSON.stringify({ retention_days, dry_run }) }),
  exportUrl: () => '/api/audit/export',
};
