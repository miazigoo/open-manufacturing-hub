import { request } from './client';

export type HealthStatus = 'ok' | 'warning' | 'down' | 'unknown' | 'maintenance';

export interface HealthSite {
  name: string;
  code: string;
  status: HealthStatus;
  internet: HealthStatus;
  hub: HealthStatus;
  wms: HealthStatus;
  erp: HealthStatus;
  queue_size: number;
  last_event_minutes_ago: number | null;
  agent_name: string | null;
  agent_status: HealthStatus;
  last_heartbeat_at: string | null;
  heartbeat_age_seconds: number | null;
}

export interface HealthComponent {
  name: string;
  type: string;
  status: HealthStatus;
}

export interface HealthDashboard {
  sites: HealthSite[];
  components: HealthComponent[];
  agents: AgentHeartbeatSummary[];
}

export interface AgentHeartbeatSummary {
  id: string;
  site_id: string;
  site_name: string;
  site_code: string;
  agent_name: string;
  status: HealthStatus;
  heartbeat_age_seconds: number;
  stale_after_seconds: number;
  internet: HealthStatus;
  hub: HealthStatus;
  wms: HealthStatus;
  erp: HealthStatus;
  local_ip: string | null;
  details_json: Record<string, unknown> | null;
  received_at: string;
}

export interface AgentHeartbeatHistoryItem {
  id: string;
  site_id: string;
  site_name: string;
  site_code: string;
  agent_name: string;
  internet_ok: boolean | null;
  can_reach_hub: boolean | null;
  can_reach_wms: boolean | null;
  can_reach_erp: boolean | null;
  local_ip: string | null;
  details_json: Record<string, unknown> | null;
  received_at: string;
}

export const healthApi = {
  dashboard: () => request<HealthDashboard>('/api/health/dashboard'),
  agents: () => request<AgentHeartbeatSummary[]>('/api/health/agents'),
  agentHeartbeats: (limit = 25) => request<AgentHeartbeatHistoryItem[]>(`/api/health/agent-heartbeats?limit=${limit}`),
};
