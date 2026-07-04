import { FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { enterpriseRuntimeApi } from '../api/enterpriseRuntime';
import type { QueueMessage, QueueStatus } from '../api/enterpriseRuntime';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

type RuntimeView = 'queue' | 'dlq' | 'monitor' | 'objects' | 'resolvers' | 'transforms' | 'rules';

const titles: Record<RuntimeView, { eyebrow: string; title: string; subtitle: string }> = {
  queue: { eyebrow: 'Enterprise Runtime', title: 'Integration Queue', subtitle: 'Prioritized operational queue with retry, worker and timeline visibility.' },
  dlq: { eyebrow: 'Enterprise Runtime', title: 'Dead Letter Queue', subtitle: 'Recover failed transactions without losing artifacts or timeline evidence.' },
  monitor: { eyebrow: 'Enterprise Runtime', title: 'Transaction Monitor', subtitle: 'Live queue posture across waiting, processing, retry, DLQ and completed work.' },
  objects: { eyebrow: 'Enterprise Runtime', title: 'Canonical Business Objects', subtitle: 'Shared object vocabulary for mappings, rules and resolver targets.' },
  resolvers: { eyebrow: 'Enterprise Runtime', title: 'Resolver Engine', subtitle: 'Resolve customers, products, warehouses, orders and printers through cache/OData/REST.' },
  transforms: { eyebrow: 'Enterprise Runtime', title: 'Transformation Library', subtitle: 'Reusable transforms for mappings and operational data shaping.' },
  rules: { eyebrow: 'Enterprise Runtime', title: 'Business Rules Engine', subtitle: 'Configurable IF/SWITCH/SET/STOP/FAIL rules for runtime decisions.' },
};

const runtimeQueryKeys = ['runtime-queue', 'runtime-dlq', 'runtime-monitor', 'runtime-objects', 'runtime-resolvers', 'runtime-transforms', 'runtime-rules', 'runtime-cache'];

function parseObject(value: string, label: string): Record<string, unknown> {
  const parsed = JSON.parse(value || '{}') as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error(`${label} must be a JSON object.`);
  return parsed as Record<string, unknown>;
}

function queueTone(status: QueueStatus) {
  if (status === 'completed') return 'ok';
  if (status === 'failed' || status === 'dlq') return 'error';
  if (status === 'retry_waiting') return 'retry_waiting';
  if (status === 'processing') return 'processing';
  if (status === 'cancelled') return 'cancelled';
  return 'pending';
}

export function EnterpriseRuntimePage({ view }: { view: RuntimeView }) {
  const queryClient = useQueryClient();
  const [result, setResult] = useState<unknown>(null);
  const install = useMutation({
    mutationFn: enterpriseRuntimeApi.installPresets,
    onSuccess: (data) => {
      setResult(data);
      runtimeQueryKeys.forEach((key) => queryClient.invalidateQueries({ queryKey: [key] }));
    },
  });
  const meta = titles[view];

  return (
    <div className="page-stack enterprise-runtime-page">
      <section className="page-header enterprise-hero">
        <span className="eyebrow">{meta.eyebrow}</span>
        <h1>{meta.title}</h1>
        <p>{meta.subtitle}</p>
        <div className="hero-meta">
          <button className="primary-button" onClick={() => install.mutate()} disabled={install.isPending}>Install enterprise presets</button>
          <span className="microcopy">Queue · DLQ · Resolvers · Rules · Cache</span>
        </div>
        {install.error instanceof Error && <div className="error-state compact">{install.error.message}</div>}
      </section>

      {view === 'queue' && <QueuePanel onResult={setResult} />}
      {view === 'dlq' && <DlqPanel onResult={setResult} />}
      {view === 'monitor' && <MonitorPanel />}
      {view === 'objects' && <ObjectsPanel />}
      {view === 'resolvers' && <ResolversPanel onResult={setResult} />}
      {view === 'transforms' && <TransformsPanel onResult={setResult} />}
      {view === 'rules' && <RulesPanel onResult={setResult} />}

      {result !== null && <JsonBlock title="Runtime result" value={(result as Record<string, unknown>) ?? {}} searchable={false} />}
    </div>
  );
}

function QueuePanel({ onResult }: { onResult: (value: unknown) => void }) {
  const queryClient = useQueryClient();
  const queue = useQuery({ queryKey: ['runtime-queue'], queryFn: enterpriseRuntimeApi.queue });
  const [form, setForm] = useState({ business_object: 'SalesOrder', operation: 'ship', priority: '50', payload_json: asJson({ order_id: 'SO-1001', warehouse_id: 'MAIN' }) });
  const [formError, setFormError] = useState<string | null>(null);
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['runtime-queue'] });
    queryClient.invalidateQueries({ queryKey: ['runtime-monitor'] });
  };
  const create = useMutation({ mutationFn: enterpriseRuntimeApi.createQueue, onSuccess: (data) => { onResult(data); refresh(); } });
  const processing = useMutation({ mutationFn: enterpriseRuntimeApi.markProcessing, onSuccess: (data) => { onResult(data); refresh(); } });
  const dlq = useMutation({ mutationFn: (id: string) => enterpriseRuntimeApi.moveToDlq(id, 'Manual operator escalation'), onSuccess: (data) => { onResult(data); refresh(); queryClient.invalidateQueries({ queryKey: ['runtime-dlq'] }); } });

  if (queue.isLoading) return <LoadingState label="Loading queue" />;
  if (queue.error) return <ErrorState error={queue.error} />;

  function submit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    try {
      create.mutate({ business_object: form.business_object, operation: form.operation, priority: Number(form.priority) || 100, payload_json: parseObject(form.payload_json, 'Payload') });
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Payload JSON is invalid.');
    }
  }

  const rows = queue.data ?? [];
  const actionError = create.error ?? processing.error ?? dlq.error;

  return (
    <section className="runtime-grid">
      <form className="panel stack-form runtime-control-card" onSubmit={submit}>
        <span className="eyebrow">Manual enqueue</span>
        <h2>Create queue message</h2>
        <label className="field-label">Business object<input value={form.business_object} onChange={(event) => setForm({ ...form, business_object: event.target.value })} /></label>
        <label className="field-label">Operation<input value={form.operation} onChange={(event) => setForm({ ...form, operation: event.target.value })} /></label>
        <label className="field-label">Priority<input value={form.priority} onChange={(event) => setForm({ ...form, priority: event.target.value })} /></label>
        <label className="field-label">Payload JSON<textarea value={form.payload_json} onChange={(event) => setForm({ ...form, payload_json: event.target.value })} /></label>
        {formError && <div className="error-state compact">{formError}</div>}
        {actionError instanceof Error && <div className="error-state compact">{actionError.message}</div>}
        <button className="primary-button" disabled={create.isPending}>Create message</button>
      </form>

      <section className="table-panel runtime-table-panel">
        <div className="panel-toolbar"><h2>Queue messages</h2><span className="microcopy">{rows.length} total</span></div>
        {rows.length === 0 ? <EmptyState title="Queue is empty" detail="Create a message manually or send data through Integration Bus." /> : <QueueTable rows={rows} onProcessing={(id) => processing.mutate(id)} onDlq={(id) => dlq.mutate(id)} pending={processing.isPending || dlq.isPending} />}
      </section>
    </section>
  );
}

