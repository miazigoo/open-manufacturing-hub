import { CodeEditor } from '../../../components/CodeEditor';

interface JsonRawTemplateEditorProps {
  value: string;
  onChange: (value: string) => void;
}

export function JsonRawTemplateEditor({ value, onChange }: JsonRawTemplateEditorProps) {
  return (
    <section className="panel stack-form">
      <div className="panel-toolbar"><div><span className="eyebrow">Advanced</span><h3>Raw JSON template</h3><p className="microcopy">{'Template должен быть валидным JSON до рендера. "{{codes}}" сохранит массив, а "x={{codes.length}}" станет строкой.'}</p></div></div>
      <CodeEditor value={value} onChange={onChange} language="json" minRows={18} />
    </section>
  );
}
