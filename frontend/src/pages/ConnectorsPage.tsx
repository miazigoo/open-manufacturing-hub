import { FormEvent, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ConnectorDirection, ConnectorPayload, connectorsApi } from '../api/connectors';
import { asJson } from '../api/client';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { useT } from '../i18n/I18nProvider';
import { formatDateTime } from '../utils';

const defaultConfigs: Record<string, Record<string, unknown>> = {
  mock_wms: { fail_warehouse_ids: ['005'], success_warehouse_ids: ['MAIN'] },
  mock_erp: { source_system: 'Mock ERP', target_system: 'Mock WMS' },
  rest: { method: 'POST', url: 'https://example.com/api/orders', headers: {}, timeout_seconds: 10 },
  webhook: { default_source_system: 'External Webhook', default_target_system: 'Mock WMS' },
  onec: {
    base_url: 'https://onec.example.local/odata/standard.odata',
    http_service_base_url: 'https://onec.example.local/hs/omh',
    auth: { type: 'none' },
    timeout_seconds: 10,
    verify_ssl: true,
    odata: { enabled: true, default_page_size: 100, max_pages: 10 },
    http_services: { enabled: true, services: [{ name: 'echo', method: 'POST', path: '/echo' }] },
  },
};

export function ConnectorsPage() {
  const t = useT();
  const queryClient = useQueryClient();
  const types = useQuery({ queryKey: ['connector-types'], queryFn: connectorsApi.types });
  const connectors = useQuery({ queryKey: ['connectors'], queryFn: connectorsApi.list });
  const [form, setForm] = useState({ name: 'Mock WMS', connector_type: 'mock_wms', direction: 'target' as ConnectorDirection, config_json: asJson(defaultConfigs.mock_wms) });
  const [result, setResult] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const typeById = useMemo(() => new Map((types.data ?? []).map((type) => [type.connector_type, type])), [types.data]);

  const create = useMutation({ mutationFn: connectorsApi.create, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['connectors'] }); setResult(t('connectors.created')); } });
  const remove = useMutation({ mutationFn: connectorsApi.delete, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['connectors'] }) });
  const enable = useMutation({ mutationFn: connectorsApi.enable, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['connectors'] }) });
  const disable = useMutation({ mutationFn: connectorsApi.disable, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['connectors'] }) });
  const health = useMutation({ mutationFn: connectorsApi.healthcheck, onSuccess: (data) => { queryClient.invalidateQueries({ queryKey: ['connectors'] }); setResult(`Health: ${data.status} · ${data.message}`); } });
  const validate = useMutation({ mutationFn: connectorsApi.testConfig, onSuccess: (data) => setResult(data.valid ? t('connectors.valid') : t('connectors.invalid', { errors: data.errors.join(', ') })) });
  const generate = useMutation({ mutationFn: connectorsApi.generateMockErpEvents, onSuccess: (data) => { queryClient.invalidateQueries({ queryKey: ['events'] }); setResult(t('connectors.generated', { count: data.created.length })); } });

  function selectType(connectorType: string) {
    const metadata = typeById.get(connectorType);
    setForm({
      ...form,
      connector_type: connectorType,
      direction: metadata?.direction ?? form.direction,
      name: metadata?.display_name ?? form.name,
      config_json: asJson(defaultConfigs[connectorType] ?? {}),
    });
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    setResult(null);
    try {
      const payload: ConnectorPayload = {
        name: form.name,
        connector_type: form.connector_type,
        direction: form.direction,
        enabled: true,
        config_json: JSON.parse(form.config_json) as Record<string, unknown>,
      };
      create.mutate(payload);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Invalid JSON');
    }
  }

  const error = types.error ?? connectors.error;
  if (types.isLoading || connectors.isLoading) return <LoadingState label={t('connectors.loading')} />;
  if (error) return <ErrorState error={error} />;

  return (
    <div className="page-stack two-column-page">
      <section className="panel form-panel">
        <span className="eyebrow">{t('connectors.eyebrow')}</span>
        <h1>{t('connectors.title')}</h1>
        <form className="stack-form" onSubmit={submit}>
          <label className="field-label">{t('connectors.name')}<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
          <label className="field-label">{t('connectors.type')}<select value={form.connector_type} onChange={(event) => selectType(event.target.value)}>{(types.data ?? []).map((type) => <option key={type.connector_type} value={type.connector_type}>{type.display_name}</option>)}</select></label>
          <label className="field-label">{t('connectors.direction')}<select value={form.direction} onChange={(event) => setForm({ ...form, direction: event.target.value as ConnectorDirection })}><option value="source">source</option><option value="target">target</option><option value="bidirectional">bidirectional</option></select></label>
          <label className="field-label">{t('connectors.configJson')}<textarea value={form.config_json} onChange={(event) => setForm({ ...form, config_json: event.target.value })} spellCheck={false} /></label>
          {formError && <div className="error-state compact">{formError}</div>}
          {create.error instanceof Error && <div className="error-state compact">{create.error.message}</div>}
          {result && <div className="success-note">{result}</div>}
          <button className="primary-button" disabled={create.isPending}>{t('connectors.create')}</button>
        </form>
      </section>

      <section className="panel">
        <div className="panel-toolbar"><h2>{t('connectors.instances')}</h2><span className="microcopy">{t('connectors.configured', { count: connectors.data?.length ?? 0 })}</span></div>
        {connectors.data?.length ? connectors.data.map((connector) => (
          <article className="connector-card" key={connector.id}>
            <div className="connector-card-top">
              <div><h3>{connector.name}</h3><p>{connector.connector_type} · {connector.direction}</p></div>
              <div className="badge-row"><StatusBadge status={connector.enabled ? 'ok' : 'unknown'} label={connector.enabled ? t('connectors.enabled') : t('connectors.disabled')} /><StatusBadge status={connector.last_health_status ?? connector.status} /></div>
            </div>
            <div className="metadata-grid compact-grid">
              <span>{t('connectors.lastHealth')}<strong>{connector.last_health_status ?? t('common.unknown')}</strong></span>
              <span>{t('connectors.message')}<strong>{connector.last_health_message ?? '—'}</strong></span>
              <span>{t('connectors.checked')}<strong>{formatDateTime(connector.last_health_at)}</strong></span>
            </div>
            <JsonBlock value={connector.config_json} title={t('connectors.config')} searchable={false} />
            <div className="action-row">
              <button className="ghost-button" onClick={() => health.mutate(connector.id)}>{t('connectors.healthcheck')}</button>
              <button className="ghost-button" onClick={() => validate.mutate(connector.id)}>{t('connectors.testConfig')}</button>
              {connector.connector_type === 'mock_erp' && <button className="ghost-button" onClick={() => generate.mutate(connector.id)}>{t('connectors.generateEvents')}</button>}
              <button className="ghost-button" onClick={() => connector.enabled ? disable.mutate(connector.id) : enable.mutate(connector.id)}>{connector.enabled ? t('connectors.disable') : t('connectors.enable')}</button>
              <button className="ghost-button danger" onClick={() => remove.mutate(connector.id)}>{t('connectors.delete')}</button>
            </div>
          </article>
        )) : <EmptyState title={t('connectors.noInstances')} detail={t('connectors.noInstancesDetail')} />}
      </section>
    </div>
  );
}
