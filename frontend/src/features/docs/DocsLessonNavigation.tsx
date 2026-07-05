import { Link } from 'react-router-dom';
import type { DocsPageRecord } from './types';
import { pagePath } from './content';
import { useI18n } from '../../i18n/useI18n';

const labels = {
  ru: { previous: '← Previous lesson', next: 'Next lesson →', here: 'You are here', lesson: 'Lesson' },
  en: { previous: '← Previous lesson', next: 'Next lesson →', here: 'You are here', lesson: 'Lesson' },
  zh: { previous: '← 上一课', next: '下一课 →', here: '当前位置', lesson: '课程' },
};

type DocsLessonNavigationProps = {
  current: DocsPageRecord;
  previous?: DocsPageRecord;
  next?: DocsPageRecord;
  index: number;
  total: number;
};

export function DocsLessonNavigation({ current, previous, next, index, total }: DocsLessonNavigationProps) {
  const { language } = useI18n();
  const copy = labels[language];
  return (
    <nav className="docs-lesson-navigation" aria-label="Academy lesson navigation">
      <div className="docs-lesson-position">
        <span className="eyebrow">Academy</span>
        <strong>{copy.here}: {copy.lesson} {index + 1} of {total}</strong>
        <small>{current.title}</small>
      </div>
      <div className="docs-lesson-nav-links">
        {previous ? <Link className="ghost-button" to={pagePath(previous)}>{copy.previous}</Link> : <span className="docs-nav-disabled">{copy.previous}</span>}
        {next ? <Link className="primary-link" to={pagePath(next)}>{copy.next}</Link> : <span className="docs-nav-disabled">{copy.next}</span>}
      </div>
    </nav>
  );
}
