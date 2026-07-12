import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { JsonBlock } from '../../components/JsonBlock';
import { StatusBadge } from '../../components/StatusBadge';
import { CopyButton } from '../../components/product/CopyButton';
import { DataTable } from '../../components/product/DataTable';
import { markingCodePoolsApi } from './api';
import { ExportDetailsModal } from './ExportDetailsModal';
import type { MarkingCodePoolActionRetryResponse, MarkingCodePoolExport, MarkingCodePoolSettings } from './types';
import { actionDetails, actionStatus, formatDate, shortHash } from './utils';

interface ExportsJournalTabProps {
  exports: MarkingCodePoolExport[];
  settings: MarkingCodePoolSettings | undefined;
}

export function ExportsJournalTab({ exports, settings }: ExportsJournalTabProps) {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<MarkingCodePoolExport | null>(null);
  const [retryResult, setRetryResult] = useState<MarkingCodePoolActionRetryResponse | null>(null);
  const onRetrySuccess = (data: MarkingCodePoolActionRetryResponse) => {
    setRetryResult(data);
    queryClient.invalidateQueries({ queryKey: ['marking-code-pools-exports'] });
  };
  const retryForward = useMutation({ mutationFn: markingCodePoolsApi.retryForward, onSuccess: onRetrySuccess });
  const retryLaserCopy = useMutation({ mutationFn: markingCodePoolsApi.retryLaserCopy, onSuccess: onRetrySuccess });
  const forwardRetryEnabled = Boolean(settings?.forward.enabled && settings.forward.url);
  const laserRetryEnabled = Boolean(settings?.laser.enabled && settings.laser.smb_unc);
  const retryError = [retryForward.error, retryLaserCopy.error].find((error): error is Error => error instanceof Error);
  return (
    <div className="page-stack">
      <DataTable
        rows={exports}
        getRowKey={(row) => row.id}
        emptyTitle="Экспортов пока нет"
        emptyDetail="Откройте вкладку Тест и сохраните тестовый файл или отправьте пул из 1С."
        columns={[
          { key: 'date', header: 'Дата', render: (row) => <>{formatDate(row.created_at)}<small>{row.id}</small></> },
          { key: 'order', header: 'Заказ', render: (row) => <strong>{row.order_number}</strong> },
          { key: 'document', header: 'Документ 1С', render: (row) => <>{row.source_document_id ?? '—'}<small>{row.source_document_name ?? row.source_system}</small></> },
          { key: 'file', header: 'Файл', render: (row) => <>{row.file_name}<small>{shortHash(row.content_sha256)}</small></> },
          { key: 'codes', header: 'Кодов', render: (row) => row.total_codes.toLocaleString() },
          { key: 'status', header: 'Статус', render: (row) => <span title={statusExplanation(row.status)}><StatusBadge status={row.status} compact /></span> },
          { key: 'local', header: 'Локальный файл', render: (row) => <ActionCell row={row} actionKey="local_outbox" /> },
          { key: 'laser', header: 'Лазер/SMB', render: (row) => <ActionCell row={row} actionKey="laser_file" /> },
          { key: 'forward', header: 'Внешняя отправка', render: (row) => <ActionCell row={row} actionKey="external_forward" /> },
          { key: 'error', header: 'Ошибка', render: (row) => row.error_message ? <span className="error-text">{row.error_message}</span> : <span className="muted">—</span> },
          {
            key: 'actions',
            header: 'Действия',
            render: (row) => (
              <div className="action-row wrap-actions">
                <button className="ghost-button" type="button" onClick={() => setSelected(row)}>Открыть детали</button>
                <a className="primary-link" href={markingCodePoolsApi.downloadUrl(row.id)}>Скачать файл</a>
                <CopyButton value={row.file_path} label="Скопировать путь" />
                <button className="ghost-button" type="button" disabled={!forwardRetryEnabled || retryForward.isPending} title={forwardRetryEnabled ? 'Повторно отправить сохранённый файл во внешний сервис.' : 'Включите внешнюю отправку и задайте URL в настройках.'} onClick={() => retryForward.mutate(row.id)}>Повторить отправку</button>
                <button className="ghost-button" type="button" disabled={!laserRetryEnabled || retryLaserCopy.isPending} title={laserRetryEnabled ? 'Повторно скопировать сохранённый файл в SMB/laser путь.' : 'Включите копию для лазера / SMB и задайте UNC в настройках.'} onClick={() => retryLaserCopy.mutate(row.id)}>Повторить SMB</button>
              </div>
            ),
          },
        ]}
      />
      {selected && <ExportDetailsModal item={selected} onClose={() => setSelected(null)} />}
      {retryError && <div className="error-state compact">{retryError.message}</div>}
      {retryResult && <JsonBlock title="Результат повторного действия" value={retryResult} searchable={false} />}
      <JsonBlock title="Последний export raw" value={exports[0] ?? {}} searchable={false} />
    </div>
  );
}

function ActionCell({ row, actionKey }: { row: MarkingCodePoolExport; actionKey: string }) {
  const action = actionDetails(row, actionKey);
  return <span title={String(action?.error ?? action?.reason ?? action?.path ?? action?.target ?? action?.url ?? '')}><StatusBadge status={actionStatus(row, actionKey)} compact /><small>{String(action?.path ?? action?.target ?? action?.url ?? action?.reason ?? action?.error ?? '—')}</small></span>;
}

function statusExplanation(status: string): string {
  const explanations: Record<string, string> = {
    saved: 'Локальный архив сохранён; optional-действия не выполнялись или были disabled.',
    forwarded: 'Локальный архив сохранён и внешняя отправка успешна.',
    partial_success: 'Локальный архив сохранён, но одно из optional-действий завершилось ошибкой.',
    failed: 'Обязательное локальное сохранение не выполнено или все действия завершились ошибкой.',
  };
  return explanations[status] ?? 'Смотрите детали действий в строке журнала.';
}
