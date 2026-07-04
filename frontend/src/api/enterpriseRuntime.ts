import { request } from './client';

export type QueueStatus = 'waiting' | 'processing' | 'retry_waiting' | 'completed' | 'failed' | 'dlq' | 'cancelled' | 'archived';

export interface QueueMessage {
  id: string;
  event_id: string | null;
  message_id: string | null;
  run_id: string | null;
  flow_id: string | null;
  endpoint_id: string | null;
  route_id: string | null;
  connector_id: string | null;
  workflow_id: string | null;
  business_object: string;
  business_key: string | null;
  operation: string;
  source_system: string | null;
  target_system: string | null;
  connector_name: string | null;
  current_step: string | null;
  status: QueueStatus;
  attempts: number;
  max_attempts: number;
  next_retry_at: string | null;
  priority: number;
  worker: string | null;
  locked_by: string | null;
  locked_at: string | null;
  locked_until: string | null;
  started_at: string | null;
  finished_at: string | null;
  completed_at: string | null;
  timeline_link: string | null;
  payload_json: Record<string, unknown>;
  original_payload_json: Record<string, unknown>;
  last_error: string | null;
  last_error_code: string | null;
  last_error_message: string | null;
  last_external_error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DlqItem {
  id: string;
  queue_message_id: string | null;
  event_id: string | null;
  message_id: string | null;
  business_object: string;
  operation: string;
  reason: string;
  payload_json: Record<string, unknown>;
  current_payload_json: Record<string, unknown>;
  last_error: string | null;
  attempts: number;
  archived: boolean;
  restored_at: string | null;
  archived_at: string | null;
  timeline_link: string | null;
  created_at: string;
}

export interface QueueProcessResponse { processed: number; completed: number; retry_waiting: number; dlq: number; failed: number; items: QueueMessage[] }
export interface MonitorSummary { waiting: number; processing: number; retry_waiting: number; dlq: number; completed: number; failed: number; cancelled: number }
export interface CanonicalObject { id: string; name: string; description: string | null; schema_json: Record<string, unknown>; active: boolean; updated_at: string }
export interface ResolverDefinition { id: string; name: string; resolver_type: 'odata' | 'rest' | 'cache'; business_object: string; config_json: Record<string, unknown>; cache_ttl_seconds: number; enabled: boolean }
export interface TransformDefinition { name: string; description: string }
export interface BusinessRule { id: string; name: string; business_object: string | null; operation: string | null; status: string; rules_json: Array<Record<string, unknown>> }
export interface ODataCacheEntry { id: string; resolver_name: string; lookup_key: string; status: string; value_json: Record<string, unknown> | null; hit_count: number; expires_at: string | null }

const queueFilters = (filters?: { status?: QueueStatus | ''; business_object?: string; operation?: string; sort?: string }) => {
  const params = new URLSearchParams();
  if (filters?.status) params.set('status', filters.status);
  if (filters?.business_object) params.set('business_object', filters.business_object);
  if (filters?.operation) params.set('operation', filters.operation);
  if (filters?.sort) params.set('sort', filters.sort);
  const query = params.toString();
  return query ? `?${query}` : '';
};

export const enterpriseRuntimeApi = {
  installPresets: () => request<Record<string, unknown>>('/api/enterprise-runtime/install-presets', { method: 'POST' }),
  queue: (filters?: { status?: QueueStatus | ''; business_object?: string; operation?: string; sort?: string }) => request<QueueMessage[]>(`/api/queue${queueFilters(filters)}`),
  queueItem: (id: string) => request<QueueMessage>(`/api/queue/${id}`),
  createQueue: (payload: Partial<QueueMessage> & { business_object: string; operation: string }) => request<QueueMessage>('/api/queue', { method: 'POST', body: JSON.stringify(payload) }),
  markProcessing: (id: string) => request<QueueMessage>(`/api/enterprise-runtime/queue/${id}/processing`, { method: 'POST' }),
  processOnce: () => request<QueueProcessResponse>('/api/queue/process-once', { method: 'POST' }),
  processBatch: (limit = 10) => request<QueueProcessResponse>(`/api/queue/process-batch?limit=${limit}`, { method: 'POST' }),
  retryNow: (id: string) => request<QueueMessage>(`/api/queue/${id}/retry-now`, { method: 'POST' }),
  cancelQueue: (id: string) => request<QueueMessage>(`/api/queue/${id}/cancel`, { method: 'POST' }),
  unlockQueue: (id: string) => request<QueueMessage>(`/api/queue/${id}/unlock`, { method: 'POST' }),
  forceCompleteQueue: (id: string) => request<QueueMessage>(`/api/queue/${id}/force-complete`, { method: 'POST' }),
  moveToDlq: (id: string, reason: string) => request<DlqItem>(`/api/queue/${id}/move-to-dlq?reason=${encodeURIComponent(reason)}`, { method: 'POST' }),
  dlq: () => request<DlqItem[]>('/api/dlq'),
  retryDlq: (id: string) => request<QueueMessage>(`/api/dlq/${id}/retry`, { method: 'POST' }),
  editRetryDlq: (id: string, payload_json: Record<string, unknown>) => request<QueueMessage>(`/api/dlq/${id}/edit-and-retry`, { method: 'POST', body: JSON.stringify({ payload_json }) }),
  archiveDlq: (id: string) => request<DlqItem>(`/api/dlq/${id}/archive`, { method: 'POST' }),
  forceCompleteDlq: (id: string) => request<QueueMessage>(`/api/dlq/${id}/force-complete`, { method: 'POST' }),
  monitor: () => request<MonitorSummary>('/api/enterprise-runtime/monitor'),
  canonicalObjects: () => request<CanonicalObject[]>('/api/enterprise-runtime/canonical-objects'),
  upsertCanonicalObject: (payload: { name: string; description?: string | null; schema_json?: Record<string, unknown>; active?: boolean }) => request<CanonicalObject>('/api/enterprise-runtime/canonical-objects', { method: 'POST', body: JSON.stringify(payload) }),
  resolvers: () => request<ResolverDefinition[]>('/api/enterprise-runtime/resolvers'),
  upsertResolver: (payload: { name: string; resolver_type: string; business_object: string; config_json?: Record<string, unknown>; cache_ttl_seconds?: number; enabled?: boolean }) => request<ResolverDefinition>('/api/enterprise-runtime/resolvers', { method: 'POST', body: JSON.stringify(payload) }),
  resolve: (id: string, input: Record<string, unknown>, lookup_key?: string) => request<Record<string, unknown>>(`/api/enterprise-runtime/resolvers/${id}/resolve`, { method: 'POST', body: JSON.stringify({ input, lookup_key }) }),
  transforms: () => request<TransformDefinition[]>('/api/enterprise-runtime/transforms'),
  applyTransform: (payload: { name: string; value?: unknown; params?: Record<string, unknown> }) => request<Record<string, unknown>>('/api/enterprise-runtime/transforms/apply', { method: 'POST', body: JSON.stringify(payload) }),
  businessRules: () => request<BusinessRule[]>('/api/enterprise-runtime/business-rules'),
  upsertBusinessRule: (payload: { name: string; business_object?: string | null; operation?: string | null; rules_json: Array<Record<string, unknown>>; status?: string }) => request<BusinessRule>('/api/enterprise-runtime/business-rules', { method: 'POST', body: JSON.stringify(payload) }),
  runBusinessRule: (id: string, payload: Record<string, unknown>) => request<Record<string, unknown>>(`/api/enterprise-runtime/business-rules/${id}/run`, { method: 'POST', body: JSON.stringify({ payload }) }),
  cache: () => request<ODataCacheEntry[]>('/api/enterprise-runtime/odata-cache'),
  preloadCache: (payload: { resolver_name: string; lookup_key: string; value_json: Record<string, unknown>; ttl_seconds?: number }) => request<ODataCacheEntry>('/api/enterprise-runtime/odata-cache/preload', { method: 'POST', body: JSON.stringify(payload) }),
  invalidateCache: (id: string) => request<ODataCacheEntry>(`/api/enterprise-runtime/odata-cache/${id}/invalidate`, { method: 'POST' }),
};
