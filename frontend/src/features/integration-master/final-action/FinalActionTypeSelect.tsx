import { CodeBlock } from '../../../components/CodeBlock';
import type { FinalActionType } from '../types';

interface FinalActionTypeSelectProps {
  value: FinalActionType;
  onChange: (value: FinalActionType) => void;
}

const OPTIONS: Array<{ type: FinalActionType; label: string; description: string; result: string; example?: unknown }> = [
  {
    type: 'return_response',
    label: 'Вернуть результат вызывающей системе',
    description: 'Ничего не отправлять наружу. OMH вернёт собранный target_payload в HTTP-ответ тому сервису, который вызвал endpoint.',
    result: 'POST в OMH -> OData/transform steps -> HTTP response с результатом',
    example: '{{target_payload}}',
  },
  {
    type: 'send_endpoint',
    label: 'Отправить на внешний endpoint и вернуть ok',
    description: 'OMH отправит target_payload во внешний сервис, а вызывающей системе вернёт короткий успешный ответ. Это текущий вариант для DnP.',
    result: 'POST в OMH -> OData/transform steps -> POST target endpoint -> HTTP 200 {"ok": true}',
    example: { ok: true },
  },
  {
    type: 'send_and_return_response',
    label: 'Отправить endpoint и вернуть его ответ',
    description: 'OMH отправит target_payload во внешний сервис и проксирует ответ этого endpoint обратно вызывающей системе.',
    result: 'POST в OMH -> target endpoint -> HTTP response от target endpoint',
  },
  {
    type: 'accepted_event',
    label: 'Принять асинхронно',
    description: 'OMH быстро вернёт event_id/queue_item_id и продолжит обработку без ожидания результата.',
    result: 'POST в OMH -> HTTP 202 accepted -> дальнейшая обработка отдельно',
  },
];

export function FinalActionTypeSelect({ value, onChange }: FinalActionTypeSelectProps) {
  return (
    <section className="panel stack-form final-action-type-select">
      <div className="panel-toolbar"><div><span className="eyebrow">Final action</span><h3>Что сделать с результатом</h3><p className="microcopy">Здесь выбирается не OData-запрос, а финальный ответ: вернуть результат тому, кто вызвал OMH, или отправить данные дальше.</p></div></div>
      <div className="metadata-grid compact-grid no-margin">
        {OPTIONS.map((option) => (
          <button key={option.type} type="button" className={`builder-help-card action-type-card ${value === option.type ? 'active' : ''}`} onClick={() => onChange(option.type)}>
            <strong>{option.label}</strong>
            <span>{option.description}</span>
            <small>{option.result}</small>
            {option.example !== undefined ? <CodeBlock code={typeof option.example === 'string' ? option.example : JSON.stringify(option.example, null, 2)} language={typeof option.example === 'string' ? 'text' : 'json'} showToolbar={false} /> : null}
          </button>
        ))}
      </div>
    </section>
  );
}
