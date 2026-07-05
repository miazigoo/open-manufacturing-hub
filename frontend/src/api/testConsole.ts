import { request } from './client';

export interface TestConsoleSendResponse { success: boolean; response: Record<string, unknown>; event_id: string | null; message_id: string | null; timeline_url: string | null; external_error: Record<string, unknown> | null; dry_run: boolean }
export interface DocsExample { id: string; title: Record<string, string>; description: Record<string, string>; endpoint_slug: string; method: string; input_mode: string; headers: Record<string, string>; body?: Record<string, unknown> | null; body_text?: string | null; expected: Record<string, unknown>; runnable: boolean; requires_setup: boolean }
export interface SavedTestCase { id: string; name: string; description: string | null; endpoint_id: string | null; method: string; headers_json: Record<string, unknown> | null; body_text: string | null; body_json: Record<string, unknown> | null; input_mode: string; expected_status: string | null; last_run_event_id: string | null; last_run_status: string | null; created_at: string; updated_at: string }
export interface SavedTestCasePayload { name: string; description?: string | null; endpoint_id?: string | null; method?: string; headers_json?: Record<string, unknown> | null; body_text?: string | null; body_json?: Record<string, unknown> | null; input_mode: string; expected_status?: string | null }

export const testConsoleApi = {
  send: (payload: { endpoint_id?: string | null; slug?: string | null; input_mode: string; headers_json: Record<string, string>; body_text?: string | null; body_json?: Record<string, unknown> | null; dry_run?: boolean }) =>
    request<TestConsoleSendResponse>('/api/test-console/send', { method: 'POST', body: JSON.stringify(payload) }),
  docsExample: (id: string) => request<DocsExample>(`/api/docs/examples/${encodeURIComponent(id)}`),
  runDocsExample: (id: string) => request<Record<string, unknown>>(`/api/docs/examples/${encodeURIComponent(id)}/run`, { method: 'POST' }),
  listCases: () => request<SavedTestCase[]>('/api/test-cases'),
  createCase: (payload: SavedTestCasePayload) => request<SavedTestCase>('/api/test-cases', { method: 'POST', body: JSON.stringify(payload) }),
  patchCase: (id: string, payload: Partial<SavedTestCasePayload>) => request<SavedTestCase>(`/api/test-cases/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteCase: (id: string) => request<void>(`/api/test-cases/${id}`, { method: 'DELETE' }),
  runCase: (id: string, dryRun = false) => request<TestConsoleSendResponse>(`/api/test-cases/${id}/run?dry_run=${dryRun}`, { method: 'POST' }),
};
