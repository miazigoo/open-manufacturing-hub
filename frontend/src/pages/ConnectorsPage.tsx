import { FormEvent, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ConnectorDirection, ConnectorPayload, connectorsApi } from '../api/connectors';
import { asJson } from '../api/client';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
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
  const queryClient = useQueryClient();
  const types = useQuery({ queryKey: ['connector-types'], queryFn: connectorsApi.types });
  const connectors = useQuery({ queryKey: ['connectors'], queryFn: connectorsApi.list });
  const [form, setForm] = useState({ name: 'Mock WMS', connector_type: 'mock_wms', direction: 'target' as ConnectorDirection, config_json: asJson(defaultConfigs.mock_wms) });
  const [result, setResult] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const typeById = useMemo(() => new Map((types.data ?? []).map((type) => [type.connector_type, type])), [types.data]);

  const create = useMutation({ mutationFn: connectorsApi.create, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['connectors'] }); setResult('Connector created'); } });
  const remove = useMutation({ mutationFn: connectorsApi.delete, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['connectors'] }) });
  const enable = useMutation({ mutationFn: connectorsApi.enable, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['connectors'] }) });
  const disable = useMutation({ mutationFn: connectorsApi.disable, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['connectors'] }) });
  const health = useMutation({ mutationFn: connectorsApi.healthcheck, onSuccess: (data) => { queryClient.invalidateQueries({ queryKey: ['connectors'] }); setResult(`Health: ${data.status} · ${data.message}`); } });
  const validate = useMutation({ mutationFn: connectorsApi.testConfig, onSuccess: (data) => setResult(data.valid ? 'Config valid' : `Config invalid: ${data.errors.join(', ')}`) });
  const generate = useMutation({ mutationFn: connectorsApi.generateMockErpEvents, onSuccess: (data) => { queryClient.invalidateQueries({ queryKey: ['events'] }); setResult(`Generated ${data.created.length} events`); } });

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
  if (types.isLoading || connectors.isLoading) return <LoadingState label="Loading connectors" />;
  if (error) return <ErrorState error={error} />;

  return (
    <div className="page-stack two-column-page">
      <section className="panel form-panel">
        <span className="eyebrow">Connector SDK</span>
        <h1>Register external systems through stable contracts.</h1>
        <form className="stack-form" onSubmit={submit}>
          <label className="field-label">Name<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
          <label className="field-label">Connector type<select value={form.connector_type} onChange={(event) => selectType(event.target.value)}>{(types.data ?? []).map((type) => <option key={type.connector_type} value={type.connector_type}>{type.display_name}</option>)}</select></label>
          <label className="field-label">Direction<select value={form.direction} onChange={(event) => setForm({ ...form, direction: event.target.value as ConnectorDirection })}><option value="source">source</option><option value="target">target</option><option value="bidirectional">bidirectional</option></select></label>
          <label className="field-label">Config JSON<textarea value={form.config_json} onChange={(event) => setForm({ ...form, config_json: event.target.value })} spellCheck={false} /></label>
          {formError && <div className="error-state compact">{formError}</div>}
          {create.error instanceof Error && <div className="error-state compact">{create.error.message}</div>}
          {result && <div className="success-note">{result}</div>}
          <button className="primary-button" disabled={create.isPending}>Create connector</button>
        </form>
      </section>

      <section className="panel">
        <div className="panel-toolbar"><h2>Connector instances</h2><span className="microcopy">{connectors.data?.length ?? 0} configured</span></div>
        {connectors.data?.length ? connectors.data.map((connector) => (
          <article className="connector-card" key={connector.id}>
            <div className="connector-card-top">
              <div><h3>{connector.name}</h3><p>{connector.connector_type} · {connector.direction}</p></div>
              <div className="badge-row"><StatusBadge status={connector.enabled ? 'ok' : 'unknown'} label={connector.enabled ? 'enabled' : 'disabled'} /><StatusBadge status={connector.last_health_status ?? connector.status} /></div>
            </div>
            <div className="metadata-grid compact-grid">
              <span>Last health<strong>{connector.last_health_status ?? 'unknown'}</strong></span>
              <span>Message<strong>{connector.last_health_message ?? '—'}</strong></span>
              <span>Checked<strong>{formatDateTime(connector.last_health_at)}</strong></span>
            </div>
            <JsonBlock value={connector.config_json} title="Config" searchable={false} />
            <div className="action-row">
              <button className="ghost-button" onClick={() => health.mutate(connector.id)}>Healthcheck</button>
              <button className="ghost-button" onClick={() => validate.mutate(connector.id)}>Test config</button>
              {connector.connector_type === 'mock_erp' && <button className="ghost-button" onClick={() => generate.mutate(connector.id)}>Generate events</button>}
              <button className="ghost-button" onClick={() => connector.enabled ? disable.mutate(connector.id) : enable.mutate(connector.id)}>{connector.enabled ? 'Disable' : 'Enable'}</button>
              <button className="ghost-button danger" onClick={() => remove.mutate(connector.id)}>Delete</button>
            </div>
          </article>
        )) : <EmptyState title="No connector instances" detail="Create Mock WMS first so pipeline send_to_target can call a connector." />}
      </section>
    </div>
  );
}
