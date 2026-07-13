import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { connectorsApi } from '../api/connectors';
import { configVersionsApi } from '../api/configVersions';
import { integrationFlowsApi } from '../api/integrationFlows';
import { resolversApi } from '../api/resolvers';
import { uiApi } from '../api/ui';
import { ErrorState } from '../components/ErrorState';
import { CodeEditor } from '../components/CodeEditor';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { XmlPathPicker } from '../components/xml/XmlPathPicker';
import { XmlResponseBuilder } from '../components/xml/XmlResponseBuilder';
import { VersionHistoryPanel } from '../features/configVersions';

type BuilderStep = Record<string, unknown> & { id: string; type: string; name?: string; save_as?: string };
type BuilderJson = { version: number; input: Record<string, unknown>; variables: Array<Record<string, unknown>>; steps: BuilderStep[] };
type ODataOption = { id: string; label: string; base_url: string; enabled: boolean };

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
      { id: 'send_to_target', type: 'call_endpoint', name: 'Send to endpoint', connector: 'DNP Service', method: 'POST', path: '/api/marking/pools', headers: { 'Content-Type': 'application/json' }, body: '{{target_payload}}', save_response_as: 'target_response', mock_response_json: { success: true, external_id: 'preview-id' } },
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

function sampleForBuilder(inputMode: unknown, value: string): Record<string, unknown> {
  if (String(inputMode) === 'xml') return { xml: value };
  if (String(inputMode) === 'raw_text') return { text: value };
  return parseJsonObject(value, 'Sample request');
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
  const builderOptions = useQuery({ queryKey: ['ui-flow-builder-options'], queryFn: uiApi.flowBuilderOptions });
  const resolvers = useQuery({ queryKey: ['resolvers-v2'], queryFn: () => resolversApi.list() });
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [builderText, setBuilderText] = useState<string | null>(null);
  const [sampleText, setSampleText] = useState(asJson(sampleRequest));
  const builder = useMemo(() => safeBuilder(builderText ? JSON.parse(builderText) : flow.data?.builder_json, flow.data?.slug ?? 'flow'), [builderText, flow.data]);
  const selectedStep = builder.steps.find((step) => step.id === selectedStepId) ?? builder.steps[0];
  const preview = useMutation({ mutationFn: (payload: { builder_json: Record<string, unknown>; sample_request: Record<string, unknown> }) => integrationFlowsApi.previewBuilder(payload) });
  const save = useMutation({
    mutationFn: (payload: BuilderJson) => configVersionsApi.createDraft('integration_flow', flowId!, {
      config_json: {
        name: flow.data!.name,
        description: flow.data!.description,
        enabled: flow.data!.enabled,
        matcher_group_json: flow.data!.matcher_group_json,
        action_json: flow.data!.action_json,
        response_config_json: flow.data!.response_config_json,
        builder_json: payload,
        test_payload_json: String(payload.input.input_mode ?? 'json') === 'json' ? parseJsonObject(sampleText, 'Sample request') : null,
        test_payload_text: String(payload.input.input_mode ?? 'json') === 'json' ? flow.data!.test_payload_text : sampleText,
      },
      comment: 'Draft saved from visual flow builder',
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['integration-flow', flowId] });
      queryClient.invalidateQueries({ queryKey: ['integration-flows'] });
      queryClient.invalidateQueries({ queryKey: ['config-versions', 'integration_flow', flowId] });
    },
  });
  const compile = useMutation({ mutationFn: () => integrationFlowsApi.compileBuilder(flowId!), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['integration-flow', flowId] }) });

  if (flow.isLoading || connectors.isLoading || builderOptions.isLoading) return <LoadingState label="Loading visual flow builder" />;
  if (flow.error || builderOptions.error) return <ErrorState error={(flow.error ?? builderOptions.error) as Error} />;
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
    const defaultOData = odataOptions.find((connection) => connection.enabled) ?? odataOptions[0];
    const base: BuilderStep = type === 'odata_query'
      ? { id, type, name: 'New OData query', connection: defaultOData?.label ?? 'OData ERP', connection_id: defaultOData?.id ?? '', resource: '', filter_builder: [{ field: '', operator: 'eq', value: '{{request.body.value}}' }], top: 1, save_as: 'lookup_result', required: true }
      : type === 'apply_transforms'
        ? { id, type, name: 'Normalize fields', chains: [{ source: 'request.body.inn', target: 'variables.normalized_inn', transforms: [{ name: 'trim' }, { name: 'remove_spaces' }] }] }
      : type === 'evaluate_rules'
        ? { id, type, name: 'Business rule', mode: 'first_match', rules: [{ name: 'DNP pool', if: { path: 'request.body.pool_type', operator: 'eq', value: 'DNP' }, then: [{ action: 'set_target_system', value: 'DNP Service' }] }] }
      : type === 'xml_extract'
        ? { id, type, name: 'Extract XML fields', source: 'request.xml', fields: [{ name: 'number', path: '/Request/Number', required: true, mode: 'first' }] }
      : type === 'raw_xml_forward'
        ? { id, type, name: 'Raw XML forward', source: 'request.xml', method: 'POST', path: '/hs/omh/receive' }
      : type === 'resolve_object'
        ? { id, type, name: 'Resolve Customer', resolver: 'resolve_customer', object_type: 'Customer', input: { inn: 'request.body.inn' }, save_as: 'customer', inject: { customer_uuid: 'customer.uuid' }, required: true, use_cache: true }
      : type === 'build_json'
        ? { id, type, name: 'Build JSON', save_as: 'target_payload', template: { id: '{{request.body.id}}' } }
        : type === 'marking_code_pool_export'
          ? {
              id,
              type,
              name: 'CHZ pool delivery',
              order_number_path: 'request.body.order_number',
              full_codes_base64_path: 'request.body.full_codes_base64',
              source_document_id_path: 'request.body.source_document_id',
              source_document_name_path: 'request.body.source_document_name',
              allow_overwrite: true,
              save_as: 'marking_pool_export',
              metadata_json: { created_from: 'visual_flow_builder' },
            }
        : type === 'build_xml_response'
          ? { id, type, name: 'Build XML response', response_body_type: 'xml', status_code: 200, headers: { 'Content-Type': 'application/xml' }, body_template: '<Response><Success>true</Success><Number>{{number}}</Number></Response>' }
        : type === 'call_endpoint'
          ? { id, type, name: 'Call endpoint', connector: 'DNP Service', method: 'POST', path: '/', headers: { 'Content-Type': 'application/json' }, body: '{{target_payload}}', save_response_as: 'target_response', mock_response_json: { success: true, id: 'preview-id' } }
          : { id, type, name: 'Read variable', path: 'request.body.value', save_as: 'value' };
    setBuilder({ ...builder, steps: [...builder.steps, base] });
    setSelectedStepId(id);
  }

  function runPreview() {
    setError(null);
    try { preview.mutate({ builder_json: builder as unknown as Record<string, unknown>, sample_request: sampleForBuilder(builder.input.input_mode, sampleText) }); }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'Invalid preview input'); }
  }

  function runSave() {
    setError(null);
    try { save.mutate(builder); }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'Invalid builder JSON'); }
  }

  const connectorNames = (connectors.data ?? []).map((connector) => connector.name);
  const odataOptions: ODataOption[] = (builderOptions.data?.odata_connections ?? []).map((item) => ({ id: item.id, label: item.label, base_url: String(item.meta.base_url ?? ''), enabled: item.meta.enabled !== false }));
  const resolverOptions = resolvers.data ?? [];

  return (
    <div className="page-stack visual-builder-page">
      <section className="page-header visual-builder-hero">
        <span className="eyebrow">Visual Integration Flow Builder</span>
        <h1>{flow.data.name}</h1>
        <p>Configure the flow in integration terms: read request fields, query OData, build JSON, call the target endpoint and return a response.</p>
        <div className="hero-meta"><StatusBadge status={flow.data.compiled_workflow_id ? 'ok' : 'warning'} label={flow.data.compiled_workflow_id ? 'compiled' : 'not compiled'} /><span className="microcopy">{flow.data.endpoint_url}</span></div>
      </section>
      <VersionHistoryPanel objectType="integration_flow" objectId={flow.data.id} compact onChanged={() => {
        queryClient.invalidateQueries({ queryKey: ['integration-flow', flowId] });
        queryClient.invalidateQueries({ queryKey: ['integration-flows'] });
      }} />

      <section className="visual-builder-grid">
        <aside className="panel builder-rail">
          <div className="panel-toolbar"><h2>Pipeline</h2><span className="microcopy">{builder.steps.length} steps</span></div>
          <div className="builder-step-list">
            {builder.steps.map((step, index) => <button key={step.id} className={`builder-step-card ${selectedStep?.id === step.id ? 'active' : ''}`} onClick={() => setSelectedStepId(step.id)}><span className="step-index">{String(index + 1).padStart(2, '0')}</span><strong>{step.name ?? step.id}</strong><small>{step.type} · {String(step.save_as ?? step.id)}</small></button>)}
          </div>
          <div className="builder-add-grid"><button className="ghost-button" onClick={() => addStep('read_variable')}>Read field</button><button className="ghost-button" onClick={() => addStep('xml_extract')}>Extract XML</button><button className="ghost-button" onClick={() => addStep('raw_xml_forward')}>Raw XML</button><button className="ghost-button" onClick={() => addStep('apply_transforms')}>Transform</button><button className="ghost-button" onClick={() => addStep('evaluate_rules')}>Rule</button><button className="ghost-button" onClick={() => addStep('odata_query')}>OData</button><button className="ghost-button" onClick={() => addStep('resolve_object')}>Resolve</button><button className="ghost-button" onClick={() => addStep('build_json')}>JSON</button><button className="ghost-button" onClick={() => addStep('marking_code_pool_export')}>CHZ pool</button><button className="ghost-button" onClick={() => addStep('build_xml_response')}>XML response</button><button className="ghost-button" onClick={() => addStep('call_endpoint')}>Endpoint</button></div>
        </aside>

        <main className="builder-main stack-form">
          <section className="panel builder-input-panel">
            <div className="panel-toolbar"><div><span className="eyebrow">Input</span><h2>Inbound request contract</h2></div><Link className="primary-link" to="/integration-flows">Back to flows</Link></div>
            <div className="metadata-grid compact-grid no-margin"><label className="field-label">Endpoint slug<input value={String(builder.input.endpoint_slug ?? flow.data.slug)} onChange={(event) => setBuilder({ ...builder, input: { ...builder.input, endpoint_slug: event.target.value } })} /></label><label className="field-label">Input mode<select value={String(builder.input.input_mode ?? 'json')} onChange={(event) => setBuilder({ ...builder, input: { ...builder.input, input_mode: event.target.value } })}><option value="json">JSON</option><option value="xml">XML</option><option value="raw_text">Raw text</option></select></label><label className="field-label">Response<select value={String(builder.input.response_mode ?? 'proxy_response')} onChange={(event) => setBuilder({ ...builder, input: { ...builder.input, response_mode: event.target.value } })}><option value="proxy_response">Proxy response</option><option value="accepted_event">Accepted event</option><option value="sync_response">Sync response</option></select></label></div>
            <label className="field-label">Sample request<CodeEditor value={sampleText} onChange={setSampleText} language={String(builder.input.input_mode ?? 'json') === 'xml' ? 'xml' : String(builder.input.input_mode ?? 'json') === 'raw_text' ? 'text' : 'json'} minRows={8} /></label>
            {String(builder.input.input_mode ?? 'json') === 'xml' && <XmlPathPicker xml={sampleText} compact onUseField={(field) => selectedStep && selectedStep.type === 'xml_extract' && updateStep(selectedStep.id, { fields: [...(Array.isArray(selectedStep.fields) ? selectedStep.fields as Array<Record<string, unknown>> : []), { name: field.path.split('/').filter(Boolean).pop()?.replace(/\[\d+\]$/, '') || 'xml_field', path: field.path, required: false, mode: field.repeated ? 'all' : 'first' }] })} />}
          </section>

          {selectedStep && <section className="panel step-editor-panel">
            <div className="panel-toolbar"><div><span className="eyebrow">Step Editor</span><h2>{selectedStep.name ?? selectedStep.id}</h2></div><div className="toolbar-actions"><button className="ghost-button" onClick={() => moveStep(selectedStep.id, -1)}>Up</button><button className="ghost-button" onClick={() => moveStep(selectedStep.id, 1)}>Down</button><button className="ghost-button" onClick={() => duplicateStep(selectedStep)}>Duplicate</button><button className="ghost-button danger" onClick={() => deleteStep(selectedStep.id)}>Delete</button></div></div>
            <div className="metadata-grid compact-grid no-margin"><label className="field-label">Step id<input value={selectedStep.id} onChange={(event) => updateStep(selectedStep.id, { id: event.target.value })} /></label><label className="field-label">Display name<input value={String(selectedStep.name ?? '')} onChange={(event) => updateStep(selectedStep.id, { name: event.target.value })} /></label><label className="field-label">Type<select value={selectedStep.type} onChange={(event) => updateStep(selectedStep.id, { type: event.target.value })}><option value="read_variable">Read variable</option><option value="xml_extract">Extract XML</option><option value="raw_xml_forward">Raw XML forward</option><option value="apply_transforms">Transform Field</option><option value="evaluate_rules">Business Rule</option><option value="odata_query">OData query</option><option value="resolve_object">Resolve Business Object</option><option value="build_json">Build JSON</option><option value="marking_code_pool_export">CHZ pool delivery</option><option value="build_xml_response">Build XML response</option><option value="condition">Condition</option><option value="call_endpoint">Call endpoint</option><option value="return_response">Return response</option></select></label></div>
            {selectedStep.type === 'read_variable' && <ReadVariableEditor step={selectedStep} update={updateStep} />}
            {selectedStep.type === 'apply_transforms' && <TransformStepEditor step={selectedStep} update={updateStep} />}
            {selectedStep.type === 'evaluate_rules' && <BusinessRuleStepEditor step={selectedStep} update={updateStep} />}
            {selectedStep.type === 'xml_extract' && <XmlExtractStepEditor step={selectedStep} update={updateStep} sampleText={sampleText} />}
            {selectedStep.type === 'raw_xml_forward' && <RawXmlForwardEditor step={selectedStep} update={updateStep} />}
            {selectedStep.type === 'odata_query' && <ODataStepEditor step={selectedStep} update={updateStep} odataOptions={odataOptions} steps={builder.steps} />}
            {selectedStep.type === 'resolve_object' && <ResolveObjectEditor step={selectedStep} update={updateStep} resolverOptions={resolverOptions} />}
            {selectedStep.type === 'build_json' && <BuildJsonEditor step={selectedStep} update={updateStep} />}
            {selectedStep.type === 'marking_code_pool_export' && <MarkingCodePoolExportEditor step={selectedStep} update={updateStep} setSampleText={setSampleText} />}
            {selectedStep.type === 'build_xml_response' && <BuildXmlResponseEditor step={selectedStep} update={updateStep} />}
            {selectedStep.type === 'call_endpoint' && <CallEndpointEditor step={selectedStep} update={updateStep} connectorNames={connectorNames} />}
            {selectedStep.type === 'return_response' && <label className="field-label">Response body<input value={String(selectedStep.body ?? '{{response}}')} onChange={(event) => updateStep(selectedStep.id, { body: event.target.value })} /></label>}
          </section>}
        </main>

        <aside className="panel builder-preview-panel">
          <div className="panel-toolbar"><div><span className="eyebrow">Preview & Compile</span><h2>Dry-run without code</h2></div></div>
          <div className="action-row wrap-actions"><button className="primary-button" onClick={runPreview} disabled={preview.isPending}>Preview</button><button className="ghost-button" onClick={runSave} disabled={save.isPending}>Save Draft</button><Link className="ghost-button" to={`/config-history/integration_flow/${flow.data.id}`}>Release control</Link><button className="primary-button" onClick={() => compile.mutate()} disabled={compile.isPending}>Compile workflow</button>{flow.data.workflow_id && <Link className="primary-link" to={`/pipelines/${flow.data.workflow_id}/edit`}>Open workflow</Link>}</div>
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

  function XmlExtractStepEditor({ step, update, sampleText }: { step: BuilderStep; update: (id: string, patch: Partial<BuilderStep>) => void; sampleText: string }) {
    const fieldsJson = asJson(step.fields ?? []);
    return <div className="stack-form"><div className="builder-help-card"><strong>XML → variables</strong><span>Этот шаг парсит входящий XML, сохраняет `xml_parse_input`, `xml_parse_tree`, `xml_extracted_fields` и создает переменные для следующих шагов: OData, API, XML response.</span></div><div className="metadata-grid compact-grid no-margin"><label className="field-label">Source<input value={String(step.source ?? 'request.xml')} onChange={(event) => update(step.id, { source: event.target.value })} /></label><span className="success-note">Common source<span>request.xml</span></span></div><XmlPathPicker xml={sampleText} compact onUseField={(field) => update(step.id, { fields: [...(Array.isArray(step.fields) ? step.fields as Array<Record<string, unknown>> : []), { name: field.path.split('/').filter(Boolean).pop()?.replace(/\[\d+\]$/, '') || 'xml_field', path: field.path, required: false, mode: field.repeated ? 'all' : 'first' }] })} /><label className="field-label">Fields JSON<CodeEditor value={fieldsJson} onChange={(value) => { try { const parsed = JSON.parse(value) as unknown; if (!Array.isArray(parsed)) throw new Error('Fields must be an array'); update(step.id, { fields: parsed }); setError(null); } catch (caught) { setError(caught instanceof Error ? caught.message : 'Invalid XML fields'); } }} language="json" minRows={7} /></label></div>;
  }

  function RawXmlForwardEditor({ step, update }: { step: BuilderStep; update: (id: string, patch: Partial<BuilderStep>) => void }) {
    return <div className="stack-form"><div className="builder-help-card"><strong>Raw XML forward</strong><span>Используйте, когда XML нельзя менять: OMH сохраняет hash до/после и кладет raw XML в Timeline. Это не парсинг, а режим “передать как пришло”.</span></div><div className="metadata-grid compact-grid no-margin"><label className="field-label">Source<input value={String(step.source ?? 'request.xml')} onChange={(event) => update(step.id, { source: event.target.value })} /></label><label className="field-label">Method<select value={String(step.method ?? 'POST')} onChange={(event) => update(step.id, { method: event.target.value })}><option value="POST">POST</option><option value="PUT">PUT</option></select></label><label className="field-label">Path<input value={String(step.path ?? '/hs/omh/receive')} onChange={(event) => update(step.id, { path: event.target.value })} /></label></div></div>;
  }

  function ODataStepEditor({ step, update, odataOptions, steps }: { step: BuilderStep; update: (id: string, patch: Partial<BuilderStep>) => void; odataOptions: ODataOption[]; steps: BuilderStep[] }) {
    const filters = Array.isArray(step.filter_builder) && step.filter_builder.length ? step.filter_builder as Array<Record<string, unknown>> : [firstFilter(step)];
    const selectedConnectionId = String(step.connection_id ?? odataOptions.find((item) => item.label === step.connection)?.id ?? '');
    const saveAs = String(step.save_as ?? step.id);
    const resultPath = `{{${saveAs}.Ref_Key}}`;
    const stepPath = `{{steps.${step.id}.first.Ref_Key}}`;
    const previousODataSteps = steps.slice(0, Math.max(steps.findIndex((item) => item.id === step.id), 0)).filter((item) => item.type === 'odata_query');
    const [linkSourceStepId, setLinkSourceStepId] = useState(previousODataSteps[0]?.id ?? '');
    const [linkField, setLinkField] = useState('Ref_Key');
    const [linkTarget, setLinkTarget] = useState<'resource' | 'filter'>('resource');
    const [linkFilterIndex, setLinkFilterIndex] = useState(0);
    const sourceStep = previousODataSteps.find((item) => item.id === linkSourceStepId);
    const sourceSaveAs = String(sourceStep?.save_as ?? sourceStep?.id ?? '');
    const sourcePlaceholder = sourceSaveAs ? `{{${sourceSaveAs}.${linkField}}}` : '';
    const updateFilter = (index: number, patch: Record<string, unknown>) => update(step.id, { filter_builder: filters.map((filter, filterIndex) => filterIndex === index ? { ...filter, ...patch } : filter) });
    const insertLinkedValue = () => {
      if (!sourcePlaceholder) return;
      if (linkTarget === 'resource') {
        update(step.id, { resource: `${String(step.resource ?? '')}${sourcePlaceholder}` });
        return;
      }
      const safeIndex = Math.min(Math.max(linkFilterIndex, 0), filters.length - 1);
      updateFilter(safeIndex, { value: sourcePlaceholder });
    };
    return <div className="stack-form">
      <div className="builder-help-card">
        <strong>Что станет переменной OData</strong>
        <span>`$select` controls which fields 1C returns. `Save as` stores the first row as <code>{saveAs}</code>. Дальше JSON Builder или следующий OData step может взять <code>{resultPath}</code>, <code>{stepPath}</code> или список строк <code>{`{{steps.${step.id}.items}}`}</code>. Чтобы один OData запрос стал фильтром для другого, вставьте этот placeholder в Value source.</span>
      </div>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">OData connection<select value={selectedConnectionId} onChange={(event) => { const selected = odataOptions.find((item) => item.id === event.target.value); update(step.id, { connection_id: event.target.value, connection: selected?.label ?? '' }); }} title="Named OData profile: ERP, УСП, WMS. Create it once, reuse it in every flow."><option value="">Select OData profile</option>{odataOptions.map((connection) => <option key={connection.id} value={connection.id}>{connection.label} · {connection.base_url}</option>)}</select></label>
        <label className="field-label">Resource<input value={String(step.resource ?? '')} onChange={(event) => update(step.id, { resource: event.target.value })} title="Exact resource from OData Master, for example Catalog_Контрагенты or Document_ЗаказКлиента." /></label>
        <label className="field-label">Save as<input value={saveAs} onChange={(event) => update(step.id, { save_as: event.target.value })} title="Variable name for the first OData row. Use it in JSON or next filters: {{contractor.Ref_Key}}." /></label>
      </div>
      <div className="builder-help-card">
        <strong>Связать с предыдущим OData step</strong>
        <span>Выберите шаг выше, поле результата и место вставки. Платформа вставит placeholder <code>{sourcePlaceholder || '{{previous.Ref_Key}}'}</code>, чтобы следующий resource или filter получил значение из предыдущего ответа 1C.</span>
      </div>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Source step<select value={linkSourceStepId} onChange={(event) => setLinkSourceStepId(event.target.value)} disabled={previousODataSteps.length === 0}><option value="">No previous OData step</option>{previousODataSteps.map((item) => <option key={item.id} value={item.id}>{item.name ?? item.id} · save as {String(item.save_as ?? item.id)}</option>)}</select></label>
        <label className="field-label">Field<select value={linkField} onChange={(event) => setLinkField(event.target.value)}><option value="Ref_Key">Ref_Key</option><option value="Number">Number</option><option value="Description">Description</option><option value="Номенклатура_Key">Номенклатура_Key</option><option value="GTIN">GTIN</option><option value="КодМаркировки">КодМаркировки</option></select></label>
        <label className="field-label">Insert into<select value={linkTarget} onChange={(event) => setLinkTarget(event.target.value as 'resource' | 'filter')}><option value="resource">Resource</option><option value="filter">Filter value</option></select></label>
        {linkTarget === 'filter' && <label className="field-label">Filter row<select value={String(linkFilterIndex)} onChange={(event) => setLinkFilterIndex(Number(event.target.value) || 0)}>{filters.map((filter, index) => <option key={index} value={index}>{index + 1}. {String(filter.field ?? 'field')}</option>)}</select></label>}
        <button type="button" className="ghost-button" onClick={insertLinkedValue} disabled={!sourcePlaceholder}>Insert selected value</button>
      </div>
      <div className="odata-filter-builder">
        <div className="panel-toolbar compact-toolbar"><h3>Filters / условия поиска</h3><button type="button" className="ghost-button" onClick={() => update(step.id, { filter_builder: [...filters, { field: '', operator: 'eq', value: '' }] })}>Add filter</button></div>
        {filters.map((filter, index) => (
          <div className="metadata-grid compact-grid no-margin" key={index}>
            <label className="field-label">Field<input value={String(filter.field ?? '')} onChange={(event) => updateFilter(index, { field: event.target.value })} title="OData field name. Check it in Explorer before using in production." /></label>
            <label className="field-label">Operator<select value={String(filter.operator ?? 'eq')} onChange={(event) => updateFilter(index, { operator: event.target.value })} title="All filter rows are joined with `and`."><option value="eq">eq</option><option value="ne">ne</option><option value="contains">contains</option><option value="startswith">startswith</option><option value="endswith">endswith</option><option value="gt">gt</option><option value="lt">lt</option><option value="ge">ge</option><option value="le">le</option></select></label>
            <label className="field-label">Value source<input value={String(filter.value ?? '')} onChange={(event) => updateFilter(index, { value: event.target.value })} title="Examples: {{request.body.inn}}, {{inn}}, {{contractor.Ref_Key}}, {{steps.get_contractor.first.Ref_Key}}." /></label>
            <button type="button" className="ghost-button danger" onClick={() => update(step.id, { filter_builder: filters.filter((_, filterIndex) => filterIndex !== index) })} disabled={filters.length === 1}>Remove</button>
          </div>
        ))}
      </div>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">$select<input value={Array.isArray(step.select) ? step.select.join(',') : String(step.select ?? '')} onChange={(event) => update(step.id, { select: event.target.value.split(',').map((item) => item.trim()).filter(Boolean) })} title="Comma-separated fields returned by 1C. Keep only fields used by JSON builder or next OData step." /></label>
        <label className="field-label">$top<input value={String(step.top ?? 1)} onChange={(event) => update(step.id, { top: Number(event.target.value) || 1 })} title="top=1 saves the first row as object. top>1 saves a list; use steps.<step>.items for the full list." /></label>
        <label className="field-label">$orderby<input value={String(step.orderby ?? '')} onChange={(event) => update(step.id, { orderby: event.target.value })} title="Optional deterministic ordering, e.g. Date desc before top=1." /></label>
        <label className="check-row"><input type="checkbox" checked={step.required !== false} onChange={(event) => update(step.id, { required: event.target.checked })} /> Required result / остановить flow, если строка не найдена</label>
      </div>
      <div className="hint-chip-row">
        {['{{request.body.inn}}', '{{inn}}', resultPath, stepPath, `{{steps.${step.id}.items}}`].map((hint) => <button key={hint} type="button" className="hint-chip" onClick={() => navigator.clipboard?.writeText(hint)} title="Click to copy placeholder">{hint}</button>)}
      </div>
      <div className="hint-chip-row">
        {['Ref_Key,Description,ИНН', 'Ref_Key,Description,Артикул', 'Ref_Key,Number,Date,Posted', 'Ref_Key,Склад_Key,Номенклатура_Key,Количество'].map((select) => <button key={select} type="button" className="hint-chip" onClick={() => update(step.id, { select: select.split(',') })} title="Use this $select preset">{select}</button>)}
      </div>
      <div className="action-row wrap-actions"><button type="button" className="ghost-button" onClick={runPreview} disabled={preview.isPending}>Preview OData query</button><Link className="primary-link" to="/odata-connections">Manage OData connections</Link><Link className="primary-link" to="/docs/onec/tools/odata-chaining-fields">OData chaining guide</Link></div>
    </div>;
  }

  function TransformStepEditor({ step, update }: { step: BuilderStep; update: (id: string, patch: Partial<BuilderStep>) => void }) {
    return <div className="stack-form"><label className="field-label">Transform chains JSON<CodeEditor value={asJson(step.chains ?? [])} onChange={(value) => { try { const parsed = JSON.parse(value) as unknown; if (!Array.isArray(parsed)) throw new Error('Chains must be an array'); update(step.id, { chains: parsed }); setError(null); } catch (caught) { setError(caught instanceof Error ? caught.message : 'Invalid chains JSON'); } }} language="json" minRows={8} /></label><div className="success-note">Example<span>{'request.body.inn -> trim -> remove_spaces -> variables.normalized_inn'}</span></div></div>;
  }

  function BusinessRuleStepEditor({ step, update }: { step: BuilderStep; update: (id: string, patch: Partial<BuilderStep>) => void }) {
    return <div className="stack-form"><div className="metadata-grid compact-grid no-margin"><label className="field-label">Saved rule set<input value={String(step.rule_set ?? '')} onChange={(event) => update(step.id, { rule_set: event.target.value })} /></label><label className="field-label">Mode<select value={String(step.mode ?? 'first_match')} onChange={(event) => update(step.id, { mode: event.target.value })}><option value="first_match">first match</option><option value="all_matches">all matches</option></select></label></div><label className="field-label">Inline rules JSON<CodeEditor value={asJson(step.rules ?? [])} onChange={(value) => { try { const parsed = JSON.parse(value) as unknown; if (!Array.isArray(parsed)) throw new Error('Rules must be an array'); update(step.id, { rules: parsed }); setError(null); } catch (caught) { setError(caught instanceof Error ? caught.message : 'Invalid rules JSON'); } }} language="json" minRows={9} /></label><div className="success-note">Action examples<span>set_variable, set_target_system, fail, stop, mark_retry</span></div></div>;
  }

  function ResolveObjectEditor({ step, update, resolverOptions }: { step: BuilderStep; update: (id: string, patch: Partial<BuilderStep>) => void; resolverOptions: Array<{ resolver_code: string; name: string; object_type: string }> }) {
    const inputJson = asJson(step.input ?? {});
    const injectJson = asJson(step.inject ?? {});
    return <div className="stack-form"><div className="metadata-grid compact-grid no-margin"><label className="field-label">Resolver<input list="resolver-codes" value={String(step.resolver_code ?? step.resolver ?? '')} onChange={(event) => update(step.id, { resolver: event.target.value, resolver_code: event.target.value })} /><datalist id="resolver-codes">{resolverOptions.map((item) => <option key={item.resolver_code} value={item.resolver_code}>{item.name}</option>)}</datalist></label><label className="field-label">Object type<input value={String(step.object_type ?? resolverOptions.find((item) => item.resolver_code === step.resolver)?.object_type ?? '')} onChange={(event) => update(step.id, { object_type: event.target.value })} /></label><label className="field-label">Save as<input value={String(step.save_as ?? '')} onChange={(event) => update(step.id, { save_as: event.target.value })} /></label></div><div className="metadata-grid compact-grid no-margin"><label className="check-row"><input type="checkbox" checked={step.required !== false} onChange={(event) => update(step.id, { required: event.target.checked })} /> Required result</label><label className="check-row"><input type="checkbox" checked={step.use_cache !== false} onChange={(event) => update(step.id, { use_cache: event.target.checked })} /> Use cache</label><span className="success-note">Example<span>{'inn -> request.body.inn'}</span></span></div><label className="field-label">Input mapping JSON<CodeEditor value={inputJson} onChange={(value) => { try { update(step.id, { input: parseJsonObject(value, 'Resolver input') }); setError(null); } catch (caught) { setError(caught instanceof Error ? caught.message : 'Invalid resolver input'); } }} language="json" minRows={6} /></label><label className="field-label">Payload injection JSON<CodeEditor value={injectJson} onChange={(value) => { try { update(step.id, { inject: parseJsonObject(value, 'Resolver injection') }); setError(null); } catch (caught) { setError(caught instanceof Error ? caught.message : 'Invalid resolver injection'); } }} language="json" minRows={6} /></label></div>;
  }

  function BuildJsonEditor({ step, update }: { step: BuilderStep; update: (id: string, patch: Partial<BuilderStep>) => void }) {
    const template = asJson(step.template ?? {});
    return <div className="stack-form"><label className="field-label">Save as<input value={String(step.save_as ?? 'target_payload')} onChange={(event) => update(step.id, { save_as: event.target.value })} /></label><div className="builder-help-card"><strong>Собирайте только нужные поля</strong><span>Используйте OData result variables напрямую: <code>{'{{contractor.Ref_Key}}'}</code>, <code>{'{{product.Description}}'}</code>, <code>{'{{steps.get_prices.items}}'}</code>. Если placeholder занимает всё значение, массивы и объекты сохраняют тип; если он вставлен внутрь строки, получится строка.</span></div><label className="field-label">JSON template<CodeEditor value={template} onChange={(value) => { try { update(step.id, { template: parseJsonObject(value, 'JSON template') }); setError(null); } catch (caught) { setError(caught instanceof Error ? caught.message : 'Invalid JSON template'); } }} language="json" minRows={8} title="Rendered after OData/Resolver/Transform steps. Use only fields target endpoint needs." /></label><div className="hint-chip-row">{['{{request.body.pool_id}}', '{{contractor.Ref_Key}}', '{{product.Ref_Key}}', '{{steps.get_contractor.first.Description}}'].map((hint) => <button key={hint} type="button" className="hint-chip" onClick={() => navigator.clipboard?.writeText(hint)}>{hint}</button>)}</div><div className="success-note">Full placeholders preserve source type<span>{'"codes": "{{request.body.codes}}"'}</span></div></div>;
  }

  function MarkingCodePoolExportEditor({ step, update, setSampleText }: { step: BuilderStep; update: (id: string, patch: Partial<BuilderStep>) => void; setSampleText: (value: string) => void }) {
    const sourceMode = step.full_codes_base64_path ? 'base64' : 'decoded';
    const metadataJson = asJson(step.metadata_json ?? {});
    const actionOverridesJson = asJson(step.actions_override ?? {});
    const sample = {
      order_number: '260703/5442',
      source_document_id: 'AEAE-000137',
      source_document_name: 'Заказ на эмиссию кодов маркировки AEAE-000137',
      full_codes_base64: ['MDEwNDY0NjE1MTY5NzE4NjIxNV88cWxrPFpiQ1dGUD5XMilmb1UdOTNsemhV'],
    };
    const switchSourceMode = (mode: string) => {
      if (mode === 'base64') {
        update(step.id, { full_codes_base64_path: 'request.body.full_codes_base64', codes_path: undefined });
      } else {
        update(step.id, { full_codes_base64_path: undefined, codes_path: 'request.body.codes' });
      }
    };
    return <div className="stack-form">
      <div className="builder-help-card">
        <strong>Что делает этот шаг</strong>
        <span>Принимает пул кодов ЧЗ от 1С, проверяет дубли, сохраняет файл для лазера через настройки CHZ Delivery и отправляет тот же пул во внешний сервис, например DnP. В production используйте <code>full_codes_base64</code>: это полный код маркировки из 1С без потери GS-разделителя.</span>
      </div>
      <div className="metadata-grid chz-pool-field-grid no-margin">
        <label className="field-label">Номер заказа из 1С<input value={String(step.order_number_path ?? 'request.body.order_number')} onChange={(event) => update(step.id, { order_number_path: event.target.value })} title="Путь к номеру заказа в JSON. Пример: request.body.order_number со значением 260703/5442." /></label>
        <label className="field-label">Источник кодов<select value={sourceMode} onChange={(event) => switchSourceMode(event.target.value)} title="Production режим - Base64 из ПолныйКодМаркировки. Decoded codes оставлен только для интеграций, которые уже передают реальный GS1-код."><option value="base64">Base64 full codes из 1С</option><option value="decoded">Already decoded codes</option></select></label>
        {sourceMode === 'base64' ? <label className="field-label">Массив Base64-кодов<input value={String(step.full_codes_base64_path ?? 'request.body.full_codes_base64')} onChange={(event) => update(step.id, { full_codes_base64_path: event.target.value, codes_path: undefined })} title="Путь к массиву строк Base64. Каждая строка - ПолныйКодМаркировки из 1С." /></label> : <label className="field-label">Массив готовых кодов<input value={String(step.codes_path ?? 'request.body.codes')} onChange={(event) => update(step.id, { codes_path: event.target.value, full_codes_base64_path: undefined })} title="Путь к массиву уже декодированных кодов. Для production лучше не использовать." /></label>}
        <label className="field-label">Сохранить результат как<input value={String(step.save_as ?? 'marking_pool_export')} onChange={(event) => update(step.id, { save_as: event.target.value })} title="Переменная результата. Обычно marking_pool_export, затем Return response возвращает {{marking_pool_export}}." /></label>
      </div>
      <div className="metadata-grid chz-pool-field-grid no-margin">
        <label className="field-label">ID документа 1С<input value={String(step.source_document_id_path ?? '')} onChange={(event) => update(step.id, { source_document_id_path: event.target.value })} title="Необязательно. Например request.body.source_document_id. Попадает в журнал и forwarding payload." /></label>
        <label className="field-label">Название документа 1С<input value={String(step.source_document_name_path ?? '')} onChange={(event) => update(step.id, { source_document_name_path: event.target.value })} title="Необязательно. Например request.body.source_document_name. Помогает оператору видеть источник в Timeline." /></label>
        <label className="field-label">Имя файла из запроса<input value={String(step.file_name_path ?? '')} onChange={(event) => update(step.id, { file_name_path: event.target.value })} title="Обычно пусто: OMH сам строит имя KM_260703-5442___1_pcs.txt. Заполняйте только если 1С должна явно задать имя файла." /></label>
        <label className="check-row"><input type="checkbox" checked={step.allow_overwrite !== false} onChange={(event) => update(step.id, { allow_overwrite: event.target.checked })} /> Разрешить перезаписать файл с тем же именем</label>
      </div>
      <div className="builder-help-card">
        <strong>Где настраиваются действия</strong>
        <span>Папка outbox, SMB-папка лазера, DnP URL и timeout задаются не в этом flow, а один раз в <code>Marking Code Pools {'->'} Settings</code> или в Environment Variables. Flow хранит только правила, откуда взять данные из JSON 1С.</span>
      </div>
      <label className="field-label">Metadata JSON<CodeEditor value={metadataJson} onChange={(value) => { try { update(step.id, { metadata_json: parseJsonObject(value, 'Metadata JSON') }); setError(null); } catch (caught) { setError(caught instanceof Error ? caught.message : 'Invalid metadata JSON'); } }} language="json" minRows={4} /></label>
      <label className="field-label">Action overrides JSON<CodeEditor value={actionOverridesJson} onChange={(value) => { try { update(step.id, { actions_override: parseJsonObject(value, 'Action overrides JSON') }); setError(null); } catch (caught) { setError(caught instanceof Error ? caught.message : 'Invalid action overrides JSON'); } }} language="json" minRows={4} title="Обычно оставляем пустым. Можно точечно отключить laser_file или external_forward для отдельного flow." /></label>
      <div className="hint-chip-row">
        {['request.body.order_number', 'request.body.full_codes_base64', 'request.body.source_document_id', 'request.body.source_document_name', '{{marking_pool_export}}'].map((hint) => <button key={hint} type="button" className="hint-chip" onClick={() => navigator.clipboard?.writeText(hint)} title="Click to copy">{hint}</button>)}
      </div>
      <div className="action-row wrap-actions">
        <button type="button" className="ghost-button" onClick={() => setSampleText(asJson(sample))}>Use CHZ sample request</button>
        <button type="button" className="ghost-button" onClick={runPreview} disabled={preview.isPending}>Preview CHZ step</button>
        <Link className="primary-link" to="/marking-code-pools">CHZ delivery settings</Link>
        <Link className="primary-link" to="/docs/onec/recipes/onec-chz-pool-delivery">Open lesson</Link>
      </div>
    </div>;
  }

  function BuildXmlResponseEditor({ step, update }: { step: BuilderStep; update: (id: string, patch: Partial<BuilderStep>) => void }) {
    const template = String(step.body_template ?? step.template ?? '<Response><Success>true</Success></Response>');
    return <div className="stack-form"><div className="metadata-grid compact-grid no-margin"><label className="field-label">HTTP status<input value={String(step.status_code ?? 200)} onChange={(event) => update(step.id, { status_code: Number(event.target.value) || 200 })} /></label><label className="field-label">Headers JSON<CodeEditor value={asJson(step.headers ?? { 'Content-Type': 'application/xml' })} onChange={(value) => { try { update(step.id, { headers: parseJsonObject(value, 'Headers') }); setError(null); } catch (caught) { setError(caught instanceof Error ? caught.message : 'Invalid headers'); } }} language="json" minRows={4} /></label></div><XmlResponseBuilder value={template} onChange={(value) => update(step.id, { body_template: value, response_body_type: 'xml' })} variables={{ number: '260666/6938', order: { Ref_Key: 'order-ref-key', Number: '260666/6938' }, products: [{ Ref_Key: 'line-1' }] }} hints={['{{number}}', '{{order.Ref_Key}}', '{{order.Number}}', '{{products}}']} /></div>;
  }

  function CallEndpointEditor({ step, update, connectorNames }: { step: BuilderStep; update: (id: string, patch: Partial<BuilderStep>) => void; connectorNames: string[] }) {
    const headersJson = asJson(step.headers ?? { 'Content-Type': 'application/json' });
    const mockResponseJson = asJson(step.mock_response_json ?? {});
    return <div className="stack-form">
      <div className="builder-help-card">
        <strong>Endpoint response becomes a variable</strong>
        <span>Этот шаг сохраняет исходящий запрос и ответ в Timeline. Если заполнить <code>Save response as</code>, body ответа станет переменной для следующих шагов: например <code>{'{{service_a.id}}'}</code> в следующем endpoint или Build JSON.</span>
      </div>
      <div className="metadata-grid endpoint-call-grid no-margin">
        <label className="field-label">Connector<input list="target-connector-names" value={String(step.connector ?? '')} onChange={(event) => update(step.id, { connector: event.target.value })} title="Имя REST/HTTP connector. Используйте connector для production: base URL, auth и timeout хранятся централизованно." /><datalist id="target-connector-names">{connectorNames.map((name) => <option key={name} value={name} />)}</datalist></label>
        <label className="field-label">Direct URL<input value={String(step.url ?? '')} onChange={(event) => update(step.id, { url: event.target.value })} title="Опционально. Если заполнено, OMH вызовет этот URL напрямую вместо connector. Для production обычно лучше connector." /></label>
        <label className="field-label">Method<select value={String(step.method ?? 'POST')} onChange={(event) => update(step.id, { method: event.target.value })}><option value="POST">POST</option><option value="PUT">PUT</option><option value="PATCH">PATCH</option></select></label>
        <label className="field-label">Path<input value={String(step.path ?? '')} onChange={(event) => update(step.id, { path: event.target.value })} title="Путь относительно connector base URL. Можно использовать переменные: /orders/{{request.body.order_number}}." /></label>
        <label className="field-label">Save response as<input value={String(step.save_response_as ?? '')} onChange={(event) => update(step.id, { save_response_as: event.target.value })} placeholder="service_a" title="Имя переменной для body ответа. Следующие шаги смогут читать service_a.id, service_a.status и т.д." /></label>
      </div>
      <label className="field-label">Body template<input value={String(step.body ?? '{{target_payload}}')} onChange={(event) => update(step.id, { body: event.target.value })} title="Можно передать целый объект {{target_payload}} или собрать объект в Build JSON перед этим шагом." /></label>
      <label className="field-label">Headers JSON<CodeEditor value={headersJson} onChange={(value) => { try { update(step.id, { headers: parseJsonObject(value, 'Headers JSON') }); setError(null); } catch (caught) { setError(caught instanceof Error ? caught.message : 'Invalid headers JSON'); } }} language="json" minRows={4} /></label>
      <label className="field-label">Mock response JSON for Preview<CodeEditor value={mockResponseJson} onChange={(value) => { try { update(step.id, { mock_response_json: parseJsonObject(value, 'Mock response JSON') }); setError(null); } catch (caught) { setError(caught instanceof Error ? caught.message : 'Invalid mock response JSON'); } }} language="json" minRows={5} title="Preview использует этот ответ без реального вызова внешнего сервиса. Так можно проверить следующие шаги цепочки." /></label>
      <div className="hint-chip-row">
        {['{{target_payload}}', '{{response.body}}', '{{service_a.id}}', '{{service_b.status}}'].map((hint) => <button key={hint} type="button" className="hint-chip" onClick={() => navigator.clipboard?.writeText(hint)} title="Click to copy">{hint}</button>)}
      </div>
    </div>;
  }
}
