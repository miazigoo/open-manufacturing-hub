import { request } from './client';

export interface XmlPathItem {
  path: string;
  value_preview: string | null;
  type: 'element' | 'text' | 'attribute';
  repeated: boolean;
}

export interface XmlParseResponse {
  success: boolean;
  valid: boolean;
  root: string | null;
  root_name: string | null;
  encoding_detected: string | null;
  namespaces: Record<string, string>;
  paths: XmlPathItem[];
  preview_tree: Record<string, unknown> | null;
  errors: string[];
  sha256: string;
  size_bytes: number;
  pretty_xml: string | null;
}

export interface XmlRenderResponse {
  success: boolean;
  rendered: string | null;
  errors: string[];
}

export const xmlToolkitApi = {
  parse: (xml: string) => request<XmlParseResponse>('/api/xml-toolkit/parse', { method: 'POST', body: JSON.stringify({ xml }) }),
  render: (template: string, variables: Record<string, unknown>, validate_xml = true) =>
    request<XmlRenderResponse>('/api/xml-toolkit/render', { method: 'POST', body: JSON.stringify({ template, variables, validate_xml }) }),
};

