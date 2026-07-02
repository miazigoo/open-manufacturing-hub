import { ReactNode, useEffect, useMemo, useState } from 'react';
import { I18nContext, I18nContextValue, TranslationParams } from './context';
import { dictionaries, languageMeta } from './dictionary';
import type { Language } from './dictionary';

const STORAGE_KEY = 'omh_language';

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

function interpolate(template: string, params?: TranslationParams): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (_, key: string) => String(params[key] ?? ''));
}
