import { request } from './client';

export type ConnectionProfileKind = 'onec_odata' | 'onec_http_service' | 'rest_api' | 'printer' | 'smb_share' | 'local_directory' | 'training_mock';

export interface ConnectionProfileHealth {
  status: string | null;
  message: string | null;
  checked_at: string | null;
}

export interface SecretReferenceRead {
  name: string;
  path: string;
}

export interface ConnectionProfile {
  id: string;
  connector_id: string;
  name: string;
  kind: ConnectionProfileKind;
  description: string | null;
  enabled: boolean;
  status: string;
  training: boolean;
  package_id: string | null;
  config_json: Record<string, unknown>;
  secret_refs: SecretReferenceRead[];
  warnings: string[];
  tags: string[];
  health: ConnectionProfileHealth;
  used_by: string[];
  read_only: boolean;
  created_at: string;
  updated_at: string;
}

export interface ConnectionProfilePayload {
  name: string;
  kind: ConnectionProfileKind;
  description?: string | null;
  enabled?: boolean;
  config_json: Record<string, unknown>;
  tags?: string[];
  package_id?: string | null;
}

export interface ConnectionProfileOption {
  id: string;
  profile_id: string;
  connector_id: string;
  label: string;
  name: string;
  kind: ConnectionProfileKind;
  enabled: boolean;
  training: boolean;
  base_url: string | null;
  details: Record<string, unknown>;
  tags: string[];
}

export interface ConnectionCenterOptions {
  profiles: ConnectionProfileOption[];
  by_kind: Record<string, ConnectionProfileOption[]>;
}

export interface ConnectionProfileTestRequest {
  dry_run?: boolean;
  confirm_write?: boolean;
  confirm_print?: boolean;
  resource?: string;
  top?: number | null;
  filter?: string | null;
  health_path?: string | null;
  custom_path?: string | null;
  payload?: Record<string, unknown>;
}

export interface ConnectionProfileTestResponse {
  success: boolean;
  status: string;
  message: string;
  profile_id: string;
  connector_id: string;
  kind: ConnectionProfileKind;
  dry_run: boolean;
  request: Record<string, unknown>;
  response: Record<string, unknown>;
  sample_items: Array<Record<string, unknown>>;
  warnings: string[];
}

export const connectionCenterApi = {
  profiles: () => request<ConnectionProfile[]>('/api/connection-center/profiles'),
  create: (payload: ConnectionProfilePayload) => request<ConnectionProfile>('/api/connection-center/profiles', { method: 'POST', body: JSON.stringify(payload) }),
  get: (id: string) => request<ConnectionProfile>(`/api/connection-center/profiles/${encodeURIComponent(id)}`),
  patch: (id: string, payload: Partial<ConnectionProfilePayload>) => request<ConnectionProfile>(`/api/connection-center/profiles/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  delete: (id: string) => request<void>(`/api/connection-center/profiles/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  test: (id: string, payload: ConnectionProfileTestRequest = {}) => request<ConnectionProfileTestResponse>(`/api/connection-center/profiles/${encodeURIComponent(id)}/test`, { method: 'POST', body: JSON.stringify(payload) }),
  enable: (id: string) => request<ConnectionProfile>(`/api/connection-center/profiles/${encodeURIComponent(id)}/enable`, { method: 'POST' }),
  disable: (id: string) => request<ConnectionProfile>(`/api/connection-center/profiles/${encodeURIComponent(id)}/disable`, { method: 'POST' }),
  options: () => request<ConnectionCenterOptions>('/api/connection-center/options'),
  odataOptions: () => request<ConnectionProfileOption[]>('/api/connection-center/options/odata'),
  onecHttpOptions: () => request<ConnectionProfileOption[]>('/api/connection-center/options/onec-http'),
  restOptions: () => request<ConnectionProfileOption[]>('/api/connection-center/options/rest'),
  printerOptions: () => request<ConnectionProfileOption[]>('/api/connection-center/options/printers'),
  fileTargetOptions: () => request<ConnectionProfileOption[]>('/api/connection-center/options/file-targets'),
};
