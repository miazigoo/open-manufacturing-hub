import { request } from './client';

export type DataContractKind = 'input' | 'output' | 'operation_request' | 'operation_response' | 'intermediate';
export type DataContractFieldType = 'string' | 'number' | 'boolean' | 'null' | 'object' | 'array' | 'date' | 'datetime' | 'guid' | 'raw';

export interface DataContractField {
  path: string;
  type: DataContractFieldType;
  required: boolean;
  label?: string | null;
  description?: string | null;
  example?: unknown;
  default?: unknown;
}

export interface DataContractSchema {
  type: 'object';
  fields: DataContractField[];
}

export interface DataContractPayload {
  name: string;
  code: string;
  kind: DataContractKind;
  owner_type?: 'operation_profile' | 'integration_pattern' | 'package' | null;
  owner_id?: string | null;
  description?: string | null;
  schema_json: DataContractSchema | Record<string, unknown>;
  example_json?: Record<string, unknown> | unknown[] | null;
}

export interface DataContract extends DataContractPayload {
  id: string;
  fields: DataContractField[];
  created_at: string;
  updated_at: string;
}

export const dataContractsApi = {
  list: (params: { kind?: string; owner_type?: string; owner_id?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.kind) query.set('kind', params.kind);
    if (params.owner_type) query.set('owner_type', params.owner_type);
    if (params.owner_id) query.set('owner_id', params.owner_id);
    const suffix = query.toString() ? `?${query.toString()}` : '';
    return request<DataContract[]>(`/api/data-contracts${suffix}`);
  },
  create: (payload: DataContractPayload) => request<DataContract>('/api/data-contracts', { method: 'POST', body: JSON.stringify(payload) }),
  get: (id: string) => request<DataContract>(`/api/data-contracts/${encodeURIComponent(id)}`),
  patch: (id: string, payload: Partial<DataContractPayload>) => request<DataContract>(`/api/data-contracts/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  delete: (id: string) => request<void>(`/api/data-contracts/${encodeURIComponent(id)}`, { method: 'DELETE' }),
};
