import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ConnectorDirection, ConnectorInstance, ConnectorPayload, connectorsApi } from '../api/connectors';
import { asJson } from '../api/client';
import { secretsApi, type SecretConfigValidation } from '../api/secrets';
import { CodeEditor } from '../components/CodeEditor';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { useT } from '../i18n/useI18n';
import { formatDateTime } from '../utils';

const defaultConfigs: Record<string, Record<string, unknown>> = {
  mock_wms: { fail_warehouse_ids: ['005'], success_warehouse_ids: ['MAIN'] },
  mock_erp: { source_system: 'Mock ERP', target_system: 'Mock WMS' },
  rest: { method: 'POST', url: 'https://example.com/api/orders', headers: {}, timeout_seconds: 10 },
  webhook: { default_source_system: 'External Webhook', default_target_system: 'Mock WMS' },
  zpl_printer: { printer_name: 'Line 1 Zebra', host: '192.168.1.50', port: 9100, dpi: 203, timeout_seconds: 5, status_mode: 'tcp_connect' },
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
  const onecConnectors = useMemo(() => (connectors.data ?? []).filter((connector) => connector.connector_type === 'onec'), [connectors.data]);

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
          <label className="field-label">{t('connectors.configJson')}<CodeEditor value={form.config_json} onChange={(value) => setForm({ ...form, config_json: value })} language="json" minRows={10} /></label>
          <SecretConfigWarnings configText={form.config_json} />
          {formError && <div className="error-state compact">{formError}</div>}
          {create.error instanceof Error && <div className="error-state compact">{create.error.message}</div>}
          {result && <div className="success-note">{result}</div>}
          <button className="primary-button" disabled={create.isPending}>{t('connectors.create')}</button>
        </form>
      </section>

      <section className="panel">
        <OneCConfigEditor connectors={onecConnectors} onSaved={() => { queryClient.invalidateQueries({ queryKey: ['connectors'] }); setResult(t('connectors.saved')); }} />
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
        )) : <EmptyState title={t('connectors.noInstances')} detail={t('connectors.noInstancesDetail')} actions={<><Link className="primary-button" to="/onboarding">Open onboarding</Link><Link className="ghost-button" to="/docs/onec/tools/connector">1C connector docs</Link></>} />}
      </section>
    </div>
  );
}

interface OneCFormState {
  connectorId: string;
  base_url: string;
  http_service_base_url: string;
  auth_type: 'none' | 'basic';
  username: string;
  password: string;
  timeout_seconds: string;
  verify_ssl: boolean;
  odata_enabled: boolean;
  default_page_size: string;
  max_pages: string;
  health_path: string;
  shipment_path: string;
  stock_path: string;
  inventory_path: string;
  movement_path: string;
}

