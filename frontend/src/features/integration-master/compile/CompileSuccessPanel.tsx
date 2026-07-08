import { Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { CodeBlock } from '../../../components/CodeBlock';
import { CopyButton } from '../../../components/product/CopyButton';
import { integrationMasterApi } from '../api';
import type { CompileDraftResponse } from '../types';

interface CompileSuccessPanelProps {
  result: CompileDraftResponse;
}

export function CompileSuccessPanel({ result }: CompileSuccessPanelProps) {
  const runTest = useMutation({ mutationFn: () => integrationMasterApi.runCompiledTest(result.integration_flow_id, { dry_run: true }) });
  const enable = useMutation({ mutationFn: () => integrationMasterApi.enableCompiled(result.integration_flow_id) });
  const endpointUrl = result.endpoint.url;
  const curl = result.curl_example ?? `curl -X POST http://localhost:8000${endpointUrl}`;

  function enableAfterConfirm() {
    if (window.confirm('После включения endpoint начнёт принимать реальные запросы. Продолжить?')) enable.mutate();
  }

  return (
    <section className="panel stack-form compile-success-panel">
      <div className="panel-toolbar"><div><span className="eyebrow">Created</span><h3>Интеграция создана</h3><p className="microcopy">Endpoint, route, workflow, flow и saved test case созданы.</p></div></div>
      <div className="status-card success"><strong>{result.endpoint.method} {endpointUrl}</strong><span>{result.enabled || enable.data?.enabled ? 'Интеграция включена' : 'Интеграция создана выключенной. Сначала выполните тест.'}</span></div>
      <div className="action-row wrap-actions">
        <CopyButton value={endpointUrl} label="Скопировать endpoint" copiedLabel="Endpoint скопирован" />
        <CopyButton value={curl} label="Скопировать curl" copiedLabel="curl скопирован" />
        {result.saved_test_case_id ? <Link className="ghost-button" to={`/test-console?testCaseId=${result.saved_test_case_id}`}>Открыть тестовый запрос</Link> : null}
        <button type="button" className="primary-button" disabled={runTest.isPending || !result.saved_test_case_id} onClick={() => runTest.mutate()}>{runTest.isPending ? 'Запускаю...' : 'Запустить тест'}</button>
        <Link className="ghost-button" to={`/integration-flows/${result.integration_flow_id}/builder`}>Открыть Integration Flow</Link>
        {!result.enabled && !enable.data?.enabled ? <button type="button" className="primary-button" disabled={enable.isPending} onClick={enableAfterConfirm}>{enable.isPending ? 'Включаю...' : 'Включить интеграцию'}</button> : null}
      </div>
      {runTest.error instanceof Error ? <div className="status-card danger"><strong>Test failed</strong><span>{runTest.error.message}</span></div> : null}
      {runTest.data ? <div className={`status-card ${runTest.data.success ? 'success' : 'danger'}`}><strong>{runTest.data.dry_run ? 'Dry run выполнен' : 'Тест отправлен'}</strong><span>{runTest.data.timeline_url ? 'Можно открыть Timeline.' : 'Dry run не создаёт событие.'}</span>{runTest.data.timeline_url ? <Link className="primary-link" to={runTest.data.timeline_url}>Открыть Timeline</Link> : null}</div> : null}
      {enable.error instanceof Error ? <div className="status-card danger"><strong>Enable failed</strong><span>{enable.error.message}</span></div> : null}
      {enable.data?.enabled ? <div className="status-card success"><strong>Интеграция включена</strong><span>Endpoint, route и workflow переведены в enabled.</span></div> : null}
      <CodeBlock title="curl" code={curl} language="bash" copyLabel="Скопировать curl" copiedLabel="Скопировано" />
      {result.next_actions.length ? <div className="status-card neutral"><strong>Что дальше</strong><span>{result.next_actions.join(' · ')}</span></div> : null}
    </section>
  );
}
