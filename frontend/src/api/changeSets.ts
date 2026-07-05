import { request } from './client';

export type ChangeSetStatus = 'draft' | 'exported' | 'import_previewed' | 'applied' | 'failed' | 'rolled_back';

export interface ChangeSetItem {
  id: string;
  change_set_id: string;
  object_type: string;
  object_id: string | null;
  object_name: string | null;
  operation: string;
  config_json: Record<string, unknown>;
  version_id: string | null;
  package_id: string | null;
  dependencies_json: Record<string, unknown> | null;
  created_at: string;
}

export interface ChangeSet {
  id: string;
  name: string;
  description: string | null;
  source_environment: string | null;
  target_environment: string | null;
  status: ChangeSetStatus;
  created_by: string | null;
  created_at: string;
  exported_at: string | null;
  applied_at: string | null;
  metadata_json: Record<string, unknown> | null;
  items: ChangeSetItem[];
}

export interface ChangeSetExport {
  omh_change_set_version: 1;
  name: string;
  description: string | null;
  created_at: string;
  source_environment: string | null;
  required_packages: Array<Record<string, unknown>>;
  items: Array<Record<string, unknown>>;
  secrets_policy: string;
  warnings: string[];
}

export interface ChangeSetPreview {
  valid: boolean;
  change_set_id: string | null;
  will_create: Array<Record<string, unknown>>;
  will_update: Array<Record<string, unknown>>;
  conflicts: Array<Record<string, unknown>>;
  missing_packages: Array<Record<string, unknown>>;
  missing_secrets: Array<Record<string, unknown>>;
  missing_environment_variables: Array<Record<string, unknown>>;
  warnings: string[];
  applied?: boolean;
  applied_change_set_id?: string | null;
  applied_items?: Array<Record<string, unknown>>;
  smoke?: Record<string, unknown> | null;
}

export interface ChangeSetMapping {
  connector_mapping?: Record<string, string>;
  secret_mapping?: Record<string, string>;
  environment_variables?: Record<string, unknown>;
  allow_conflicts?: boolean;
  run_smoke_tests?: boolean;
}

export const changeSetsApi = {
  list: () => request<ChangeSet[]>('/api/change-sets'),
  get: (id: string) => request<ChangeSet>(`/api/change-sets/${id}`),
  createFromDrafts: (payload: { name: string; description?: string | null; object_refs: Array<{ object_type: string; object_id: string }>; include_dependencies?: boolean }) =>
    request<ChangeSet>('/api/change-sets/from-drafts', { method: 'POST', body: JSON.stringify(payload) }),
  export: (id: string) => request<ChangeSetExport>(`/api/change-sets/${id}/export`),
  previewImport: (change_set: Record<string, unknown>, mapping: ChangeSetMapping = {}) =>
    request<ChangeSetPreview>('/api/change-sets/import/preview', { method: 'POST', body: JSON.stringify({ change_set, mapping }) }),
  applyImport: (change_set: Record<string, unknown>, mapping: ChangeSetMapping = {}) =>
    request<ChangeSetPreview>('/api/change-sets/import/apply', { method: 'POST', body: JSON.stringify({ change_set, mapping }) }),
  runSmokeTests: (id: string) => request<Record<string, unknown>>(`/api/change-sets/${id}/run-smoke-tests`, { method: 'POST' }),
};
