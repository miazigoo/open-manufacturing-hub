import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { request } from '../../api/client';
import { CopyButton } from '../../components/product/CopyButton';
import { JsonBlock } from '../../components/JsonBlock';
import { useI18n } from '../../i18n/useI18n';
import { exampleBodyText, getDocsExample } from './DocsExampleRegistry';

export function ExampleBlock({ exampleId }: { exampleId: string }) {
  const { language } = useI18n();
  const example = getDocsExample(exampleId);
  const run = useMutation({ mutationFn: () => request<Record<string, unknown>>(`/api/docs/examples/${encodeURIComponent(exampleId)}/run`, { method: 'POST' }) });

  if (!example) return <div className="error-state compact">Documentation example is missing: {exampleId}</div>;

  const body = exampleBodyText(example);
  const title = example.title[language] ?? example.title.ru;
  const description = example.description[language] ?? example.description.ru;
  const testConsoleUrl = `/test-console?exampleId=${encodeURIComponent(exampleId)}`;

  return (
    <section className="docs-example-card">
      <div className="docs-example-head">
        <div>
          <span className="eyebrow">Verified example · {exampleId}</span>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
        <div className="docs-example-actions">
          <Link className="primary-button" to={testConsoleUrl}>Open in Test Console</Link>
          <button className="ghost-button" type="button" onClick={() => run.mutate()} disabled={run.isPending}>Run Example</button>
        </div>
      </div>
      <div className="metadata-grid compact-grid">
        <span>Endpoint<strong>POST /api/bus/in/{example.endpoint_slug}</strong></span>
        <span>Input<strong>{example.input_mode}</strong></span>
        <span>Setup<strong>{example.requires_setup ? 'required' : 'ready'}</strong></span>
      </div>
      <div className="docs-code-block">
        <div className="docs-code-toolbar"><span>{example.input_mode}</span><CopyButton value={body} label="Copy" copiedLabel="Copied" failedLabel="Copy unavailable" /></div>
        <pre><code>{body}</code></pre>
      </div>
      <JsonBlock title="Expected" value={example.expected} searchable={false} />
      {run.error instanceof Error && <div className="error-state compact">{run.error.message}</div>}
      {run.data && <JsonBlock title="Run result" value={run.data} searchable={false} />}
    </section>
  );
}
