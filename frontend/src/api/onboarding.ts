import { request } from './client';

export interface OnboardingItem {
  id: string | null;
  key: string;
  title: string;
  description: string;
  route: string | null;
  docs_url: string | null;
  completed: boolean;
  completed_at: string | null;
  skipped: boolean;
  skipped_at: string | null;
  metadata_json: Record<string, unknown>;
}

export interface OnboardingState {
  items: OnboardingItem[];
  completed_count: number;
  total_count: number;
  setup_done: boolean;
}

export interface ExampleRunResponse {
  success: boolean;
  example_id: string;
  event_id: string;
  timeline_url: string;
  message: string;
}

export const onboardingApi = {
  state: () => request<OnboardingState>('/api/onboarding/state'),
  complete: (key: string, metadata_json: Record<string, unknown> = {}) => request<OnboardingItem>('/api/onboarding/complete', { method: 'POST', body: JSON.stringify({ key, metadata_json }) }),
  skip: (key: string, metadata_json: Record<string, unknown> = {}) => request<OnboardingItem>('/api/onboarding/skip', { method: 'POST', body: JSON.stringify({ key, metadata_json }) }),
  reset: (key?: string) => request<OnboardingState>('/api/onboarding/reset', { method: 'POST', body: key ? JSON.stringify({ key, metadata_json: {} }) : undefined }),
  runExample: (exampleId: string) => request<ExampleRunResponse>(`/api/onboarding/examples/${exampleId}/run`, { method: 'POST' }),
};
