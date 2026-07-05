import { useI18n } from '../../i18n/useI18n';

type DocsLessonPageProps = {
  label?: string;
};

const copy = {
  ru: {
    defaultLabel: 'Академия интеграции 1C',
    title: 'Учебный формат',
    body: 'Каждый урок идет по одному шаблону: что собрать, зачем это нужно, что нажать, какие значения ввести, что должно появиться в UI и какие ошибки проверить.',
  },
  en: {
    defaultLabel: '1C Integration Academy',
    title: 'Learning format',
    body: 'Every lesson follows one template: what to build, why it matters, where to click, which values to enter, what should appear in the UI and which errors to check.',
  },
  zh: {
    defaultLabel: '1C 集成学院',
    title: '学习格式',
    body: '每节课都遵循同一模板：要构建什么、为什么重要、点击哪里、输入哪些值、UI 中应出现什么以及要检查哪些错误。',
  },
};

export function DocsLessonPage({ label }: DocsLessonPageProps) {
  const { language } = useI18n();
  const text = copy[language];
  const resolvedLabel = label ?? text.defaultLabel;
  return (
    <section className="docs-lesson-shell" aria-label={resolvedLabel}>
      <span className="eyebrow">{resolvedLabel}</span>
      <strong>{text.title}</strong>
      <p>{text.body}</p>
    </section>
  );
}
