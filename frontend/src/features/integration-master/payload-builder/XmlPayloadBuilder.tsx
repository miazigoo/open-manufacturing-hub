interface XmlPayloadBuilderProps {
  value: string;
  onChange: (value: string) => void;
}

export function XmlPayloadBuilder({ value, onChange }: XmlPayloadBuilderProps) {
  return (
    <section className="panel stack-form">
      <div className="panel-toolbar"><div><span className="eyebrow">XML</span><h3>XML template</h3><p className="microcopy">Значения переменных будут XML-escaped, а результат проверяется на well-formed XML.</p></div></div>
      <textarea className="code-textarea" rows={12} value={value} onChange={(event) => onChange(event.target.value)} spellCheck={false} />
    </section>
  );
}
