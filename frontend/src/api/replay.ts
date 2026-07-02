import { EventRun, request } from './client';

export const replayApi = {
  full: (eventId: string) => request<EventRun>(`/api/events/${eventId}/replay`, { method: 'POST' }),
  fromStep: (runId: string, stepName: string) =>
    request<EventRun>(`/api/runs/${runId}/replay-from-step`, { method: 'POST', body: JSON.stringify({ step_name: stepName }) }),
  editReplay: (artifactId: string, editedContent: Record<string, unknown>, startFromStep: string) =>
    request<EventRun>(`/api/artifacts/${artifactId}/edit-replay`, {
      method: 'POST',
      body: JSON.stringify({ edited_content: editedContent, start_from_step: startFromStep }),
    }),
  dryRun: (eventId: string) => request<EventRun>(`/api/events/${eventId}/dry-run`, { method: 'POST' }),
};
