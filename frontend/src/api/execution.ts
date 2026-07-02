import { request } from './client';

export interface ExecutionStepMetadata {
  name: string;
  display_name: string;
}

export const executionApi = {
  steps: () => request<ExecutionStepMetadata[]>('/api/execution/steps'),
};
