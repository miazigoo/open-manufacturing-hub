import { request } from './client';

export type IncidentStatus = 'open' | 'acknowledged' | 'resolved' | 'ignored';
export type IncidentSeverity = 'info' | 'warning' | 'error' | 'critical';

export interface Incident {
  id: string;
  fingerprint: string;
  title: string;
  status: IncidentStatus;
  severity: IncidentSeverity;
  source_system: string | null;
  target_system: string | null;
  failed_step: string | null;
  error_code: string | null;
  normalized_error_message: string | null;
  affected_events_count: number;
  first_seen_at: string;
  last_seen_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
}

export interface IncidentEventLink {
  id: string;
  incident_id: string;
  event_id: string;
  run_id: string | null;
  step_id: string | null;
}

export const incidentsApi = {
  list: () => request<Incident[]>('/api/incidents'),
  get: (incidentId: string) => request<Incident>(`/api/incidents/${incidentId}`),
  events: (incidentId: string) => request<IncidentEventLink[]>(`/api/incidents/${incidentId}/events`),
  acknowledge: (incidentId: string) => request<Incident>(`/api/incidents/${incidentId}/acknowledge`, { method: 'POST' }),
  resolve: (incidentId: string) => request<Incident>(`/api/incidents/${incidentId}/resolve`, { method: 'POST' }),
  ignore: (incidentId: string) => request<Incident>(`/api/incidents/${incidentId}/ignore`, { method: 'POST' }),
};
