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
  polling_job_id: string | null;
  mappings: string[];
  notes: string[];
}

export interface ShipmentFactTestPayload {
  order_id: string;
  shipment_id: string;
  status: string;
  warehouse_id: string;
  items: Array<Record<string, unknown>>;
}

export interface StockBalanceTestPayload {
  warehouse_id: string;
  occurred_at: string;
  items: Array<Record<string, unknown>>;
}

export interface InventoryResultTestPayload {
  inventory_id: string;
  warehouse_id: string;
  completed_at: string;
  items: Array<Record<string, unknown>>;
}

export interface ShipmentFactTestResult {
  event_id: string;
  status: string;
  timeline_url: string;
}

export const onecScenariosApi = {
  presets: () => request<OneCScenarioPreset[]>('/api/onec-scenarios/presets'),
  installSalesOrderDemo: () => request<OneCScenarioInstallResult>('/api/onec-scenarios/install-sales-order-demo', { method: 'POST' }),
  installBidirectionalDemo: () => request<OneCScenarioInstallResult>('/api/onec-scenarios/install-bidirectional-demo', { method: 'POST' }),
  installErpWmsIntegration: () => request<OneCScenarioInstallResult>('/api/onec-scenarios/install-erp-wms-integration', { method: 'POST' }),
  testShipmentFact: (payload: ShipmentFactTestPayload) => request<ShipmentFactTestResult>('/api/onec-scenarios/test-shipment-fact', { method: 'POST', body: JSON.stringify(payload) }),
  testStockBalance: (payload: StockBalanceTestPayload) => request<ShipmentFactTestResult>('/api/onec-scenarios/test-stock-balance', { method: 'POST', body: JSON.stringify(payload) }),
  testInventoryResult: (payload: InventoryResultTestPayload) => request<ShipmentFactTestResult>('/api/onec-scenarios/test-inventory-result', { method: 'POST', body: JSON.stringify(payload) }),
};
