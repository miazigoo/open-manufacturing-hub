import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { xmlToolsApi } from '../api/xmlTools';
import { JsonBlock } from '../components/JsonBlock';
import { StatusBadge } from '../components/StatusBadge';

const sampleXml = '<Документ><Номер>UPD-1001</Номер><ИНН>1234567890</ИНН></Документ>';

export function XmlToolsPage() {
  const [left, setLeft] = useState(sampleXml);
  const [right, setRight] = useState(sampleXml.replace('1001', '1002'));
  const parse = useMutation({ mutationFn: () => xmlToolsApi.parse(left) });
  const diff = useMutation({ mutationFn: () => xmlToolsApi.diff(left, right) });
  const runtimeError = parse.error ?? diff.error;

  return (
    <div className="page-stack two-column-page">
      <section className="panel form-panel">
        <span className="eyebrow">XML Tools</span>
        <h1>Inspect XML safely</h1>
        <label className="field-label">Original XML<textarea value={left} onChange={(event) => setLeft(event.target.value)} /></label>
        <label className="field-label">Forwarded / comparison XML<textarea value={right} onChange={(event) => setRight(event.target.value)} /></label>
        {runtimeError instanceof Error && <div className="error-state compact">{runtimeError.message}</div>}
        <div className="action-row">
          <button className="primary-button" onClick={() => parse.mutate()} disabled={parse.isPending}>Parse XML</button>
          <button className="ghost-button" onClick={() => diff.mutate()} disabled={diff.isPending}>Diff XML</button>
        </div>
        {parse.data && <div className="metadata-grid compact-grid"><span>Valid<strong>{parse.data.valid ? 'yes' : 'no'}</strong></span><span>Size<strong>{parse.data.size_bytes}</strong></span><span>Hash<strong className="mono">{parse.data.sha256.slice(0, 12)}</strong></span></div>}
        {diff.data && <StatusBadge status={diff.data.forwarded_unchanged ? 'ok' : 'warning'} label={diff.data.forwarded_unchanged ? 'unchanged' : 'changed'} />}
      </section>
      <section className="page-stack">
        <JsonBlock title="Parsed XML / paths" value={parse.data ?? { hint: 'Parse XML to inspect normalized paths and metadata.' }} searchable />
        <JsonBlock title="Pretty XML" value={{ pretty_xml: parse.data?.pretty_xml ?? '' }} searchable={false} />
        <pre className="json-block">{diff.data?.diff_text ?? 'Run XML diff to see changes'}</pre>
      </section>
    </div>
  );
}
