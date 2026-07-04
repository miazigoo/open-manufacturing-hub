import { request } from './client';

export interface IntegrationEndpoint {
  id: string;
  name: string;
  slug: string;
  enabled: boolean;
  input_mode: string;
  response_mode: string;
  default_source_system: string | null;
  default_target_system: string | null;
  default_event_type: string;
  default_entity_type: string | null;
  workflow_id: string | null;
  route_id: string | null;
  auth_mode: string;
  auth_config_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface IntegrationRoute {
  id: string;
  name: string;
  enabled: boolean;
  source_system: string | null;
  target_system: string | null;
  event_type: string | null;
  message_type: string | null;
  operation: string | null;
  workflow_id: string | null;
  priority: number;
  created_at: string;
  updated_at: string;
}

export interface ODataLookupTemplate {
  id: string;
  name: string;
  connector_id: string;
  resource: string;
  filter_template: string;
  extract_json: Record<string, string>;
  required: boolean;
  cache_ttl_seconds: number | null;
  created_at: string;
  updated_at: string;
}

export interface BusInstallResponse {
  endpoints: IntegrationEndpoint[];
  routes: IntegrationRoute[];
  lookups: ODataLookupTemplate[];
}

export const integrationBusApi = {
  endpoints: () => request<IntegrationEndpoint[]>('/api/integration-bus/endpoints'),
  routes: () => request<IntegrationRoute[]>('/api/integration-bus/routes'),
  lookups: () => request<ODataLookupTemplate[]>('/api/odata-lookups'),
  createEndpoint: (payload: Partial<IntegrationEndpoint> & { name: string; slug: string; input_mode: string; response_mode: string; default_event_type: string }) =>
    request<IntegrationEndpoint>('/api/integration-bus/endpoints', { method: 'POST', body: JSON.stringify(payload) }),
  createRoute: (payload: Partial<IntegrationRoute> & { name: string }) =>
    request<IntegrationRoute>('/api/integration-bus/routes', { method: 'POST', body: JSON.stringify(payload) }),
  installPresets: () => request<BusInstallResponse>('/api/integration-bus/install-presets', { method: 'POST' }),
  sendJson: (slug: string, payload: unknown, headers: Record<string, string> = {}) =>
    request<unknown>(`/api/bus/in/${slug}`, { method: 'POST', headers, body: JSON.stringify(payload) }),
  sendText: (slug: string, body: string, contentType: string, headers: Record<string, string> = {}) =>
    request<unknown>(`/api/bus/in/${slug}`, { method: 'POST', headers: { ...headers, 'Content-Type': contentType }, body }),
};
