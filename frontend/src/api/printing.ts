import { request } from './client';

export interface PrintPrinter {
  id: string;
  name: string;
  connector_id: string;
  dpi: number;
  enabled: boolean;
  description: string | null;
  settings_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface PrintJob {
  id: string;
  job_key: string;
  printer_id: string;
  source_system: string;
  source_document_id: string | null;
  source_document_name: string | null;
  status: string;
  total_lines: number;
  sent_lines: number;
  printed_lines: number;
  error_lines: number;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface PrintJobLine {
  id: string;
  job_id: string;
  sequence_no: number;
  code_visible: string;
  code_sha256: string;
  zpl_sha256: string;
  status: string;
  attempts: number;
  last_error: string | null;
  sent_at: string | null;
  printed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PrintJobLog {
  id: string;
  job_id: string;
  line_id: string | null;
  sequence_no: number | null;
  action: string;
  status: string;
  message: string | null;
  details_json: Record<string, unknown>;
  created_at: string;
}

export const printingApi = {
  printers: () => request<PrintPrinter[]>('/api/printing/printers'),
  jobs: () => request<PrintJob[]>('/api/printing/jobs'),
  lines: (jobId: string) => request<PrintJobLine[]>(`/api/printing/jobs/${jobId}/lines`),
  logs: (jobId: string) => request<PrintJobLog[]>(`/api/printing/jobs/${jobId}/logs`),
  sendBatch: (jobId: string, payload: { limit: number; dry_run: boolean; include_returned: boolean }) =>
    request(`/api/printing/jobs/${jobId}/send-batch`, { method: 'POST', body: JSON.stringify(payload) }),
  confirmPrinted: (jobId: string, payload: { through_sequence_no?: number; line_ids?: string[] }) =>
    request<PrintJob>(`/api/printing/jobs/${jobId}/confirm-printed`, { method: 'POST', body: JSON.stringify(payload) }),
  returnToPrint: (jobId: string, payload: { from_sequence_no: number; reason?: string }) =>
    request<PrintJob>(`/api/printing/jobs/${jobId}/return-to-print`, { method: 'POST', body: JSON.stringify(payload) }),
};
