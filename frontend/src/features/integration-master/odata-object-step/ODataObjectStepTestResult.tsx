import { JsonBlock } from '../../../components/JsonBlock';
import type { ODataObjectStepTestResponse } from '../types';

interface ODataObjectStepTestResultProps {
  result?: ODataObjectStepTestResponse;
  error?: string | null;
  loading: boolean;
  onTest: () => void;
}

export function ODataObjectStepTestResult({ result, error, loading, onTest }: ODataObjectStepTestResultProps) {
  return (
    <section className="panel odata-test-panel stack-form">
      <div className="panel-toolbar"><div><span className="eyebrow">Test</span><h3>Проверить чтение табличной части</h3></div><button type="button" className="primary-button" onClick={onTest} disabled={loading}>{loading ? 'Выполняю...' : 'Проверить чтение табличной части'}</button></div>
      {error ? <div className="error-state compact">{error}</div> : null}
      {result ? (
        <>
          <div className={result.success ? 'success-note' : 'error-state compact'}><strong>{result.success ? `1С вернула ${result.items_count} строк` : result.error_code ?? 'OData test failed'}</strong><span>{result.message}{result.hint ? ` · ${result.hint}` : ''}</span></div>
          <div className="metadata-grid compact-grid no-margin"><span><small>Items</small><strong>{result.items_count}</strong></span><span><small>save_as</small><strong>{result.saved_as}</strong></span><span><small>Resource</small><strong className="mono">{result.rendered_resource}</strong></span></div>
          <JsonBlock title="Products preview" value={result.result_preview} searchable={false} />
          <div className="odata-variable-list"><strong>Будущие переменные:</strong>{result.variables_after_step.map((item) => <code key={item}>{item}</code>)}</div>
          <JsonBlock title="Request" value={result.request} searchable={false} />
        </>
      ) : <p className="microcopy">Следующий шаг сможет пройти по массиву `products` и выполнить OData-запрос для каждой строки. Foreach будет отдельным этапом.</p>}
    </section>
  );
}
