import type { Language } from '../../i18n/dictionary';

export type DocsPackageId = 'core' | 'onec' | 'reference' | 'printer' | 'auth' | 'secrets' | 'packages';

export interface DocsPageRecord {
  id: string;
  packageId: DocsPackageId;
  sectionId: string;
  slug: string;
  title: string;
  description: string;
  order: number;
  updatedAt: string;
  markdown: string;
  translationStatus?: 'complete' | 'in_progress' | 'fallback';
}

export interface DocsSectionRecord {
  id: string;
  packageId: DocsPackageId;
  title: string;
  description: string;
  order: number;
  pages: DocsPageRecord[];
}

export interface DocsPackageRecord {
  id: DocsPackageId;
  title: string;
  description: string;
  order: number;
  accent: string;
  sections: DocsSectionRecord[];
}

export interface DocsLanguageBundle {
  language: Language;
  packages: DocsPackageRecord[];
}

export interface TocItem {
  id: string;
  text: string;
  level: number;
}
