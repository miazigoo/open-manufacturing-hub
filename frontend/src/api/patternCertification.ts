import { request } from './client';
import type { LocalizedText } from './integrationPatterns';

export type PatternCertificationStatus = 'not_started' | 'partial' | 'ready_for_training' | 'ready_for_production' | 'deprecated';
export type PatternCertificationCheckStatus = 'passed' | 'warning' | 'failed' | 'planned';

export interface PatternCertificationCheck {
  key: string;
  label: LocalizedText;
  status: PatternCertificationCheckStatus;
  message: LocalizedText;
  link: string | null;
  source: string;
}

export interface PatternCertification {
  pattern_id: string;
  title: LocalizedText;
  description: LocalizedText;
  certification_status: PatternCertificationStatus;
  status_label: LocalizedText;
  wizard_route: string | null;
  docs_link: string | null;
  coverage_requirement_ids: string[];
  ui_status: PatternCertificationCheckStatus;
  docs_status: PatternCertificationCheckStatus;
  training_status: PatternCertificationCheckStatus;
  tests_status: PatternCertificationCheckStatus;
  timeline_status: PatternCertificationCheckStatus;
  simple_mode_status: PatternCertificationCheckStatus;
  checks: PatternCertificationCheck[];
  problems: string[];
  actions: LocalizedText[];
}

export interface PatternCertificationSummary {
  total: number;
  not_started: number;
  partial: number;
  ready_for_training: number;
  ready_for_production: number;
  deprecated: number;
  problem_patterns: number;
}

export interface PatternCertificationListResponse {
  summary: PatternCertificationSummary;
  items: PatternCertification[];
}

export const patternCertificationApi = {
  list: () => request<PatternCertificationListResponse>('/api/integration-patterns/certification'),
  get: (patternId: string) => request<PatternCertification>(`/api/integration-patterns/${patternId}/certification`),
  check: (patternId: string) => request<PatternCertification>(`/api/integration-patterns/${patternId}/certification/check`, { method: 'POST' }),
};
