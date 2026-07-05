import type { TranslationParams } from './context';

type Translate = (key: string, params?: TranslationParams) => string;

export interface ErrorTranslation {
  title: string;
  hint: string;
}

export function getExternalErrorTranslation(code: string | null | undefined, t: Translate): ErrorTranslation {
  const safeCode = code || 'unknown';
  const titleKey = `errors.${safeCode}.title`;
  const hintKey = `errors.${safeCode}.hint`;
  const title = t(titleKey);
  const hint = t(hintKey);
  if (title !== titleKey && hint !== hintKey) return { title, hint };
  return { title: t('errors.unknown.title'), hint: t('errors.unknown.hint') };
}
