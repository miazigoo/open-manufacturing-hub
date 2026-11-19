import { DashboardSummary, EventOverview, EventStatus, EventSummary, EventTimeline, request } from './client';

export interface EventCreatePayload {
  correlation_id?: string | null;
  source_system: string;
  target_system?: string | null;
  event_type: string;
  entity_type?: string | null;
  entity_id?: string | null;
  payload: Record<string, unknown>;
}

export interface EventJournalItem extends EventSummary {
  human_title: string;
  human_summary: string;
  business_key: string | null;
  operation: string | null;
  document_type: string | null;
  document_number: string | null;
  source_display: string | null;
  target_display: string | null;
  last_step: string | null;
  last_error_code: string | null;
  last_error_summary: string | null;
  last_external_error_message: string | null;
  hint: string | null;
  requires_attention: boolean;
  status: EventStatus;
  queue_status: string | null;
  queue_attempts: number | null;
  queue_max_attempts: number | null;
  queue_next_retry_at: string | null;
}

export interface CursorPage<T> {
  items: T[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface EventJournalParams {
  status?: EventStatus | 'all';
  event_type?: string;
  source?: string;
  target?: string;
  q?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  cursor?: string | null;
}

export const eventsApi = {
  list: (init?: RequestInit) => request<EventSummary[]>('/api/events', init),
  journal: (init?: RequestInit) => request<EventJournalItem[]>('/api/events/journal', init),
  journalPage: (params: EventJournalParams = {}, init?: RequestInit) => {
    const search = new URLSearchParams();
    if (params.status && params.status !== 'all') search.set('status', params.status);
    if (params.event_type?.trim()) search.set('event_type', params.event_type.trim());
    if (params.source?.trim()) search.set('source', params.source.trim());
    if (params.target?.trim()) search.set('target', params.target.trim());
    if (params.q?.trim()) search.set('q', params.q.trim());
    if (params.date_from?.trim()) search.set('date_from', params.date_from.trim());
    if (params.date_to?.trim()) search.set('date_to', params.date_to.trim());
    if (params.limit) search.set('limit', String(params.limit));
    if (params.cursor) search.set('cursor', params.cursor);
    const queryStr = search.toString();
    return request<CursorPage<EventJournalItem>>(`/api/events/journal/page${queryStr ? `?${queryStr}` : ''}`, init);
  },
  get: (eventId: string, init?: RequestInit) => request<EventSummary>(`/api/events/${eventId}`, init),
  runMetadata: (eventId: string, runId: string, signal: AbortSignal) => request<EventOverview['runs'][number]>(`/api/events/${eventId}/runs/${runId}/metadata`, { signal }),
  overview: (eventId: string, params: { limit?: number; offset?: number; before?: string; brief?: boolean } = {}, init?: RequestInit) => {
    const search = new URLSearchParams();
    if (params.limit !== undefined) search.set('limit', String(params.limit));
    if (params.brief) search.set('brief', 'true');
    if (params.before) search.set('before_run', params.before);
    if (params.offset !== undefined) search.set('offset', String(params.offset));
    const queryStr = search.toString();
    return request<EventOverview>(`/api/events/${eventId}/overview${queryStr ? `?${queryStr}` : ''}`, init);
  },
  dashboardSummary: (init?: RequestInit) => request<DashboardSummary>('/api/events/dashboard-summary', init),
  timeline: (eventId: string, init?: RequestInit) => request<EventTimeline>(`/api/events/${eventId}/timeline`, init),
  create: (payload: EventCreatePayload, init?: RequestInit) => request<EventSummary>('/api/events', { ...init, method: 'POST', body: JSON.stringify(payload) }),
  pin: (eventId: string, init?: RequestInit) => request<EventSummary>(`/api/events/${eventId}/pin`, { ...init, method: 'POST' }),
  unpin: (eventId: string, init?: RequestInit) => request<EventSummary>(`/api/events/${eventId}/unpin`, { ...init, method: 'POST' }),
};
