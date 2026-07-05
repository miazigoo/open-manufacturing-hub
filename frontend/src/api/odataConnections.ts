import { request } from './client';

export interface ODataConnection {
  id: string;
  connector_id: string;
  name: string;
  description: string | null;
  base_url: string;
  auth_type: string;
  username: string | null;
  password_secret: string | null;
  timeout_seconds: number;
  verify_ssl: boolean;
  default_top: number;
  max_pages: number;
  tags: string[];
  enabled: boolean;
  status: string;
  last_health_status: string | null;
  last_health_message: string | null;
  last_health_at: string | null;
  config_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ODataConnectionPayload {
  name: string;
  description?: string | null;
  connector_id?: string | null;
  base_url: string;
  auth_type: string;
  username?: string | null;
  password?: string | null;
  password_secret?: string | null;
  timeout_seconds: number;
  verify_ssl: boolean;
  default_top: number;
  max_pages: number;
  tags: string[];
  enabled?: boolean;
}

export interface ODataConnectionOption {
  id: string;
  connector_id: string;
  label: string;
  base_url: string;
  enabled: boolean;
  tags: string[];
}

export interface ODataConnectionTestResponse {
  success: boolean;
  status: string;
  message: string;
  connector_id: string;
  request: Record<string, unknown>;
  response: Record<string, unknown>;
  sample_items: Array<Record<string, unknown>>;
}

export const odataConnectionsApi = {
  list: () => request<ODataConnection[]>('/api/odata-connections'),
  options: () => request<ODataConnectionOption[]>('/api/odata-connections/options'),
  get: (id: string) => request<ODataConnection>(`/api/odata-connections/${id}`),
  create: (payload: ODataConnectionPayload) => request<ODataConnection>('/api/odata-connections', { method: 'POST', body: JSON.stringify(payload) }),
  patch: (id: string, payload: Partial<ODataConnectionPayload>) => request<ODataConnection>(`/api/odata-connections/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  delete: (id: string) => request<void>(`/api/odata-connections/${id}`, { method: 'DELETE' }),
  test: (id: string, payload: { resource?: string; top?: number | null; filter?: string | null } = {}) => request<ODataConnectionTestResponse>(`/api/odata-connections/${id}/test`, { method: 'POST', body: JSON.stringify(payload) }),
};
