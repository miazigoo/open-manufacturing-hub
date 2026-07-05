import { FormEvent, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
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
  const [filters, setFilters] = useState({ status: '' as QueueStatus | '', sort: 'priority' });
  const queue = useQuery({ queryKey: ['runtime-queue', filters], queryFn: () => enterpriseRuntimeApi.queue(filters) });
  const [form, setForm] = useState({ business_object: 'SalesOrder', operation: 'ship', priority: '50', payload_json: asJson({ order_id: 'SO-1001', warehouse_id: 'MAIN' }) });
  const [formError, setFormError] = useState<string | null>(null);
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['runtime-queue'] });
    queryClient.invalidateQueries({ queryKey: ['runtime-monitor'] });
  };
  const create = useMutation({ mutationFn: enterpriseRuntimeApi.createQueue, onSuccess: (data) => { onResult(data); refresh(); } });
  const processOnce = useMutation({ mutationFn: enterpriseRuntimeApi.processOnce, onSuccess: (data) => { onResult(data); refresh(); queryClient.invalidateQueries({ queryKey: ['runtime-dlq'] }); } });
  const processBatch = useMutation({ mutationFn: () => enterpriseRuntimeApi.processBatch(10), onSuccess: (data) => { onResult(data); refresh(); queryClient.invalidateQueries({ queryKey: ['runtime-dlq'] }); } });
  const retryNow = useMutation({ mutationFn: enterpriseRuntimeApi.retryNow, onSuccess: (data) => { onResult(data); refresh(); } });
  const cancel = useMutation({ mutationFn: enterpriseRuntimeApi.cancelQueue, onSuccess: (data) => { onResult(data); refresh(); } });
  const unlock = useMutation({ mutationFn: enterpriseRuntimeApi.unlockQueue, onSuccess: (data) => { onResult(data); refresh(); } });
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
  const actionError = create.error ?? processOnce.error ?? processBatch.error ?? retryNow.error ?? cancel.error ?? unlock.error ?? dlq.error;

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
        <div className="panel-toolbar"><h2>Queue messages</h2><div className="toolbar-actions"><button className="primary-button" onClick={() => processOnce.mutate()} disabled={processOnce.isPending}>Process once</button><button className="ghost-button" onClick={() => processBatch.mutate()} disabled={processBatch.isPending}>Process batch</button><span className="microcopy">{rows.length} total</span></div></div>
        <div className="filter-bar"><label className="field-label">Status<select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value as QueueStatus | '' })}><option value="">All</option><option value="waiting">waiting</option><option value="processing">processing</option><option value="retry_waiting">retry waiting</option><option value="dlq">dlq</option><option value="failed">failed</option><option value="completed">completed</option><option value="cancelled">cancelled</option></select></label><label className="field-label">Sort<select value={filters.sort} onChange={(event) => setFilters({ ...filters, sort: event.target.value })}><option value="priority">priority</option><option value="created_at">created</option><option value="next_retry_at">next retry</option><option value="attempts">attempts</option></select></label></div>
        {rows.length === 0 ? <EmptyState title="Queue is empty" detail="Incoming integration requests will appear here after endpoints receive data." actions={<><Link className="primary-button" to="/test-console">Send test request</Link><Link className="ghost-button" to="/docs/core/start/concepts">Learn about Queue</Link></>} /> : <QueueTable rows={rows} onRetry={(id) => retryNow.mutate(id)} onCancel={(id) => cancel.mutate(id)} onUnlock={(id) => unlock.mutate(id)} onDlq={(id) => dlq.mutate(id)} pending={retryNow.isPending || cancel.isPending || unlock.isPending || dlq.isPending} />}
      </section>
    </section>
  );
}

