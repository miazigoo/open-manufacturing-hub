import { request } from './client';

export interface ScenarioRead {
  code: string;
  title: string;
  description: string;
  source: string;
  target: string;
  input_modes: string[];
  default_slug: string;
  event_type: string;
  entity_type: string | null;
  operation_code: string;
  sample_payload: unknown;
}

export interface ScenarioPreview {
  scenario: string;
  will_create: Record<string, number>;
  objects: Array<{ type: string; name: string }>;
}

export interface ScenarioInstallResponse {
  scenario: string;
  endpoint_id: string;
  route_id: string;
  workflow_id: string;
  operation_template_id: string | null;
  test_case_id: string | null;
  endpoint_url: string;
  curl_example: string;
  onec_http_example: string;
  next_steps: string[];
}

export const scenarioLibraryApi = {
  list: () => request<ScenarioRead[]>('/api/scenario-library'),
  preview: (code: string) => request<ScenarioPreview>(`/api/scenario-library/${code}/preview`, { method: 'POST' }),
  install: (code: string, payload: Record<string, unknown> = {}) => request<ScenarioInstallResponse>(`/api/scenario-library/${code}/install`, { method: 'POST', body: JSON.stringify(payload) }),
};
