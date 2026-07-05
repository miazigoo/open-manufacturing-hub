import { languageMeta, type Language } from '../../i18n/dictionary';
import { useT } from '../../i18n/useI18n';

const languages: Language[] = ['ru', 'en', 'zh'];

export function LanguageSwitcher({ value, onChange }: { value: Language; onChange: (language: Language) => void }) {
  const t = useT();
  return (
    <div className="docs-language-switcher" aria-label={t('topbar.language')}>
      <span>{t('topbar.language')}</span>
      {languages.map((language) => <button key={language} type="button" className={value === language ? 'active' : ''} onClick={() => onChange(language)}>{languageMeta[language].nativeName}</button>)}
    </div>
  );
}
