import { request } from './client';
import type { LocalizedText } from './integrationPatterns';

export type CoverageStatus = 'ready' | 'partial' | 'planned' | 'missing' | 'missing_docs' | 'missing_wizard';
export type DimensionStatus = 'ready' | 'partial' | 'planned' | 'missing' | 'missing_docs' | 'missing_wizard' | 'missing_training' | 'not_applicable';

export interface CoverageDimensionStatuses {
  wizard: DimensionStatus;
  docs: DimensionStatus;
  training: DimensionStatus;
  troubleshooting: DimensionStatus;
  e2e: DimensionStatus;
}

export interface CoverageChecklistItem {
  label: string;
  status: DimensionStatus;
  link: string | null;
  note: string | null;
}

export interface PackageCoverageStatus {
  package_id: string;
  installed: boolean;
  enabled: boolean;
  warning: string | null;
}

export interface IntegrationCoverageItem {
  requirement_id: string;
  title: LocalizedText;
  description: LocalizedText;
  category: string;
  source_systems: string[];
  source_summary: LocalizedText;
  input_modes: string[];
  input_summary: LocalizedText;
  omh_actions: string[];
  omh_actions_summary: LocalizedText;
  result_summary: LocalizedText;
  runtime_needs: string[];
  personas: string[];
  complexity: 'basic' | 'intermediate' | 'advanced';
  required_capabilities: string[];
  recommended_pattern: string | null;
  recommended_tool: LocalizedText;
  wizard_route: string | null;
  workbench_route: string | null;
  docs_links: string[];
  recipe_link: string | null;
  training_example_ids: string[];
  troubleshooting_links: string[];
  e2e_tests: string[];
  test_case_ids: string[];
  package_requirements: string[];
  statuses: CoverageDimensionStatuses;
  status: CoverageStatus;
  readiness_score: number;
  gaps: string[];
  checklist: CoverageChecklistItem[];
  package_statuses: PackageCoverageStatus[];
  show_in_integration_start: boolean;
}

export interface IntegrationCoverageSummary {
  total: number;
  ready: number;
  partial: number;
  planned: number;
  missing: number;
  missing_docs: number;
  missing_wizard: number;
  average_readiness: number;
  by_status: Record<string, number>;
  by_persona: Record<string, number>;
}

export interface IntegrationCoverageResponse {
  summary: IntegrationCoverageSummary;
  items: IntegrationCoverageItem[];
}

export interface IntegrationCoverageReportResponse {
  markdown: string;
}

export const integrationCoverageApi = {
  list: () => request<IntegrationCoverageResponse>('/api/integration-coverage'),
  get: (requirementId: string) => request<IntegrationCoverageItem>(`/api/integration-coverage/${requirementId}`),
  summary: () => request<IntegrationCoverageSummary>('/api/integration-coverage/summary'),
  report: () => request<IntegrationCoverageReportResponse>('/api/integration-coverage/report'),
};
