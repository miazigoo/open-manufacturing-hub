import { CompileSuccessPanel } from '../../integration-master/compile/CompileSuccessPanel';
import type { RequestMultipleODataResponseCreateResponse } from './types';

interface SaveStepProps {
  result?: RequestMultipleODataResponseCreateResponse;
  error?: string | null;
  loading: boolean;
  disabled: boolean;
  onCreate: () => void;
}

export function SaveStep({ result, error, loading, disabled, onCreate }: SaveStepProps) {
  if (result) {
    return <section className="wizard-step integration-master-step request-multiple-save-step"><span className="step-index">06</span><CompileSuccessPanel result={result.compile} /></section>;
  }
  return (
    <section className="wizard-step integration-master-step request-multiple-save-step">
      <span className="step-index">06</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Save integration</span>
          <h2>Создать интеграцию</h2>
          <p>Интеграция создаётся disabled by default, с route, flow и saved test case. Включайте endpoint только после успешного теста.</p>
        </div>
        <button type="button" className="primary-button" disabled={loading || disabled} onClick={onCreate}>{loading ? 'Создаю...' : 'Создать интеграцию'}</button>
      </div>
      {disabled ? <div className="status-card warning"><strong>Сначала нужен valid preview</strong><span>Создание доступно после успешного preview.</span></div> : null}
      {error ? <div className="status-card danger"><strong>Create failed</strong><span>{error}</span></div> : null}
      <div className="metadata-grid compact-grid no-margin">
        <span className="status-card neutral"><small>Enabled</small><strong>false</strong><span>Включение остаётся ручным действием.</span></span>
        <span className="status-card neutral"><small>Saved test case</small><strong>true</strong><span>Тест использует default request `lookup_order_products`.</span></span>
        <span className="status-card neutral"><small>Response</small><strong>sync</strong><span>Caller получает XML/JSON/raw прямо в ответе.</span></span>
      </div>
    </section>
  );
}
