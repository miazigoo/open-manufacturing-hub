import { request } from './client';

export type EnvironmentType = 'development' | 'test' | 'staging' | 'production' | 'custom';

export interface EnvironmentVariable {
  id: string;
  environment_id: string;
  key: string;
  value_json: unknown;
  secret_ref: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface EnvironmentProfile {
  id: string;
  name: string;
  code: string;
  environment_type: EnvironmentType;
  description: string | null;
  is_current: boolean;
  base_url: string | null;
  created_at: string;
  updated_at: string;
  variables: EnvironmentVariable[];
}

export interface EnvironmentPayload {
  name: string;
  code: string;
  environment_type: EnvironmentType;
  description?: string | null;
  is_current?: boolean;
  base_url?: string | null;
  variables?: Array<{ key: string; value_json?: unknown; secret_ref?: string | null; description?: string | null }>;
}

export const environmentsApi = {
  list: () => request<EnvironmentProfile[]>('/api/environments'),
  current: () => request<EnvironmentProfile | null>('/api/environments/current'),
  create: (payload: EnvironmentPayload) => request<EnvironmentProfile>('/api/environments', { method: 'POST', body: JSON.stringify(payload) }),
  patch: (id: string, payload: Partial<EnvironmentPayload>) => request<EnvironmentProfile>(`/api/environments/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  setCurrent: (id: string) => request<EnvironmentProfile>(`/api/environments/${id}/set-current`, { method: 'POST' }),
  remove: (id: string) => request<void>(`/api/environments/${id}`, { method: 'DELETE' }),
  upsertVariable: (environmentId: string, payload: { key: string; value_json?: unknown; secret_ref?: string | null; description?: string | null }) =>
    request<EnvironmentVariable>(`/api/environments/${environmentId}/variables`, { method: 'POST', body: JSON.stringify(payload) }),
  deleteVariable: (environmentId: string, key: string) => request<void>(`/api/environments/${environmentId}/variables/${encodeURIComponent(key)}`, { method: 'DELETE' }),
};
