import { request } from '../../api/client';
import type { InputContract, InputContractValidationResponse, InputDraftSaveResponse, InputParseRequest, InputParseResponse, IntegrationScenario, ODataStepConfig, ODataStepPreviewResponse, ODataStepRequest, ODataStepSaveResponse, ODataStepTestResponse, ODataStepValidationResponse } from './types';

export const integrationMasterApi = {
  scenarios: () => request<IntegrationScenario[]>('/api/integration-master/scenarios'),
  parse: (payload: InputParseRequest) => request<InputParseResponse>('/api/integration-master/input/parse', { method: 'POST', body: JSON.stringify(payload) }),
  validate: (contract: InputContract) => request<InputContractValidationResponse>('/api/integration-master/input/validate', { method: 'POST', body: JSON.stringify({ contract }) }),
  saveDraft: (contract: InputContract, parseResult?: InputParseResponse | null) => request<InputDraftSaveResponse>('/api/integration-master/input/save-draft', { method: 'POST', body: JSON.stringify({ contract, parse_result: parseResult ?? null }) }),
  validateODataStep: (payload: ODataStepRequest) => request<ODataStepValidationResponse>('/api/integration-master/odata-step/validate', { method: 'POST', body: JSON.stringify(payload) }),
  previewODataStep: (payload: ODataStepRequest) => request<ODataStepPreviewResponse>('/api/integration-master/odata-step/preview', { method: 'POST', body: JSON.stringify(payload) }),
  testODataStep: (payload: ODataStepRequest) => request<ODataStepTestResponse>('/api/integration-master/odata-step/test', { method: 'POST', body: JSON.stringify(payload) }),
  saveODataStep: (draftId: string, inputContract: InputContract, step: ODataStepConfig) =>
    request<ODataStepSaveResponse>(`/api/integration-master/drafts/${draftId}/odata-steps`, { method: 'POST', body: JSON.stringify({ input_contract: inputContract, odata_step: step }) }),
};
