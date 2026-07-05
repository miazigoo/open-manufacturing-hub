import { createContext } from 'react';
import type { Language } from './dictionary';
import type { I18nNamespace } from './types';

export type TranslationParams = Record<string, string | number | null | undefined>;

export interface I18nContextValue {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: string, params?: TranslationParams) => string;
  fallbackChain: Language[];
  loadedNamespaces: I18nNamespace[];
  missingKeys: string[];
}

export const I18nContext = createContext<I18nContextValue | null>(null);
