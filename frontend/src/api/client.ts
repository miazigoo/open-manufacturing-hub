export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === 'string' ? detail : `API request failed with ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

export type { Artifact, ArtifactDiff, EventRun, EventStatus, EventStep, EventSummary, EventTimeline, ExternalErrorSummary, RunMode, RunStatus, StepStatus } from './types';

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');

  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (response.status === 204) return undefined as T;

  const text = await response.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text || null;
  }
  if (!response.ok) {
    const detail = typeof data === 'object' && data !== null && 'detail' in data ? (data as { detail: unknown }).detail : data;
    throw new ApiError(response.status, detail);
  }
  return data as T;
}

export function asJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}
