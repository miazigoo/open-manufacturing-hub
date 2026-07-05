import { request } from './client';

export interface UIOption { id: string; label: string; type: string | null; meta: Record<string, unknown> }
export interface UIPackageState { package_id: string; installed: boolean; enabled: boolean; status: string | null; action_label: string }
export interface UINavigationItem { group: string; title: string; route: string; package_id: string | null; enabled: boolean; installed?: boolean; advanced: boolean }
export interface UICockpitSummary {
  package_state: UIPackageState;
  metrics: Record<string, number>;
  quick_actions: Array<Record<string, unknown>>;
  integrations: Array<Record<string, unknown>>;
  connection_health: Array<Record<string, unknown>>;
  recent_events: Array<Record<string, unknown>>;
}
export interface UICockpitOptions {
  package_state: UIPackageState;
  connectors: UIOption[];
  onec_connectors: UIOption[];
  odata_connections: UIOption[];
  rest_connectors: UIOption[];
  printer_connectors: UIOption[];
  operation_templates: UIOption[];
  odata_lookup_templates: UIOption[];
  scenario_presets: Array<Record<string, unknown>>;
  input_modes: string[];
  response_modes: string[];
}
export interface UIFlowBuilderOptions extends UICockpitOptions {
  matcher_types: string[];
  action_types: string[];
  available_steps: Array<{ type: string; description: string }>;
  saved_test_cases: UIOption[];
}

export const uiApi = {
  navigation: () => request<UINavigationItem[]>('/api/ui/navigation'),
  cockpitSummary: () => request<UICockpitSummary>('/api/ui/cockpit/summary'),
  cockpitOptions: () => request<UICockpitOptions>('/api/ui/cockpit/options'),
  flowBuilderOptions: () => request<UIFlowBuilderOptions>('/api/ui/flow-builder/options'),
  flowBuilderState: (flowId: string) => request<{ flow_id: string; flow: Record<string, unknown>; builder_json: Record<string, unknown>; options: UIFlowBuilderOptions }>(`/api/ui/flow-builder/${flowId}/state`),
};
