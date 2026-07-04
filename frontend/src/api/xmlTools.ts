import { request } from './client';

export interface XmlParseResponse { valid: boolean; sha256: string; size_bytes: number; parsed: Record<string, unknown> | null; preview: string; pretty_xml: string | null; paths: string[]; error: string | null }
export interface XmlDiffResponse { same_hash: boolean; left_sha256: string; right_sha256: string; forwarded_unchanged: boolean; diff_text: string }

export const xmlToolsApi = {
  parse: (xml: string) => request<XmlParseResponse>('/api/xml-tools/parse', { method: 'POST', body: JSON.stringify({ xml }) }),
  diff: (left_xml: string, right_xml: string) => request<XmlDiffResponse>('/api/xml-tools/diff', { method: 'POST', body: JSON.stringify({ left_xml, right_xml }) }),
};
