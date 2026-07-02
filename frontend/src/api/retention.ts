import { request } from './client';

export interface RetentionPreview {
  expired_artifacts: number;
  expired_events: number;
  pinned_skipped: number;
}

export const retentionApi = {
  preview: () => request<RetentionPreview>('/api/retention/preview'),
  cleanup: () => request<RetentionPreview>('/api/retention/cleanup', { method: 'POST' }),
};
