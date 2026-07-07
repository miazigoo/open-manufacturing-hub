import { useEffect, useState } from 'react';
import { CodeEditor } from '../../../components/CodeEditor';
import type { ODataBodyType } from '../types';
import { prettyJson, safeJsonParse } from '../utils/placeholders';

interface PayloadBuilderProps { title: string; bodyType: ODataBodyType; value: unknown; onBodyTypeChange: (type: ODataBodyType) => void; onChange: (value: unknown) => void }

export function PayloadBuilder({ title, bodyType, value, onBodyTypeChange, onChange }: PayloadBuilderProps) {
  const [text, setText] = useState(() => bodyType === 'json' ? prettyJson(value || {}) : String(value || ''));

  useEffect(() => {
    setText(bodyType === 'json' ? prettyJson(value || {}) : String(value || ''));
  }, [bodyType, value]);

  function changeText(next: string) {
    setText(next);
    onChange(bodyType === 'json' ? safeJsonParse<Record<string, unknown>>(next, {}) : next);
  }

  return (
    <div className="stack-form">
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">{title}: тип тела<select value={bodyType} onChange={(event) => onBodyTypeChange(event.target.value as ODataBodyType)}><option value="json">JSON</option><option value="xml">XML</option><option value="raw_text">raw text</option></select></label>
      </div>
      <CodeEditor value={text} onChange={changeText} language={bodyType === 'json' ? 'json' : bodyType === 'xml' ? 'xml' : 'text'} minRows={bodyType === 'json' ? 10 : 7} />
      {bodyType === 'json' && <span className="microcopy">Если значение равно "{'{{codes}}'}", OMH вставит массив/объект как настоящий JSON, не как строку.</span>}
    </div>
  );
}
