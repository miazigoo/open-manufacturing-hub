type DocsExpectedResultProps = {
  items: string[];
};

export function DocsExpectedResult({ items }: DocsExpectedResultProps) {
  return (
    <section className="docs-expected-result">
      <span className="eyebrow">Expected result</span>
      <div>
        {items.map((item) => (
          <p key={item}>{item}</p>
        ))}
      </div>
    </section>
  );
}
