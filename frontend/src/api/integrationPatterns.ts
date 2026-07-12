import { request } from './client';

export type PatternStatus = 'available' | 'coming_soon';
export type InputMode = 'json' | 'xml' | 'raw_text' | 'file' | 'odata';

export interface LocalizedText { ru?: string; en?: string; [key: string]: string | undefined }

export interface IntegrationPattern {
  pattern_id: string;
  title: LocalizedText;
  description: LocalizedText;
  category: string;
  difficulty: string;
  status: PatternStatus;
  input_modes: InputMode[];
  data_steps: string[];
  final_actions: string[];
  recommended_wizard: string;
  wizard_route: string | null;
  wizard_label: LocalizedText;
  examples: string[];
  package_requirements: string[];
  docs_link: string;
  use_cases: LocalizedText[];
  flow: string[];
  initial_steps: string[];
  required_inputs: LocalizedText[];
  expected_result: LocalizedText;
  test_plan: LocalizedText[];
  timeline_hint: LocalizedText;
  start_disabled_reason?: LocalizedText | null;
}

export interface PatternRecommendRequest {
  source_system?: string | null;
  input_mode?: InputMode | null;
  needs_odata?: boolean | null;
  needs_foreach?: boolean | null;
  needs_file_save?: boolean | null;
  needs_response?: boolean | null;
  needs_send_endpoint?: boolean | null;
  needs_print?: boolean | null;
  needs_writeback?: boolean | null;
  needs_polling?: boolean | null;
}

export interface PatternRecommendation {
  pattern_id: string;
  confidence: number;
  reason: string;
  pattern: IntegrationPattern;
}

export interface PatternRecommendResponse {
  recommended_patterns: PatternRecommendation[];
}

export interface PatternStartResponse {
  pattern_id: string;
  wizard_route: string;
  recommended_wizard: string;
  wizard_label: LocalizedText;
  initial_steps: string[];
  explanation: LocalizedText;
  examples: string[];
  package_requirements: string[];
}

export const integrationPatternsApi = {
  list: () => request<IntegrationPattern[]>('/api/integration-patterns'),
  get: (patternId: string) => request<IntegrationPattern>(`/api/integration-patterns/${patternId}`),
  recommend: (payload: PatternRecommendRequest) => request<PatternRecommendResponse>('/api/integration-patterns/recommend', { method: 'POST', body: JSON.stringify(payload) }),
  start: (patternId: string) => request<PatternStartResponse>('/api/integration-patterns/start', { method: 'POST', body: JSON.stringify({ pattern_id: patternId }) }),
};

export function localized(value: LocalizedText | null | undefined, fallback = '—') {
  return value?.ru || value?.en || fallback;
}
