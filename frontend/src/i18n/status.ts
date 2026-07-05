import type { TranslationParams } from './context';

type Translate = (key: string, params?: TranslationParams) => string;

export function statusTranslationKey(status?: string | null) {
  return `statuses.${status || 'unknown'}`;
}

export function getStatusLabel(status: string | null | undefined, t: Translate) {
  const safeStatus = status || 'unknown';
  const namespacedKey = statusTranslationKey(safeStatus);
  const namespaced = t(namespacedKey);
  if (namespaced !== namespacedKey) return namespaced;
  const legacyKey = `status.${safeStatus}`;
  const legacy = t(legacyKey);
  if (legacy !== legacyKey) return legacy;
  return safeStatus.replaceAll('_', ' ');
}
