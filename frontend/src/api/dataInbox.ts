import { request } from './client';

export interface InboxField {
  path: string;
  type: string;
  required: boolean;
  default?: unknown;
}

export interface InboxTemplate {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  enabled: boolean;
  input_mode: string;
  schema_json: { fields: InboxField[] };
  missing_policy: string;
  storage_mode: string;
  storage_days: number;
  response_json: Record<string, unknown> | null;
  auth_token_set: boolean;
  created_at: string;
}

export type InboxTemplatePayload = Omit<InboxTemplate, 'id' | 'created_at' | 'auth_token_set'> & { auth_token?: string | null };

export interface InboxRecord {
  id: string;
  template_id: string;
  status: string;
  payload_json: Record<string, unknown>;
  fields_json: Record<string, unknown>;
  warnings_json: Array<{ path: string; message: string }>;
  source_ip: string | null;
  created_at: string;
}

export interface InboxRecordList {
  total: number;
  items: InboxRecord[];
}

export interface InboxTemplateTestResult {
  status: string;
  fields: Record<string, unknown>;
  warnings: Array<{ path: string; message: string }>;
  response: Record<string, unknown>;
}

export interface SqlQueryResult {
  columns: string[];
  rows: Array<Record<string, unknown>>;
  row_count: number;
  truncated: boolean;
  elapsed_ms: number;
}

export interface BackupRecord {
  id: string;
  backup_type: string;
  status: string;
  file_path: string | null;
  size_bytes: number | null;
  error_message: string | null;
  created_at: string;
}

export interface EnvironmentProfile {
  id: string;
  name: string;
  is_current: boolean;
  variables: Array<{ id: string; key: string; value_json: unknown }>;
}

export const dataInboxApi = {
  templates: () => request<InboxTemplate[]>('/api/inbox-templates'),
  createTemplate: (payload: Partial<InboxTemplatePayload>) => request<InboxTemplate>('/api/inbox-templates', { method: 'POST', body: JSON.stringify(payload) }),
  patchTemplate: (id: string, payload: Partial<InboxTemplatePayload>) => request<InboxTemplate>(`/api/inbox-templates/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteTemplate: (id: string) => request<void>(`/api/inbox-templates/${id}`, { method: 'DELETE' }),
  testTemplate: (id: string, payload: unknown) => request<InboxTemplateTestResult>(`/api/inbox-templates/${id}/test`, { method: 'POST', body: JSON.stringify({ payload }) }),
  records: (params: Record<string, string>) => request<InboxRecordList>(`/api/inbox-records?${new URLSearchParams(params).toString()}`),
  patchRecord: (id: string, payload: { payload_json?: Record<string, unknown>; fields_json?: Record<string, unknown> }) => request<InboxRecord>(`/api/inbox-records/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteRecord: (id: string) => request<void>(`/api/inbox-records/${id}`, { method: 'DELETE' }),
  resendRecord: (id: string, url: string) => request<{ success: boolean; status: string; message: string }>(`/api/inbox-records/${id}/resend`, { method: 'POST', body: JSON.stringify({ url }) }),
  exportUrl: (params: Record<string, string>) => `/api/inbox-records/export.csv${params ? `?${new URLSearchParams(params).toString()}` : ''}`,
  runSql: (query: string, limit = 200) => request<SqlQueryResult>('/api/sql-console/query', { method: 'POST', body: JSON.stringify({ query, limit }) }),
  backups: () => request<BackupRecord[]>('/api/production/exports'),
  createDbBackup: () => request<BackupRecord>('/api/production/backups/db', { method: 'POST' }),
  backupDownloadUrl: (id: string) => `/api/production/exports/${id}/download`,
  currentEnvironment: () => request<EnvironmentProfile | null>('/api/environments/current'),
  addVariable: (environmentId: string, key: string, value: unknown) => request<unknown>(`/api/environments/${environmentId}/variables`, { method: 'POST', body: JSON.stringify({ key, value_json: value }) }),
  patchVariable: (environmentId: string, key: string, value: unknown) => request<unknown>(`/api/environments/${environmentId}/variables/${key}`, { method: 'PATCH', body: JSON.stringify({ value_json: value }) }),
};
