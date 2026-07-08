import { useEffect, useState } from 'react';
import { CodeEditor } from '../../../components/CodeEditor';

interface EndpointHeadersEditorProps {
  value: Record<string, unknown>;
  onChange: (value: Record<string, unknown>) => void;
  label?: string;
  hint?: string;
}

export function EndpointHeadersEditor({ value, onChange, label = 'Headers JSON', hint = 'Можно указать строковые заголовки или secret ref: {"Authorization":{"$secret":"dnp_api_token"}}.' }: EndpointHeadersEditorProps) {
  const [text, setText] = useState(() => JSON.stringify(value ?? {}, null, 2));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setText(JSON.stringify(value ?? {}, null, 2));
  }, [value]);

  function apply(nextText: string) {
    setText(nextText);
    try {
      const parsed = JSON.parse(nextText || '{}') as unknown;
      if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') throw new Error('Headers must be a JSON object');
      setError(null);
      onChange(parsed as Record<string, unknown>);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Invalid JSON');
    }
  }

  return (
    <label className="field-label full-span">{label}
      <CodeEditor value={text} onChange={apply} language="json" minRows={4} />
      <small>{error ? <span className="error-text">{error}</span> : hint}</small>
    </label>
  );
}
