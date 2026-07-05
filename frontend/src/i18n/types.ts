export const i18nLanguages = ['ru', 'en', 'zh'] as const;
export type I18nLanguage = typeof i18nLanguages[number];

export const i18nNamespaces = [
  'common',
  'navigation',
  'statuses',
  'packages',
  'errors',
  'onboarding',
  'docs',
  'integration',
  'onec',
  'printer',
  'auth',
  'secrets',
  'production',
  'audit',
] as const;

export type I18nNamespace = typeof i18nNamespaces[number];
export type LocaleTree = Record<string, unknown>;
