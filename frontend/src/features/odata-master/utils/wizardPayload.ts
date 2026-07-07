import type { ODataWizardSpec } from '../types';
import { prettyJson, safeJsonParse } from './placeholders';

export const defaultIncomingJson = {
  operation: 'dnp_sinc_pull_codes',
  sinc: 'dnp_sinc_pull_codes',
  order_id: 10271,
  order_name: '26-0666/6938',
  Number: '260666/6938',
};

export function defaultWizardSpec(): ODataWizardSpec {
  return {
    name: 'DnP CHZ codes sync',
    slug: 'dnp_sinc_pull_codes',
    description: 'DnP запрашивает пул кодов Честного знака по номеру производственного заказа 1C.',
    source: {
      system: 'dnp',
      input_mode: 'json',
      sample: defaultIncomingJson,
      operation_key: { field: 'sinc', value: 'dnp_sinc_pull_codes' },
      auth_mode: 'none',
      auth_config_json: {},
    },
    steps: [],
    final_action: {
      type: 'return_response',
      method: 'POST',
      url: '',
      headers: {},
      body_type: 'json',
      body: {},
      response_to_caller: { mode: 'sync_response', body_type: 'json', body: { ok: true } },
    },
  };
}

export function sampleAsText(spec: ODataWizardSpec) {
  if (spec.source.input_mode === 'json') return prettyJson(spec.source.sample || {});
  return String(spec.source.sample || '');
}

export function applySampleText(spec: ODataWizardSpec, text: string): ODataWizardSpec {
  const sample = spec.source.input_mode === 'json' ? safeJsonParse<Record<string, unknown>>(text, {}) : text;
  return { ...spec, source: { ...spec.source, sample } };
}
