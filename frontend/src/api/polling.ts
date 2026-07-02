import { request } from './client';

export type PollingJobStatus = 'idle' | 'running' | 'success' | 'failed' | 'disabled';
export type PollingCursorType = 'none' | 'updated_at' | 'skip' | 'custom';

export interface PollingJob {
  id: string;
  name: string;
  enabled: boolean;
  source_connector_id: string;
  target_system: string | null;
  resource: string;
  query_json: Record<string, unknown>;
  event_type: string;
  entity_type: string | null;
  entity_id_field: string | null;
  correlation_id_field: string | null;
  updated_at_field: string | null;
  cursor_value: string | null;
  cursor_type: PollingCursorType;
  interval_seconds: number;
  last_run_at: string | null;
  next_run_at: string | null;
  status: PollingJobStatus;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface PollingJobRun {
  id: string;
  job_id: string;
  status: PollingJobStatus;
  items_read: number;
  events_created: number;
  items_skipped: number;
  started_at: string;
  finished_at: string | null;
  error_message: string | null;
  details_json: Record<string, unknown>;
  created_at: string;
}

export interface PollingJobPayload {
  name: string;
  enabled?: boolean;
  source_connector_id: string;
  target_system?: string | null;
  resource: string;
  query_json?: Record<string, unknown>;
  event_type: string;
  entity_type?: string | null;
  entity_id_field?: string | null;
  correlation_id_field?: string | null;
  updated_at_field?: string | null;
  cursor_type?: PollingCursorType;
  interval_seconds?: number;
}

export const pollingApi = {
  list: () => request<PollingJob[]>('/api/polling/jobs'),
  create: (payload: PollingJobPayload) => request<PollingJob>('/api/polling/jobs', { method: 'POST', body: JSON.stringify(payload) }),
  patch: (id: string, payload: Partial<PollingJobPayload>) => request<PollingJob>(`/api/polling/jobs/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  delete: (id: string) => request<void>(`/api/polling/jobs/${id}`, { method: 'DELETE' }),
  enable: (id: string) => request<PollingJob>(`/api/polling/jobs/${id}/enable`, { method: 'POST' }),
  disable: (id: string) => request<PollingJob>(`/api/polling/jobs/${id}/disable`, { method: 'POST' }),
  runOnce: (id: string) => request<PollingJobRun>(`/api/polling/jobs/${id}/run-once`, { method: 'POST' }),
  runs: (id: string) => request<PollingJobRun[]>(`/api/polling/jobs/${id}/runs`),
};
