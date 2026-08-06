import { request } from './client';

export interface RetentionPreview {
  expired_artifacts: number;
  expired_events: number;
  pinned_skipped: number;
  expired_health_checks: number;
  health_checks_retention_days: number;
  aged_artifacts: number;
  aged_events: number;
  retention_artifacts_days: number;
  retention_events_days: number;
}

export const retentionApi = {
  preview: () => request<RetentionPreview>('/api/retention/preview'),
  cleanup: () => request<RetentionPreview>('/api/retention/cleanup', { method: 'POST' }),
};
