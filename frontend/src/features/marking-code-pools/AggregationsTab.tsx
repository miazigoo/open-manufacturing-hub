import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { StatusBadge } from '../../components/StatusBadge';
import { markingCodePoolsApi } from './api';
import type { ChzAggregationSettings, ChzAggregationSettingsPatch } from './types';

export function AggregationsTab() {
  const queryClient = useQueryClient();
  const settings = useQuery({ queryKey: ['chz-aggregation-settings'], queryFn: markingCodePoolsApi.aggregationSettings });
  const registrations = useQuery({ queryKey: ['chz-aggregation-registrations'], queryFn: markingCodePoolsApi.aggregationRegistrations });
  const [file, setFile] = useState<File | null>(null);
  const [orderNumber, setOrderNumber] = useState('');
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null);
  const [message, setMessage] = useState('');

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
  const error = settings.error ?? registrations.error ?? previewFile.error ?? sendFile.error;

  const currentUrl = settings.data?.onec_url ?? '';
  const forwardingEnabled = Boolean(currentUrl && settings.data?.onec_enabled);
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
            <StatusBadge status={forwardingEnabled ? 'enabled' : 'disabled'} label={!currentUrl ? 'Адрес 1С не указан' : forwardingEnabled ? 'Отправка включена' : 'Отправка выключена'} />
          </div>
          <p className="microcopy">CSV должен быть без заголовка: полный код маркировки, затем TAB, затем код агрегата. GS-разделитель остаётся внутри кода и в 1С уходит как Base64.</p>
          {settings.data && <AggregationSettingsForm settings={settings.data} />}
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
            <button className="primary-button" type="button" onClick={() => sendFile.mutate()} disabled={!file || !forwardingEnabled || sendFile.isPending}>Отправить в 1С</button>
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
                  <td><StatusBadge status={row.status === 'forwarded' ? 'enabled' : row.status === 'skipped' ? 'disabled' : 'error'} label={row.status === 'skipped' ? 'Пропущено' : row.status} /></td>
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

