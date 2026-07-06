import { FormEvent, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { changeSetsApi } from '../api/changeSets';
import { integrationFlowsApi, IntegrationFlow } from '../api/integrationFlows';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { CodeBlock } from '../components/CodeBlock';
import { CodeEditor } from '../components/CodeEditor';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { VersionHistoryPanel } from '../features/configVersions';
import { useI18n } from '../i18n/useI18n';

const sampleJson = { pool_type: 'DNP', order_id: 'ORD-123', codes: ['010464615169738421ABC', '010464615169738421DEF'] };

function slugify(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 80) || 'integration-flow';
}

function parseJsonObject(value: string, label: string): Record<string, unknown> {
  const parsed = JSON.parse(value || '{}') as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error(`${label} must be a JSON object`);
  return parsed as Record<string, unknown>;
}

function actionFor(kind: string, target: string, path: string) {
  if (kind === 'call_1c_http_service') return { type: kind, target_connector: target || '1C ERP', operation: 'receive_upd_xml', body_mode: 'raw_xml', payload_source: 'raw_xml', verify_unchanged_hash: true };
  if (kind === 'call_odata_lookup') return { type: kind, lookup_template: target || 'Find contractor by INN', input: { inn: 'payload.inn' }, inject: { 'payload.contractor_uuid': 'contractor_uuid' } };
  if (kind === 'call_printer') return { type: kind, printer_connector: target || 'Zebra Production', payload_source: 'incoming_payload' };
  if (kind === 'create_event_only') return { type: kind };
  return { type: 'call_rest_api', target_connector: target || 'DNP Service', method: 'POST', path: path || '/api/marking/codes/pool', body_mode: 'json', payload_source: 'incoming_payload', response_mode: 'proxy_response' };
}

