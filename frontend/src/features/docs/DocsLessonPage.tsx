type DocsLessonPageProps = {
  label?: string;
};

export function DocsLessonPage({ label = '1C Integration Academy' }: DocsLessonPageProps) {
  return (
    <section className="docs-lesson-shell" aria-label={label}>
      <span className="eyebrow">{label}</span>
      <strong>Учебный формат</strong>
      <p>Каждый урок идет по одному шаблону: что собрать, зачем это нужно, что нажать, какие значения ввести, что должно появиться в UI и какие ошибки проверить.</p>
    </section>
  );
}
