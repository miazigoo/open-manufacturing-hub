import { FormEvent, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { odataConnectionsApi, type ODataConnection, type ODataConnectionPayload } from '../api/odataConnections';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { useI18n } from '../i18n/useI18n';

const presets = [
  { name: 'OData ERP', base_url: 'http://erp-server/base/odata/standard.odata', username: 'exchange_user', tags: ['ERP', 'contractors', 'products'] },
  { name: 'OData УСП', base_url: 'http://usp-server/base/odata/standard.odata', username: 'exchange_usp', tags: ['УСП', 'marking'] },
  { name: 'OData WMS', base_url: 'http://wms-server/base/odata/standard.odata', username: 'wms_exchange', tags: ['WMS', 'warehouse'] },
];

function emptyForm(): ODataConnectionPayload {
  return { name: 'OData ERP', description: 'OData profile for reading contractors and products from 1C ERP.', base_url: 'http://erp-server/base/odata/standard.odata', auth_type: 'basic', username: 'exchange_user', password: '', password_secret: '', timeout_seconds: 20, verify_ssl: true, default_top: 100, max_pages: 10, tags: ['ERP'] };
}

export function ODataConnectionsPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const connections = useQuery({ queryKey: ['odata-connections'], queryFn: odataConnectionsApi.list });
  const [form, setForm] = useState<ODataConnectionPayload>(() => emptyForm());
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [result, setResult] = useState<unknown>(null);
  const selected = useMemo(() => (connections.data ?? []).find((item) => item.id === selectedId) ?? connections.data?.[0] ?? null, [connections.data, selectedId]);
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['odata-connections'] });
  const create = useMutation({ mutationFn: odataConnectionsApi.create, onSuccess: (data) => { setSelectedId(data.id); setResult(data); refresh(); } });
  const patch = useMutation({ mutationFn: (payload: { id: string; data: Partial<ODataConnectionPayload> }) => odataConnectionsApi.patch(payload.id, payload.data), onSuccess: (data) => { setResult(data); refresh(); } });
  const remove = useMutation({ mutationFn: odataConnectionsApi.delete, onSuccess: () => { setSelectedId(null); refresh(); } });
  const test = useMutation({ mutationFn: (id: string) => odataConnectionsApi.test(id, { resource: '$metadata' }), onSuccess: setResult });

  if (connections.isLoading) return <LoadingState label={t('integration.odataConnections.loading')} />;
  if (connections.error) return <ErrorState error={connections.error} />;

  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate({ ...form, tags: normalizeTags(form.tags) });
  }

  function loadPreset(preset: typeof presets[number]) {
    setForm({ ...emptyForm(), ...preset, tags: preset.tags, password: preset.name === 'OData УСП' ? '123' : '' });
  }

  return (
    <div className="page-stack odata-connections-page">
      <section className="page-header product-page-header">
        <div>
          <span className="eyebrow">1C OData</span>
          <h1>{t('integration.odataConnections.title')}</h1>
          <p>{t('integration.odataConnections.description')}</p>
        </div>
        <div className="product-header-actions"><Link className="primary-button" to="/docs/onec/academy/create-odata-connection">{t('integration.odataConnections.openLesson')}</Link><Link className="ghost-button" to="/odata-explorer">{t('integration.odataConnections.testExplorer')}</Link></div>
      </section>

      <section className="flow-layout">
        <form className="panel stack-form" onSubmit={submit}>
          <div className="panel-toolbar"><div><span className="eyebrow">{t('integration.odataConnections.create')}</span><h2>{t('integration.odataConnections.newConnection')}</h2><p>{t('integration.odataConnections.newConnectionHint')}</p></div><button className="primary-button" disabled={create.isPending}>{t('integration.odataConnections.createButton')}</button></div>
          <div className="component-strip package-capabilities">{presets.map((preset) => <button type="button" className="ghost-button" key={preset.name} onClick={() => loadPreset(preset)}>{preset.name}</button>)}</div>
          <label className="field-label">{t('integration.odataConnections.name')}<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
          <label className="field-label">{t('integration.odataConnections.descriptionLabel')}<input value={form.description ?? ''} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
          <label className="field-label">{t('integration.odataConnections.odataUrl')}<input value={form.base_url} onChange={(event) => setForm({ ...form, base_url: event.target.value })} /></label>
          <div className="metadata-grid compact-grid no-margin">
            <label className="field-label">{t('integration.odataConnections.auth')}<select value={form.auth_type} onChange={(event) => setForm({ ...form, auth_type: event.target.value })}><option value="basic">basic</option><option value="none">none</option></select></label>
            <label className="field-label">{t('integration.odataConnections.username')}<input value={form.username ?? ''} onChange={(event) => setForm({ ...form, username: event.target.value })} disabled={form.auth_type === 'none'} /></label>
            <label className="field-label">{t('integration.odataConnections.password')}<input value={form.password_secret || form.password || ''} onChange={(event) => event.target.value.startsWith('$secret:') ? setForm({ ...form, password_secret: event.target.value.replace('$secret:', ''), password: '' }) : setForm({ ...form, password: event.target.value, password_secret: '' })} disabled={form.auth_type === 'none'} placeholder={t('integration.odataConnections.passwordPlaceholder')} /></label>
          </div>
          <div className="metadata-grid compact-grid no-margin">
            <label className="field-label">{t('integration.odataConnections.timeout')}<input type="number" min="1" value={form.timeout_seconds} onChange={(event) => setForm({ ...form, timeout_seconds: Number(event.target.value) || 20 })} /></label>
            <label className="field-label">{t('integration.odataConnections.defaultTop')}<input type="number" min="1" value={form.default_top} onChange={(event) => setForm({ ...form, default_top: Number(event.target.value) || 100 })} /></label>
            <label className="field-label">{t('integration.odataConnections.maxPages')}<input type="number" min="1" value={form.max_pages} onChange={(event) => setForm({ ...form, max_pages: Number(event.target.value) || 10 })} /></label>
          </div>
          <label className="check-row"><input type="checkbox" checked={form.verify_ssl} onChange={(event) => setForm({ ...form, verify_ssl: event.target.checked })} /> {t('integration.odataConnections.verifySsl')}</label>
          <label className="field-label">{t('integration.odataConnections.tags')}<input value={form.tags.join(', ')} onChange={(event) => setForm({ ...form, tags: normalizeTags(event.target.value) })} /></label>
          {create.error instanceof Error && <div className="error-state compact">{create.error.message}</div>}
        </form>

        <section className="panel">
          <div className="panel-toolbar"><h2>{t('integration.odataConnections.saved')}</h2><span className="microcopy">{connections.data?.length ?? 0}</span></div>
          {(connections.data ?? []).length === 0 ? <EmptyState title={t('integration.odataConnections.emptyTitle')} detail={t('integration.odataConnections.emptyDetail')} /> : <div className="flow-list">{connections.data?.map((connection) => <button key={connection.id} className={`flow-list-item ${selected?.id === connection.id ? 'active' : ''}`} onClick={() => setSelectedId(connection.id)}><span><strong>{connection.name}</strong><small>{connection.base_url}</small></span><StatusBadge status={connection.enabled ? 'enabled' : 'disabled'} compact /></button>)}</div>}
        </section>
      </section>

      {selected && <ConnectionDetails connection={selected} onTest={() => test.mutate(selected.id)} onToggle={() => patch.mutate({ id: selected.id, data: { enabled: !selected.enabled } })} onDelete={() => remove.mutate(selected.id)} busy={test.isPending || patch.isPending || remove.isPending} />}
      {result !== null && <JsonBlock title={t('integration.odataConnections.lastOperation')} value={result as Record<string, unknown>} searchable />}
      {[test.error, patch.error, remove.error].find(Boolean) instanceof Error && <div className="error-state compact">{(([test.error, patch.error, remove.error].find(Boolean)) as Error).message}</div>}
    </div>
  );
}

