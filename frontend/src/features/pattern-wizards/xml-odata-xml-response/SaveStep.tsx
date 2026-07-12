import { CompileSuccessPanel } from '../../integration-master/compile/CompileSuccessPanel';
import type { XmlODataXmlResponseCreateResponse } from './types';

interface SaveStepProps {
  result?: XmlODataXmlResponseCreateResponse;
  error?: string | null;
  loading: boolean;
  disabled: boolean;
  onCreate: () => void;
}

export function SaveStep({ result, error, loading, disabled, onCreate }: SaveStepProps) {
  if (result) {
    return (
      <section className="wizard-step integration-master-step xml-odata-save-step">
        <span className="step-index">06</span>
        <div className="status-card success"><strong>Интеграция создана</strong><span>Endpoint: POST {String(result.compile.endpoint.url)}</span></div>
        <CompileSuccessPanel result={result.compile} />
      </section>
    );
  }

  return (
    <section className="wizard-step integration-master-step xml-odata-save-step">
      <span className="step-index">06</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Save integration</span>
          <h2>Создать disabled integration</h2>
          <p>Backend создаст endpoint, route, IntegrationFlow, builder_json и saved test case с XML body. Включение остаётся ручным после проверки Timeline.</p>
        </div>
        <button type="button" className="primary-button" disabled={loading || disabled} onClick={onCreate}>{loading ? 'Создаю...' : 'Создать интеграцию'}</button>
      </div>
      {disabled ? <div className="status-card warning"><strong>Сначала нужен valid preview</strong><span>Создание доступно после успешного preview, чтобы не сохранять сломанный endpoint.</span></div> : null}
      {error ? <div className="status-card danger"><strong>Create failed</strong><span>{error}</span></div> : null}
      <div className="metadata-grid compact-grid no-margin">
        <span className="status-card neutral"><small>Enabled</small><strong>false</strong><span>Интеграция создаётся выключенной.</span></span>
        <span className="status-card neutral"><small>Artifacts</small><strong>XML + OData + response</strong><span>Timeline покажет raw XML, extracted fields, OData request/response и rendered response.</span></span>
        <span className="status-card neutral"><small>Saved test case</small><strong>XML body</strong><span>После создания можно запустить тест из Test Console.</span></span>
      </div>
    </section>
  );
}
