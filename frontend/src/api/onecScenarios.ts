import { request } from './client';

export interface OneCScenarioPreset {
  key: string;
  name: string;
  description: string;
  source_resource: string;
  event_type: string;
  entity_type: string;
  mappings: string[];
}

export interface OneCScenarioInstallResult {
  scenario: string;
  source_connector_id: string;
  target_connector_id: string;
  workflow_id: string;
  polling_job_id: string;
  mappings: string[];
  notes: string[];
}

export const onecScenariosApi = {
  presets: () => request<OneCScenarioPreset[]>('/api/onec-scenarios/presets'),
  installSalesOrderDemo: () => request<OneCScenarioInstallResult>('/api/onec-scenarios/install-sales-order-demo', { method: 'POST' }),
};
