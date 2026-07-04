import { EventRun, request, RunStatus } from './client';
import { MappingVersion } from './mappings';

export interface WorkflowDefinition {
  id: string;
  name: string;
  description: string | null;
  event_type: string | null;
  source_system: string | null;
  target_system: string | null;
  entity_type: string | null;
  version: number;
  enabled: boolean;
  steps_json: Array<string | Record<string, unknown>>;
  validation_json: Record<string, unknown>;
  source_mapping_version_id: string | null;
  target_mapping_version_id: string | null;
  source_mapping_version: MappingVersion | null;
  target_mapping_version: MappingVersion | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowPayload {
  name: string;
  description?: string | null;
  event_type?: string | null;
  source_system?: string | null;
  target_system?: string | null;
  entity_type?: string | null;
  version?: number;
  enabled?: boolean;
  steps_json?: Array<string | Record<string, unknown>>;
  validation_json?: Record<string, unknown>;
  source_mapping_version_id?: string | null;
  target_mapping_version_id?: string | null;
}

export interface WorkflowValidation { valid: boolean; errors: Array<{ step: string | null; message: string }> }

export interface WorkflowDryRunResponse {
  workflow_id: string;
  workflow_name: string;
  status: RunStatus;
  run: EventRun;
}

export const workflowsApi = {
  list: () => request<WorkflowDefinition[]>('/api/workflows'),
  create: (payload: WorkflowPayload) => request<WorkflowDefinition>('/api/workflows', { method: 'POST', body: JSON.stringify(payload) }),
  patch: (id: string, payload: Partial<WorkflowPayload>) => request<WorkflowDefinition>(`/api/workflows/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  delete: (id: string) => request<void>(`/api/workflows/${id}`, { method: 'DELETE' }),
  enable: (id: string) => request<WorkflowDefinition>(`/api/workflows/${id}/enable`, { method: 'POST' }),
  disable: (id: string) => request<WorkflowDefinition>(`/api/workflows/${id}/disable`, { method: 'POST' }),
  dryRun: (id: string, payload: Record<string, unknown>, source_system?: string | null, target_system?: string | null, entity_type?: string | null) =>
    request<WorkflowDryRunResponse>(`/api/workflows/${id}/dry-run`, { method: 'POST', body: JSON.stringify({ payload, source_system, target_system, entity_type }) }),
  test: (id: string, payload: Record<string, unknown>, source_system?: string | null, target_system?: string | null, entity_type?: string | null) =>
    request<WorkflowDryRunResponse>(`/api/workflows/${id}/test`, { method: 'POST', body: JSON.stringify({ payload, source_system, target_system, entity_type }) }),
  validate: (id: string) => request<WorkflowValidation>(`/api/workflows/${id}/validate`, { method: 'POST' }),
};
