import { useI18n } from '../../i18n/useI18n';

type DocsLessonPageProps = {
  label?: string;
};

const copy = {
  ru: {
    defaultLabel: 'Академия интеграции 1C',
    title: 'Учебный формат',
    body: 'Каждый урок идет по одному шаблону: что собрать, зачем это нужно, что нажать, какие значения ввести, что должно появиться в UI и какие ошибки проверить.',
    operatorSteps: [
      'Откройте урок и нужный экран продукта в соседних вкладках.',
      'Выполняйте по одному шагу и сразу сверяйте раздел “Что должно получиться”.',
      'Отмечайте чеклист только после проверки результата в UI, Timeline или Training Sandbox.',
      'Если результат отличается, не угадывайте: откройте artifacts и разберите первый failed step.',
    ],
  },
  en: {
    defaultLabel: '1C Integration Academy',
    title: 'Learning format',
    body: 'Every lesson follows one template: what to build, why it matters, where to click, which values to enter, what should appear in the UI and which errors to check.',
    operatorSteps: [
      'Open the lesson and the product screen in separate tabs.',
      'Complete one step at a time and compare it with the expected result.',
      'Mark the checklist only after checking the UI, Timeline or Training Sandbox.',
      'If the result differs, inspect artifacts and the first failed step instead of guessing.',
    ],
  },
  zh: {
    defaultLabel: '1C 集成学院',
    title: '学习格式',
    body: '每节课都遵循同一模板：要构建什么、为什么重要、点击哪里、输入哪些值、UI 中应出现什么以及要检查哪些错误。',
    operatorSteps: [
      '在不同标签页中打开课程和产品页面。',
      '一次只完成一个步骤，并与预期结果对照。',
      '只有在 UI、Timeline 或 Training Sandbox 中确认结果后才勾选清单。',
      '如果结果不同，请查看 artifacts 和第一个失败步骤，不要猜测。',
    ],
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
      <ol className="docs-operator-rhythm">
        {text.operatorSteps.map((step) => <li key={step}>{step}</li>)}
      </ol>
    </section>
  );
}
