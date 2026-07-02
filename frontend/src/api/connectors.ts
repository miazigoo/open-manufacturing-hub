import { request } from './client';

export type ConnectorDirection = 'source' | 'target' | 'bidirectional';
export type ConnectorStatus = 'enabled' | 'disabled' | 'maintenance' | 'error' | 'unknown';
export type HealthStatus = 'ok' | 'warning' | 'down' | 'unknown' | 'maintenance';

export interface ConnectorType {
  connector_type: string;
  display_name: string;
  direction: ConnectorDirection;
}

export interface ConnectorInstance {
  id: string;
  name: string;
  connector_type: string;
  direction: ConnectorDirection;
  enabled: boolean;
  config_json: Record<string, unknown>;
  status: ConnectorStatus;
  last_health_status: HealthStatus | null;
  last_health_message: string | null;
  last_health_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConnectorPayload {
  name: string;
  connector_type: string;
  direction: ConnectorDirection;
  enabled?: boolean;
  config_json: Record<string, unknown>;
}

export interface ConnectorValidation {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface ConnectorHealth {
  status: HealthStatus;
  message: string;
  details: Record<string, unknown>;
  checked_at: string;
}

export const connectorsApi = {
  types: () => request<ConnectorType[]>('/api/connectors/types'),
  list: () => request<ConnectorInstance[]>('/api/connectors'),
  create: (payload: ConnectorPayload) => request<ConnectorInstance>('/api/connectors', { method: 'POST', body: JSON.stringify(payload) }),
  patch: (id: string, payload: Partial<ConnectorPayload> & { status?: ConnectorStatus }) =>
    request<ConnectorInstance>(`/api/connectors/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  delete: (id: string) => request<void>(`/api/connectors/${id}`, { method: 'DELETE' }),
  testConfig: (id: string) => request<ConnectorValidation>(`/api/connectors/${id}/test-config`, { method: 'POST' }),
  healthcheck: (id: string) => request<ConnectorHealth>(`/api/connectors/${id}/healthcheck`, { method: 'POST' }),
  enable: (id: string) => request<ConnectorInstance>(`/api/connectors/${id}/enable`, { method: 'POST' }),
  disable: (id: string) => request<ConnectorInstance>(`/api/connectors/${id}/disable`, { method: 'POST' }),
  generateMockErpEvents: (id: string) => request<{ created: Array<{ event_id: string; status: string }> }>(`/api/connectors/${id}/mock-erp/generate-events`, { method: 'POST' }),
};
