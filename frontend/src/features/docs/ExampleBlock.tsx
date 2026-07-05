import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { request } from '../../api/client';
import { CodeBlock } from '../../components/CodeBlock';
import { JsonBlock } from '../../components/JsonBlock';
import { useI18n } from '../../i18n/useI18n';
import { exampleBodyText, getDocsExample } from './DocsExampleRegistry';

export function ExampleBlock({ exampleId }: { exampleId: string }) {
  const { language, t } = useI18n();
  const example = getDocsExample(exampleId);
  const trainingExample = exampleId.startsWith('training.');
  const run = useMutation({ mutationFn: () => request<Record<string, unknown>>(`${trainingExample ? '/api/training/examples' : '/api/docs/examples'}/${encodeURIComponent(exampleId)}/run`, { method: 'POST' }) });

  if (!example) return <div className="error-state compact">{t('docs.exampleMissing', { exampleId })}</div>;

  const body = exampleBodyText(example);
  const title = example.title[language] ?? example.title.ru;
  const description = example.description[language] ?? example.description.ru;
  const testConsoleUrl = trainingExample ? `/test-console?trainingExampleId=${encodeURIComponent(exampleId)}` : `/test-console?exampleId=${encodeURIComponent(exampleId)}`;

  return (
    <section className="docs-example-card">
      <div className="docs-example-head">
        <div>
          <span className="eyebrow">{t('docs.verifiedExample')} · {exampleId}</span>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
        <div className="docs-example-actions">
          <Link className="primary-button" to={testConsoleUrl}>{t('docs.openInTestConsole')}</Link>
          <button className="ghost-button" type="button" onClick={() => run.mutate()} disabled={run.isPending}>{t('docs.runExample')}</button>
        </div>
      </div>
      <div className="metadata-grid compact-grid">
        <span>{t('docs.endpoint')}<strong>POST /api/bus/in/{example.endpoint_slug}</strong></span>
        <span>{t('docs.input')}<strong>{example.input_mode}</strong></span>
        <span>{t('docs.setup')}<strong>{example.requires_setup ? t('docs.required') : t('docs.ready')}</strong></span>
      </div>
      <CodeBlock code={body} language={example.input_mode} copyLabel={t('common.buttons.copy')} copiedLabel={t('common.copied')} failedLabel={t('docs.copyUnavailable')} />
      <JsonBlock title={t('docs.expected')} value={example.expected} searchable={false} />
      {run.error instanceof Error && <div className="error-state compact">{run.error.message}</div>}
      {run.data && <JsonBlock title={t('docs.runResult')} value={run.data} searchable={false} />}
    </section>
  );
}
