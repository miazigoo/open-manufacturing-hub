import { EventStatus, EventSummary, EventTimeline, request } from './client';

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

export const eventsApi = {
  list: () => request<EventSummary[]>('/api/events'),
  journal: () => request<EventJournalItem[]>('/api/events/journal'),
  get: (eventId: string) => request<EventSummary>(`/api/events/${eventId}`),
  timeline: (eventId: string) => request<EventTimeline>(`/api/events/${eventId}/timeline`),
  create: (payload: EventCreatePayload) => request<EventSummary>('/api/events', { method: 'POST', body: JSON.stringify(payload) }),
  pin: (eventId: string) => request<EventSummary>(`/api/events/${eventId}/pin`, { method: 'POST' }),
  unpin: (eventId: string) => request<EventSummary>(`/api/events/${eventId}/unpin`, { method: 'POST' }),
};
