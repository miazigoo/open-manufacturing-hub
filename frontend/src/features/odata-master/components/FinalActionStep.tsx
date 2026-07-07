import type { ODataFinalAction } from '../types';
import { PayloadBuilder } from './PayloadBuilder';
import { ResponseBuilder } from './ResponseBuilder';

interface FinalActionStepProps { value: ODataFinalAction; onChange: (value: ODataFinalAction) => void }

export function FinalActionStep({ value, onChange }: FinalActionStepProps) {
  const sends = value.type === 'send_endpoint' || value.type === 'send_onec_http_service';
  return (
    <section className="panel form-panel">
      <div className="panel-toolbar">
        <div>
          <span className="eyebrow">Итоговое действие</span>
          <h2>Что делаем с результатом?</h2>
          <p className="microcopy">Можно вернуть JSON/XML/raw сразу, отправить данные во внешний endpoint или принять запрос асинхронно.</p>
        </div>
      </div>
      <div className="stack-form">
        <label className="field-label">Итоговое действие<select value={value.type} onChange={(event) => onChange({ ...value, type: event.target.value as ODataFinalAction['type'] })}><option value="return_response">Вернуть ответ вызывающему</option><option value="send_endpoint">Отправить на endpoint</option><option value="send_onec_http_service">Отправить в HTTP-сервис 1C</option><option value="async_accepted">Асинхронно: accepted response</option></select></label>
        {sends && (
          <>
            <div className="metadata-grid compact-grid no-margin">
              <label className="field-label">Method<select value={value.method} onChange={(event) => onChange({ ...value, method: event.target.value })}><option value="POST">POST</option><option value="PUT">PUT</option><option value="PATCH">PATCH</option></select></label>
              <label className="field-label">URL<input value={value.url || ''} onChange={(event) => onChange({ ...value, url: event.target.value })} placeholder="http://172.16.3.10/api/v2/integrations/omh/chz/codes/import" /></label>
            </div>
            <PayloadBuilder title="Что отправить" bodyType={value.body_type} value={value.body} onBodyTypeChange={(bodyType) => onChange({ ...value, body_type: bodyType, body: bodyType === 'json' ? {} : '' })} onChange={(body) => onChange({ ...value, body })} />
          </>
        )}
        {value.type !== 'async_accepted' && <ResponseBuilder value={value.response_to_caller} onChange={(response_to_caller) => onChange({ ...value, response_to_caller })} />}
      </div>
    </section>
  );
}