function QueueTable({ rows, onProcessing, onDlq, pending }: { rows: QueueMessage[]; onProcessing: (id: string) => void; onDlq: (id: string) => void; pending: boolean }) {
  return (
    <table>
      <thead><tr><th>Object</th><th>Status</th><th>Attempts</th><th>Timeline</th><th>Actions</th></tr></thead>
      <tbody>
        {rows.map((item) => (
          <tr key={item.id}>
            <td><strong>{item.business_object}</strong><small>{item.operation} · priority {item.priority}</small></td>
            <td><StatusBadge status={queueTone(item.status)} label={item.status} /></td>
            <td>{item.attempts}/{item.max_attempts}</td>
            <td>{item.timeline_link ? <Link className="primary-link" to={item.timeline_link}>Timeline</Link> : '—'}</td>
            <td><div className="action-row"><button className="ghost-button" disabled={pending} onClick={() => onProcessing(item.id)}>Processing</button><button className="ghost-button danger" disabled={pending} onClick={() => onDlq(item.id)}>Move DLQ</button></div></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function DlqPanel({ onResult }: { onResult: (value: unknown) => void }) {
  const queryClient = useQueryClient();
  const dlq = useQuery({ queryKey: ['runtime-dlq'], queryFn: enterpriseRuntimeApi.dlq });
  const retry = useMutation({ mutationFn: enterpriseRuntimeApi.retryDlq, onSuccess: (data) => { onResult(data); queryClient.invalidateQueries({ queryKey: ['runtime-dlq'] }); queryClient.invalidateQueries({ queryKey: ['runtime-queue'] }); queryClient.invalidateQueries({ queryKey: ['runtime-monitor'] }); } });
  const archive = useMutation({ mutationFn: enterpriseRuntimeApi.archiveDlq, onSuccess: (data) => { onResult(data); queryClient.invalidateQueries({ queryKey: ['runtime-dlq'] }); queryClient.invalidateQueries({ queryKey: ['runtime-monitor'] }); } });
  if (dlq.isLoading) return <LoadingState label="Loading DLQ" />;
  if (dlq.error) return <ErrorState error={dlq.error} />;
  const rows = dlq.data ?? [];
  const actionError = retry.error ?? archive.error;
  return (
    <section className="table-panel runtime-table-panel">
      <div className="panel-toolbar"><h2>Dead letters</h2><span className="microcopy">{rows.length} active</span></div>
      {actionError instanceof Error && <div className="error-state compact">{actionError.message}</div>}
      {rows.length === 0 ? <EmptyState title="DLQ is empty" detail="Failed messages moved to dead letter queue will appear here with recovery actions." /> : (
        <table>
          <thead><tr><th>Object</th><th>Reason</th><th>Timeline</th><th>Actions</th></tr></thead>
          <tbody>{rows.map((item) => <tr key={item.id}><td><strong>{item.business_object}</strong><small>{item.operation}</small></td><td>{item.reason}</td><td>{item.timeline_link ? <Link className="primary-link" to={item.timeline_link}>Timeline</Link> : '—'}</td><td><div className="action-row"><button className="ghost-button" disabled={retry.isPending} onClick={() => retry.mutate(item.id)}>Retry / Restore</button><button className="ghost-button danger" disabled={archive.isPending} onClick={() => archive.mutate(item.id)}>Archive</button></div></td></tr>)}</tbody>
        </table>
      )}
    </section>
  );
}

function MonitorPanel() {
  const monitor = useQuery({ queryKey: ['runtime-monitor'], queryFn: enterpriseRuntimeApi.monitor, refetchInterval: 10000 });
  if (monitor.isLoading) return <LoadingState label="Loading transaction monitor" />;
  if (monitor.error) return <ErrorState error={monitor.error} />;
  const entries = Object.entries(monitor.data ?? {});
  return <section className="metric-grid runtime-metrics">{entries.map(([key, value]) => <article className={`metric-card ${key === 'dlq' || key === 'failed' ? 'bad' : key === 'retry_waiting' ? 'warn' : 'info'}`} key={key}><span>{key}</span><strong>{value}</strong></article>)}</section>;
}

function ObjectsPanel() {
  const objects = useQuery({ queryKey: ['runtime-objects'], queryFn: enterpriseRuntimeApi.canonicalObjects });
  if (objects.isLoading) return <LoadingState label="Loading business objects" />;
  if (objects.error) return <ErrorState error={objects.error} />;
  const rows = objects.data ?? [];
  if (rows.length === 0) return <EmptyState title="No canonical objects" detail="Install enterprise presets to add Customer, Product, SalesOrder, Shipment, PrintJob and other canonical objects." />;
  return <section className="card-grid runtime-card-grid">{rows.map((item) => <article className="panel runtime-card" key={item.id}><span className="eyebrow">Canonical</span><h2>{item.name}</h2><p>{item.description}</p><JsonBlock title="Schema" value={item.schema_json} searchable={false} /></article>)}</section>;
}

function ResolversPanel({ onResult }: { onResult: (value: unknown) => void }) {
  const resolvers = useQuery({ queryKey: ['runtime-resolvers'], queryFn: enterpriseRuntimeApi.resolvers });
  const [payload, setPayload] = useState(asJson({ warehouse_id: 'MAIN' }));
  const [formError, setFormError] = useState<string | null>(null);
  const resolve = useMutation({ mutationFn: ({ id, input }: { id: string; input: Record<string, unknown> }) => enterpriseRuntimeApi.resolve(id, input), onSuccess: onResult });
  if (resolvers.isLoading) return <LoadingState label="Loading resolvers" />;
  if (resolvers.error) return <ErrorState error={resolvers.error} />;
  const rows = resolvers.data ?? [];
  function run(id: string) {
    setFormError(null);
    try { resolve.mutate({ id, input: parseObject(payload, 'Resolve input') }); }
    catch (error) { setFormError(error instanceof Error ? error.message : 'Resolve input is invalid.'); }
  }
  return (
    <section className="runtime-grid">
      <section className="panel stack-form runtime-control-card"><span className="eyebrow">Resolver input</span><h2>Resolve input</h2><textarea value={payload} onChange={(event) => setPayload(event.target.value)} />{formError && <div className="error-state compact">{formError}</div>}{resolve.error instanceof Error && <div className="error-state compact">{resolve.error.message}</div>}</section>
      {rows.length === 0 ? <EmptyState title="No resolvers" detail="Install enterprise presets to add ResolveCustomer, ResolveProduct, ResolveWarehouse and other resolvers." /> : <section className="card-grid runtime-card-grid">{rows.map((item) => <article className="panel runtime-card" key={item.id}><span className="eyebrow">{item.resolver_type}</span><h2>{item.name}</h2><p>{item.business_object}</p><button className="primary-button" disabled={resolve.isPending} onClick={() => run(item.id)}>Resolve</button><JsonBlock title="Config" value={item.config_json} searchable={false} /></article>)}</section>}
    </section>
  );
}

function TransformsPanel({ onResult }: { onResult: (value: unknown) => void }) {
  const transforms = useQuery({ queryKey: ['runtime-transforms'], queryFn: enterpriseRuntimeApi.transforms });
  const [value, setValue] = useState('  hello OMH  ');
  const apply = useMutation({ mutationFn: (name: string) => enterpriseRuntimeApi.applyTransform({ name, value, params: { old: 'OMH', new: 'Enterprise Runtime', separator: ' ' } }), onSuccess: onResult });
  if (transforms.isLoading) return <LoadingState label="Loading transforms" />;
  if (transforms.error) return <ErrorState error={transforms.error} />;
  return (
    <section className="page-stack">
      <section className="panel runtime-control-card"><label className="field-label">Input<input value={value} onChange={(event) => setValue(event.target.value)} /></label>{apply.error instanceof Error && <div className="error-state compact">{apply.error.message}</div>}</section>
      <section className="card-grid runtime-card-grid">{(transforms.data ?? []).map((item) => <article className="panel runtime-card" key={item.name}><h2>{item.name}</h2><p>{item.description}</p><button className="ghost-button" disabled={apply.isPending} onClick={() => apply.mutate(item.name)}>Apply</button></article>)}</section>
    </section>
  );
}

function RulesPanel({ onResult }: { onResult: (value: unknown) => void }) {
  const rules = useQuery({ queryKey: ['runtime-rules'], queryFn: enterpriseRuntimeApi.businessRules });
  const [payload, setPayload] = useState(asJson({ status: 'cancelled', order_id: 'SO-1001' }));
  const [formError, setFormError] = useState<string | null>(null);
  const runRule = useMutation({ mutationFn: ({ id, input }: { id: string; input: Record<string, unknown> }) => enterpriseRuntimeApi.runBusinessRule(id, input), onSuccess: onResult });
  if (rules.isLoading) return <LoadingState label="Loading business rules" />;
  if (rules.error) return <ErrorState error={rules.error} />;
  const rows = rules.data ?? [];
  function run(id: string) {
    setFormError(null);
    try { runRule.mutate({ id, input: parseObject(payload, 'Rule payload') }); }
    catch (error) { setFormError(error instanceof Error ? error.message : 'Rule payload is invalid.'); }
  }
  return (
    <section className="runtime-grid">
      <section className="panel stack-form runtime-control-card"><span className="eyebrow">Rule payload</span><h2>Run rule</h2><textarea value={payload} onChange={(event) => setPayload(event.target.value)} />{formError && <div className="error-state compact">{formError}</div>}{runRule.error instanceof Error && <div className="error-state compact">{runRule.error.message}</div>}</section>
      {rows.length === 0 ? <EmptyState title="No business rules" detail="Install enterprise presets to add the default operational rules." /> : <section className="card-grid runtime-card-grid">{rows.map((item) => <article className="panel runtime-card" key={item.id}><span className="eyebrow">{item.status}</span><h2>{item.name}</h2><p>{item.business_object ?? 'Any object'} · {item.operation ?? 'Any operation'}</p><button className="primary-button" disabled={runRule.isPending} onClick={() => run(item.id)}>Run rule</button><JsonBlock title="Rules" value={item.rules_json} searchable={false} /></article>)}</section>}
    </section>
  );
}

export const IntegrationQueuePage = () => <EnterpriseRuntimePage view="queue" />;
export const DeadLetterQueuePage = () => <EnterpriseRuntimePage view="dlq" />;
export const TransactionMonitorPage = () => <EnterpriseRuntimePage view="monitor" />;
export const BusinessObjectsPage = () => <EnterpriseRuntimePage view="objects" />;
export const ResolversPage = () => <EnterpriseRuntimePage view="resolvers" />;
export const TransformationLibraryPage = () => <EnterpriseRuntimePage view="transforms" />;
export const BusinessRulesPage = () => <EnterpriseRuntimePage view="rules" />;
