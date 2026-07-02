import { request } from './client';

export interface MappingVersionPayload {
  rules_json: Array<Record<string, unknown>>;
  source_schema_json?: Record<string, unknown>;
  target_schema_json?: Record<string, unknown>;
  notes?: string | null;
}

export interface MappingVersion extends Required<Omit<MappingVersionPayload, 'notes'>> {
  id: string;
  mapping_id: string;
  version: number;
  notes: string | null;
  created_at: string;
}

export interface MappingDefinition {
  id: string;
  name: string;
  description: string | null;
  source_entity: string | null;
  target_entity: string | null;
  created_at: string;
  updated_at: string;
  versions: MappingVersion[];
}

export interface MappingPayload {
  name: string;
  description?: string | null;
  source_entity?: string | null;
  target_entity?: string | null;
  initial_version: MappingVersionPayload;
}

export interface MappingValidation {
  valid: boolean;
  errors: string[];
  warnings: string[];
  preview: Record<string, unknown> | null;
}

export interface MappingDiff {
  mapping_id: string;
  left_version: number;
  right_version: number;
  added: Array<Record<string, unknown>>;
  removed: Array<Record<string, unknown>>;
  changed: Array<Record<string, unknown>>;
}

export interface MappingPreset {
  name: string;
  description?: string;
  source_entity?: string;
  target_entity?: string;
  rules_json: Array<Record<string, unknown>>;
}

export const mappingsApi = {
  list: () => request<MappingDefinition[]>('/api/mappings'),
  presets: () => request<MappingPreset[]>('/api/mappings/presets'),
  installPresets: () => request<MappingDefinition[]>('/api/mappings/presets/install', { method: 'POST' }),
  create: (payload: MappingPayload) => request<MappingDefinition>('/api/mappings', { method: 'POST', body: JSON.stringify(payload) }),
  delete: (id: string) => request<void>(`/api/mappings/${id}`, { method: 'DELETE' }),
  createVersion: (id: string, payload: MappingVersionPayload) => request<MappingVersion>(`/api/mappings/${id}/versions`, { method: 'POST', body: JSON.stringify(payload) }),
  cloneVersion: (id: string, version: number) => request<MappingVersion>(`/api/mappings/${id}/versions/${version}/clone`, { method: 'POST', body: JSON.stringify({}) }),
  compare: (id: string, leftVersion: number, rightVersion: number) => request<MappingDiff>(`/api/mappings/${id}/compare?left_version=${leftVersion}&right_version=${rightVersion}`),
  validate: (rules_json: Array<Record<string, unknown>>, sample_payload?: Record<string, unknown>) =>
    request<MappingValidation>('/api/mappings/validate', { method: 'POST', body: JSON.stringify({ rules_json, sample_payload }) }),
  execute: (id: string, version: number, payload: Record<string, unknown>) =>
    request<{ output: Record<string, unknown> }>(`/api/mappings/${id}/versions/${version}/execute`, { method: 'POST', body: JSON.stringify({ payload }) }),
};
