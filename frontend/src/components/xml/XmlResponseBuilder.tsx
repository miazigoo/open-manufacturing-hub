import { useMutation } from '@tanstack/react-query';
import { xmlToolkitApi } from '../../api/xmlToolkit';
import { CodeEditor } from '../CodeEditor';

interface XmlResponseBuilderProps {
  value: string;
  onChange: (value: string) => void;
  variables: Record<string, unknown>;
  hints?: string[];
}

export function XmlResponseBuilder({ value, onChange, variables, hints = [] }: XmlResponseBuilderProps) {
  const render = useMutation({ mutationFn: () => xmlToolkitApi.render(value, variables, true) });
  const rendered = render.data?.rendered ?? '';
  return (
    <div className="xml-response-builder stack-form">
      <div className="builder-help-card">
        <strong>XML response builder</strong>
        <span>Шаблон рендерится на backend: переменные экранируются как XML, пропущенные поля дают явную ошибку, итоговый XML валидируется перед сохранением.</span>
      </div>
      <label className="field-label">XML template<CodeEditor value={value} onChange={onChange} language="xml" minRows={8} /></label>
      <div className="hint-chip-row">{hints.map((hint) => <button key={hint} type="button" className="hint-chip" onClick={() => navigator.clipboard?.writeText(hint)}>{hint}</button>)}</div>
      <div className="action-row"><button type="button" className="ghost-button" onClick={() => render.mutate()} disabled={render.isPending}>Validate rendered XML</button></div>
      {render.error instanceof Error && <div className="error-state compact">{render.error.message}</div>}
      {render.data && !render.data.success && <div className="error-state compact">{render.data.errors.join('; ')}</div>}
      {render.data?.success && <CodeEditor value={rendered} onChange={() => undefined} language="xml" minRows={6} title="Rendered XML preview" />}
    </div>
  );
}

