import { CompileSuccessPanel } from '../../integration-master/compile/CompileSuccessPanel';
import type { RequestPrintCreateResponse } from './types';

interface SaveStepProps {
  result?: RequestPrintCreateResponse;
  error?: string | null;
  loading: boolean;
  disabled: boolean;
  onCreate: () => void;
}

export function SaveStep({ result, error, loading, disabled, onCreate }: SaveStepProps) {
  if (result) {
    return <section className="wizard-step integration-master-step request-print-save-step"><span className="step-index">08</span><div className="status-card success"><strong>Интеграция создана</strong><span>Endpoint: POST {String(result.compile.endpoint.url)}</span></div><CompileSuccessPanel result={result.compile} /></section>;
  }
  return (
    <section className="wizard-step integration-master-step request-print-save-step">
      <span className="step-index">08</span>
      <div className="odata-step-heading"><div><span className="eyebrow">Save integration</span><h2>Создать disabled integration</h2><p>Backend создаст endpoint, route, IntegrationFlow, builder_json и saved test case. Включение остаётся ручным после dry-run/test print.</p></div><button type="button" className="primary-button" disabled={loading || disabled} onClick={onCreate}>{loading ? 'Создаю...' : 'Создать интеграцию'}</button></div>
      {disabled ? <div className="status-card warning"><strong>Сначала нужен valid preview</strong><span>Создание доступно после успешного preview, чтобы не сохранить сломанный endpoint.</span></div> : null}
      {error ? <div className="status-card danger"><strong>Create failed</strong><span>{error}</span></div> : null}
      <div className="metadata-grid compact-grid no-margin"><span className="status-card neutral"><small>Enabled</small><strong>false</strong><span>Интеграция создаётся выключенной.</span></span><span className="status-card neutral"><small>Artifacts</small><strong>ZPL + printer response</strong><span>Timeline покажет request, selected printer, ZPL и printer response.</span></span><span className="status-card neutral"><small>Saved test case</small><strong>JSON body</strong><span>Можно запускать из Test Console.</span></span></div>
    </section>
  );
}
