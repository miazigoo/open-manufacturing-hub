import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { connectorsApi } from '../api/connectors';
import { integrationFlowsApi } from '../api/integrationFlows';
import { resolversApi } from '../api/resolvers';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

type BuilderStep = Record<string, unknown> & { id: string; type: string; name?: string; save_as?: string };
type BuilderJson = { version: number; input: Record<string, unknown>; variables: Array<Record<string, unknown>>; steps: BuilderStep[] };

const sampleRequest = { inn: '1234567890', product_code: 'ABC-123', pool_id: 'POOL-001', codes: ['code1', 'code2'] };

function defaultBuilder(slug = 'onec-pool-to-dnp'): BuilderJson {
  return {
    version: 1,
    input: { endpoint_slug: slug, input_mode: 'json', response_mode: 'proxy_response' },
    variables: [
      { name: 'inn', source: 'request.body.inn' },
      { name: 'product_code', source: 'request.body.product_code' },
      { name: 'pool_id', source: 'request.body.pool_id' },
    ],
    steps: [
      { id: 'read_inn', type: 'read_variable', name: 'Read INN', path: 'request.body.inn', save_as: 'inn' },
      { id: 'resolve_customer', type: 'resolve_object', name: 'Resolve Customer', resolver: 'resolve_customer', object_type: 'Customer', input: { inn: 'request.body.inn' }, save_as: 'customer', inject: { customer_uuid: 'customer.uuid' }, required: true, use_cache: true },
      { id: 'resolve_product', type: 'resolve_object', name: 'Resolve Product', resolver: 'resolve_product', object_type: 'Product', input: { article: 'request.body.product_code' }, save_as: 'product', inject: { product_uuid: 'product.uuid' }, required: true, use_cache: true },
      { id: 'build_payload', type: 'build_json', name: 'Build target JSON', save_as: 'target_payload', template: { pool_id: '{{request.body.pool_id}}', customer_uuid: '{{customer.uuid}}', product_uuid: '{{product.uuid}}', codes: '{{request.body.codes}}' } },
      { id: 'send_to_target', type: 'call_endpoint', name: 'Send to endpoint', connector: 'DNP Service', method: 'POST', path: '/api/marking/pools', body: '{{target_payload}}' },
      { id: 'return_response', type: 'return_response', name: 'Return response', body: '{{response}}' },
    ],
  };
}

function safeBuilder(value: unknown, slug: string): BuilderJson {
  if (value && typeof value === 'object' && Array.isArray((value as BuilderJson).steps)) return value as BuilderJson;
  return defaultBuilder(slug);
}

function parseJsonObject(value: string, label: string): Record<string, unknown> {
  const parsed = JSON.parse(value || '{}') as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error(`${label} must be a JSON object`);
  return parsed as Record<string, unknown>;
}

function firstFilter(step: BuilderStep) {
  const filters = Array.isArray(step.filter_builder) ? step.filter_builder as Array<Record<string, unknown>> : [];
  return filters[0] ?? { field: '', operator: 'eq', value: '' };
}

