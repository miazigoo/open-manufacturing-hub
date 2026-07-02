import { request } from './client';

export type HealthStatus = 'ok' | 'warning' | 'down' | 'unknown' | 'maintenance';

export interface HealthSite {
  name: string;
  status: HealthStatus;
  internet: HealthStatus;
  wms: HealthStatus;
  erp: HealthStatus;
  queue_size: number;
  last_event_minutes_ago: number | null;
}

export interface HealthComponent {
  name: string;
  type: string;
  status: HealthStatus;
}

export interface HealthDashboard {
  sites: HealthSite[];
  components: HealthComponent[];
}

export const healthApi = {
  dashboard: () => request<HealthDashboard>('/api/health/dashboard'),
};
