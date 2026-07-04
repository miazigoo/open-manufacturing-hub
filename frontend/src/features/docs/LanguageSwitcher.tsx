import { languageMeta, type Language } from '../../i18n/dictionary';

const languages: Language[] = ['ru', 'en', 'zh'];
const labels: Record<Language, string> = { ru: 'Язык', en: 'Language', zh: '语言' };

export function LanguageSwitcher({ value, onChange }: { value: Language; onChange: (language: Language) => void }) {
  return (
    <div className="docs-language-switcher" aria-label={labels[value]}>
      <span>{labels[value]}</span>
      {languages.map((language) => <button key={language} type="button" className={value === language ? 'active' : ''} onClick={() => onChange(language)}>{languageMeta[language].nativeName}</button>)}
    </div>
  );
}
