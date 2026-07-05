import { FormEvent, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../../api/client';
import { integrationFlowsApi, type IntegrationFlow } from '../../api/integrationFlows';
import { uiApi } from '../../api/ui';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { StatusBadge } from '../../components/StatusBadge';
import { ConnectorSelect } from '../../components/integration/ConnectorSelect';
import { FlowPreviewPanel } from '../../components/integration/FlowPreviewPanel';
import { JsonPayloadBuilder } from '../../components/integration/JsonPayloadBuilder';
import { MatcherBuilder } from '../../components/integration/MatcherBuilder';
import { ODataLookupBlockEditor, type ODataLookupDraft } from '../../components/integration/ODataLookupBlockEditor';
import { TargetActionEditor } from '../../components/integration/TargetActionEditor';
import { CopyButton } from '../../components/product/CopyButton';
import { EndpointUrlBox } from '../../components/product/EndpointUrlBox';
import { FormGrid } from '../../components/product/FormGrid';
import { PageHeader } from '../../components/product/PageHeader';
import { ResultPanel } from '../../components/product/ResultPanel';
import { SectionCard } from '../../components/product/SectionCard';

interface WizardForm {
  name: string;
  slug: string;
  description: string;
  sourceType: string;
  targetType: string;
  inputMode: string;
  responseMode: string;
  authMode: string;
  token: string;
  onecConnector: string;
  targetConnector: string;
  actionType: string;
  targetPath: string;
  targetMethod: string;
  matcherMode: string;
  matcherType: string;
  matcherPath: string;
  matcherValue: string;
  payloadTemplate: string;
  sampleRequest: string;
}

const sampleJson = { inn: '1234567890', product_code: 'ABC-123', pool_id: 'POOL-001', codes: ['010464615169738421ABC'] };

function slugify(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 80) || 'onec-integration';
}

function parseObject(value: string, label: string): Record<string, unknown> {
  const parsed = JSON.parse(value || '{}') as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error(`${label} must be a JSON object`);
  return parsed as Record<string, unknown>;
}

function defaultForm(preset: string | null): WizardForm {
  const apiToOnec = preset === 'api_to_onec';
  const xmlBridge = preset === 'onec_xml_raw_bridge';
  const printer = preset === 'onec_to_printer';
  const twoOData = preset === 'onec_post_two_odata_to_endpoint';
  const name = printer ? '1C print request to production printer' : apiToOnec ? 'Website API to 1C HTTP service' : xmlBridge ? '1C raw XML bridge' : twoOData ? '1C order to API via OData enrichment' : '1C order to external API';
  return {
    name,
    slug: slugify(name),
    description: twoOData ? 'Read 1C POST body, enrich it from OData, build target JSON and proxy endpoint response.' : 'Generated from the 1C cockpit wizard.',
    sourceType: apiToOnec ? 'external_api' : 'onec',
    targetType: printer ? 'printer' : apiToOnec || xmlBridge ? 'onec' : 'external_api',
    inputMode: xmlBridge ? 'xml' : 'json',
    responseMode: twoOData ? 'proxy_response' : 'accepted_event',
    authMode: 'none',
    token: '',
    onecConnector: '1C ERP',
    targetConnector: printer ? 'Zebra Production' : apiToOnec || xmlBridge ? '1C ERP' : 'DNP Service',
    actionType: printer ? 'call_printer' : apiToOnec || xmlBridge ? 'call_1c_http_service' : 'call_rest_api',
    targetPath: printer ? '/print/zpl' : apiToOnec || xmlBridge ? '/hs/omh/receive' : '/api/orders',
    targetMethod: 'POST',
    matcherMode: twoOData ? 'all' : 'any',
    matcherType: xmlBridge ? 'xml_contains' : 'body_path_exists',
    matcherPath: twoOData ? 'inn' : 'pool_id',
    matcherValue: xmlBridge ? '<Document' : '',
    payloadTemplate: asJson(twoOData ? { pool_id: '{{request.body.pool_id}}', contractor_uuid: '{{contractor.Ref_Key}}', product_uuid: '{{product.Ref_Key}}', codes: '{{request.body.codes}}', source: '1C' } : { id: '{{request.body.id}}', payload: '{{request.body}}', source: '1C' }),
    sampleRequest: asJson(sampleJson),
  };
}

