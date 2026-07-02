import { EventSummary, EventTimeline, request } from './client';

export interface EventCreatePayload {
  correlation_id?: string | null;
  source_system: string;
  target_system?: string | null;
  event_type: string;
  entity_type?: string | null;
  entity_id?: string | null;
  payload: Record<string, unknown>;
}

export const eventsApi = {
  list: () => request<EventSummary[]>('/api/events'),
  get: (eventId: string) => request<EventSummary>(`/api/events/${eventId}`),
  timeline: (eventId: string) => request<EventTimeline>(`/api/events/${eventId}/timeline`),
  create: (payload: EventCreatePayload) => request<EventSummary>('/api/events', { method: 'POST', body: JSON.stringify(payload) }),
  pin: (eventId: string) => request<EventSummary>(`/api/events/${eventId}/pin`, { method: 'POST' }),
  unpin: (eventId: string) => request<EventSummary>(`/api/events/${eventId}/unpin`, { method: 'POST' }),
};
