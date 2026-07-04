export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === 'string' ? detail : `API request failed with ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

export type EventStatus = 'new' | 'processing' | 'success' | 'failed' | 'retry_waiting' | 'cancelled' | 'expired';
export type RunMode = 'normal' | 'replay' | 'replay_from_step' | 'edit_replay' | 'dry_run';
export type RunStatus = 'created' | 'running' | 'success' | 'failed' | 'cancelled' | 'dry_run_success' | 'dry_run_failed';
export type StepStatus = 'pending' | 'running' | 'success' | 'failed' | 'skipped' | 'dry_run';

export interface EventSummary {
  id: string;
  correlation_id: string | null;
  source_system: string;
  target_system: string | null;
  event_type: string;
  entity_type: string | null;
  entity_id: string | null;
  status: EventStatus;
  pinned: boolean;
  created_at: string;
}

export interface ExternalErrorSummary {
  id: string;
  event_id: string | null;
  run_id: string | null;
  step_id: string | null;
  incident_id: string | null;
  source_system: string | null;
  target_system: string | null;
  connector_type: string | null;
  connector_name: string | null;
  operation: string | null;
  endpoint_url: string | null;
  http_method: string | null;
  http_status: number | null;
  normalized_code: string;
  normalized_message: string;
  human_title: string | null;
  human_summary: string | null;
  developer_message: string | null;
  hint: string | null;
  external_error_code: string | null;
  external_error_message: string | null;
  external_error_type: string | null;
  response_content_type: string | null;
  response_body_preview: string | null;
  response_body_sha256: string | null;
  response_size_bytes: number | null;
  created_at: string;
}

export interface Artifact {
  id: string;
  event_id: string;
  run_id: string;
  step_id: string | null;
  artifact_type: string;
  name: string;
  content_json: Record<string, unknown>;
  content_hash: string;
  size_bytes: number;
  created_at: string;
}

export interface EventStep {
  id: string;
  step_order: number;
  step_name: string;
  status: StepStatus;
  error_code: string | null;
  error_message: string | null;
  human_title: string | null;
  human_summary: string | null;
  developer_message: string | null;
  hint: string | null;
  external_error_record_id: string | null;
  external_error: ExternalErrorSummary | null;
  artifacts: Artifact[];
}

export interface EventRun {
  id: string;
  event_id: string;
  run_number: number;
  mode: RunMode;
  status: RunStatus;
  parent_run_id: string | null;
  workflow_id: string | null;
  workflow_name: string | null;
  workflow_version: number | null;
  mapping_versions_json: Record<string, unknown>;
  started_at: string | null;
  finished_at: string | null;
  steps: EventStep[];
  artifacts: Artifact[];
}

export interface EventTimeline {
  event: EventSummary;
  runs: EventRun[];
}

export interface ArtifactDiff {
  artifact_id: string;
  compare_with: string;
  added: Record<string, unknown>;
  removed: Record<string, unknown>;
  changed: Record<string, { from: unknown; to: unknown }>;
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');

  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (response.status === 204) return undefined as T;

  const text = await response.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text || null;
  }
  if (!response.ok) {
    const detail = typeof data === 'object' && data !== null && 'detail' in data ? (data as { detail: unknown }).detail : data;
    throw new ApiError(response.status, detail);
  }
  return data as T;
}

export function asJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}