function OneCConfigEditor({ connectors, onSaved }: { connectors: ConnectorInstance[]; onSaved: () => void }) {
  const t = useT();
  const [form, setForm] = useState<OneCFormState>(() => onecFormFromConfig(connectors[0]));
  const [error, setError] = useState<string | null>(null);
  const selected = connectors.find((connector) => connector.id === form.connectorId);
  const save = useMutation({
    mutationFn: () => {
      if (!selected) throw new Error(t('connectors.onecSelectRequired'));
      return connectorsApi.patch(selected.id, { config_json: onecConfigFromForm(form) });
    },
    onSuccess: onSaved,
  });

  useEffect(() => {
    if (!connectors.length) return;
    const stillExists = connectors.some((connector) => connector.id === form.connectorId);
    if (!stillExists) setForm(onecFormFromConfig(connectors[0]));
  }, [connectors, form.connectorId]);

  function selectConnector(connectorId: string) {
    setForm(onecFormFromConfig(connectors.find((connector) => connector.id === connectorId)));
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      onecConfigFromForm(form);
      save.mutate();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t('common.unknownError'));
    }
  }

  if (!connectors.length) {
    return (
      <div className="onec-config-editor">
        <div>
          <span className="eyebrow">{t('connectors.onecSetup')}</span>
          <h2>{t('connectors.onecNoConnector')}</h2>
          <p>{t('connectors.onecNoConnectorDetail')}</p>
        </div>
      </div>
    );
  }

  return (
    <form className="onec-config-editor stack-form" onSubmit={submit}>
      <div>
        <span className="eyebrow">{t('connectors.onecSetup')}</span>
        <h2>{t('connectors.onecTitle')}</h2>
        <p>{t('connectors.onecHint')}</p>
      </div>
      <label className="field-label">{t('connectors.onecInstance')}<select value={form.connectorId} onChange={(event) => selectConnector(event.target.value)}>{connectors.map((connector) => <option key={connector.id} value={connector.id}>{connector.name}</option>)}</select></label>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">{t('connectors.odataUrl')}<input value={form.base_url} onChange={(event) => setForm({ ...form, base_url: event.target.value })} /></label>
        <label className="field-label">{t('connectors.httpServiceUrl')}<input value={form.http_service_base_url} onChange={(event) => setForm({ ...form, http_service_base_url: event.target.value })} /></label>
        <label className="field-label">{t('connectors.timeout')}<input type="number" min="1" value={form.timeout_seconds} onChange={(event) => setForm({ ...form, timeout_seconds: event.target.value })} /></label>
      </div>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">{t('connectors.authType')}<select value={form.auth_type} onChange={(event) => setForm({ ...form, auth_type: event.target.value as OneCFormState['auth_type'] })}><option value="none">none</option><option value="basic">basic</option></select></label>
        <label className="field-label">{t('connectors.username')}<input value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} disabled={form.auth_type === 'none'} /></label>
        <label className="field-label">{t('connectors.password')}<input value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} disabled={form.auth_type === 'none'} placeholder='{ \"$secret\": \"onec.erp.password\" }' /></label>
      </div>
      <SecretConfigWarnings configObject={onecConfigPreviewFromForm(form)} />
      <div className="metadata-grid compact-grid no-margin">
        <label className="check-row"><input type="checkbox" checked={form.verify_ssl} onChange={(event) => setForm({ ...form, verify_ssl: event.target.checked })} />{t('connectors.verifySsl')}</label>
        <label className="check-row"><input type="checkbox" checked={form.odata_enabled} onChange={(event) => setForm({ ...form, odata_enabled: event.target.checked })} />{t('connectors.odataEnabled')}</label>
        <label className="field-label">{t('connectors.pageSize')}<input type="number" min="1" value={form.default_page_size} onChange={(event) => setForm({ ...form, default_page_size: event.target.value })} /></label>
      </div>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">{t('connectors.maxPages')}<input type="number" min="1" value={form.max_pages} onChange={(event) => setForm({ ...form, max_pages: event.target.value })} /></label>
        <label className="field-label">{t('connectors.healthPath')}<input value={form.health_path} onChange={(event) => setForm({ ...form, health_path: event.target.value })} /></label>
        <label className="field-label">{t('connectors.shipmentPath')}<input value={form.shipment_path} onChange={(event) => setForm({ ...form, shipment_path: event.target.value })} /></label>
      </div>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">{t('connectors.stockPath')}<input value={form.stock_path} onChange={(event) => setForm({ ...form, stock_path: event.target.value })} /></label>
        <label className="field-label">{t('connectors.inventoryPath')}<input value={form.inventory_path} onChange={(event) => setForm({ ...form, inventory_path: event.target.value })} /></label>
        <label className="field-label">{t('connectors.movementPath')}<input value={form.movement_path} onChange={(event) => setForm({ ...form, movement_path: event.target.value })} /></label>
      </div>
      {error && <div className="error-state compact">{error}</div>}
      {save.error instanceof Error && <div className="error-state compact">{save.error.message}</div>}
      <div className="action-row"><button className="primary-button" disabled={save.isPending}>{t('connectors.saveOneC')}</button></div>
    </form>
  );
}

function onecFormFromConfig(connector?: { id: string; config_json: Record<string, unknown> }): OneCFormState {
  const config = connector?.config_json ?? defaultConfigs.onec;
  const auth = objectValue(config.auth);
  const odata = objectValue(config.odata);
  const operations = objectValue(config.operations);
  const httpServices = objectValue(config.http_services);
  const services = Array.isArray(httpServices.services) ? httpServices.services : [];
  return {
    connectorId: connector?.id ?? '',
    base_url: stringValue(config.base_url),
    http_service_base_url: stringValue(config.http_service_base_url),
    auth_type: stringValue(auth.type) === 'basic' ? 'basic' : 'none',
    username: stringValue(auth.username),
    password: secretInputValue(auth.password),
    timeout_seconds: stringValue(config.timeout_seconds || 10),
    verify_ssl: config.verify_ssl !== false,
    odata_enabled: odata.enabled !== false,
    default_page_size: stringValue(odata.default_page_size || 100),
    max_pages: stringValue(odata.max_pages || 10),
    health_path: servicePath(services, 'health') || '/health',
    shipment_path: operationPath(operations, 'update_shipment_status') || servicePath(services, 'shipment_facts') || '/shipment-facts',
    stock_path: operationPath(operations, 'update_stock_balance') || servicePath(services, 'stock_balances') || '/stock-balances',
    inventory_path: operationPath(operations, 'send_inventory_result') || servicePath(services, 'inventory_results') || '/inventory-results',
    movement_path: operationPath(operations, 'send_movement_fact') || servicePath(services, 'movements') || '/movements',
  };
}

