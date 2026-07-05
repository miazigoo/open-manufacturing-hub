export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(errorMessage(status, detail));
    this.status = status;
    this.detail = detail;
  }
}

function errorMessage(status: number, detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && 'message' in detail && typeof (detail as { message?: unknown }).message === 'string') return (detail as { message: string }).message;
  if (detail && typeof detail === 'object' && 'error' in detail && typeof (detail as { error?: unknown }).error === 'string') return (detail as { error: string }).error;
  return `API request failed with ${status}`;
}

export type { Artifact, ArtifactDiff, EventRun, EventStatus, EventStep, EventSummary, EventTimeline, ExternalErrorSummary, RunMode, RunStatus, StepStatus } from './types';

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');

  const response = await fetch(apiUrl(path), { ...init, headers, credentials: 'include' });
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

export function apiUrl(path: string): string {
  const base = String(API_BASE_URL || '').replace(/\/$/, '');
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  if (base.endsWith('/api') && normalizedPath.startsWith('/api/')) return `${base}${normalizedPath.slice(4)}`;
  return `${base}${normalizedPath}`;
}
