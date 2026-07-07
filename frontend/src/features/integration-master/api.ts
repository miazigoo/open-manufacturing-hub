import { request } from '../../api/client';
import type { InputContract, InputContractValidationResponse, InputDraftSaveResponse, InputParseRequest, InputParseResponse, IntegrationScenario } from './types';

export const integrationMasterApi = {
  scenarios: () => request<IntegrationScenario[]>('/api/integration-master/scenarios'),
  parse: (payload: InputParseRequest) => request<InputParseResponse>('/api/integration-master/input/parse', { method: 'POST', body: JSON.stringify(payload) }),
  validate: (contract: InputContract) => request<InputContractValidationResponse>('/api/integration-master/input/validate', { method: 'POST', body: JSON.stringify({ contract }) }),
  saveDraft: (contract: InputContract, parseResult?: InputParseResponse | null) => request<InputDraftSaveResponse>('/api/integration-master/input/save-draft', { method: 'POST', body: JSON.stringify({ contract, parse_result: parseResult ?? null }) }),
};
