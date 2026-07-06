import { request } from './client';

export interface OperationTemplate {
  id: string;
  name: string;
  operation_code: string | null;
  system_type: string;
  operation: string;
  direction: string;
  input_mode: string | null;
  output_mode: string | null;
  target_connector_type: string | null;
  default_body_mode: string | null;
  default_content_type: string | null;
  description: string | null;
  enabled: boolean;
  request_schema_json: Record<string, unknown> | null;
  request_template_json: Record<string, unknown>;
  response_schema_json: Record<string, unknown> | null;
  example_request_json: Record<string, unknown> | null;
  example_response_json: Record<string, unknown> | null;
  default_workflow_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface OperationTemplatePayload {
  name: string;
  operation_code?: string | null;
  system_type: string;
  operation: string;
  direction?: string;
  input_mode?: string | null;
  output_mode?: string | null;
  target_connector_type?: string | null;
  default_body_mode?: string | null;
  default_content_type?: string | null;
  description?: string | null;
  enabled?: boolean;
  request_schema_json?: Record<string, unknown> | null;
  request_template_json?: Record<string, unknown>;
  response_schema_json?: Record<string, unknown> | null;
  example_request_json?: Record<string, unknown> | null;
  example_response_json?: Record<string, unknown> | null;
  default_workflow_id?: string | null;
}

export const operationTemplatesApi = {
  list: () => request<OperationTemplate[]>('/api/operation-templates'),
  create: (payload: OperationTemplatePayload) => request<OperationTemplate>('/api/operation-templates', { method: 'POST', body: JSON.stringify(payload) }),
  patch: (id: string, payload: Partial<OperationTemplatePayload>) => request<OperationTemplate>(`/api/operation-templates/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  delete: (id: string) => request<void>(`/api/operation-templates/${id}`, { method: 'DELETE' }),
};
