import { useI18n } from '../../i18n/useI18n';

type DocsCommonMistakesProps = {
  items: string[];
};

const labels = {
  ru: 'Частые ошибки',
  en: 'Common mistakes',
  zh: '常见错误',
};

export function DocsCommonMistakes({ items }: DocsCommonMistakesProps) {
  const { language } = useI18n();
  return (
    <section className="docs-common-mistakes">
      <span className="eyebrow">{labels[language]}</span>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}
