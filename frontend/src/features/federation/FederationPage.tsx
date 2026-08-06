import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { request } from '../../api/client';
import { dataInboxApi } from '../../api/dataInbox';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { StatusBadge } from '../../components/StatusBadge';

interface FederationStatus {
  enabled: boolean;
  center_url: string;
  token_set: boolean;
  sync_interval_seconds: number;
  last_applied_version: string;
  local_version: string;
  runs_count: number;
  last_run: FederationRun | null;
}

interface FederationRun {
  id: string;
  direction: string;
  center_url: string;
  version: string;
  status: string;
  message: string | null;
  created_at: string;
}

const federationApi = {
  status: () => request<FederationStatus>('/api/federation/status'),
  runs: () => request<FederationRun[]>('/api/federation/runs'),
  syncNow: () => request<{ status: string; message: string; version: string }>('/api/federation/sync-now', { method: 'POST' }),
  bundleUrl: '/api/federation/config-bundle',
};

const RUN_LABELS: Record<string, string> = {
  success: 'применено',
  skipped: 'уже актуально',
  failed: 'ошибка',
};

export function FederationPage() {
  const queryClient = useQueryClient();
  const status = useQuery({ queryKey: ['federation-status'], queryFn: federationApi.status });
  const runs = useQuery({ queryKey: ['federation-runs'], queryFn: federationApi.runs });
  const environment = useQuery({ queryKey: ['current-environment'], queryFn: dataInboxApi.currentEnvironment });
  const [form, setForm] = useState({ center_url: '', token: '', enabled: true, interval: '300' });
  const [message, setMessage] = useState('');

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ['federation-status'] });
    await queryClient.invalidateQueries({ queryKey: ['federation-runs'] });
    await queryClient.invalidateQueries({ queryKey: ['current-environment'] });
  };

  const saveSettings = useMutation({
    mutationFn: async () => {
      if (!environment.data) throw new Error('Нет текущего environment');
      const envId = environment.data.id;
      const upsert = async (key: string, value: unknown) => {
        const existing = environment.data!.variables.find((item) => item.key === key);
        if (existing) return dataInboxApi.patchVariable(envId, key, value);
        return dataInboxApi.addVariable(envId, key, value);
      };
      await upsert('FEDERATION_CENTER_URL', form.center_url.trim());
      await upsert('FEDERATION_ENABLED', form.enabled ? 'true' : 'false');
      await upsert('FEDERATION_SYNC_INTERVAL_SECONDS', form.interval || '300');
      if (form.token) await upsert('FEDERATION_TOKEN', form.token);
    },
    onSuccess: async () => {
      setMessage('Настройки федерации сохранены.');
      await refresh();
    },
    onError: (caught) => setMessage(caught instanceof Error ? caught.message : 'Ошибка сохранения'),
  });

  const sync = useMutation({
    mutationFn: federationApi.syncNow,
    onSuccess: async (data) => {
      setMessage(data.message);
      await refresh();
    },
    onError: (caught) => setMessage(caught instanceof Error ? caught.message : 'Ошибка синхронизации'),
  });

  if (status.isLoading || runs.isLoading || environment.isLoading) return <LoadingState label="Загрузка федерации" />;
  const error = status.error ?? runs.error ?? environment.error;
  if (error) return <ErrorState error={error} />;
  const data = status.data!;
  const currentValues = (key: string) => String(environment.data?.variables.find((item) => item.key === key)?.value_json ?? '');

  return (
    <div className="page-stack">
      <section className="page-header onec-hero">
        <span className="eyebrow">Федерация (холдинг)</span>
        <h1>Раздача конфигурации на филиалы</h1>
        <p>Центральный OMH раздает весь конфиг интеграций (без секретов). Филиалы забирают его автоматически по расписанию или по кнопке — обновление интеграции в центре раскатывается на все филиалы одним кликом.</p>
        <div className="hero-meta">
          <StatusBadge status={data.enabled ? 'enabled' : 'disabled'} label={data.enabled ? 'автосинхронизация включена' : 'автосинхронизация выключена'} />
          <span className="microcopy">локальная версия: {data.local_version.slice(0, 19)}</span>
          <span className="microcopy">примененная: {data.last_applied_version ? data.last_applied_version.slice(0, 19) : '—'}</span>
        </div>
      </section>

      {message && <p className="microcopy">{message}</p>}

      <section className="panel-grid two-columns">
        <article className="info-panel">
          <span className="eyebrow">Я — филиал</span>
          <h2>Подключение к центру</h2>
          <p className="microcopy">Укажите адрес центрального OMH и общий токен. Филиал сам заберет конфиг и будет обновляться каждые {data.sync_interval_seconds} секунд.</p>
          <div className="metadata-grid compact-grid">
            <label className="field-label">URL центра<input value={form.center_url} onChange={(event) => setForm({ ...form, center_url: event.target.value })} placeholder={data.center_url || 'http://center-omh:8710'} /></label>
            <label className="field-label">Токен федерации<input value={form.token} onChange={(event) => setForm({ ...form, token: event.target.value })} placeholder={data.token_set ? 'токен уже сохранен' : 'общий секрет центра'} /></label>
            <label className="field-label">Интервал, секунд<input value={form.interval} onChange={(event) => setForm({ ...form, interval: event.target.value })} placeholder={String(data.sync_interval_seconds)} /></label>
            <label className="check-row"><input type="checkbox" checked={form.enabled} onChange={(event) => setForm({ ...form, enabled: event.target.checked })} /> Автосинхронизация по расписанию</label>
          </div>
          <div className="action-row wrap-actions">
            <button className="primary-button" onClick={() => saveSettings.mutate()} disabled={saveSettings.isPending}>Сохранить настройки</button>
            <button className="ghost-button" onClick={() => sync.mutate()} disabled={sync.isPending || !data.center_url}>Синхронизировать сейчас</button>
          </div>
          {data.last_run && (
            <p className="microcopy">Последняя синхронизация: <StatusBadge status={data.last_run.status === 'failed' ? 'error' : 'enabled'} label={RUN_LABELS[data.last_run.status] ?? data.last_run.status} /> {data.last_run.message}</p>
          )}
        </article>

        <article className="info-panel">
          <span className="eyebrow">Я — центр</span>
          <h2>Раздача конфига филиалам</h2>
          <p className="microcopy">Филиалы забирают бандл по этому адресу с заголовком <code>X-OMH-Token</code>. Токен задается переменной <code>FEDERATION_TOKEN</code> в Environments этого OMH (та же форма слева, если этот OMH — центр).</p>
          <div className="endpoint-url-box">
            <span>GET</span>
            <code>/api/federation/config-bundle</code>
          </div>
          <div className="builder-help-card">
            <strong>Что попадает в бандл</strong>
            <span>Все интеграции: flows, endpoints, маршруты, маппинги, коннекторы, правила, шаблоны OData, принтеры. Секреты (пароли, токены) маскируются — на филиале их вводят один раз вручную.</span>
          </div>
          <div className="builder-help-card">
            <strong>Версия на dashboard</strong>
            <span>Филиал может сообщать примененную версию через heartbeat-агента в <code>details_json.config_version</code> — тогда на странице Здоровье видно, какой филиал на какой версии.</span>
          </div>
        </article>
      </section>

      <section className="info-panel">
        <div className="section-title-row">
          <div><span className="eyebrow">История</span><h2>Синхронизации ({data.runs_count})</h2></div>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>Дата</th><th>Статус</th><th>Версия</th><th>Сообщение</th></tr></thead>
            <tbody>
              {(runs.data ?? []).map((run) => (
                <tr key={run.id}>
                  <td>{new Date(run.created_at).toLocaleString()}</td>
                  <td><StatusBadge status={run.status === 'failed' ? 'error' : 'enabled'} label={RUN_LABELS[run.status] ?? run.status} /></td>
                  <td className="microcopy">{run.version ? run.version.slice(0, 19) : '—'}</td>
                  <td>{run.message}</td>
                </tr>
              ))}
              {!(runs.data ?? []).length && <tr><td colSpan={4}>Синхронизаций пока не было.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