function onecConfigFromForm(form: OneCFormState): Record<string, unknown> {
  const timeout = positiveInt(form.timeout_seconds, 'timeout_seconds');
  const pageSize = positiveInt(form.default_page_size, 'odata.default_page_size');
  const maxPages = positiveInt(form.max_pages, 'odata.max_pages');
  const username = form.username.trim();
  const password = parseSecretInput(form.password);
  if (form.auth_type === 'basic' && (!username || !password)) throw new Error('Basic auth requires username and password');
  const auth = form.auth_type === 'basic' ? { type: 'basic', username, password } : { type: 'none' };
  return {
    base_url: form.base_url.trim(),
    http_service_base_url: form.http_service_base_url.trim(),
    auth,
    timeout_seconds: timeout,
    verify_ssl: form.verify_ssl,
    odata: { enabled: form.odata_enabled, default_page_size: pageSize, max_pages: maxPages },
    http_services: {
      enabled: true,
      default_path: '/events',
      services: [
        { name: 'health', method: 'GET', path: normalizePath(form.health_path) },
        { name: 'shipment_facts', method: 'POST', path: normalizePath(form.shipment_path) },
        { name: 'stock_balances', method: 'POST', path: normalizePath(form.stock_path) },
        { name: 'inventory_results', method: 'POST', path: normalizePath(form.inventory_path) },
        { name: 'movements', method: 'POST', path: normalizePath(form.movement_path) },
      ],
    },
    operations: {
      update_shipment_status: { method: 'POST', path: normalizePath(form.shipment_path) },
      update_stock_balance: { method: 'POST', path: normalizePath(form.stock_path) },
      send_inventory_result: { method: 'POST', path: normalizePath(form.inventory_path) },
      send_movement_fact: { method: 'POST', path: normalizePath(form.movement_path) },
    },
  };
}

function onecConfigPreviewFromForm(form: OneCFormState): Record<string, unknown> {
  const username = form.username.trim();
  const password = parseSecretInput(form.password);
  return {
    base_url: form.base_url.trim(),
    http_service_base_url: form.http_service_base_url.trim(),
    auth: form.auth_type === 'basic' ? { type: 'basic', username, password } : { type: 'none' },
    timeout_seconds: Number.parseInt(form.timeout_seconds, 10) || 10,
    verify_ssl: form.verify_ssl,
    odata: { enabled: form.odata_enabled, default_page_size: Number.parseInt(form.default_page_size, 10) || 100, max_pages: Number.parseInt(form.max_pages, 10) || 10 },
  };
}

function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function stringValue(value: unknown): string {
  return value === undefined || value === null ? '' : String(value);
}

function secretInputValue(value: unknown): string {
  if (value && typeof value === 'object' && !Array.isArray(value) && '$secret' in value) return JSON.stringify(value);
  const text = stringValue(value);
  return text === '***' ? '' : text;
}

function parseSecretInput(value: string): string | { $secret: string } {
  const trimmed = value.trim();
  if (!trimmed) return '';
  if (trimmed.startsWith('{')) {
    try {
      const parsed = JSON.parse(trimmed) as unknown;
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed) && typeof (parsed as { $secret?: unknown }).$secret === 'string') return parsed as { $secret: string };
    } catch {
      return value;
    }
  }
  return value;
}

function SecretConfigWarnings({ configText, configObject }: { configText?: string; configObject?: Record<string, unknown> }) {
  const t = useT();
  const [error, setError] = useState<string | null>(null);
  const validate = useMutation({
    mutationFn: async () => {
      setError(null);
      if (configObject) return secretsApi.validateConfig(configObject);
      try {
        return await secretsApi.validateConfig(JSON.parse(configText || '{}') as Record<string, unknown>);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'Invalid JSON');
        throw caught;
      }
    },
  });
  const data = validate.data as SecretConfigValidation | undefined;
  return (
    <div className="secret-config-panel">
      <div className="panel-toolbar compact-toolbar"><span className="microcopy">{t('secrets.configWarnings')}</span><button type="button" className="ghost-button" onClick={() => validate.mutate()} disabled={validate.isPending}>Check secrets</button></div>
      {error && <div className="error-state compact">{error}</div>}
      {validate.error instanceof Error && !error && <div className="error-state compact">{validate.error.message}</div>}
      {data && data.references.length === 0 && data.raw_secret_warnings.length === 0 && <div className="success-note">{t('secrets.configOk')}</div>}
      {data && data.references.length > 0 && <div className="secret-warning-list">{data.references.map((item) => <span key={`${item.path}:${item.name}`} className={item.status === 'ok' ? 'success-note' : 'error-state compact'}>{item.path}: {item.name} · {item.status}</span>)}</div>}
      {data && data.raw_secret_warnings.length > 0 && <div className="error-state compact"><strong>{t('secrets.rawWarnings')}</strong>{data.raw_secret_warnings.map((item) => <span key={item}>{item}</span>)}</div>}
    </div>
  );
}

function positiveInt(value: string, field: string): number {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) throw new Error(`${field} must be positive`);
  return parsed;
}

function normalizePath(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return '/';
  return trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
}

function servicePath(services: unknown[], name: string): string {
  const service = services.find((item) => objectValue(item).name === name);
  return stringValue(objectValue(service).path);
}

function operationPath(operations: Record<string, unknown>, name: string): string {
  return stringValue(objectValue(operations[name]).path);
}
