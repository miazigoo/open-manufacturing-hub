import { request } from './client';

export interface BusinessRuleSet {
  id: string;
  name: string;
  description: string | null;
  enabled: boolean;
  scope: 'global' | 'workflow' | 'integration_flow' | 'package' | null;
  rules_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface RuleEvaluationResult {
  success: boolean;
  matched_rules: string[];
  actions_applied: Array<Record<string, unknown>>;
  status: string;
  error_code: string | null;
  error_message: string | null;
  payload: Record<string, unknown>;
  variables: Record<string, unknown>;
  target_system: string | null;
  operation: string | null;
  route: string | null;
  skip_steps: string[];
  trace: Record<string, unknown>;
}

export const businessRulesApi = {
  list: () => request<BusinessRuleSet[]>('/api/business-rules'),
  get: (id: string) => request<BusinessRuleSet>(`/api/business-rules/${id}`),
  create: (payload: Partial<BusinessRuleSet>) => request<BusinessRuleSet>('/api/business-rules', { method: 'POST', body: JSON.stringify(payload) }),
  patch: (id: string, payload: Partial<BusinessRuleSet>) => request<BusinessRuleSet>(`/api/business-rules/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  installPresets: () => request<Record<string, number>>('/api/business-rules/install-presets', { method: 'POST' }),
  test: (id: string, payload: { payload: Record<string, unknown>; variables?: Record<string, unknown>; rules_json?: Record<string, unknown> }) => request<RuleEvaluationResult>(`/api/business-rules/${id}/test`, { method: 'POST', body: JSON.stringify(payload) }),
};
