import { Link } from 'react-router-dom';

type DocsNextLessonProps = {
  href?: string;
  label: string;
};

export function DocsNextLesson({ href, label }: DocsNextLessonProps) {
  const content = (
    <>
      <span className="eyebrow">Next lesson</span>
      <strong>{label}</strong>
    </>
  );
  if (!href) return <div className="docs-next-lesson">{content}</div>;
  return <Link className="docs-next-lesson" to={href}>{content}</Link>;
}
