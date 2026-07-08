import { JsonBlock } from '../../../components/JsonBlock';
import type { ODataStepTestResponse } from '../types';

interface ODataTestResultProps {
  result?: ODataStepTestResponse;
  error?: string | null;
  loading: boolean;
  onTest: () => void;
}

export function ODataTestResult({ result, error, loading, onTest }: ODataTestResultProps) {
  return (
    <section className="panel odata-test-panel stack-form">
      <div className="panel-toolbar">
        <div><span className="eyebrow">Test</span><h3>Пробный запрос в 1C OData</h3></div>
        <button type="button" className="primary-button" onClick={onTest} disabled={loading}>{loading ? 'Выполняю...' : 'Выполнить запрос'}</button>
      </div>
      {error ? <div className="error-state compact">{error}</div> : null}
      {result ? (
        <>
          <div className={result.success ? 'success-note' : 'error-state compact'}><strong>{result.success ? 'OData вернула результат' : result.error_code ?? 'OData test failed'}</strong><span>{result.message}{result.hint ? ` · ${result.hint}` : ''}</span></div>
          <div className="metadata-grid compact-grid no-margin">
            <span><small>Items</small><strong>{result.items_count}</strong></span>
            <span><small>Resource</small><strong className="mono">{result.rendered_resource}</strong></span>
            <span><small>Filter</small><strong className="mono">{result.rendered_filter || 'нет'}</strong></span>
          </div>
          <JsonBlock title="Result preview" value={result.result_preview ?? {}} searchable={false} />
          <JsonBlock title="Request" value={result.request} searchable={false} />
        </>
      ) : <p className="microcopy">Test выполняет реальный запрос через выбранное OData-подключение. Для пустого required результата будет `ODATA_RESULT_EMPTY`.</p>}
    </section>
  );
}
