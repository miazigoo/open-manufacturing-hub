import { request } from './client';

export interface IntegrationFlow {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  enabled: boolean;
  source_type: string;
  target_type: string;
  endpoint_id: string | null;
  route_id: string | null;
  workflow_id: string | null;
  compiled_workflow_id: string | null;
  matcher_group_json: Record<string, unknown>;
  action_json: Record<string, unknown>;
  response_config_json: Record<string, unknown>;
  builder_json: Record<string, unknown> | null;
  last_validation_json: Record<string, unknown> | null;
  compiled_at: string | null;
  test_payload_json: Record<string, unknown> | null;
  test_payload_text: string | null;
  endpoint_url: string;
  curl_example: string;
  onec_http_example: string;
  updated_at: string;
}

export interface FlowCreatePayload {
  name: string;
  slug: string;
  description?: string | null;
  enabled?: boolean;
  source_type: string;
  target_type: string;
  endpoint: { input_mode: string; response_mode: string; processing_mode?: string; auth_mode: string; auth_config_json: Record<string, unknown> };
  matcher_group_json: Record<string, unknown>;
  action_json: Record<string, unknown>;
  response_config_json?: Record<string, unknown>;
  builder_json?: Record<string, unknown> | null;
  test_payload_json?: Record<string, unknown> | null;
  test_payload_text?: string | null;
}

export interface MatcherTestResponse { matched: boolean; trace: Array<Record<string, unknown>> }

export interface FlowBuilderPreviewResponse {
  valid: boolean;
  variables: Record<string, unknown>;
  steps: Array<{ id: string; type: string; name?: string | null; status: string; request_preview?: unknown; result_preview?: unknown; error?: Record<string, unknown> | null }>;
  final_payload_preview: unknown;
  target_request_preview: unknown;
  errors: Array<Record<string, unknown>>;
}

export interface FlowCompileResponse {
  valid: boolean;
  workflow_id: string | null;
  steps_json: Array<Record<string, unknown>>;
  validation: Record<string, unknown>;
}

export const integrationFlowsApi = {
  list: () => request<IntegrationFlow[]>('/api/integration-flows'),
  create: (payload: FlowCreatePayload) => request<IntegrationFlow>('/api/integration-flows', { method: 'POST', body: JSON.stringify(payload) }),
  patch: (id: string, payload: Partial<IntegrationFlow>) => request<IntegrationFlow>(`/api/integration-flows/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  duplicate: (id: string) => request<IntegrationFlow>(`/api/integration-flows/${id}/duplicate`, { method: 'POST' }),
  export: (id: string) => request<Record<string, unknown>>(`/api/integration-flows/${id}/export`),
  test: (id: string, payload: { input_mode: string; payload_json?: Record<string, unknown> | null; payload_text?: string | null; headers_json?: Record<string, string>; dry_run?: boolean }) => request<Record<string, unknown>>(`/api/integration-flows/${id}/test`, { method: 'POST', body: JSON.stringify(payload) }),
  installMarkingPool: () => request<IntegrationFlow>('/api/integration-flows/presets/marking-pool-to-internal-service/install', { method: 'POST' }),
  installOneCChzPoolDelivery: () => request<IntegrationFlow>('/api/integration-flows/presets/onec-chz-pool-delivery/install', { method: 'POST' }),
  installTwoODataToEndpoint: () => request<IntegrationFlow>('/api/integration-flows/presets/onec-post-two-odata-to-endpoint/install', { method: 'POST' }),
  installOperationKeyODataChain: () => request<IntegrationFlow>('/api/integration-flows/presets/operation-key-odata-chain/install', { method: 'POST' }),
  testMatcher: (payload: { input_mode: string; payload?: unknown; text?: string | null; headers?: Record<string, string>; query?: Record<string, string>; matcher_group: Record<string, unknown> }) => request<MatcherTestResponse>('/api/matchers/test', { method: 'POST', body: JSON.stringify(payload) }),
  getBuilder: (id: string) => request<{ flow_id: string; builder_json: Record<string, unknown>; last_validation_json: Record<string, unknown> }>(`/api/flow-builder/flows/${id}`),
  saveBuilder: (id: string, payload: { builder_json: Record<string, unknown>; sample_request?: Record<string, unknown>; run_real_queries?: boolean }) =>
    request<IntegrationFlow>(`/api/flow-builder/flows/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  previewBuilder: (payload: { builder_json: Record<string, unknown>; sample_request: Record<string, unknown>; run_real_queries?: boolean }) =>
    request<FlowBuilderPreviewResponse>('/api/flow-builder/preview', { method: 'POST', body: JSON.stringify(payload) }),
  compileBuilder: (id: string) => request<FlowCompileResponse>(`/api/flow-builder/flows/${id}/compile`, { method: 'POST' }),
};