function defaultLookups(preset: string | null): ODataLookupDraft[] {
  if (preset !== 'onec_post_two_odata_to_endpoint') return [];
  return [
    { id: 'get_contractor', name: 'Find contractor by INN', connection: '1C ERP', resource: 'Catalog_ContrAgents', field: 'INN', operator: 'eq', value: '{{inn}}', select: 'Ref_Key,Description,INN', saveAs: 'contractor', required: true },
    { id: 'get_product', name: 'Find product by code', connection: '1C ERP', resource: 'Catalog_Products', field: 'Article', operator: 'eq', value: '{{product_code}}', select: 'Ref_Key,Description,Article', saveAs: 'product', required: true },
  ];
}

function actionFor(form: WizardForm): Record<string, unknown> {
  if (form.actionType === 'call_1c_http_service') return { type: form.actionType, target_connector: form.targetConnector, method: form.targetMethod, path: form.targetPath, body_mode: form.inputMode === 'xml' ? 'raw_xml' : 'json', payload_source: form.inputMode === 'xml' ? 'raw_xml' : 'incoming_payload', verify_unchanged_hash: form.inputMode === 'xml' };
  if (form.actionType === 'call_printer') return { type: form.actionType, printer_connector: form.targetConnector, payload_source: 'incoming_payload' };
  if (form.actionType === 'create_event_only') return { type: form.actionType };
  return { type: 'call_rest_api', target_connector: form.targetConnector, method: form.targetMethod, path: form.targetPath, body_mode: 'json', payload_source: 'target_payload', response_mode: form.responseMode, mock_response_json: { accepted: true, preview: true } };
}

function matcherFor(form: WizardForm): Record<string, unknown> {
  const rule: Record<string, unknown> = { type: form.matcherType };
  if (form.matcherPath) rule.path = form.matcherPath;
  if (form.matcherValue) rule.value = form.matcherValue;
  return { mode: form.matcherMode, rules: [rule] };
}

function builderFor(form: WizardForm, lookups: ODataLookupDraft[]): Record<string, unknown> {
  const variables = new Set<string>();
  lookups.forEach((lookup) => {
    const match = lookup.value.match(/^{{(.+)}}$/);
    if (match?.[1]) variables.add(match[1].replace(/^request\.body\./, ''));
  });
  if (form.matcherPath) variables.add(form.matcherPath);
  const readSteps = Array.from(variables).map((name) => ({ id: `read_${slugify(name).replaceAll('-', '_')}`, type: 'read_variable', name: `Read ${name}`, path: `request.body.${name}`, save_as: name }));
  const lookupSteps = lookups.map((lookup) => ({ id: lookup.id, type: 'odata_query', name: lookup.name, connection: lookup.connection || form.onecConnector, resource: lookup.resource, filter_builder: [{ field: lookup.field, operator: lookup.operator, value: lookup.value }], select: (lookup.select ?? '').split(',').map((item) => item.trim()).filter(Boolean), orderby: lookup.orderby || undefined, top: 1, save_as: lookup.saveAs, required: lookup.required }));
  const buildJson = { id: 'build_target_payload', type: 'build_json', name: 'Build target JSON', save_as: 'target_payload', template: parseObject(form.payloadTemplate, 'Payload template') };
  const callEndpoint = { id: 'send_to_target', type: 'call_endpoint', name: 'Send to target', connector: form.targetConnector, method: form.targetMethod, path: form.targetPath, body: form.actionType === 'call_printer' ? '{{request.body}}' : '{{target_payload}}', response_mode: form.responseMode };
  const returnStep = { id: 'return_response', type: 'return_response', name: 'Return response', body: '{{response}}' };
  return { version: 1, input: { endpoint_slug: form.slug, input_mode: form.inputMode, response_mode: form.responseMode }, variables: Array.from(variables).map((name) => ({ name, source: `request.body.${name}` })), steps: [...readSteps, ...lookupSteps, buildJson, callEndpoint, returnStep] };
}

