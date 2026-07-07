interface RawTextPayloadBuilderProps {
  value: string;
  onChange: (value: string) => void;
}

export function RawTextPayloadBuilder({ value, onChange }: RawTextPayloadBuilderProps) {
  return (
    <section className="panel stack-form">
      <div className="panel-toolbar"><div><span className="eyebrow">Raw text</span><h3>Text template</h3><p className="microcopy">{'Подходит для простого ответа вроде OK order={{order.Number}} codes={{codes.length}}.'}</p></div></div>
      <textarea className="code-textarea" rows={8} value={value} onChange={(event) => onChange(event.target.value)} spellCheck={false} />
    </section>
  );
}
