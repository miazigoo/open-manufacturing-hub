import type { ActionDetails, MarkingCodePoolExport, OneCMarkingCodePoolExportRequest } from './types';

export function lines(value: string): string[] {
  return value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
}

export function parseJsonObject(value: string): Record<string, unknown> {
  const parsed = value.trim() ? JSON.parse(value) : {};
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('metadata JSON должен быть объектом');
  return parsed as Record<string, unknown>;
}

export function buildRequest(input: {
  source_system: string;
  source_document_id: string;
  source_document_name: string;
  order_number: string;
  code_mode: 'base64' | 'legacy';
  codes_text: string;
  metadata_json: string;
  allow_overwrite: boolean;
  actions_override?: OneCMarkingCodePoolExportRequest['actions_override'];
}): OneCMarkingCodePoolExportRequest {
  const request: OneCMarkingCodePoolExportRequest = {
    source_system: input.source_system || '1C ERP',
    source_document_id: input.source_document_id || null,
    source_document_name: input.source_document_name || null,
    order_number: input.order_number,
    allow_overwrite: input.allow_overwrite,
    actions_override: input.actions_override,
    metadata_json: parseJsonObject(input.metadata_json),
  };
  const codeLines = lines(input.codes_text);
  if (input.code_mode === 'base64') request.full_codes_base64 = codeLines;
  else {
    request.codes = codeLines;
    request.gs_marker = '{GS}';
  }
  return request;
}

export function actionsOf(row: MarkingCodePoolExport): Record<string, ActionDetails> {
  const actions = row.metadata_json?.actions;
  return actions && typeof actions === 'object' && !Array.isArray(actions) ? actions as Record<string, ActionDetails> : {};
}

export function actionStatus(row: MarkingCodePoolExport, key: string): string {
  return String(actionDetails(row, key)?.status ?? 'unknown');
}

export function actionDetails(row: MarkingCodePoolExport, key: string): ActionDetails | undefined {
  const actions = actionsOf(row);
  if (key === 'external_forward') return actions.external_forward ?? actions.dnp_forward;
  return actions[key];
}

export function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : '—';
}

export function shortHash(value: string): string {
  return value.length > 16 ? `${value.slice(0, 12)}…${value.slice(-6)}` : value;
}
