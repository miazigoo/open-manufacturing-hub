import { request } from './client';

export interface XmlInboundResponse {
  message_id: string;
  event_id: string;
  status: string;
  timeline_url: string;
}

export interface IntegrationMessage {
  id: string;
  source_system: string;
  target_system: string | null;
  message_type: string;
  status: string;
  payload_sha256: string;
  payload_size_bytes: number;
  event_id: string | null;
  last_error: string | null;
  created_at: string;
}

export interface ODataLookupResponse {
  request: Record<string, unknown>;
  response: Record<string, unknown>;
  extracted: Record<string, unknown>;
}

export interface OperationTemplate {
  id: string;
  name: string;
  system_type: string;
  operation: string;
  description: string | null;
  enabled: boolean;
  request_template_json: Record<string, unknown>;
  response_schema_json: Record<string, unknown> | null;
  default_workflow_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkbenchInstallResponse {
  workflow_id: string;
  workflow_name: string;
  installed: boolean;
}

export const onecWorkbenchApi = {
  sendXml: (payload: { source_system: string; target_system?: string | null; message_type: string; correlation_id?: string | null; xml: string }) =>
    request<XmlInboundResponse>('/api/onec/xml/inbound', { method: 'POST', body: JSON.stringify(payload) }),
  messages: () => request<IntegrationMessage[]>('/api/onec/xml/messages'),
  lookup: (payload: { connector_name: string; resource: string; filter_template: string; input: Record<string, unknown>; extract: Record<string, string> }) =>
    request<ODataLookupResponse>('/api/onec/lookup/test', { method: 'POST', body: JSON.stringify(payload) }),
  templates: () => request<OperationTemplate[]>('/api/operation-templates'),
  installTemplates: () => request<OperationTemplate[]>('/api/operation-templates/install-presets', { method: 'POST' }),
  installXmlBridge: () => request<WorkbenchInstallResponse>('/api/onec-workbench/install-xml-bridge', { method: 'POST' }),
  installInnLookupDemo: () => request<WorkbenchInstallResponse>('/api/onec-workbench/install-inn-lookup-demo', { method: 'POST' }),
  installPrintPipeline: () => request<WorkbenchInstallResponse>('/api/onec-workbench/install-print-pipeline', { method: 'POST' }),
};
