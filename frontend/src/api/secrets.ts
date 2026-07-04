import { request } from './client';

export type SecretType = 'password' | 'api_token' | 'bearer_token' | 'basic_auth_password' | 'static_token' | 'webhook_secret' | 'private_key' | 'generic';

export interface SecretRead {
  id: string;
  name: string;
  description: string | null;
  secret_type: SecretType;
  value_preview: string | null;
  enabled: boolean;
  reference: { $secret: string };
  created_at: string;
  updated_at: string;
  last_used_at: string | null;
  rotated_at: string | null;
  created_by: string | null;
  updated_by: string | null;
}

export interface SecretPayload {
  name: string;
  description?: string | null;
  secret_type: SecretType;
  value: string;
}

export interface SecretReferenceStatus {
  name: string;
  status: 'ok' | 'missing' | 'disabled' | 'invalid';
  path: string;
  value_preview?: string | null;
}

export interface SecretConfigValidation {
  valid: boolean;
  references: SecretReferenceStatus[];
  raw_secret_warnings: string[];
}

export const secretTypes: SecretType[] = ['password', 'api_token', 'bearer_token', 'basic_auth_password', 'static_token', 'webhook_secret', 'private_key', 'generic'];

export const secretsApi = {
  list: () => request<SecretRead[]>('/api/secrets'),
  create: (payload: SecretPayload) => request<SecretRead>('/api/secrets', { method: 'POST', body: JSON.stringify(payload) }),
  patch: (id: string, payload: Partial<Omit<SecretPayload, 'value'>>) => request<SecretRead>(`/api/secrets/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  delete: (id: string) => request<void>(`/api/secrets/${id}`, { method: 'DELETE' }),
  rotate: (id: string, value: string) => request<SecretRead>(`/api/secrets/${id}/rotate`, { method: 'POST', body: JSON.stringify({ value }) }),
  enable: (id: string) => request<SecretRead>(`/api/secrets/${id}/enable`, { method: 'POST' }),
  disable: (id: string) => request<SecretRead>(`/api/secrets/${id}/disable`, { method: 'POST' }),
  validateConfig: (config: Record<string, unknown>) => request<SecretConfigValidation>('/api/secrets/validate-config', { method: 'POST', body: JSON.stringify({ config }) }),
};