export function OneCCockpitWizardPage() {
  const [searchParams] = useSearchParams();
  const preset = searchParams.get('preset');
  const queryClient = useQueryClient();
  const options = useQuery({ queryKey: ['ui-flow-builder-options'], queryFn: uiApi.flowBuilderOptions });
  const [form, setForm] = useState<WizardForm>(() => defaultForm(preset));
  const [lookups, setLookups] = useState<ODataLookupDraft[]>(() => defaultLookups(preset));
  const [selectedFlow, setSelectedFlow] = useState<IntegrationFlow | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [result, setResult] = useState<unknown>(null);

  const builderState = useMemo(() => {
    try { return { builder: builderFor(form, lookups), error: null as string | null }; }
    catch (error) { return { builder: { version: 1, input: {}, steps: [] } as Record<string, unknown>, error: error instanceof Error ? error.message : 'Invalid builder input' }; }
  }, [form, lookups]);
  const builder = builderState.builder;

  const preview = useMutation({ mutationFn: () => integrationFlowsApi.previewBuilder({ builder_json: builder, sample_request: parseObject(form.sampleRequest, 'Sample request'), run_real_queries: false }), onSuccess: setResult });
  const create = useMutation({ mutationFn: () => integrationFlowsApi.create({ name: form.name, slug: form.slug, description: form.description, enabled: true, source_type: form.sourceType, target_type: form.targetType, endpoint: { input_mode: form.inputMode, response_mode: form.responseMode, auth_mode: form.authMode, auth_config_json: form.authMode === 'static_token' ? { token: form.token } : {} }, matcher_group_json: matcherFor(form), action_json: actionFor(form), response_config_json: { response_mode: form.responseMode }, builder_json: builder, test_payload_json: form.inputMode === 'json' ? parseObject(form.sampleRequest, 'Sample request') : null, test_payload_text: form.inputMode === 'json' ? null : form.sampleRequest }), onSuccess: (flow) => { setSelectedFlow(flow); setResult(flow); queryClient.invalidateQueries({ queryKey: ['ui-cockpit-summary'] }); } });
  const compile = useMutation({ mutationFn: () => integrationFlowsApi.compileBuilder(selectedFlow!.id), onSuccess: setResult });
  const test = useMutation({ mutationFn: () => integrationFlowsApi.test(selectedFlow!.id, { input_mode: form.inputMode, payload_json: form.inputMode === 'json' ? parseObject(form.sampleRequest, 'Sample request') : null, payload_text: form.inputMode === 'json' ? null : form.sampleRequest, dry_run: false }), onSuccess: setResult });

  if (options.isLoading) return <LoadingState label="Loading cockpit builder options" />;
  if (options.error) return <ErrorState error={options.error} />;
  if (!options.data) return <ErrorState error={new Error('Flow builder options are empty')} />;

  function guarded(action: () => void) {
    setFormError(null);
    try {
      if (builderState.error) throw new Error(builderState.error);
      action();
    }
    catch (error) { setFormError(error instanceof Error ? error.message : 'Invalid wizard input'); }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    guarded(() => create.mutate());
  }

  const targetConnectors = form.targetType === 'printer' ? options.data.printer_connectors : form.targetType === 'onec' ? options.data.onec_connectors : options.data.rest_connectors;

  return (
    <div className="page-stack cockpit-wizard-page">
      <PageHeader
        eyebrow="New 1C Integration"
        title="Build a production route without editing JSON by hand."
        description="Configure inbound endpoint, match rules, OData enrichment, target delivery and preview the generated runtime flow before publishing."
        className="cockpit-hero wizard"
        meta={<><StatusBadge status={options.data.package_state.enabled ? 'ok' : 'warning'} label={options.data.package_state.enabled ? '1C package enabled' : options.data.package_state.action_label} /><span className="microcopy">Preset: {preset ?? 'custom'}</span></>}
        actions={<><Link className="ghost-button" to="/onec-cockpit">Back to cockpit</Link>{selectedFlow && <Link className="primary-button" to={`/integration-flows/${selectedFlow.id}/builder`}>Open visual builder</Link>}</>}
      />

      <section className="cockpit-wizard-grid">
        <form className="panel cockpit-wizard-form" onSubmit={submit}>
          <div className="panel-toolbar"><div><span className="eyebrow">01 Contract</span><h2>Endpoint and route identity</h2></div><button className="primary-button" disabled={create.isPending}>Create integration</button></div>
          <FormGrid columns={3}>
            <label className="field-label">Name<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value, slug: slugify(event.target.value) })} /></label>
            <label className="field-label">Slug<input value={form.slug} onChange={(event) => setForm({ ...form, slug: slugify(event.target.value) })} /></label>
            <label className="field-label">Description<input value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
            <label className="field-label">Source<select value={form.sourceType} onChange={(event) => setForm({ ...form, sourceType: event.target.value })}><option value="onec">1C</option><option value="external_api">External API</option><option value="website">Website</option><option value="wms">WMS</option><option value="webhook">Webhook</option></select></label>
            <label className="field-label">Input<select value={form.inputMode} onChange={(event) => setForm({ ...form, inputMode: event.target.value })}>{options.data.input_modes.map((mode) => <option key={mode} value={mode}>{mode}</option>)}</select></label>
            <label className="field-label">Response<select value={form.responseMode} onChange={(event) => setForm({ ...form, responseMode: event.target.value })}>{options.data.response_modes.map((mode) => <option key={mode} value={mode}>{mode}</option>)}</select></label>
            <label className="field-label">Auth<select value={form.authMode} onChange={(event) => setForm({ ...form, authMode: event.target.value })}><option value="none">None</option><option value="static_token">Static token</option></select></label>
            {form.authMode === 'static_token' && <label className="field-label">Token<input value={form.token} onChange={(event) => setForm({ ...form, token: event.target.value })} /></label>}
          </FormGrid>
          <EndpointUrlBox url={`/api/bus/in/${form.slug}`} label="Generated inbound endpoint" />

          <MatcherBuilder mode={form.matcherMode} matcherType={form.matcherType} path={form.matcherPath} value={form.matcherValue} matcherTypes={options.data.matcher_types} onChange={(patch) => setForm({ ...form, ...patch })} />

          <SectionCard eyebrow="02 Enrich" title="OData lookup chain" description="Add one or more 1C OData reads before building the final JSON.">
            <div className="lookup-editor-list">
              {lookups.map((lookup, index) => <ODataLookupBlockEditor key={lookup.id} lookup={lookup} index={index} connectors={options.data.onec_connectors} templates={options.data.odata_lookup_templates} onChange={(next) => setLookups(lookups.map((item) => item.id === lookup.id ? next : item))} onRemove={() => setLookups(lookups.filter((item) => item.id !== lookup.id))} />)}
            </div>
            <button type="button" className="ghost-button" onClick={() => setLookups([...lookups, { id: `odata_${lookups.length + 1}`, name: 'OData lookup', connection: form.onecConnector, resource: '', field: '', operator: 'eq', value: '{{request.body.value}}', select: 'Ref_Key,Description', saveAs: `lookup_${lookups.length + 1}`, required: true }])}>Add OData lookup</button>
          </SectionCard>

          <JsonPayloadBuilder value={form.payloadTemplate} onChange={(value) => setForm({ ...form, payloadTemplate: value })} />
          <TargetActionEditor targetType={form.targetType} actionType={form.actionType} connector={form.targetConnector} path={form.targetPath} method={form.targetMethod} connectors={targetConnectors} operationTemplates={options.data.operation_templates} onChange={(patch) => setForm({ ...form, ...patch })} />

          <SectionCard eyebrow="03 Test Input" title="Sample request">
            <ConnectorSelect label="Default 1C connector" value={form.onecConnector} options={options.data.onec_connectors} onChange={(value) => setForm({ ...form, onecConnector: value })} />
            <label className="field-label">Sample request<textarea value={form.sampleRequest} onChange={(event) => setForm({ ...form, sampleRequest: event.target.value })} /></label>
            <div className="action-row"><button type="button" className="ghost-button" onClick={() => guarded(() => preview.mutate())} disabled={preview.isPending}>Preview</button>{selectedFlow && <button type="button" className="ghost-button" onClick={() => compile.mutate()} disabled={compile.isPending}>Compile</button>}{selectedFlow && <button type="button" className="primary-button" onClick={() => guarded(() => test.mutate())} disabled={test.isPending}>Test live route</button>}{selectedFlow && <CopyButton value={selectedFlow.onec_http_example} label="Copy 1C HTTP code" />}</div>
            {(builderState.error || formError || create.error || preview.error || compile.error || test.error) && <div className="error-state compact">{builderState.error ?? formError ?? ((create.error ?? preview.error ?? compile.error ?? test.error) as Error).message}</div>}
          </SectionCard>
        </form>

        <aside className="cockpit-wizard-sidecar">
          {selectedFlow && <SectionCard eyebrow="Published" title={selectedFlow.name} description={selectedFlow.description}><EndpointUrlBox url={selectedFlow.endpoint_url} /><div className="action-row"><Link className="primary-link" to={`/integration-flows/${selectedFlow.id}/builder`}>Open builder</Link><Link className="primary-link" to="/test-console">Open test console</Link></div></SectionCard>}
          <FlowPreviewPanel preview={preview.data ?? null} builder={builder} />
          <SectionCard eyebrow="Result" title="Last backend response"><ResultPanel result={result} /></SectionCard>
        </aside>
      </section>
    </div>
  );
}