function ConnectionDetails({ connection, onTest, onToggle, onDelete, busy }: { connection: ODataConnection; onTest: () => void; onToggle: () => void; onDelete: () => void; busy: boolean }) {
  const { t } = useI18n();
  return (
    <section className="panel flow-detail">
      <div className="panel-toolbar"><div><span className="eyebrow">{t('integration.odataConnections.selected')}</span><h2>{connection.name}</h2><p>{connection.description}</p></div><StatusBadge status={connection.last_health_status ?? (connection.enabled ? 'enabled' : 'disabled')} /></div>
      <div className="metadata-grid compact-grid">
        <span>OData URL<strong>{connection.base_url}</strong></span>
        <span>{t('integration.odataConnections.user')}<strong>{connection.username ?? t('integration.odataConnections.none')}</strong></span>
        <span>{t('integration.odataConnections.passwordState')}<strong>{connection.password_secret ? `$secret:${connection.password_secret}` : connection.auth_type === 'basic' ? t('integration.odataConnections.storedMasked') : t('integration.odataConnections.none')}</strong></span>
        <span>{t('integration.odataConnections.defaultTop')}<strong>{connection.default_top}</strong></span>
        <span>{t('integration.odataConnections.maxPages')}<strong>{connection.max_pages}</strong></span>
        <span>{t('integration.odataConnections.tags')}<strong>{connection.tags.join(', ') || t('integration.odataConnections.none')}</strong></span>
      </div>
      <div className="action-row wrap-actions"><button className="primary-button" onClick={onTest} disabled={busy}>{t('integration.odataConnections.testMetadata')}</button><Link className="primary-link" to={`/odata-explorer?connection=${connection.id}`}>{t('integration.odataConnections.openExplorer')}</Link><button className="ghost-button" onClick={onToggle} disabled={busy}>{connection.enabled ? t('integration.odataConnections.disable') : t('integration.odataConnections.enable')}</button><button className="ghost-button danger" onClick={onDelete} disabled={busy}>{t('integration.odataConnections.delete')}</button></div>
    </section>
  );
}

function normalizeTags(value: string[] | string) {
  const source = Array.isArray(value) ? value.join(',') : value;
  return source.split(',').map((item) => item.trim()).filter(Boolean);
}
