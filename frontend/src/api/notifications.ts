import { request } from './client';

export type TriggerType = 'event_failed' | 'incident_created' | 'incident_updated' | 'health_down' | 'queue_threshold' | 'queue_item_dlq' | 'queue_backlog_threshold' | 'worker_stuck' | 'retry_exhausted' | 'daily_report';
export type DeliveryStatus = 'pending' | 'sent' | 'failed' | 'skipped_cooldown';

export interface NotificationRule {
  id: string;
  name: string;
  enabled: boolean;
  trigger_type: TriggerType;
  filters_json: Record<string, unknown>;
  channels_json: Array<Record<string, unknown>>;
  cooldown_seconds: number;
  last_triggered_at: string | null;
}

export interface NotificationRulePayload {
  name: string;
  enabled?: boolean;
  trigger_type: TriggerType;
  filters: Record<string, unknown>;
  channels: Array<Record<string, unknown>>;
  cooldown_seconds: number;
}

export interface NotificationDelivery {
  id: string;
  rule_id: string | null;
  trigger_type: string;
  target_channel: string;
  target_address: string;
  status: DeliveryStatus;
  request_payload: Record<string, unknown> | null;
  response_payload: Record<string, unknown> | null;
  error_message: string | null;
  sent_at: string | null;
}

export const notificationsApi = {
  rules: () => request<NotificationRule[]>('/api/notifications/rules'),
  createRule: (payload: NotificationRulePayload) =>
    request<NotificationRule>('/api/notifications/rules', { method: 'POST', body: JSON.stringify(payload) }),
  patchRule: (ruleId: string, payload: Partial<Omit<NotificationRulePayload, 'trigger_type'>>) =>
    request<NotificationRule>(`/api/notifications/rules/${ruleId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteRule: (ruleId: string) => request<void>(`/api/notifications/rules/${ruleId}`, { method: 'DELETE' }),
  testRule: (ruleId: string) => request<NotificationDelivery[]>(`/api/notifications/rules/${ruleId}/test`, { method: 'POST' }),
  deliveries: () => request<NotificationDelivery[]>('/api/notifications/deliveries'),
};
