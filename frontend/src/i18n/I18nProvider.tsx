import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from 'react';
import { dictionaries, languageMeta } from './dictionary';
import type { Language } from './dictionary';

const STORAGE_KEY = 'omh_language';

type Params = Record<string, string | number | null | undefined>;

interface I18nContextValue {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: string, params?: Params) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

function initialLanguage(): Language {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && stored in dictionaries) return stored as Language;
  } catch {
    // Browser privacy settings can block storage. Language fallback must still work.
  }
  const browser = navigator.language?.toLowerCase() ?? '';
  if (browser.startsWith('ru')) return 'ru';
  if (browser.startsWith('zh')) return 'zh';
  return 'en';
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => initialLanguage());

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
    t: (key, params) => interpolate(dictionaries[language][key] ?? dictionaries.en[key] ?? key, params),
  }), [language]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) throw new Error('useI18n must be used inside I18nProvider');
  return context;
}

export function useT() {
  return useI18n().t;
}

function interpolate(template: string, params?: Params): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (_, key: string) => String(params[key] ?? ''));
}
