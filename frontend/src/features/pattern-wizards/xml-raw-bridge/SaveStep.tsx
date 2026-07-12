import { CompileSuccessPanel } from '../../integration-master/compile/CompileSuccessPanel';
import type { XmlRawBridgeCreateResponse } from './types';

interface SaveStepProps {
  result?: XmlRawBridgeCreateResponse;
  error?: string | null;
  loading: boolean;
  disabled: boolean;
  onCreate: () => void;
}

export function SaveStep({ result, error, loading, disabled, onCreate }: SaveStepProps) {
  if (result) {
    return (
      <section className="wizard-step integration-master-step xml-raw-save-step">
        <span className="step-index">06</span>
        <div className="status-card success"><strong>Интеграция создана</strong><span>Endpoint: POST {String(result.compile.endpoint.url)}</span></div>
        <CompileSuccessPanel result={result.compile} />
      </section>
    );
  }

  return (
    <section className="wizard-step integration-master-step xml-raw-save-step">
      <span className="step-index">06</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Save integration</span>
          <h2>Создать интеграцию</h2>
          <p>Backend создаст disabled endpoint, route, integration flow, builder_json и saved test case с XML body.</p>
        </div>
        <button type="button" className="primary-button" disabled={loading || disabled} onClick={onCreate}>{loading ? 'Создаю...' : 'Создать интеграцию'}</button>
      </div>
      {disabled ? <div className="status-card warning"><strong>Сначала нужен valid preview</strong><span>Создание доступно после успешного preview, чтобы не сохранять сломанный endpoint.</span></div> : null}
      {error ? <div className="status-card danger"><strong>Create failed</strong><span>{error}</span></div> : null}
      <div className="metadata-grid compact-grid no-margin">
        <span className="status-card neutral"><small>Enabled</small><strong>false</strong><span>Интеграция создаётся выключенной по умолчанию.</span></span>
        <span className="status-card neutral"><small>Artifacts</small><strong>raw XML + hash</strong><span>Timeline сохранит original/forwarded XML и hash check.</span></span>
        <span className="status-card neutral"><small>Saved test case</small><strong>XML body</strong><span>После создания можно запустить тест из Test Console.</span></span>
      </div>
    </section>
  );
}
