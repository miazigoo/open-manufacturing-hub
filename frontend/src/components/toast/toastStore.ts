export type ToastTone = 'success' | 'error' | 'info';

export interface Toast {
  id: string;
  tone: ToastTone;
  message: string;
  createdAt: number;
}

type Listener = () => void;

const listeners = new Set<Listener>();
let toasts: Toast[] = [];
const timers = new Map<string, ReturnType<typeof setTimeout>>();

const DEFAULT_DURATION = 6000;
const MAX_TOASTS = 4;

function emit() {
  for (const listener of listeners) listener();
}

export function subscribeToasts(listener: Listener) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function getToasts() {
  return toasts;
}

export function dismissToast(id: string) {
  const timer = timers.get(id);
  if (timer) {
    clearTimeout(timer);
    timers.delete(id);
  }
  toasts = toasts.filter((toast) => toast.id !== id);
  emit();
}

function pushToast(tone: ToastTone, message: string, duration = DEFAULT_DURATION) {
  const trimmed = message?.trim();
  if (!trimmed) return;
  const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  toasts = [...toasts, { id, tone, message: trimmed, createdAt: Date.now() }].slice(-MAX_TOASTS);
  if (duration > 0) {
    timers.set(id, setTimeout(() => dismissToast(id), duration));
  }
  emit();
  return id;
}

export const toast = {
  success: (message: string, duration?: number) => pushToast('success', message, duration),
  error: (message: string, duration?: number) => pushToast('error', message, duration),
  info: (message: string, duration?: number) => pushToast('info', message, duration),
};
