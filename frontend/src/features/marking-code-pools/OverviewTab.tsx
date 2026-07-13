import { Link } from 'react-router-dom';
import { StatusBadge } from '../../components/StatusBadge';
import { SectionCard } from '../../components/product/SectionCard';
import type { MarkingCodePoolExport, MarkingCodePoolSettings } from './types';
import { actionStatus, formatDate } from './utils';

interface OverviewTabProps {
  settings: MarkingCodePoolSettings | undefined;
  exports: MarkingCodePoolExport[];
}

export function OverviewTab({ settings, exports }: OverviewTabProps) {
  const latest = exports[0] ?? null;
  const errors = exports.filter((item) => item.error_message).slice(0, 3);
  return (
    <div className="page-stack">
      <SectionCard title="Что делает инструмент" description="Этот инструмент принимает от 1С пул кодов Честного знака и сохраняет его в файл. Дополнительно OMH может сохранить копию в сетевую директорию для лазера и/или отправить пул во внешний сервис, например DnP.">
        <div className="chz-flow-diagram" aria-label="1C to OMH code pool flow">
          <span>1C</span>
          <strong>POST /api/bus/in/onec-chz-pool-delivery</strong>
          <span>OMH</span>
          <ul>
            <li>быстрый accepted-ответ для 1C</li>
            <li>локальный архив</li>
            <li>опциональная копия для лазера / SMB</li>
            <li>опциональная внешняя отправка</li>
          </ul>
        </div>
      </SectionCard>

      <section className="metadata-grid compact-grid no-margin">
        <span>Локальная директория<strong>{settings?.local_outbox.export_dir ?? '—'}</strong><small>{settings?.local_outbox.note}</small></span>
        <span>SMB/laser<strong>{settings?.laser.enabled ? 'включено' : 'выключено'}</strong><small>{settings?.laser.smb_unc || 'UNC путь не задан'}</small></span>
        <span>Внешняя отправка<strong>{settings?.forward.enabled ? 'включено' : 'выключено'}</strong><small>{settings?.forward.url || 'URL не задан'}</small></span>
        <span>Последний экспорт<strong>{latest ? latest.order_number : 'нет экспортов'}</strong><small>{latest ? `${formatDate(latest.created_at)} · ${latest.file_name}` : 'Проверьте вкладку Тест'}</small></span>
        <span>Статус последнего<strong>{latest ? <StatusBadge status={latest.status} compact /> : '—'}</strong><small>{latest ? `${latest.total_codes} кодов` : '—'}</small></span>
        <span>Ошибки<strong>{errors.length ? `${errors.length} последних` : 'нет'}</strong><small>{errors[0]?.error_message ?? 'Критичных ошибок в журнале не видно'}</small></span>
      </section>

      {latest && (
        <SectionCard title="Последний пул" actions={<Link className="primary-link" to="/marking-code-pools?tab=journal">Открыть журнал</Link>}>
          <div className="metadata-grid compact-grid no-margin">
            <span>Локальный файл<strong><StatusBadge status={actionStatus(latest, 'local_outbox')} compact /></strong><small>{latest.file_path}</small></span>
            <span>Лазер/SMB<strong><StatusBadge status={actionStatus(latest, 'laser_file')} compact /></strong><small>{latest.error_message ?? 'см. details в журнале'}</small></span>
            <span>Внешняя отправка<strong><StatusBadge status={actionStatus(latest, 'external_forward')} compact /></strong><small>{latest.forwarded_at ? formatDate(latest.forwarded_at) : 'не отправлялось или выключено'}</small></span>
          </div>
        </SectionCard>
      )}
    </div>
  );
}
