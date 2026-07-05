type DocsCommonMistakesProps = {
  items: string[];
};

export function DocsCommonMistakes({ items }: DocsCommonMistakesProps) {
  return (
    <section className="docs-common-mistakes">
      <span className="eyebrow">Common mistakes</span>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}
