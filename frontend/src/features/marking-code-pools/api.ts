import { apiUrl, request } from '../../api/client';
import type {
  MarkingCodePoolActionRetryResponse,
  MarkingCodePoolExport,
  MarkingCodePoolExportResponse,
  MarkingCodePoolPreviewResponse,
  MarkingCodePoolSettings,
  MarkingCodePoolSettingsPatch,
  MarkingCodePoolSettingsTestResponse,
  OneCMarkingCodePoolExportRequest,
} from './types';

const base = '/api/marking-code-pools';

export const markingCodePoolsApi = {
  settings: () => request<MarkingCodePoolSettings>(`${base}/settings`),
  patchSettings: (payload: MarkingCodePoolSettingsPatch) => request<MarkingCodePoolSettings>(`${base}/settings`, { method: 'PATCH', body: JSON.stringify(payload) }),
  testLocalDir: () => request<MarkingCodePoolSettingsTestResponse>(`${base}/settings/test-local-dir`, { method: 'POST' }),
  testLaserDir: (dry_run = true) => request<MarkingCodePoolSettingsTestResponse>(`${base}/settings/test-laser-dir`, { method: 'POST', body: JSON.stringify({ dry_run }) }),
  testForward: (send_test_request = false) => request<MarkingCodePoolSettingsTestResponse>(`${base}/settings/test-forward`, { method: 'POST', body: JSON.stringify({ send_test_request }) }),
  preview: (payload: OneCMarkingCodePoolExportRequest) => request<MarkingCodePoolPreviewResponse>(`${base}/onec/export-file/preview`, { method: 'POST', body: JSON.stringify(payload) }),
  exportFile: (payload: OneCMarkingCodePoolExportRequest) => request<MarkingCodePoolExportResponse>(`${base}/onec/export-file`, { method: 'POST', body: JSON.stringify(payload) }),
  exports: () => request<MarkingCodePoolExport[]>(`${base}/exports`),
  exportDetails: (id: string) => request<MarkingCodePoolExport>(`${base}/exports/${id}`),
  retryForward: (id: string) => request<MarkingCodePoolActionRetryResponse>(`${base}/exports/${id}/retry-forward`, { method: 'POST' }),
  retryLaserCopy: (id: string) => request<MarkingCodePoolActionRetryResponse>(`${base}/exports/${id}/retry-laser-copy`, { method: 'POST' }),
  downloadUrl: (id: string) => apiUrl(`${base}/exports/${id}/download`),
};