export function IntegrationFlowsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { t } = useI18n();
  const flows = useQuery({ queryKey: ['integration-flows'], queryFn: integrationFlowsApi.list });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = useMemo(() => (flows.data ?? []).find((item) => item.id === selectedId) ?? flows.data?.[0] ?? null, [flows.data, selectedId]);
  const [result, setResult] = useState<unknown>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: '1C marking pool to DNP service',
    slug: 'marking-pool',
    description: 'Route DNP marking code pools from 1C to the internal DNP service.',
    source_type: 'onec',
    target_type: 'external_api',
    input_mode: 'json',
    response_mode: 'proxy_response',
    auth_mode: 'none',
    token: '',
    matcher_mode: 'any',
    matcher_type: 'body_path_equals',
    matcher_path: 'pool_type',
    matcher_value: 'DNP',
    second_matcher_type: 'text_contains',
    second_matcher_value: 'DNP',
    action_type: 'call_rest_api',
    target_connector: 'DNP Service',
    target_path: '/api/marking/codes/pool',
    test_payload: asJson(sampleJson),
  });

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['integration-flows'] });
  const create = useMutation({ mutationFn: integrationFlowsApi.create, onSuccess: (data) => { setResult(data); setSelectedId(data.id); refresh(); } });
  const installPreset = useMutation({ mutationFn: integrationFlowsApi.installMarkingPool, onSuccess: (data) => { setResult(data); setSelectedId(data.id); refresh(); } });
  const installBuilderPreset = useMutation({ mutationFn: integrationFlowsApi.installTwoODataToEndpoint, onSuccess: (data) => { setResult(data); setSelectedId(data.id); refresh(); } });
  const installDnpPullCodes = useMutation({ mutationFn: integrationFlowsApi.installDnpPullCodes, onSuccess: (data) => { setResult(data); setSelectedId(data.id); refresh(); } });
  const duplicate = useMutation({ mutationFn: integrationFlowsApi.duplicate, onSuccess: (data) => { setResult(data); setSelectedId(data.id); refresh(); } });
  const exportFlow = useMutation({ mutationFn: integrationFlowsApi.export, onSuccess: setResult });
  const exportForProduction = useMutation({
    mutationFn: (flow: IntegrationFlow) => changeSetsApi.createFromDrafts({ name: `Promote ${flow.name}`, description: 'Export for production from Integration Flow detail', object_refs: [{ object_type: 'integration_flow', object_id: flow.id }], include_dependencies: true }),
    onSuccess: (changeSet) => navigate(`/change-sets/${changeSet.id}`),
  });
  const testFlow = useMutation({ mutationFn: (payload: { id: string; body: Record<string, unknown> }) => integrationFlowsApi.test(payload.id, { input_mode: 'json', payload_json: payload.body, dry_run: false }), onSuccess: setResult });
  const testMatcher = useMutation({ mutationFn: (payload: { body: Record<string, unknown>; matcher: Record<string, unknown> }) => integrationFlowsApi.testMatcher({ input_mode: 'json', payload: payload.body, matcher_group: payload.matcher }), onSuccess: setResult });

  if (flows.isLoading) return <LoadingState label={t('integration.flowBuilder.loading')} />;
  if (flows.error) return <ErrorState error={flows.error} />;

  const matcher = { mode: form.matcher_mode, rules: [{ type: form.matcher_type, path: form.matcher_type.startsWith('body_path') ? form.matcher_path : undefined, value: form.matcher_value }, { type: form.second_matcher_type, value: form.second_matcher_value }] };
  const action = actionFor(form.action_type, form.target_connector, form.target_path);

  function submit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    try {
      const testPayload = parseJsonObject(form.test_payload, 'Test payload');
      create.mutate({
        name: form.name,
        slug: form.slug,
        description: form.description,
        enabled: true,
        source_type: form.source_type,
        target_type: form.target_type,
        endpoint: { input_mode: form.input_mode, response_mode: form.response_mode, auth_mode: form.auth_mode, auth_config_json: form.auth_mode === 'static_token' ? { token: form.token } : {} },
        matcher_group_json: matcher,
        action_json: action,
        response_config_json: { response_mode: form.response_mode },
        test_payload_json: testPayload,
      });
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Invalid flow form');
    }
  }

  function runMatcher() {
    setFormError(null);
    try { testMatcher.mutate({ body: parseJsonObject(form.test_payload, 'Test payload'), matcher }); }
    catch (error) { setFormError(error instanceof Error ? error.message : 'Invalid matcher input'); }
  }

  function runSelectedFlow(flow: IntegrationFlow) {
    setFormError(null);
    try { testFlow.mutate({ id: flow.id, body: parseJsonObject(asJson(flow.test_payload_json ?? sampleJson), 'Flow test payload') }); }
    catch (error) { setFormError(error instanceof Error ? error.message : 'Invalid flow test payload'); }
  }

  return (
    <div className="page-stack flow-builder-page">
      <section className="page-header flow-hero">
        <span className="eyebrow">{t('integration.flowBuilder.eyebrow')}</span>
        <h1>{t('integration.flowBuilder.title')}</h1>
        <p>{t('integration.flowBuilder.description')}</p>
        <div className="hero-meta" data-tour="flow-presets"><button className="primary-button" onClick={() => installDnpPullCodes.mutate()} disabled={installDnpPullCodes.isPending}>Install DNP key flow</button><button className="ghost-button" onClick={() => installBuilderPreset.mutate()} disabled={installBuilderPreset.isPending}>{t('integration.flowBuilder.installODataPreset')}</button><button className="ghost-button" onClick={() => installPreset.mutate()} disabled={installPreset.isPending}>{t('integration.flowBuilder.installMarkingPreset')}</button><span className="microcopy">{t('integration.flowBuilder.flowPipeline')}</span></div>
      </section>

      <section className="flow-layout">
        <section className="panel flow-list-panel">
          <div className="panel-toolbar"><h2>{t('integration.flowBuilder.flows')}</h2><span className="microcopy">{flows.data?.length ?? 0}</span></div>
          {(flows.data ?? []).length === 0 ? <EmptyState title={t('integration.flowBuilder.noFlows')} detail={t('integration.flowBuilder.noFlowsDetail')} actions={<><Link className="primary-button" to="/onboarding/first-integration">{t('integration.flowBuilder.createFirst')}</Link><Link className="ghost-button" to="/docs/onec/tools/visual-flow-builder">{t('integration.flowBuilder.openGuide')}</Link></>} /> : <div className="flow-list">{(flows.data ?? []).map((flow) => <button key={flow.id} className={`flow-list-item ${selected?.id === flow.id ? 'active' : ''}`} onClick={() => setSelectedId(flow.id)}><span><strong>{flow.name}</strong><small>{flow.endpoint_url}</small></span><StatusBadge status={flow.enabled ? 'ok' : 'cancelled'} label={flow.enabled ? t('integration.flowBuilder.enabled') : t('integration.flowBuilder.disabled')} compact /></button>)}</div>}
        </section>

        <form className="panel stack-form flow-wizard" onSubmit={submit} data-tour="flow-create">
          <div className="panel-toolbar"><div><span className="eyebrow">{t('integration.flowBuilder.createWizard')}</span><h2>{t('integration.flowBuilder.wizardTitle')}</h2></div><button className="primary-button" disabled={create.isPending}>{t('integration.flowBuilder.createFlow')}</button></div>
          <section className="wizard-step"><span className="step-index">01</span><label className="field-label">{t('integration.flowBuilder.flowName')}<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value, slug: slugify(event.target.value) })} /></label><label className="field-label">{t('integration.flowBuilder.descriptionLabel')}<input value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label><div className="metadata-grid compact-grid no-margin"><label className="field-label">{t('integration.flowBuilder.source')}<select value={form.source_type} onChange={(event) => setForm({ ...form, source_type: event.target.value })}><option value="onec">1C</option><option value="website">Website</option><option value="wms">WMS</option><option value="external_api">External API</option><option value="manual">Manual</option><option value="webhook">Webhook</option></select></label><label className="field-label">{t('integration.flowBuilder.target')}<select value={form.target_type} onChange={(event) => setForm({ ...form, target_type: event.target.value })}><option value="external_api">External API</option><option value="onec">1C</option><option value="wms">WMS</option><option value="printer">Printer</option><option value="odata_lookup">OData lookup</option><option value="internal">Internal</option></select></label><label className="field-label">{t('integration.flowBuilder.slug')}<input value={form.slug} onChange={(event) => setForm({ ...form, slug: event.target.value })} /></label></div></section>
          <section className="wizard-step"><span className="step-index">02</span><div className="metadata-grid compact-grid no-margin"><label className="field-label">{t('integration.flowBuilder.input')}<select value={form.input_mode} onChange={(event) => setForm({ ...form, input_mode: event.target.value })}><option value="json">JSON</option><option value="xml">XML</option><option value="raw_text">Raw text</option><option value="form">Form</option><option value="multipart_file">File</option></select></label><label className="field-label">{t('integration.flowBuilder.response')}<select value={form.response_mode} onChange={(event) => setForm({ ...form, response_mode: event.target.value })}><option value="accepted_event">Accepted event</option><option value="accepted_message">Accepted message</option><option value="sync_response">Sync response</option><option value="proxy_response">Proxy response</option></select></label><label className="field-label">{t('integration.flowBuilder.auth')}<select value={form.auth_mode} onChange={(event) => setForm({ ...form, auth_mode: event.target.value })}><option value="none">None</option><option value="static_token">Static token</option></select></label></div>{form.auth_mode === 'static_token' && <label className="field-label">{t('integration.flowBuilder.token')}<input value={form.token} onChange={(event) => setForm({ ...form, token: event.target.value })} /></label>}<div className="success-note"><strong>/api/bus/in/{form.slug}</strong><span>{t('integration.flowBuilder.generatedEndpoint')}</span></div></section>
          <section className="wizard-step"><span className="step-index">03</span><div className="metadata-grid compact-grid no-margin"><label className="field-label">{t('integration.flowBuilder.mode')}<select value={form.matcher_mode} onChange={(event) => setForm({ ...form, matcher_mode: event.target.value })}><option value="all">All</option><option value="any">Any</option><option value="none">None</option></select></label><label className="field-label">{t('integration.flowBuilder.matcher')}<select value={form.matcher_type} onChange={(event) => setForm({ ...form, matcher_type: event.target.value })}><option value="body_path_equals">Body path equals</option><option value="body_path_exists">Body path exists</option><option value="xml_contains">XML contains</option><option value="text_contains">Text contains</option><option value="regex">Regex</option></select></label><label className="field-label">{t('integration.flowBuilder.path')}<input value={form.matcher_path} onChange={(event) => setForm({ ...form, matcher_path: event.target.value })} /></label></div><label className="field-label">{t('integration.flowBuilder.value')}<input value={form.matcher_value} onChange={(event) => setForm({ ...form, matcher_value: event.target.value })} /></label><button type="button" className="ghost-button" onClick={runMatcher} disabled={testMatcher.isPending}>{t('integration.flowBuilder.testMatcher')}</button></section>
          <section className="wizard-step"><span className="step-index">04</span><div className="metadata-grid compact-grid no-margin"><label className="field-label">{t('integration.flowBuilder.action')}<select value={form.action_type} onChange={(event) => setForm({ ...form, action_type: event.target.value })}><option value="call_rest_api">Forward JSON to API</option><option value="call_1c_http_service">Forward raw XML to 1C</option><option value="call_odata_lookup">Call OData lookup</option><option value="call_printer">Print</option><option value="create_event_only">Create event only</option></select></label><label className="field-label">{t('integration.flowBuilder.targetConnector')}<input value={form.target_connector} onChange={(event) => setForm({ ...form, target_connector: event.target.value })} /></label><label className="field-label">{t('integration.flowBuilder.targetPath')}<input value={form.target_path} onChange={(event) => setForm({ ...form, target_path: event.target.value })} /></label></div></section>
          <section className="wizard-step"><span className="step-index">05</span><label className="field-label">{t('integration.flowBuilder.samplePayload')}<CodeEditor value={form.test_payload} onChange={(value) => setForm({ ...form, test_payload: value })} language="json" minRows={8} /></label></section>
          {formError && <div className="error-state compact">{formError}</div>}
          {[create, installPreset, installBuilderPreset, testMatcher].find((item) => item.error)?.error instanceof Error && <div className="error-state compact">{([create, installPreset, installBuilderPreset, testMatcher].find((item) => item.error)?.error as Error).message}</div>}
        </form>
      </section>

      {selected && <VersionHistoryPanel objectType="integration_flow" objectId={selected.id} compact onChanged={refresh} />}
      {selected && <section className="panel flow-detail" data-tour="flow-detail"><div className="panel-toolbar"><div><span className="eyebrow">{t('integration.flowBuilder.selectedFlow')}</span><h2>{selected.name}</h2><p>{selected.description}</p></div><StatusBadge status={selected.enabled ? 'ok' : 'cancelled'} label={selected.enabled ? t('integration.flowBuilder.enabled') : t('integration.flowBuilder.disabled')} /></div><div className="metadata-grid compact-grid"><span>Endpoint<strong>{selected.endpoint_url}</strong></span><span>{t('integration.flowBuilder.source')}<strong>{selected.source_type}</strong></span><span>{t('integration.flowBuilder.target')}<strong>{selected.target_type}</strong></span></div><div className="action-row"><Link className="primary-button" to={`/integration-flows/${selected.id}/builder`}>{t('integration.flowBuilder.openVisualBuilder')}</Link><button className="primary-button" onClick={() => exportForProduction.mutate(selected)} disabled={exportForProduction.isPending}>{t('integration.flowBuilder.exportProduction')}</button><Link className="ghost-button" to={`/config-history/integration_flow/${selected.id}`}>{t('integration.flowBuilder.releaseControl')}</Link><button className="primary-button" onClick={() => runSelectedFlow(selected)} disabled={testFlow.isPending}>{t('integration.flowBuilder.testThisFlow')}</button><button className="ghost-button" onClick={() => navigator.clipboard?.writeText(selected.endpoint_url)}>{t('integration.flowBuilder.copyUrl')}</button><button className="ghost-button" onClick={() => duplicate.mutate(selected.id)} disabled={duplicate.isPending}>{t('integration.flowBuilder.duplicate')}</button><button className="ghost-button" onClick={() => exportFlow.mutate(selected.id)} disabled={exportFlow.isPending}>{t('integration.flowBuilder.export')}</button>{selected.endpoint_id && <Link className="primary-link" to="/test-console">{t('integration.flowBuilder.openTestConsole')}</Link>}</div>{exportForProduction.error instanceof Error && <div className="error-state compact">{exportForProduction.error.message}</div>}<section className="flow-output-grid"><JsonBlock title="Matcher" value={selected.matcher_group_json} searchable={false} /><JsonBlock title="Builder JSON" value={selected.builder_json ?? selected.action_json} searchable={false} /><CodeBlock title="curl" code={selected.curl_example} language="bash" /><CodeBlock title="1C HTTP" code={selected.onec_http_example} language="bash" /></section></section>}
      {result !== null && <JsonBlock title={t('integration.flowBuilder.flowResult')} value={(result as Record<string, unknown>) ?? {}} searchable />}
    </div>
  );
}