function AggregationSettingsForm({ settings }: { settings: ChzAggregationSettings }) {
  const queryClient = useQueryClient();
  const [enabled, setEnabled] = useState<boolean>();
  const [url, setUrl] = useState<string>();
  const [timeout, setTimeoutValue] = useState<string>();
  const [header, setHeader] = useState<string>();
  const [token, setToken] = useState('');
  const [authMode, setAuthMode] = useState<'header' | 'basic'>('header');
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [removeToken, setRemoveToken] = useState(false);
  const save = useMutation({
    mutationFn: markingCodePoolsApi.patchAggregationSettings,
    onSuccess: (data) => {
      queryClient.setQueryData(['chz-aggregation-settings'], data);
      setEnabled(undefined);
      setUrl(undefined);
      setTimeoutValue(undefined);
      setHeader(undefined);
      setToken('');
      setPassword('');
      setLogin('');
      setAuthMode('header');
      setRemoveToken(false);
    },
  });

  const patch: ChzAggregationSettingsPatch = {};
  if (enabled !== undefined && enabled !== settings.onec_enabled) patch.onec_enabled = enabled;
  if (url !== undefined && url.trim() !== settings.onec_url) patch.onec_url = url.trim();
  if (timeout !== undefined && Number(timeout) !== settings.timeout_seconds) patch.onec_timeout_seconds = Number(timeout);
  if (authMode === 'header' && header !== undefined && header.trim() !== settings.header_name) patch.onec_header_name = header.trim();
  if (removeToken) patch.onec_token = '';
  else if (authMode === 'header' && token) patch.onec_token = token;
  const replaceBasic = authMode === 'basic' && !removeToken;
  const changed = Object.keys(patch).length > 0 || replaceBasic;
  const changedServer = patch.onec_url !== undefined && urlOrigin(patch.onec_url) !== urlOrigin(settings.onec_url);
  const needsCredentials = settings.token_set && changedServer && patch.onec_token === undefined && !replaceBasic;

  function saveSettings() {
    if (replaceBasic) {
      const utf8 = new TextEncoder().encode(login + ':' + password);
      patch.onec_header_name = 'Authorization';
      patch.onec_token = 'Basic ' + btoa(Array.from(utf8, (byte) => String.fromCharCode(byte)).join(''));
    }
    if (changed) save.mutate(patch);
  }

  return (
    <form onSubmit={(event) => { event.preventDefault(); saveSettings(); }}>
      <label className="check-row">
        <input type="checkbox" checked={enabled ?? settings.onec_enabled} disabled={save.isPending}
          onChange={(event) => setEnabled(event.target.checked)} />
        Отправлять в 1С
      </label>
      <div className="metadata-grid compact-grid">
        <label className="field-label">Адрес HTTP-сервиса 1С
          <input type="url" pattern="https?://.+" value={url ?? settings.onec_url} disabled={save.isPending}
            onChange={(event) => setUrl(event.target.value)} placeholder="https://…" />
        </label>
        <label className="field-label">Тайм-аут, секунд
          <input type="number" required min="0" step="any" value={timeout ?? String(settings.timeout_seconds)} disabled={save.isPending}
            onChange={(event) => setTimeoutValue(event.target.value)} />
        </label>
        <label className="field-label">Способ авторизации
          <select value={authMode} disabled={save.isPending || removeToken}
            onChange={(event) => setAuthMode(event.target.value === 'basic' ? 'basic' : 'header')}>
            <option value="header">HTTP-заголовок</option>
            <option value="basic">Логин и пароль (Basic)</option>
          </select>
        </label>
        {authMode === 'basic' ? <>
          <label className="field-label">Логин 1С
            <input required pattern="[^:]+" autoComplete="off" value={login} disabled={save.isPending || removeToken}
              onChange={(event) => setLogin(event.target.value)} />
          </label>
          <label className="field-label">Пароль 1С
            <input type="password" required autoComplete="new-password" value={password} disabled={save.isPending || removeToken}
              onChange={(event) => setPassword(event.target.value)} />
          </label>
        </> : <>
          <label className="field-label">HTTP-заголовок для токена
            <input required value={header ?? settings.header_name} disabled={save.isPending || removeToken}
              onChange={(event) => setHeader(event.target.value)} />
          </label>
          <label className="field-label">Значение заголовка
            <input type="password" autoComplete="new-password" value={token} disabled={save.isPending || removeToken}
              onChange={(event) => setToken(event.target.value)} placeholder={settings.token_set ? 'Значение уже сохранено' : 'Без авторизации'} />
          </label>
        </>}
      </div>
      {settings.token_set && (
        <label className="check-row">
          <input type="checkbox" checked={removeToken} disabled={save.isPending}
            onChange={(event) => setRemoveToken(event.target.checked)} />
          Удалить сохранённые данные авторизации
        </label>
      )}
      {needsCredentials && <p className="microcopy">При смене сервера или протокола введите новые данные авторизации либо удалите сохранённые.</p>}
      <button className="primary-button" type="submit" disabled={!changed || needsCredentials || save.isPending || Number(timeout ?? settings.timeout_seconds) <= 0}>
        Сохранить настройки
      </button>
      {save.error && <ErrorState error={save.error} />}
      {save.isSuccess && !changed && <p className="microcopy" role="status">Настройки отправки в 1С сохранены.</p>}
    </form>
  );
}

function urlOrigin(value: string): string {
  try {
    return new URL(value).origin;
  } catch {
    return '';
  }
}

function buildForm(file: File | null, orderNumber: string): FormData {
  if (!file) throw new Error('Выберите файл с агрегированными кодами.');
  const form = new FormData();
  form.append('file', file);
  if (orderNumber.trim()) form.append('order_number', orderNumber.trim());
  return form;
}
