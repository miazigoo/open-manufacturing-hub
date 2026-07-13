import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { StatusBadge } from '../../components/StatusBadge';
import { markingCodePoolsApi } from './api';

export function AggregationsTab() {
  const queryClient = useQueryClient();
  const settings = useQuery({ queryKey: ['chz-aggregation-settings'], queryFn: markingCodePoolsApi.aggregationSettings });
  const registrations = useQuery({ queryKey: ['chz-aggregation-registrations'], queryFn: markingCodePoolsApi.aggregationRegistrations });
  const [onecUrl, setOnecUrl] = useState('');
  const [timeout, setTimeoutValue] = useState('180');
  const [token, setToken] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [orderNumber, setOrderNumber] = useState('');
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null);
  const [message, setMessage] = useState('');

  const patchSettings = useMutation({
    mutationFn: () => markingCodePoolsApi.patchAggregationSettings({
      onec_url: onecUrl || settings.data?.onec_url || '',
      onec_timeout_seconds: Number(timeout || settings.data?.timeout_seconds || 180),
      ...(token ? { onec_token: token } : {}),
    }),
    onSuccess: async (data) => {
      setMessage('Настройки отправки агрегированных кодов в 1С сохранены.');
      setOnecUrl(data.onec_url);
      setTimeoutValue(String(data.timeout_seconds));
      setToken('');
      await queryClient.invalidateQueries({ queryKey: ['chz-aggregation-settings'] });
    },
  });

  const previewFile = useMutation({
    mutationFn: () => markingCodePoolsApi.aggregationPreviewFile(buildForm(file, orderNumber)),
    onSuccess: (data) => {
      setPreview(data as unknown as Record<string, unknown>);
      setMessage(`Preview: ${data.total_codes} кодов, ${data.total_aggregates} агрегатов, заказ ${data.order_number_1c}.`);
    },
  });

  const sendFile = useMutation({
    mutationFn: () => markingCodePoolsApi.aggregationRegisterFile(buildForm(file, orderNumber)),
    onSuccess: async (data) => {
      setMessage(data.message);
      await queryClient.invalidateQueries({ queryKey: ['chz-aggregation-registrations'] });
    },
  });

  if (settings.isLoading || registrations.isLoading) return <LoadingState label="Загрузка агрегации ЧЗ" />;
  const error = settings.error ?? registrations.error ?? patchSettings.error ?? previewFile.error ?? sendFile.error;

  const currentUrl = settings.data?.onec_url ?? '';
  const rows = registrations.data ?? [];

  return (
    <div className="page-stack">
      {error && <ErrorState error={error} />}
      <section className="panel-grid two-columns">
        <article className="info-panel">
          <div className="section-title-row">
            <div>
              <span className="eyebrow">Внешний сервис {'->'} OMH {'->'} 1С</span>
              <h2>Регистрация агрегированных кодов</h2>
            </div>
            <StatusBadge status={currentUrl ? 'enabled' : 'disabled'} label={currentUrl ? '1С настроена' : '1С не настроена'} />
          </div>
          <p className="microcopy">CSV должен быть без заголовка: полный код маркировки, затем TAB, затем код агрегата. GS-разделитель остаётся внутри кода и в 1С уходит как Base64.</p>
          <div className="metadata-grid compact-grid">
            <label className="field-label">HTTP service 1С<input value={onecUrl || currentUrl} onChange={(event) => setOnecUrl(event.target.value)} placeholder="http://1c-server/hs/chz/aggregation" /></label>
            <label className="field-label">Timeout, секунд<input type="number" value={timeout || String(settings.data?.timeout_seconds ?? 180)} onChange={(event) => setTimeoutValue(event.target.value)} /></label>
            <label className="field-label">Token, если нужен<input value={token} onChange={(event) => setToken(event.target.value)} placeholder={settings.data?.token_set ? 'token уже сохранён' : 'необязательно'} /></label>
          </div>
          <button className="primary-button" type="button" onClick={() => patchSettings.mutate()} disabled={patchSettings.isPending}>Сохранить настройки</button>
        </article>

        <article className="info-panel">
          <span className="eyebrow">Тестовая отправка</span>
          <h2>Загрузить CSV</h2>
          <div className="metadata-grid compact-grid">
            <label className="field-label">Файл<input type="file" accept=".csv,.txt,text/csv,text/plain" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /></label>
            <label className="field-label">Номер заказа, если его нет в имени файла<input value={orderNumber} onChange={(event) => setOrderNumber(event.target.value)} placeholder="260530/6543" /></label>
          </div>
          <div className="action-row wrap-actions">
            <button className="ghost-button" type="button" onClick={() => previewFile.mutate()} disabled={!file || previewFile.isPending}>Preview</button>
            <button className="primary-button" type="button" onClick={() => sendFile.mutate()} disabled={!file || sendFile.isPending}>Отправить в 1С</button>
          </div>
          {message && <p className="microcopy">{message}</p>}
          {preview && <pre className="code-block small-code">{JSON.stringify(preview, null, 2)}</pre>}
        </article>
      </section>

      <section className="info-panel">
        <div className="section-title-row">
          <div>
            <span className="eyebrow">Журнал</span>
            <h2>Последние отправки агрегации</h2>
          </div>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>Дата</th><th>Заказ 1С</th><th>Агрегатов</th><th>Кодов</th><th>Статус</th><th>Файл</th></tr></thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>{new Date(row.created_at).toLocaleString()}</td>
                  <td>{row.order_number_1c}</td>
                  <td>{row.total_aggregates}</td>
                  <td>{row.total_codes}</td>
                  <td><StatusBadge status={row.status === 'forwarded' ? 'enabled' : 'error'} label={row.status} /></td>
                  <td>{row.source_file_name ?? 'JSON'}</td>
                </tr>
              ))}
              {!rows.length && <tr><td colSpan={6}>Отправок пока нет.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function buildForm(file: File | null, orderNumber: string): FormData {
  if (!file) throw new Error('Выберите файл с агрегированными кодами.');
  const form = new FormData();
  form.append('file', file);
  if (orderNumber.trim()) form.append('order_number', orderNumber.trim());
  return form;
}
