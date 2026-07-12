import { request } from './client';

export type PollingJobStatus = 'idle' | 'running' | 'success' | 'failed' | 'disabled';
export type PollingCursorType = 'none' | 'updated_at' | 'skip' | 'custom';

export interface PollingJob {
  id: string;
  name: string;
  slug: string | null;
  enabled: boolean;
  source_connector_id: string;
  integration_flow_id: string | null;
  target_system: string | null;
  resource: string;
  query_json: Record<string, unknown>;
  config_json: Record<string, unknown>;
  event_type: string;
  entity_type: string | null;
  entity_id_field: string | null;
  correlation_id_field: string | null;
  updated_at_field: string | null;
  cursor_value: string | null;
  cursor_json: Record<string, unknown>;
  cursor_type: PollingCursorType;
  schedule_type: 'manual_only' | 'interval_minutes' | string;
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
  sent_count: number;
  items_skipped: number;
  started_at: string;
  finished_at: string | null;
  error_message: string | null;
  event_id: string | null;
  cursor_before_json: Record<string, unknown>;
  cursor_after_json: Record<string, unknown>;
  details_json: Record<string, unknown>;
  created_at: string;
}

export interface PollingJobPayload {
  name: string;
  slug?: string | null;
  enabled?: boolean;
  source_connector_id: string;
  integration_flow_id?: string | null;
  target_system?: string | null;
  resource: string;
  query_json?: Record<string, unknown>;
  config_json?: Record<string, unknown>;
  event_type: string;
  entity_type?: string | null;
  entity_id_field?: string | null;
  correlation_id_field?: string | null;
  updated_at_field?: string | null;
  cursor_json?: Record<string, unknown>;
  cursor_type?: PollingCursorType;
  schedule_type?: 'manual_only' | 'interval_minutes' | string;
  interval_seconds?: number;
}

export interface PollingRunNowOptions {
  dry_run?: boolean;
  update_cursor?: boolean;
}

export const pollingApi = {
  list: () => request<PollingJob[]>('/api/polling-jobs'),
  create: (payload: PollingJobPayload) => request<PollingJob>('/api/polling/jobs', { method: 'POST', body: JSON.stringify(payload) }),
  patch: (id: string, payload: Partial<PollingJobPayload>) => request<PollingJob>(`/api/polling/jobs/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  delete: (id: string) => request<void>(`/api/polling/jobs/${id}`, { method: 'DELETE' }),
  enable: (id: string) => request<PollingJob>(`/api/polling-jobs/${id}/enable`, { method: 'POST' }),
  disable: (id: string) => request<PollingJob>(`/api/polling-jobs/${id}/disable`, { method: 'POST' }),
  runOnce: (id: string, options: PollingRunNowOptions = {}) => request<PollingJobRun>(`/api/polling-jobs/${id}/run-now`, { method: 'POST', body: JSON.stringify(options) }),
  runs: (id: string) => request<PollingJobRun[]>(`/api/polling-jobs/${id}/runs`),
};
