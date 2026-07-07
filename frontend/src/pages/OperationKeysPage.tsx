import { FormEvent, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { operationTemplatesApi, type OperationTemplate } from '../api/operationTemplates';
import { CodeEditor } from '../components/CodeEditor';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

const sampleRequest = { operation: 'lookup_order_products', Number: '260666/6938' };

function slugify(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 120);
}

function parseObject(value: string, label: string): Record<string, unknown> {
  const parsed = JSON.parse(value || '{}') as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error(`${label} must be a JSON object`);
  return parsed as Record<string, unknown>;
}

export function OperationKeysPage() {
  const queryClient = useQueryClient();
  const keys = useQuery({ queryKey: ['operation-templates'], queryFn: operationTemplatesApi.list });
  const [form, setForm] = useState({ name: 'Lookup order products', operation: 'lookup_order_products', description: 'External system asks OMH to find a production order and related rows.', example_request_json: asJson(sampleRequest) });
  const [operationTouched, setOperationTouched] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const create = useMutation({
    mutationFn: () => operationTemplatesApi.create({
      name: form.name,
      operation: form.operation,
      operation_code: form.operation,
      system_type: 'operation_key',
      direction: 'inbound',
      input_mode: 'json',
      output_mode: 'json',
      description: form.description,
      enabled: true,
      request_template_json: { operation: form.operation },
      example_request_json: parseObject(form.example_request_json, 'Example request'),
    }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['operation-templates'] }),
  });
  const remove = useMutation({ mutationFn: operationTemplatesApi.delete, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['operation-templates'] }) });

  if (keys.isLoading) return <LoadingState label="Loading operation keys" />;
  if (keys.error) return <ErrorState error={keys.error} />;

  function submit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    try { create.mutate(); } catch (error) { setFormError(error instanceof Error ? error.message : 'Invalid operation key form'); }
  }

  const rows = (keys.data ?? []).filter((item) => item.system_type === 'operation_key' || item.direction === 'inbound');
  return (
    <div className="page-stack enterprise-runtime-page">
      <section className="page-header enterprise-hero">
        <span className="eyebrow">Operation Keys</span>
        <h1>Inbound operation keys</h1>
        <p>Ключ говорит платформе, какой flow запускать для входящего JSON. Это не название внешней системы: DNP, сайт или WMS можно описать в description.</p>
        <div className="hero-meta"><span className="microcopy">{rows.length} keys</span></div>
      </section>
      <section className="runtime-grid">
        <form className="panel stack-form runtime-control-card" onSubmit={submit}>
          <span className="eyebrow">Add key</span>
          <h2>Новый ключ операции</h2>
          <label className="field-label">Name<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value, operation: operationTouched ? form.operation : slugify(event.target.value) })} /></label>
          <label className="field-label">Operation key<input value={form.operation} onChange={(event) => { setOperationTouched(true); setForm({ ...form, operation: slugify(event.target.value) }); }} /></label>
          <label className="field-label">Description<input value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
          <label className="field-label">Example JSON<CodeEditor value={form.example_request_json} onChange={(value) => setForm({ ...form, example_request_json: value })} language="json" minRows={6} /></label>
          <button className="primary-button" disabled={create.isPending}>Save operation key</button>
          {formError && <div className="error-state compact">{formError}</div>}
          {create.error instanceof Error && <div className="error-state compact">{create.error.message}</div>}
        </form>
        {rows.length === 0 ? <EmptyState title="No operation keys" detail="Create the first key, then use it when saving a draft flow from OData Master." /> : <section className="card-grid runtime-card-grid">{rows.map((item) => <OperationKeyCard key={item.id} item={item} onDelete={() => remove.mutate(item.id)} busy={remove.isPending} />)}</section>}
      </section>
    </div>
  );
}

function OperationKeyCard({ item, onDelete, busy }: { item: OperationTemplate; onDelete: () => void; busy: boolean }) {
  return (
    <article className="panel runtime-card">
      <div className="panel-toolbar">
        <div><span className="eyebrow">{item.direction}</span><h2>{item.name}</h2></div>
        <StatusBadge status={item.enabled ? 'ok' : 'warning'} label={item.enabled ? 'enabled' : 'disabled'} />
      </div>
      <p>{item.description}</p>
      <div className="metadata-grid compact-grid">
        <span>Operation<strong>{item.operation}</strong></span>
        <span>Input<strong>{item.input_mode ?? 'json'}</strong></span>
      </div>
      <JsonBlock title="Example request" value={item.example_request_json ?? { operation: item.operation }} searchable={false} />
      <button className="ghost-button danger" onClick={onDelete} disabled={busy}>Delete</button>
    </article>
  );
}
