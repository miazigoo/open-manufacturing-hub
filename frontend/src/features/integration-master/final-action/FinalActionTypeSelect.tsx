import type { FinalActionType } from '../types';

interface FinalActionTypeSelectProps {
  value: FinalActionType;
  onChange: (value: FinalActionType) => void;
}

const OPTIONS: Array<{ type: FinalActionType; label: string; description: string }> = [
  { type: 'return_response', label: 'Вернуть ответ вызывающей системе', description: 'OMH сразу отдаст JSON, XML или raw body из target_payload или custom template.' },
  { type: 'send_endpoint', label: 'Отправить на внешний endpoint', description: 'OMH отправит target_payload во внешний сервис и вернёт выбранный caller response.' },
  { type: 'send_and_return_response', label: 'Отправить endpoint и вернуть его ответ', description: 'Shortcut: send_endpoint + proxy_response для синхронного проксирования ответа.' },
  { type: 'accepted_event', label: 'Принять асинхронно', description: 'OMH вернёт event_id/queue_item_id и продолжит обработку без ожидания результата.' },
];

export function FinalActionTypeSelect({ value, onChange }: FinalActionTypeSelectProps) {
  return (
    <section className="panel stack-form final-action-type-select">
      <div className="panel-toolbar"><div><span className="eyebrow">Action type</span><h3>Что сделать с результатом</h3><p className="microcopy">Выберите один финальный сценарий. Full publish/queue execution будет отдельным этапом.</p></div></div>
      <div className="metadata-grid compact-grid no-margin">
        {OPTIONS.map((option) => (
          <button key={option.type} type="button" className={`builder-help-card action-type-card ${value === option.type ? 'active' : ''}`} onClick={() => onChange(option.type)}>
            <strong>{option.label}</strong>
            <span>{option.description}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
