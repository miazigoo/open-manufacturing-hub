import { request } from './client';

export interface MaintenanceWindow {
  id: string;
  component_type: string;
  component_name: string;
  reason: string | null;
  starts_at: string;
  ends_at: string;
  enabled: boolean;
}

export interface MaintenancePayload {
  component_type: string;
  component_name: string;
  reason?: string | null;
  starts_at: string;
  ends_at: string;
  enabled?: boolean;
}

export const maintenanceApi = {
  list: () => request<MaintenanceWindow[]>('/api/maintenance'),
  create: (payload: MaintenancePayload) => request<MaintenanceWindow>('/api/maintenance', { method: 'POST', body: JSON.stringify(payload) }),
  patch: (id: string, payload: Partial<MaintenancePayload>) =>
    request<MaintenanceWindow>(`/api/maintenance/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  delete: (id: string) => request<void>(`/api/maintenance/${id}`, { method: 'DELETE' }),
};