function QueueTable({ rows, onRetry, onCancel, onUnlock, onDlq, pending }: { rows: QueueMessage[]; onRetry: (id: string) => void; onCancel: (id: string) => void; onUnlock: (id: string) => void; onDlq: (id: string) => void; pending: boolean }) {
  return (
    <table>
      <thead><tr><th>Status</th><th>Object</th><th>Source → Target</th><th>Attempts</th><th>Next Retry</th><th>Error</th><th>Actions</th></tr></thead>
      <tbody>
        {rows.map((item) => (
          <tr key={item.id}>
            <td><StatusBadge status={queueTone(item.status)} label={item.status} /></td>
            <td><strong>{item.business_object}</strong><small>{item.operation} · {item.business_key ?? item.id}</small></td>
            <td>{item.source_system ?? '—'} → {item.target_system ?? '—'}</td>
            <td>{item.attempts}/{item.max_attempts}</td>
            <td>{item.next_retry_at ? new Date(item.next_retry_at).toLocaleString() : '—'}</td>
            <td>{item.last_error_message ?? item.last_error ?? '—'}<small>{item.current_step ?? ''}</small></td>
            <td><div className="action-row wrap-actions"><Link className="primary-link" to={`/runtime/queue/${item.id}`}>Details</Link>{item.timeline_link && <Link className="primary-link" to={item.timeline_link}>Timeline</Link>}<button className="ghost-button" disabled={pending} onClick={() => onRetry(item.id)}>Retry now</button><button className="ghost-button" disabled={pending} onClick={() => onUnlock(item.id)}>Unlock</button><button className="ghost-button" disabled={pending} onClick={() => onCancel(item.id)}>Cancel</button><button className="ghost-button danger" disabled={pending} onClick={() => onDlq(item.id)}>Move DLQ</button></div></td>
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
  const forceComplete = useMutation({ mutationFn: enterpriseRuntimeApi.forceCompleteDlq, onSuccess: (data) => { onResult(data); queryClient.invalidateQueries({ queryKey: ['runtime-dlq'] }); queryClient.invalidateQueries({ queryKey: ['runtime-queue'] }); queryClient.invalidateQueries({ queryKey: ['runtime-monitor'] }); } });
  const archive = useMutation({ mutationFn: enterpriseRuntimeApi.archiveDlq, onSuccess: (data) => { onResult(data); queryClient.invalidateQueries({ queryKey: ['runtime-dlq'] }); queryClient.invalidateQueries({ queryKey: ['runtime-monitor'] }); } });
  if (dlq.isLoading) return <LoadingState label="Loading DLQ" />;
  if (dlq.error) return <ErrorState error={dlq.error} />;
  const rows = dlq.data ?? [];
  const actionError = retry.error ?? forceComplete.error ?? archive.error;
  return (
    <section className="table-panel runtime-table-panel">
      <div className="panel-toolbar"><h2>Dead letters</h2><span className="microcopy">{rows.length} active</span></div>
      {actionError instanceof Error && <div className="error-state compact">{actionError.message}</div>}
      {rows.length === 0 ? <EmptyState title="DLQ is empty" detail="Failed messages moved to dead letter queue will appear here with recovery actions." actions={<Link className="ghost-button" to="/docs/core/start/concepts">Learn recovery flow</Link>} /> : (
        <table>
          <thead><tr><th>Object</th><th>Reason</th><th>Attempts</th><th>Timeline</th><th>Actions</th></tr></thead>
          <tbody>{rows.map((item) => <tr key={item.id}><td><strong>{item.business_object}</strong><small>{item.operation}</small></td><td>{item.reason}<small>{item.last_error}</small></td><td>{item.attempts}</td><td>{item.timeline_link ? <Link className="primary-link" to={item.timeline_link}>Timeline</Link> : '—'}</td><td><div className="action-row wrap-actions"><button className="ghost-button" disabled={retry.isPending} onClick={() => retry.mutate(item.id)}>Retry / Restore</button><button className="ghost-button" disabled={forceComplete.isPending} onClick={() => forceComplete.mutate(item.id)}>Force complete</button><button className="ghost-button danger" disabled={archive.isPending} onClick={() => archive.mutate(item.id)}>Archive</button></div></td></tr>)}</tbody>
        </table>
      )}
    </section>
  );
}

function MonitorPanel() {
  const monitor = useQuery({ queryKey: ['runtime-monitor'], queryFn: enterpriseRuntimeApi.monitor, refetchInterval: 10000 });
  const queue = useQuery({ queryKey: ['runtime-monitor-queue'], queryFn: () => enterpriseRuntimeApi.queue({ sort: 'created_at' }), refetchInterval: 10000 });
  if (monitor.isLoading) return <LoadingState label="Loading transaction monitor" />;
  if (monitor.error) return <ErrorState error={monitor.error} />;
  const entries = Object.entries(monitor.data ?? {});
  return <div className="page-stack"><section className="metric-grid runtime-metrics">{entries.map(([key, value]) => <article className={`metric-card ${key === 'dlq' || key === 'failed' ? 'bad' : key === 'retry_waiting' ? 'warn' : 'info'}`} key={key}><span>{key}</span><strong>{value}</strong></article>)}</section><section className="table-panel runtime-table-panel"><div className="panel-toolbar"><h2>Transaction monitor</h2><span className="microcopy">Queue-first runtime</span></div>{queue.data && <QueueTable rows={queue.data.slice(0, 20)} onRetry={() => undefined} onCancel={() => undefined} onUnlock={() => undefined} onDlq={() => undefined} pending={true} />}</section></div>;
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


export function QueueItemDetailsPage() {
  const { queueId } = useParams();
  const item = useQuery({ queryKey: ['runtime-queue-item', queueId], queryFn: () => enterpriseRuntimeApi.queueItem(queueId!), enabled: Boolean(queueId) });
  if (item.isLoading) return <LoadingState label="Loading queue item" />;
  if (item.error) return <ErrorState error={item.error} />;
  if (!item.data) return <ErrorState error={new Error('Queue item not found')} />;
  return (
    <div className="page-stack">
      <section className="page-header enterprise-hero"><span className="eyebrow">Queue Item</span><h1>{item.data.business_object}</h1><p>{item.data.operation} · {item.data.business_key ?? item.data.id}</p><div className="hero-meta"><StatusBadge status={queueTone(item.data.status)} label={item.data.status} /><span className="microcopy">Attempts {item.data.attempts}/{item.data.max_attempts}</span>{item.data.timeline_link && <Link className="primary-link" to={item.data.timeline_link}>Open timeline</Link>}</div></section>
      <section className="metadata-grid"><span>Source<strong>{item.data.source_system ?? '—'}</strong></span><span>Target<strong>{item.data.target_system ?? '—'}</strong></span><span>Next retry<strong>{item.data.next_retry_at ?? '—'}</strong></span><span>Locked by<strong>{item.data.locked_by ?? '—'}</strong></span><span>Current step<strong>{item.data.current_step ?? '—'}</strong></span><span>Last error<strong>{item.data.last_error_message ?? item.data.last_error ?? '—'}</strong></span></section>
      <section className="flow-output-grid"><JsonBlock title="Current payload" value={item.data.payload_json} searchable /><JsonBlock title="Original payload" value={item.data.original_payload_json} searchable /></section>
    </div>
  );
}
