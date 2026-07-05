import { request } from './client';

export interface TrainingExample {
  id: string;
  title: Record<string, string>;
  description: Record<string, string>;
  endpoint_slug: string;
  method: string;
  input_mode: string;
  headers: Record<string, string>;
  body?: Record<string, unknown> | null;
  body_text?: string | null;
  expected: Record<string, unknown>;
  runnable: boolean;
  requires_setup: boolean;
}

export interface TrainingStatus {
  package: { installed: boolean; enabled: boolean; status: string | null };
  sandbox_installed: boolean;
  connectors: Array<{ id: string; name: string; connector_type: string; direction: string; enabled: boolean; status: string; base_url?: string | null }>;
  flows: Array<{ id: string; name: string; slug: string; endpoint_url: string }>;
  test_cases: Array<{ id: string; name: string; endpoint_id: string | null; last_run_status: string | null }>;
  examples: TrainingExample[];
}

export interface TrainingRunResult {
  success: boolean;
  example_id: string;
  requires_setup: boolean;
  dry_run: boolean;
  response: Record<string, unknown>;
  event_id: string | null;
  message_id: string | null;
  timeline_url: string | null;
  external_error: Record<string, unknown> | null;
}

export const trainingApi = {
  status: () => request<TrainingStatus>('/api/training/status'),
  install: () => request<TrainingStatus>('/api/training/install', { method: 'POST' }),
  reset: () => request<Record<string, unknown>>('/api/training/reset', { method: 'POST' }),
  examples: () => request<TrainingExample[]>('/api/training/examples'),
  example: (id: string) => request<TrainingExample>(`/api/training/examples/${encodeURIComponent(id)}`),
  runExample: (id: string) => request<TrainingRunResult>(`/api/training/examples/${encodeURIComponent(id)}/run`, { method: 'POST' }),
  openTestConsole: (id: string) => request<{ example: TrainingExample; url: string }>(`/api/training/examples/${encodeURIComponent(id)}/open-test-console`, { method: 'POST' }),
};

