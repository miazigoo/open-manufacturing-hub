import { request } from './client';

export type ResolverStrategy = 'odata' | 'rest' | 'static_map' | 'chain';

export interface ResolverDefinitionV2 {
  id: string;
  name: string;
  resolver_code: string;
  object_type: string;
  enabled: boolean;
  strategy: ResolverStrategy;
  connector_id: string | null;
  input_schema_json: Record<string, unknown>;
  output_schema_json: Record<string, unknown> | null;
  config_json: Record<string, unknown>;
  cache_enabled: boolean;
  cache_ttl_seconds: number;
  created_at: string;
  updated_at: string;
}

export interface ResolverResult {
  success: boolean;
  resolver_code: string;
  object_type: string | null;
  object_json: Record<string, unknown> | null;
  cache_status: string;
  source: Record<string, unknown>;
  error_code: string | null;
  error_message: string | null;
  artifacts: Array<{ name: string; type: string; payload: Record<string, unknown> }>;
}

export interface ResolverCacheEntry {
  id: string;
  resolver_id: string;
  resolver_code: string;
  cache_key: string;
  input_hash: string;
  object_type: string;
  resolved_object_json: Record<string, unknown>;
  source_connector_id: string | null;
  source_system: string | null;
  expires_at: string | null;
  hit_count: number;
  last_hit_at: string | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export const resolversApi = {
  list: (filters?: { object_type?: string; enabled?: boolean }) => {
    const params = new URLSearchParams();
    if (filters?.object_type) params.set('object_type', filters.object_type);
    if (filters?.enabled !== undefined) params.set('enabled', String(filters.enabled));
    const query = params.toString();
    return request<ResolverDefinitionV2[]>(`/api/resolvers${query ? `?${query}` : ''}`);
  },
  get: (id: string) => request<ResolverDefinitionV2>(`/api/resolvers/${id}`),
  create: (payload: Partial<ResolverDefinitionV2>) => request<ResolverDefinitionV2>('/api/resolvers', { method: 'POST', body: JSON.stringify(payload) }),
  patch: (id: string, payload: Partial<ResolverDefinitionV2>) => request<ResolverDefinitionV2>(`/api/resolvers/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  installPresets: () => request<Record<string, number>>('/api/resolvers/install-presets', { method: 'POST' }),
  resolve: (id: string, input: Record<string, unknown>, use_cache = true) => request<ResolverResult>(`/api/resolvers/${id}/resolve`, { method: 'POST', body: JSON.stringify({ input, use_cache }) }),
  resolveByCode: (resolverCode: string, input: Record<string, unknown>, use_cache = true) => request<ResolverResult>(`/api/resolvers/code/${encodeURIComponent(resolverCode)}/resolve`, { method: 'POST', body: JSON.stringify({ input, use_cache }) }),
  cache: (filters?: { resolver_code?: string; object_type?: string }) => {
    const params = new URLSearchParams();
    if (filters?.resolver_code) params.set('resolver_code', filters.resolver_code);
    if (filters?.object_type) params.set('object_type', filters.object_type);
    const query = params.toString();
    return request<ResolverCacheEntry[]>(`/api/resolvers/cache${query ? `?${query}` : ''}`);
  },
  deleteCacheEntry: (id: string) => request<Record<string, boolean>>(`/api/resolvers/cache/${id}`, { method: 'DELETE' }),
  clearCache: (id: string) => request<Record<string, number>>(`/api/resolvers/${id}/cache/clear`, { method: 'POST' }),
};
