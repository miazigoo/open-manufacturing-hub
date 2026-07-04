import { request } from './client';

export interface DesignerBuildRequest {
  scenario_code: string;
  source: Record<string, unknown>;
  target: Record<string, unknown>;
  operation?: Record<string, unknown>;
  logic: Record<string, unknown>;
  test_payload?: unknown;
}

export interface DesignerBuildResponse {
  created: { endpoint_id: string; route_id: string; workflow_id: string; operation_template_id: string | null; test_case_id: string | null };
  endpoint_url: string;
  curl_example: string;
  onec_http_example: string;
  next_steps: string[];
}

export const integrationDesignerApi = {
  build: (payload: DesignerBuildRequest) => request<DesignerBuildResponse>('/api/integration-designer/build', { method: 'POST', body: JSON.stringify(payload) }),
};
