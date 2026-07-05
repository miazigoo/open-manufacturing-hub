import { ReactNode, useEffect, useMemo, useRef, useState } from 'react';
import { I18nContext, I18nContextValue, TranslationParams } from './context';
import { dictionaries, languageMeta } from './dictionary';
import type { Language } from './dictionary';
import { i18nNamespaces } from './types';

const STORAGE_KEY = 'omh_language';

function initialLanguage(): Language {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && stored in dictionaries) return stored as Language;
  } catch {
    // Browser privacy settings can block storage. Language fallback must still work.
  }
  return 'ru';
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => initialLanguage());
  const missingKeys = useRef(new Set<string>());

  useEffect(() => {
    document.documentElement.lang = languageMeta[language].htmlLang;
    try {
      localStorage.setItem(STORAGE_KEY, language);
    } catch {
      // Persisting the preference is best-effort; switching in the current session still works.
    }
  }, [language]);

  const value = useMemo<I18nContextValue>(() => ({
    language,
    setLanguage: setLanguageState,
    fallbackChain: language === 'ru' ? ['ru', 'en'] : [language, 'ru', 'en'],
    loadedNamespaces: [...i18nNamespaces],
    missingKeys: Array.from(missingKeys.current).sort(),
    t: (key, params) => interpolate(resolveTranslation(key, language, missingKeys.current), params),
  }), [language]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

function resolveTranslation(key: string, language: Language, missingKeys: Set<string>) {
  const chain: Language[] = language === 'ru' ? ['ru', 'en'] : [language, 'ru', 'en'];
  for (const candidate of chain) {
    const translated = dictionaries[candidate][key];
    if (translated !== undefined) return translated;
  }
  missingKeys.add(key);
  return key;
}

function interpolate(template: string, params?: TranslationParams): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (_, key: string) => String(params[key] ?? ''));
}
