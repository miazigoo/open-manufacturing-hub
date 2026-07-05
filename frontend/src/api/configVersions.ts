import { request } from './client';

export type ConfigObjectType =
  | 'integration_flow'
  | 'workflow'
  | 'mapping'
  | 'business_rule'
  | 'resolver'
  | 'operation_template'
  | 'odata_lookup_template'
  | 'route'
  | 'endpoint';

export type ConfigVersionStatus = 'draft' | 'active' | 'archived' | 'rollback' | 'rejected';
export type ConfigVersionTestStatus = 'not_tested' | 'passed' | 'failed' | 'warning';

export interface ConfigVersion {
  id: string;
  object_type: ConfigObjectType | string;
  object_id: string;
  object_name: string | null;
  version_number: number;
  status: ConfigVersionStatus;
  config_json: Record<string, unknown>;
  metadata_json: Record<string, unknown> | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  published_by: string | null;
  published_at: string | null;
  archived_at: string | null;
  rollback_of_version_id: string | null;
  test_status: ConfigVersionTestStatus;
  last_test_event_id: string | null;
  last_test_run_at: string | null;
  last_test_error: string | null;
  comment: string | null;
}

export interface ConfigVersionsResponse {
  object_type: ConfigObjectType | string;
  object_id: string;
  active_version: ConfigVersion | null;
  draft_version: ConfigVersion | null;
  versions: ConfigVersion[];
}

export interface ConfigDiffEntry {
  path: string;
  before?: unknown;
  after?: unknown;
  value?: unknown;
}

export interface ConfigDiffResponse {
  from_version_id: string;
  to_version_id: string;
  added: ConfigDiffEntry[];
  removed: ConfigDiffEntry[];
  changed: ConfigDiffEntry[];
}

export interface ConfigVersionTestResponse {
  test_status: ConfigVersionTestStatus;
  event_id: string | null;
  timeline_url: string | null;
  result: Record<string, unknown>;
  error: string | null;
}

interface DraftPayload {
  config_json?: Record<string, unknown>;
  metadata_json?: Record<string, unknown>;
  comment?: string | null;
}

const base = (objectType: ConfigObjectType | string, objectId: string) => `/api/config/${encodeURIComponent(objectType)}/${encodeURIComponent(objectId)}`;

export const configVersionQueryKey = (objectType: ConfigObjectType | string, objectId?: string) => ['config-versions', objectType, objectId] as const;

export const configVersionsApi = {
  versions: (objectType: ConfigObjectType | string, objectId: string) => request<ConfigVersionsResponse>(`${base(objectType, objectId)}/versions`),
  get: (objectType: ConfigObjectType | string, objectId: string, versionId: string) => request<ConfigVersion>(`${base(objectType, objectId)}/versions/${encodeURIComponent(versionId)}`),
  createDraft: (objectType: ConfigObjectType | string, objectId: string, payload: DraftPayload) => request<ConfigVersion>(`${base(objectType, objectId)}/draft`, { method: 'POST', body: JSON.stringify(payload) }),
  patchDraft: (objectType: ConfigObjectType | string, objectId: string, payload: DraftPayload) => request<ConfigVersion>(`${base(objectType, objectId)}/draft`, { method: 'PATCH', body: JSON.stringify(payload) }),
  discardDraft: (objectType: ConfigObjectType | string, objectId: string) => request<void>(`${base(objectType, objectId)}/draft`, { method: 'DELETE' }),
  publish: (objectType: ConfigObjectType | string, objectId: string, versionId: string, comment?: string | null) => request<ConfigVersion>(`${base(objectType, objectId)}/publish`, { method: 'POST', body: JSON.stringify({ version_id: versionId, comment, confirm_untested: true }) }),
  rollback: (objectType: ConfigObjectType | string, objectId: string, targetVersionId: string, comment?: string | null) => request<ConfigVersion>(`${base(objectType, objectId)}/rollback`, { method: 'POST', body: JSON.stringify({ target_version_id: targetVersionId, comment, confirm_untested: true }) }),
  diff: (objectType: ConfigObjectType | string, objectId: string, fromVersion: string, toVersion: string) => request<ConfigDiffResponse>(`${base(objectType, objectId)}/diff?from_version=${encodeURIComponent(fromVersion)}&to_version=${encodeURIComponent(toVersion)}`),
  test: (objectType: ConfigObjectType | string, objectId: string, versionId: string, payload: Record<string, unknown> = {}) => request<ConfigVersionTestResponse>(`${base(objectType, objectId)}/versions/${encodeURIComponent(versionId)}/test`, { method: 'POST', body: JSON.stringify(payload) }),
};