export function VisualFlowBuilderPage() {
  const { flowId } = useParams();
  const queryClient = useQueryClient();
  const flow = useQuery({ queryKey: ['integration-flow', flowId], queryFn: async () => (await integrationFlowsApi.list()).find((item) => item.id === flowId) ?? null, enabled: Boolean(flowId) });
  const connectors = useQuery({ queryKey: ['connectors'], queryFn: connectorsApi.list });
  const resolvers = useQuery({ queryKey: ['resolvers-v2'], queryFn: () => resolversApi.list() });
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [builderText, setBuilderText] = useState<string | null>(null);
  const [sampleText, setSampleText] = useState(asJson(sampleRequest));
  const builder = useMemo(() => safeBuilder(builderText ? JSON.parse(builderText) : flow.data?.builder_json, flow.data?.slug ?? 'flow'), [builderText, flow.data]);
  const selectedStep = builder.steps.find((step) => step.id === selectedStepId) ?? builder.steps[0];
  const preview = useMutation({ mutationFn: (payload: { builder_json: Record<string, unknown>; sample_request: Record<string, unknown> }) => integrationFlowsApi.previewBuilder(payload) });
  const save = useMutation({ mutationFn: (payload: BuilderJson) => integrationFlowsApi.saveBuilder(flowId!, { builder_json: payload, sample_request: parseJsonObject(sampleText, 'Sample request') }), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['integration-flow', flowId] }) });
  const compile = useMutation({ mutationFn: () => integrationFlowsApi.compileBuilder(flowId!), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['integration-flow', flowId] }) });

  if (flow.isLoading || connectors.isLoading) return <LoadingState label="Loading visual flow builder" />;
  if (flow.error) return <ErrorState error={flow.error} />;
  if (!flow.data) return <ErrorState error={new Error('Integration flow not found')} />;

  function setBuilder(next: BuilderJson) {
    setBuilderText(asJson(next));
  }

  function updateStep(id: string, patch: Partial<BuilderStep>) {
    setBuilder({ ...builder, steps: builder.steps.map((step) => (step.id === id ? { ...step, ...patch } : step)) });
  }

  function moveStep(id: string, direction: -1 | 1) {
    const index = builder.steps.findIndex((step) => step.id === id);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= builder.steps.length) return;
    const steps = [...builder.steps];
    [steps[index], steps[target]] = [steps[target], steps[index]];
    setBuilder({ ...builder, steps });
  }

  function duplicateStep(step: BuilderStep) {
    const copy = { ...step, id: `${step.id}_copy`, name: `${step.name ?? step.id} Copy` };
    setBuilder({ ...builder, steps: [...builder.steps, copy] });
    setSelectedStepId(copy.id);
  }

  function deleteStep(id: string) {
    setBuilder({ ...builder, steps: builder.steps.filter((step) => step.id !== id) });
    setSelectedStepId(null);
  }

  function addStep(type: string) {
    const id = `${type}_${builder.steps.length + 1}`;
    const base: BuilderStep = type === 'odata_query'
      ? { id, type, name: 'New OData query', connection: '1C ERP', resource: '', filter_builder: [{ field: '', operator: 'eq', value: '{{request.body.value}}' }], top: 1, save_as: 'lookup_result', required: true }
      : type === 'apply_transforms'
        ? { id, type, name: 'Normalize fields', chains: [{ source: 'request.body.inn', target: 'variables.normalized_inn', transforms: [{ name: 'trim' }, { name: 'remove_spaces' }] }] }
      : type === 'evaluate_rules'
        ? { id, type, name: 'Business rule', mode: 'first_match', rules: [{ name: 'DNP pool', if: { path: 'request.body.pool_type', operator: 'eq', value: 'DNP' }, then: [{ action: 'set_target_system', value: 'DNP Service' }] }] }
      : type === 'resolve_object'
        ? { id, type, name: 'Resolve Customer', resolver: 'resolve_customer', object_type: 'Customer', input: { inn: 'request.body.inn' }, save_as: 'customer', inject: { customer_uuid: 'customer.uuid' }, required: true, use_cache: true }
      : type === 'build_json'
        ? { id, type, name: 'Build JSON', save_as: 'target_payload', template: { id: '{{request.body.id}}' } }
        : type === 'call_endpoint'
          ? { id, type, name: 'Call endpoint', connector: 'DNP Service', method: 'POST', path: '/', body: '{{target_payload}}' }
          : { id, type, name: 'Read variable', path: 'request.body.value', save_as: 'value' };
    setBuilder({ ...builder, steps: [...builder.steps, base] });
    setSelectedStepId(id);
  }

  function runPreview() {
    setError(null);
    try { preview.mutate({ builder_json: builder as unknown as Record<string, unknown>, sample_request: parseJsonObject(sampleText, 'Sample request') }); }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'Invalid preview input'); }
  }

  function runSave() {
    setError(null);
    try { save.mutate(builder); }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'Invalid builder JSON'); }
  }

  const connectorNames = (connectors.data ?? []).map((connector) => connector.name);
  const resolverOptions = resolvers.data ?? [];

  return (
    <div className="page-stack visual-builder-page">
      <section className="page-header visual-builder-hero">
        <span className="eyebrow">Visual Integration Flow Builder</span>
        <h1>{flow.data.name}</h1>
        <p>Configure the flow in integration terms: read request fields, query OData, build JSON, call the target endpoint and return a response.</p>
        <div className="hero-meta"><StatusBadge status={flow.data.compiled_workflow_id ? 'ok' : 'warning'} label={flow.data.compiled_workflow_id ? 'compiled' : 'not compiled'} /><span className="microcopy">{flow.data.endpoint_url}</span></div>
      </section>

      <section className="visual-builder-grid">
        <aside className="panel builder-rail">
          <div className="panel-toolbar"><h2>Pipeline</h2><span className="microcopy">{builder.steps.length} steps</span></div>
          <div className="builder-step-list">
            {builder.steps.map((step, index) => <button key={step.id} className={`builder-step-card ${selectedStep?.id === step.id ? 'active' : ''}`} onClick={() => setSelectedStepId(step.id)}><span className="step-index">{String(index + 1).padStart(2, '0')}</span><strong>{step.name ?? step.id}</strong><small>{step.type} · {String(step.save_as ?? step.id)}</small></button>)}
          </div>
          <div className="builder-add-grid"><button className="ghost-button" onClick={() => addStep('read_variable')}>Read field</button><button className="ghost-button" onClick={() => addStep('apply_transforms')}>Transform</button><button className="ghost-button" onClick={() => addStep('evaluate_rules')}>Rule</button><button className="ghost-button" onClick={() => addStep('odata_query')}>OData</button><button className="ghost-button" onClick={() => addStep('resolve_object')}>Resolve</button><button className="ghost-button" onClick={() => addStep('build_json')}>JSON</button><button className="ghost-button" onClick={() => addStep('call_endpoint')}>Endpoint</button></div>
        </aside>

        <main className="builder-main stack-form">
          <section className="panel builder-input-panel">
            <div className="panel-toolbar"><div><span className="eyebrow">Input</span><h2>Inbound request contract</h2></div><Link className="primary-link" to="/integration-flows">Back to flows</Link></div>
            <div className="metadata-grid compact-grid no-margin"><label className="field-label">Endpoint slug<input value={String(builder.input.endpoint_slug ?? flow.data.slug)} onChange={(event) => setBuilder({ ...builder, input: { ...builder.input, endpoint_slug: event.target.value } })} /></label><label className="field-label">Input mode<select value={String(builder.input.input_mode ?? 'json')} onChange={(event) => setBuilder({ ...builder, input: { ...builder.input, input_mode: event.target.value } })}><option value="json">JSON</option><option value="xml">XML</option><option value="raw_text">Raw text</option></select></label><label className="field-label">Response<select value={String(builder.input.response_mode ?? 'proxy_response')} onChange={(event) => setBuilder({ ...builder, input: { ...builder.input, response_mode: event.target.value } })}><option value="proxy_response">Proxy response</option><option value="accepted_event">Accepted event</option><option value="sync_response">Sync response</option></select></label></div>
            <label className="field-label">Sample request<textarea value={sampleText} onChange={(event) => setSampleText(event.target.value)} /></label>
          </section>

          {selectedStep && <section className="panel step-editor-panel">
            <div className="panel-toolbar"><div><span className="eyebrow">Step Editor</span><h2>{selectedStep.name ?? selectedStep.id}</h2></div><div className="toolbar-actions"><button className="ghost-button" onClick={() => moveStep(selectedStep.id, -1)}>Up</button><button className="ghost-button" onClick={() => moveStep(selectedStep.id, 1)}>Down</button><button className="ghost-button" onClick={() => duplicateStep(selectedStep)}>Duplicate</button><button className="ghost-button danger" onClick={() => deleteStep(selectedStep.id)}>Delete</button></div></div>
            <div className="metadata-grid compact-grid no-margin"><label className="field-label">Step id<input value={selectedStep.id} onChange={(event) => updateStep(selectedStep.id, { id: event.target.value })} /></label><label className="field-label">Display name<input value={String(selectedStep.name ?? '')} onChange={(event) => updateStep(selectedStep.id, { name: event.target.value })} /></label><label className="field-label">Type<select value={selectedStep.type} onChange={(event) => updateStep(selectedStep.id, { type: event.target.value })}><option value="read_variable">Read variable</option><option value="apply_transforms">Transform Field</option><option value="evaluate_rules">Business Rule</option><option value="odata_query">OData query</option><option value="resolve_object">Resolve Business Object</option><option value="build_json">Build JSON</option><option value="condition">Condition</option><option value="call_endpoint">Call endpoint</option><option value="return_response">Return response</option></select></label></div>
            {selectedStep.type === 'read_variable' && <ReadVariableEditor step={selectedStep} update={updateStep} />}
            {selectedStep.type === 'apply_transforms' && <TransformStepEditor step={selectedStep} update={updateStep} />}
            {selectedStep.type === 'evaluate_rules' && <BusinessRuleStepEditor step={selectedStep} update={updateStep} />}
            {selectedStep.type === 'odata_query' && <ODataStepEditor step={selectedStep} update={updateStep} connectorNames={connectorNames} />}
            {selectedStep.type === 'resolve_object' && <ResolveObjectEditor step={selectedStep} update={updateStep} resolverOptions={resolverOptions} />}
            {selectedStep.type === 'build_json' && <BuildJsonEditor step={selectedStep} update={updateStep} />}
            {selectedStep.type === 'call_endpoint' && <CallEndpointEditor step={selectedStep} update={updateStep} connectorNames={connectorNames} />}
            {selectedStep.type === 'return_response' && <label className="field-label">Response body<input value={String(selectedStep.body ?? '{{response}}')} onChange={(event) => updateStep(selectedStep.id, { body: event.target.value })} /></label>}
          </section>}
        </main>

        <aside className="panel builder-preview-panel">
          <div className="panel-toolbar"><div><span className="eyebrow">Preview & Compile</span><h2>Dry-run without code</h2></div></div>
          <div className="action-row wrap-actions"><button className="primary-button" onClick={runPreview} disabled={preview.isPending}>Preview</button><button className="ghost-button" onClick={runSave} disabled={save.isPending}>Save builder</button><button className="primary-button" onClick={() => compile.mutate()} disabled={compile.isPending}>Compile workflow</button>{flow.data.workflow_id && <Link className="primary-link" to={`/pipelines/${flow.data.workflow_id}/edit`}>Open workflow</Link>}</div>
          {(error || preview.error || save.error || compile.error) && <div className="error-state compact">{error ?? (preview.error as Error | null)?.message ?? (save.error as Error | null)?.message ?? (compile.error as Error | null)?.message}</div>}
          {preview.data && <div className="builder-preview-steps">{preview.data.steps.map((step) => <article key={step.id} className={`preview-step ${step.status}`}><strong>{step.id}</strong><span>{step.type}</span><StatusBadge status={step.status === 'success' ? 'ok' : 'failed'} label={step.status} compact />{step.error && <small>{String(step.error.message ?? step.error.code)}</small>}</article>)}</div>}
          {preview.data && <JsonBlock title="Final JSON preview" value={preview.data.final_payload_preview ?? {}} searchable={false} />}
          {preview.data && <JsonBlock title="Target request" value={preview.data.target_request_preview ?? {}} searchable={false} />}
          {compile.data && <JsonBlock title="Compiled workflow" value={compile.data} searchable={false} />}
          <JsonBlock title="Advanced builder JSON" value={builder} />
        </aside>
      </section>
    </div>
  );

  function ReadVariableEditor({ step, update }: { step: BuilderStep; update: (id: string, patch: Partial<BuilderStep>) => void }) {
    return <div className="metadata-grid compact-grid no-margin"><label className="field-label">Save as<input value={String(step.save_as ?? '')} onChange={(event) => update(step.id, { save_as: event.target.value })} /></label><label className="field-label">Source path<input value={String(step.path ?? '')} onChange={(event) => update(step.id, { path: event.target.value })} /></label><span className="success-note">Example<span>request.body.inn</span></span></div>;
  }

  function ODataStepEditor({ step, update, connectorNames }: { step: BuilderStep; update: (id: string, patch: Partial<BuilderStep>) => void; connectorNames: string[] }) {
    const filter = firstFilter(step);
    const setFilter = (patch: Record<string, unknown>) => update(step.id, { filter_builder: [{ ...filter, ...patch }] });
    return <div className="stack-form"><div className="metadata-grid compact-grid no-margin"><label className="field-label">Connection<input list="connector-names" value={String(step.connection ?? '')} onChange={(event) => update(step.id, { connection: event.target.value })} /><datalist id="connector-names">{connectorNames.map((name) => <option key={name} value={name} />)}</datalist></label><label className="field-label">Resource<input value={String(step.resource ?? '')} onChange={(event) => update(step.id, { resource: event.target.value })} /></label><label className="field-label">Save as<input value={String(step.save_as ?? '')} onChange={(event) => update(step.id, { save_as: event.target.value })} /></label></div><div className="metadata-grid compact-grid no-margin"><label className="field-label">Field<input value={String(filter.field ?? '')} onChange={(event) => setFilter({ field: event.target.value })} /></label><label className="field-label">Operator<select value={String(filter.operator ?? 'eq')} onChange={(event) => setFilter({ operator: event.target.value })}><option value="eq">eq</option><option value="ne">ne</option><option value="contains">contains</option><option value="startswith">startswith</option><option value="endswith">endswith</option><option value="gt">gt</option><option value="lt">lt</option><option value="ge">ge</option><option value="le">le</option></select></label><label className="field-label">Value source<input value={String(filter.value ?? '')} onChange={(event) => setFilter({ value: event.target.value })} /></label></div><div className="metadata-grid compact-grid no-margin"><label className="field-label">$select<input value={Array.isArray(step.select) ? step.select.join(',') : String(step.select ?? '')} onChange={(event) => update(step.id, { select: event.target.value.split(',').map((item) => item.trim()).filter(Boolean) })} /></label><label className="field-label">$top<input value={String(step.top ?? 1)} onChange={(event) => update(step.id, { top: Number(event.target.value) || 1 })} /></label><label className="check-row"><input type="checkbox" checked={step.required !== false} onChange={(event) => update(step.id, { required: event.target.checked })} /> Required result</label></div></div>;
  }

  function TransformStepEditor({ step, update }: { step: BuilderStep; update: (id: string, patch: Partial<BuilderStep>) => void }) {
    return <div className="stack-form"><label className="field-label">Transform chains JSON<textarea value={asJson(step.chains ?? [])} onChange={(event) => { try { const parsed = JSON.parse(event.target.value) as unknown; if (!Array.isArray(parsed)) throw new Error('Chains must be an array'); update(step.id, { chains: parsed }); setError(null); } catch (caught) { setError(caught instanceof Error ? caught.message : 'Invalid chains JSON'); } }} /></label><div className="success-note">Example<span>{'request.body.inn -> trim -> remove_spaces -> variables.normalized_inn'}</span></div></div>;
  }

  function BusinessRuleStepEditor({ step, update }: { step: BuilderStep; update: (id: string, patch: Partial<BuilderStep>) => void }) {
    return <div className="stack-form"><div className="metadata-grid compact-grid no-margin"><label className="field-label">Saved rule set<input value={String(step.rule_set ?? '')} onChange={(event) => update(step.id, { rule_set: event.target.value })} /></label><label className="field-label">Mode<select value={String(step.mode ?? 'first_match')} onChange={(event) => update(step.id, { mode: event.target.value })}><option value="first_match">first match</option><option value="all_matches">all matches</option></select></label></div><label className="field-label">Inline rules JSON<textarea value={asJson(step.rules ?? [])} onChange={(event) => { try { const parsed = JSON.parse(event.target.value) as unknown; if (!Array.isArray(parsed)) throw new Error('Rules must be an array'); update(step.id, { rules: parsed }); setError(null); } catch (caught) { setError(caught instanceof Error ? caught.message : 'Invalid rules JSON'); } }} /></label><div className="success-note">Action examples<span>set_variable, set_target_system, fail, stop, mark_retry</span></div></div>;
  }

  function ResolveObjectEditor({ step, update, resolverOptions }: { step: BuilderStep; update: (id: string, patch: Partial<BuilderStep>) => void; resolverOptions: Array<{ resolver_code: string; name: string; object_type: string }> }) {
    const inputJson = asJson(step.input ?? {});
    const injectJson = asJson(step.inject ?? {});
    return <div className="stack-form"><div className="metadata-grid compact-grid no-margin"><label className="field-label">Resolver<input list="resolver-codes" value={String(step.resolver_code ?? step.resolver ?? '')} onChange={(event) => update(step.id, { resolver: event.target.value, resolver_code: event.target.value })} /><datalist id="resolver-codes">{resolverOptions.map((item) => <option key={item.resolver_code} value={item.resolver_code}>{item.name}</option>)}</datalist></label><label className="field-label">Object type<input value={String(step.object_type ?? resolverOptions.find((item) => item.resolver_code === step.resolver)?.object_type ?? '')} onChange={(event) => update(step.id, { object_type: event.target.value })} /></label><label className="field-label">Save as<input value={String(step.save_as ?? '')} onChange={(event) => update(step.id, { save_as: event.target.value })} /></label></div><div className="metadata-grid compact-grid no-margin"><label className="check-row"><input type="checkbox" checked={step.required !== false} onChange={(event) => update(step.id, { required: event.target.checked })} /> Required result</label><label className="check-row"><input type="checkbox" checked={step.use_cache !== false} onChange={(event) => update(step.id, { use_cache: event.target.checked })} /> Use cache</label><span className="success-note">Example<span>{'inn -> request.body.inn'}</span></span></div><label className="field-label">Input mapping JSON<textarea value={inputJson} onChange={(event) => { try { update(step.id, { input: parseJsonObject(event.target.value, 'Resolver input') }); setError(null); } catch (caught) { setError(caught instanceof Error ? caught.message : 'Invalid resolver input'); } }} /></label><label className="field-label">Payload injection JSON<textarea value={injectJson} onChange={(event) => { try { update(step.id, { inject: parseJsonObject(event.target.value, 'Resolver injection') }); setError(null); } catch (caught) { setError(caught instanceof Error ? caught.message : 'Invalid resolver injection'); } }} /></label></div>;
  }

  function BuildJsonEditor({ step, update }: { step: BuilderStep; update: (id: string, patch: Partial<BuilderStep>) => void }) {
    const template = asJson(step.template ?? {});
    return <div className="stack-form"><label className="field-label">Save as<input value={String(step.save_as ?? 'target_payload')} onChange={(event) => update(step.id, { save_as: event.target.value })} /></label><label className="field-label">JSON template<textarea value={template} onChange={(event) => { try { update(step.id, { template: parseJsonObject(event.target.value, 'JSON template') }); setError(null); } catch (caught) { setError(caught instanceof Error ? caught.message : 'Invalid JSON template'); } }} /></label><div className="success-note">Full placeholders preserve source type<span>{'"codes": "{{request.body.codes}}"'}</span></div></div>;
  }

  function CallEndpointEditor({ step, update, connectorNames }: { step: BuilderStep; update: (id: string, patch: Partial<BuilderStep>) => void; connectorNames: string[] }) {
    return <div className="metadata-grid compact-grid no-margin"><label className="field-label">Connector<input list="target-connector-names" value={String(step.connector ?? '')} onChange={(event) => update(step.id, { connector: event.target.value })} /><datalist id="target-connector-names">{connectorNames.map((name) => <option key={name} value={name} />)}</datalist></label><label className="field-label">Method<select value={String(step.method ?? 'POST')} onChange={(event) => update(step.id, { method: event.target.value })}><option value="POST">POST</option><option value="PUT">PUT</option><option value="PATCH">PATCH</option></select></label><label className="field-label">Path<input value={String(step.path ?? '')} onChange={(event) => update(step.id, { path: event.target.value })} /></label><label className="field-label full-span">Body<input value={String(step.body ?? '{{target_payload}}')} onChange={(event) => update(step.id, { body: event.target.value })} /></label></div>;
  }
}
