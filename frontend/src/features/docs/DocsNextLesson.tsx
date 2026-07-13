import { Link } from 'react-router-dom';
import { useI18n } from '../../i18n/useI18n';

type DocsNextLessonProps = {
  href?: string;
  label?: string;
};

const labels = {
  ru: { next: 'Следующий урок' },
  en: { next: 'Next lesson' },
  zh: { next: '下一课' },
};

export function DocsNextLesson({ href, label }: DocsNextLessonProps) {
  const { language } = useI18n();
  const nextLabel = labels[language].next;
  const accessibleLabel = label ? `${nextLabel}: ${label}` : nextLabel;
  const content = (
    <>
      <span className="eyebrow">{nextLabel}</span>
      <strong>{label ?? nextLabel}</strong>
    </>
  );
  if (!href) return <div className="docs-next-lesson">{content}</div>;
  return <Link className="docs-next-lesson" to={href} aria-label={accessibleLabel}>{content}</Link>;
}
