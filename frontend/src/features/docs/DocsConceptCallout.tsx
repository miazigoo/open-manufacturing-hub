type DocsConceptCalloutProps = {
  title: string;
  body: string;
};

export function DocsConceptCallout({ title, body }: DocsConceptCalloutProps) {
  return (
    <aside className="docs-concept-callout">
      <span className="eyebrow">Concept</span>
      <h3>{title}</h3>
      <p>{body}</p>
    </aside>
  );
}
