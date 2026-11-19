import { request } from './client';

export interface ProductionStatus {
  app_env: string;
  production_mode: boolean;
  version: string;
  database_revision: string | null;
  packages: Array<Record<string, unknown>>;
  warnings: string[];
  update_mode_enabled: boolean;
  current_environment: Record<string, unknown> | null;
  pending_change_sets: number;
  last_applied_change_set: Record<string, unknown> | null;
}

export interface SystemSnapshot {
  app_version: string;
  backend_version: string;
  frontend_version: string | null;
  app_env: string;
  production_mode: boolean;
  database_revision: string | null;
  migration_head: string | null;
  packages: Array<Record<string, unknown>>;
  counts: Record<string, number>;
  queue: Record<string, number>;
  dlq_count: number;
  auth_users_count: number | null;
  current_environment: Record<string, unknown> | null;
  pending_change_sets: number;
  last_applied_change_set: Record<string, unknown> | null;
  last_backup_at: string | null;
  health: Record<string, unknown>;
  warnings: string[];
  update_mode: { enabled: boolean; message: string | null; enabled_at: string | null; enabled_by: string | null };
}

export interface BackupRecord {
  id: string;
  backup_type: string;
  status: string;
  file_path: string | null;
  size_bytes: number | null;
  created_at: string;
  finished_at: string | null;
  created_by: string | null;
  error_message: string | null;
  metadata_json: Record<string, unknown> | null;
}

export interface UpdateCheck {
  safe_to_update: boolean;
  checks: Array<{ name: string; status: 'ok' | 'warning' | 'error'; message: string | null; details?: Record<string, unknown> | null }>;
  required_actions: string[];
}

export interface ImportPreview {
  valid: boolean;
  mode: string;
  will_create: Record<string, number>;
  will_update: Record<string, number>;
  conflicts: Array<Record<string, unknown>>;
  warnings: string[];
  applied?: boolean;
}

export interface ProductionDoctor {
  generated_at: string;
  app_env: string;
  status: 'ok' | 'warning' | 'error';
  summary: Record<string, number>;
  checks: Array<{ name: string; status: 'ok' | 'warning' | 'error'; message: string | null; details?: Record<string, unknown> | null }>;
  counts: Record<string, number>;
}

export interface FirstRunChecklist {
  generated_at: string;
  complete: boolean;
  items: Array<{ code: string; title: string; status: 'ok' | 'warning' | 'action_required' | 'manual'; details: Record<string, unknown> }>;
}

export const productionApi = {
  status: () => request<ProductionStatus>('/api/production/status'),
  snapshot: () => request<SystemSnapshot>('/api/production/snapshot'),
  doctor: () => request<ProductionDoctor>('/api/production/doctor'),
  checklist: () => request<FirstRunChecklist>('/api/production/checklist'),
  exports: (backup_type?: string, limit?: number) => {
    const params = new URLSearchParams();
    if (backup_type) params.set('backup_type', backup_type);
    if (limit) params.set('limit', String(limit));
    const qs = params.toString();
    return request<BackupRecord[]>(`/api/production/exports${qs ? `?${qs}` : ''}`);
  },
  exportConfig: () => request<{ export_id: string; file_name: string; size_bytes: number; warnings: string[]; download_url: string }>('/api/production/export-config', { method: 'POST', body: JSON.stringify({ secrets_policy: 'masked' }) }),
  previewImport: (payload: Record<string, unknown>, mode: string) => request<ImportPreview>('/api/production/import-config/preview', { method: 'POST', body: JSON.stringify({ export: payload, mode }) }),
  applyImport: (payload: Record<string, unknown>, mode: string) => request<ImportPreview>('/api/production/import-config/apply', { method: 'POST', body: JSON.stringify({ export: payload, mode }) }),
  preUpdateCheck: () => request<UpdateCheck>('/api/production/pre-update-check', { method: 'POST' }),
  postUpdateCheck: () => request<UpdateCheck>('/api/production/post-update-check', { method: 'POST' }),
  updateMode: () => request<{ enabled: boolean; message: string | null; enabled_at: string | null; enabled_by: string | null }>('/api/production/update-mode'),
  enableUpdateMode: () => request<{ enabled: boolean; message: string | null }>('/api/production/update-mode/enable', { method: 'POST', body: JSON.stringify({ message: 'Update mode enabled from UI', enabled_by: 'ui' }) }),
  disableUpdateMode: () => request<{ enabled: boolean; message: string | null }>('/api/production/update-mode/disable', { method: 'POST' }),
};
