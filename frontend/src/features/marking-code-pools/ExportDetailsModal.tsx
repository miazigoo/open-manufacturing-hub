import { JsonBlock } from '../../components/JsonBlock';
import { StatusBadge } from '../../components/StatusBadge';
import type { ActionDetails, MarkingCodePoolExport } from './types';
import { actionDetails, actionsOf, formatDate, shortHash } from './utils';

interface ExportDetailsModalProps {
  item: MarkingCodePoolExport;
  onClose: () => void;
}

export function ExportDetailsModal({ item, onClose }: ExportDetailsModalProps) {
  const actions = actionsOf(item);
  return (
    <div className="scenario-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="scenario-modal" role="dialog" aria-modal="true" aria-labelledby="chz-export-details-title" onMouseDown={(event) => event.stopPropagation()}>
        <div className="panel-toolbar">
          <div>
            <span className="eyebrow">Export details</span>
            <h2 id="chz-export-details-title">{item.order_number}</h2>
            <p>Полные значения кодов не отображаются в UI. Скачайте файл только если есть производственная необходимость.</p>
          </div>
          <button className="ghost-button" type="button" onClick={onClose}>Закрыть</button>
        </div>
        <div className="metadata-grid compact-grid no-margin">
          <span>Система-источник<strong>{item.source_system}</strong></span>
          <span>Документ 1С<strong>{item.source_document_id ?? '—'}</strong></span>
          <span>Название документа<strong>{item.source_document_name ?? '—'}</strong></span>
          <span>Файл<strong>{item.file_name}</strong><small>{item.file_path}</small></span>
          <span>Кодов<strong>{item.total_codes}</strong></span>
          <span>SHA256<strong>{shortHash(item.content_sha256)}</strong><small>{item.content_sha256}</small></span>
          <span>Статус<strong><StatusBadge status={item.status} compact /></strong><small>{item.error_message ?? 'нет ошибки'}</small></span>
          <span>Создано<strong>{formatDate(item.created_at)}</strong></span>
          <span>Отправлено внешне<strong>{formatDate(item.forwarded_at)}</strong></span>
        </div>
        <div className="action-details-grid">
          <ActionSection title="Локальное сохранение" action={actionDetails(item, 'local_outbox')} fields={['path', 'error', 'reason']} />
          <ActionSection title="Лазер / SMB" action={actionDetails(item, 'laser_file')} fields={['target', 'file_name', 'error', 'reason']} />
          <ActionSection title="Внешняя отправка" action={actionDetails(item, 'external_forward')} fields={['url', 'http_status', 'error', 'reason', 'response']} />
        </div>
        <section className="workbench-grid lower">
          <JsonBlock title="Advanced: actions JSON" value={actions} searchable={false} />
          <JsonBlock title="Advanced: metadata JSON" value={item.metadata_json} searchable={false} />
        </section>
      </section>
    </div>
  );
}

function ActionSection({ title, action, fields }: { title: string; action?: ActionDetails; fields: string[] }) {
  const status = String(action?.status ?? 'unknown');
  return (
    <section className="action-detail-card">
      <div className="action-detail-head">
        <h3>{title}</h3>
        <StatusBadge status={status} compact />
      </div>
      <dl>
        {fields.map((field) => {
          const value = action?.[field];
          if (value === undefined || value === null || value === '') return null;
          return (
            <div key={field}>
              <dt>{fieldLabel(field)}</dt>
              <dd>{field === 'response' ? responsePreview(value) : String(value)}</dd>
            </div>
          );
        })}
      </dl>
      {!action && <p className="muted">Действие не записано в metadata.</p>}
    </section>
  );
}

function fieldLabel(field: string): string {
  const labels: Record<string, string> = {
    path: 'Путь',
    target: 'Цель',
    file_name: 'Файл',
    url: 'URL',
    http_status: 'HTTP статус',
    error: 'Ошибка',
    reason: 'Причина',
    response: 'Ответ',
  };
  return labels[field] ?? field;
}

function responsePreview(value: unknown): string {
  const text = typeof value === 'string' ? value : JSON.stringify(value) ?? String(value);
  return text.length > 800 ? `${text.slice(0, 800)}...` : text;
}
