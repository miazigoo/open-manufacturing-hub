import { request } from './client';

export type MappingSourceType = 'variable' | 'constant' | 'template' | 'dynamic_object_entry';

export interface MappingFieldRule {
  target_path: string;
  source_type: MappingSourceType;
  source?: string | null;
  value?: unknown;
  preserve_type?: boolean;
  allow_duplicate?: boolean;
}

export interface MappingDynamicEntryRule {
  object_path: string;
  key_source: string;
  value_source: string;
  preserve_type?: boolean;
}

export interface MappingJson {
  version: 1;
  target_contract_code?: string | null;
  fields: MappingFieldRule[];
  dynamic_entries: MappingDynamicEntryRule[];
}

export interface MappingIssue {
  error_code: string;
  message: string;
  path?: string | null;
  severity: 'error' | 'warning';
}

export interface MappingProfilePayload {
  name: string;
  code: string;
  source_context_json?: Record<string, unknown> | null;
  target_contract_id?: string | null;
  operation_profile_id?: string | null;
  mapping_json: MappingJson | Record<string, unknown>;
  description?: string | null;
  package_id?: string | null;
}

export interface MappingProfile extends MappingProfilePayload {
  id: string;
  target_contract_name: string | null;
  target_contract_code: string | null;
  operation_profile_name: string | null;
  operation_profile_code: string | null;
  status: string;
  used_by: string[];
  created_at: string;
  updated_at: string;
}

export interface MappingPreviewRequest {
  mapping_profile_id?: string | null;
  mapping_json?: MappingJson | Record<string, unknown> | null;
  source_context_json?: Record<string, unknown> | null;
  target_contract_id?: string | null;
}

export interface MappingRenderResponse {
  success: boolean;
  payload: unknown;
  preview: unknown;
  errors: MappingIssue[];
  warnings: MappingIssue[];
  summary: { root_type: string; top_level_keys: string[]; truncated_arrays: Record<string, number> } | null;
}

export interface MappingValidationResponse {
  valid: boolean;
  errors: MappingIssue[];
  warnings: MappingIssue[];
}

export interface MappingPresetsResponse {
  contracts: Array<Record<string, unknown>>;
  mappings: Array<Record<string, unknown>>;
}

export interface InstallMappingPresetsResponse {
  contracts: unknown[];
  mappings: MappingProfile[];
  linked_operations: string[];
}

export const mappingCenterApi = {
  list: (params: { operation_profile_id?: string; target_contract_id?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.operation_profile_id) query.set('operation_profile_id', params.operation_profile_id);
    if (params.target_contract_id) query.set('target_contract_id', params.target_contract_id);
    const suffix = query.toString() ? `?${query.toString()}` : '';
    return request<MappingProfile[]>(`/api/mapping-center/mappings${suffix}`);
  },
  create: (payload: MappingProfilePayload) => request<MappingProfile>('/api/mapping-center/mappings', { method: 'POST', body: JSON.stringify(payload) }),
  get: (id: string) => request<MappingProfile>(`/api/mapping-center/mappings/${encodeURIComponent(id)}`),
  patch: (id: string, payload: Partial<MappingProfilePayload>) => request<MappingProfile>(`/api/mapping-center/mappings/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  delete: (id: string) => request<void>(`/api/mapping-center/mappings/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  preview: (payload: MappingPreviewRequest) => request<MappingRenderResponse>('/api/mapping-center/preview', { method: 'POST', body: JSON.stringify(payload) }),
  validate: (payload: MappingPreviewRequest) => request<MappingValidationResponse>('/api/mapping-center/validate', { method: 'POST', body: JSON.stringify(payload) }),
  presets: () => request<MappingPresetsResponse>('/api/mapping-center/presets'),
  installPresets: () => request<InstallMappingPresetsResponse>('/api/mapping-center/install-presets', { method: 'POST' }),
};
