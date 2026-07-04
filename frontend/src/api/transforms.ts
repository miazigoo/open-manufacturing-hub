import { request } from './client';

export interface TransformDefinition {
  name: string;
  category: string;
  description: string;
  args_schema: Record<string, unknown>;
}

export interface TransformTraceItem {
  transform: string;
  before: unknown;
  after: unknown;
  args: Record<string, unknown>;
}

export interface TransformTestResponse {
  success: boolean;
  result: unknown;
  error_code: string | null;
  error_message: string | null;
  trace: TransformTraceItem[];
}

export const transformsApi = {
  list: () => request<TransformDefinition[]>('/api/transforms'),
  test: (payload: { value: unknown; chain: Array<Record<string, unknown>>; context?: Record<string, unknown> }) => request<TransformTestResponse>('/api/transforms/test', { method: 'POST', body: JSON.stringify(payload) }),
};
