import { CompileSuccessPanel } from '../../integration-master/compile/CompileSuccessPanel';
import type { RequestODataSendEndpointCreateResponse } from './types';

interface SaveStepProps {
  result?: RequestODataSendEndpointCreateResponse;
  error?: string | null;
  loading: boolean;
  disabled: boolean;
  onCreate: () => void;
}

export function SaveStep({ result, error, loading, disabled, onCreate }: SaveStepProps) {
  if (result) {
    return (
      <section className="wizard-step integration-master-step pattern-save-step">
        <span className="step-index">07</span>
        <CompileSuccessPanel result={result.compile} />
      </section>
    );
  }

  return (
    <section className="wizard-step integration-master-step pattern-save-step">
      <span className="step-index">07</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Save integration</span>
          <h2>Создать интеграцию</h2>
          <p>Backend создаст выключенную интеграцию и saved test case. Включение production-интеграции остаётся ручным действием.</p>
        </div>
        <button type="button" className="primary-button" disabled={loading || disabled} onClick={onCreate}>{loading ? 'Создаю...' : 'Создать интеграцию'}</button>
      </div>
      {disabled ? <div className="status-card warning"><strong>Сначала нужен valid preview</strong><span>Создание доступно после успешного preview, чтобы не сохранять сломанный endpoint.</span></div> : null}
      {error ? <div className="status-card danger"><strong>Create failed</strong><span>{error}</span></div> : null}
      <div className="metadata-grid compact-grid no-margin">
        <span className="status-card neutral"><small>Enabled</small><strong>false</strong><span>Интеграция создаётся выключенной по умолчанию.</span></span>
        <span className="status-card neutral"><small>Saved test case</small><strong>true</strong><span>После создания можно сразу запустить dry-run тест.</span></span>
        <span className="status-card neutral"><small>Target errors</small><strong>preserved</strong><span>4xx/5xx target response не теряется и виден в Timeline.</span></span>
      </div>
    </section>
  );
}
