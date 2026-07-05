import enAudit from './locales/en/audit.json';
import enAuth from './locales/en/auth.json';
import enCommon from './locales/en/common.json';
import enDocs from './locales/en/docs.json';
import enErrors from './locales/en/errors.json';
import enIntegration from './locales/en/integration.json';
import enNavigation from './locales/en/navigation.json';
import enOnboarding from './locales/en/onboarding.json';
import enOnec from './locales/en/onec.json';
import enPackages from './locales/en/packages.json';
import enPrinter from './locales/en/printer.json';
import enProduction from './locales/en/production.json';
import enSecrets from './locales/en/secrets.json';
import enStatuses from './locales/en/statuses.json';
import ruAudit from './locales/ru/audit.json';
import ruAuth from './locales/ru/auth.json';
import ruCommon from './locales/ru/common.json';
import ruDocs from './locales/ru/docs.json';
import ruErrors from './locales/ru/errors.json';
import ruIntegration from './locales/ru/integration.json';
import ruNavigation from './locales/ru/navigation.json';
import ruOnboarding from './locales/ru/onboarding.json';
import ruOnec from './locales/ru/onec.json';
import ruPackages from './locales/ru/packages.json';
import ruPrinter from './locales/ru/printer.json';
import ruProduction from './locales/ru/production.json';
import ruSecrets from './locales/ru/secrets.json';
import ruStatuses from './locales/ru/statuses.json';
import zhAudit from './locales/zh/audit.json';
import zhAuth from './locales/zh/auth.json';
import zhCommon from './locales/zh/common.json';
import zhDocs from './locales/zh/docs.json';
import zhErrors from './locales/zh/errors.json';
import zhIntegration from './locales/zh/integration.json';
import zhNavigation from './locales/zh/navigation.json';
import zhOnboarding from './locales/zh/onboarding.json';
import zhOnec from './locales/zh/onec.json';
import zhPackages from './locales/zh/packages.json';
import zhPrinter from './locales/zh/printer.json';
import zhProduction from './locales/zh/production.json';
import zhSecrets from './locales/zh/secrets.json';
import zhStatuses from './locales/zh/statuses.json';
import type { Dictionary, Language } from './dictionary';
import type { I18nNamespace, LocaleTree } from './types';

export const packageTranslationNamespaces = ['onec', 'printer', 'auth', 'secrets'] as const;

export const namespaceResources: Record<Language, Record<I18nNamespace, LocaleTree>> = {
  en: { audit: enAudit, auth: enAuth, common: enCommon, docs: enDocs, errors: enErrors, integration: enIntegration, navigation: enNavigation, onboarding: enOnboarding, onec: enOnec, packages: enPackages, printer: enPrinter, production: enProduction, secrets: enSecrets, statuses: enStatuses },
  ru: { audit: ruAudit, auth: ruAuth, common: ruCommon, docs: ruDocs, errors: ruErrors, integration: ruIntegration, navigation: ruNavigation, onboarding: ruOnboarding, onec: ruOnec, packages: ruPackages, printer: ruPrinter, production: ruProduction, secrets: ruSecrets, statuses: ruStatuses },
  zh: { audit: zhAudit, auth: zhAuth, common: zhCommon, docs: zhDocs, errors: zhErrors, integration: zhIntegration, navigation: zhNavigation, onboarding: zhOnboarding, onec: zhOnec, packages: zhPackages, printer: zhPrinter, production: zhProduction, secrets: zhSecrets, statuses: zhStatuses },
};

export const namespaceDictionaries: Record<Language, Dictionary> = {
  en: flattenLanguage(namespaceResources.en),
  ru: flattenLanguage(namespaceResources.ru),
  zh: flattenLanguage(namespaceResources.zh),
};

function flattenLanguage(resources: Record<I18nNamespace, LocaleTree>): Dictionary {
  return Object.entries(resources).reduce<Dictionary>((acc, [namespace, tree]) => {
    flattenTree(namespace, tree, acc);
    return acc;
  }, {});
}

function flattenTree(prefix: string, value: unknown, target: Dictionary) {
  if (typeof value === 'string') {
    target[prefix] = value;
    return;
  }
  if (!value || typeof value !== 'object' || Array.isArray(value)) return;
  Object.entries(value as Record<string, unknown>).forEach(([key, nested]) => flattenTree(`${prefix}.${key}`, nested, target));
}
