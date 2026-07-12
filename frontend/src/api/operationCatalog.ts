import { request } from './client';

export type OperationKind = 'rest_api_operation' | 'onec_http_operation' | 'printer_operation' | 'file_operation' | 'training_operation';
export type OperationBodyType = 'json' | 'xml' | 'raw_text' | 'form' | 'none';
export type OperationMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
export type SuccessConditionType = 'http_status_2xx' | 'http_status_equals' | 'json_path_equals' | 'json_path_exists' | 'response_contains_text' | 'always_success';

export interface OperationProfilePayload {
  name: string;
  code: string;
  kind: OperationKind;
  connection_profile_id?: string | null;
  request_contract_id?: string | null;
  response_contract_id?: string | null;
  description?: string | null;
  enabled?: boolean;
  method?: OperationMethod | null;
  path?: string | null;
  full_url?: string | null;
  headers_json?: Record<string, unknown> | null;
  body_type?: OperationBodyType | null;
  request_template_json?: Record<string, unknown> | unknown[] | null;
  request_template_text?: string | null;
  response_body_type?: OperationBodyType | null;
  success_condition_json?: Record<string, unknown> | null;
  response_extractors_json?: Array<Record<string, unknown>> | null;
  sample_request_json?: Record<string, unknown> | unknown[] | null;
  sample_response_json?: Record<string, unknown> | unknown[] | string | null;
  timeout_seconds?: number | null;
  tags_json?: string[] | null;
  package_id?: string | null;
}

export interface OperationProfile extends OperationProfilePayload {
  id: string;
  enabled: boolean;
  connection_name: string | null;
  connection_kind: string | null;
  final_url: string | null;
  used_by: string[];
  last_test_at: string | null;
  last_test_success: boolean | null;
  created_at: string;
  updated_at: string;
}

export interface OperationProfileOption {
  id: string;
  label: string;
  name: string;
  code: string;
  kind: OperationKind;
  connection_profile_id: string | null;
  request_contract_id: string | null;
  response_contract_id: string | null;
  connection_name: string | null;
  connection_kind: string | null;
  method: string | null;
  path: string | null;
  full_url: string | null;
  final_url: string | null;
  headers_json: Record<string, unknown> | null;
  body_type: string | null;
  response_body_type: string | null;
  timeout_seconds: number | null;
  tags: string[];
  used_by: string[];
}

export interface OperationCatalogOptions {
  operations: OperationProfileOption[];
  by_kind: Record<string, OperationProfileOption[]>;
}

export interface OperationTestRequest {
  dry_run?: boolean;
  confirm_real_request?: boolean;
  mock_response?: boolean;
  request_body?: unknown;
  response_body?: unknown;
  http_status?: number;
}

export interface OperationTestResponse {
  success: boolean;
  status: string;
  message: string;
  operation_id: string;
  dry_run: boolean;
  final_url: string | null;
  method: string | null;
  request: Record<string, unknown>;
  response: Record<string, unknown>;
  http_status: number | null;
  response_body: unknown;
  success_condition_result: Record<string, unknown> | null;
  extracted: Record<string, unknown>;
  errors: string[];
  warnings: string[];
}

export interface InstallPresetsResponse {
  installed: OperationProfile[];
  skipped: string[];
}

export const operationCatalogApi = {
  list: (params: { kind?: string; connection_profile_id?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.kind) query.set('kind', params.kind);
    if (params.connection_profile_id) query.set('connection_profile_id', params.connection_profile_id);
    const suffix = query.toString() ? `?${query.toString()}` : '';
    return request<OperationProfile[]>(`/api/operation-catalog/operations${suffix}`);
  },
  create: (payload: OperationProfilePayload) => request<OperationProfile>('/api/operation-catalog/operations', { method: 'POST', body: JSON.stringify(payload) }),
  get: (id: string) => request<OperationProfile>(`/api/operation-catalog/operations/${encodeURIComponent(id)}`),
  patch: (id: string, payload: Partial<OperationProfilePayload>) => request<OperationProfile>(`/api/operation-catalog/operations/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  delete: (id: string) => request<void>(`/api/operation-catalog/operations/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  test: (id: string, payload: OperationTestRequest = {}) => request<OperationTestResponse>(`/api/operation-catalog/operations/${encodeURIComponent(id)}/test`, { method: 'POST', body: JSON.stringify(payload) }),
  enable: (id: string) => request<OperationProfile>(`/api/operation-catalog/operations/${encodeURIComponent(id)}/enable`, { method: 'POST' }),
  disable: (id: string) => request<OperationProfile>(`/api/operation-catalog/operations/${encodeURIComponent(id)}/disable`, { method: 'POST' }),
  options: () => request<OperationCatalogOptions>('/api/operation-catalog/options'),
  restOptions: () => request<OperationProfileOption[]>('/api/operation-catalog/options/rest'),
  onecHttpOptions: () => request<OperationProfileOption[]>('/api/operation-catalog/options/onec-http'),
  installPresets: () => request<InstallPresetsResponse>('/api/operation-catalog/install-presets', { method: 'POST' }),
};
