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

function humanType(value: string) {
  const labels: Record<string, string> = {
    external_api: 'Входящий HTTP-запрос',
    odata_lookup: 'Цепочка OData',
    onec: '1C',
    website: 'Сайт',
    wms: 'WMS',
    printer: 'Принтер',
    internal: 'Внутренний flow',
    manual: 'Ручной запуск',
    webhook: 'Webhook',
  };
  return labels[value] ?? value;
}

function getBodyPathEquals(matcher: Record<string, unknown>, path: string) {
  const rules = Array.isArray(matcher.rules) ? matcher.rules : [];
  const rule = rules.find((item) => item && typeof item === 'object' && (item as Record<string, unknown>).type === 'body_path_equals' && (item as Record<string, unknown>).path === path) as Record<string, unknown> | undefined;
  return typeof rule?.value === 'string' ? rule.value : null;
}

function builderSteps(builder: Record<string, unknown> | null) {
  const steps = builder && Array.isArray(builder.steps) ? builder.steps : [];
  return steps.filter((step): step is Record<string, unknown> => Boolean(step && typeof step === 'object'));
}

function readPath(source: unknown, path: string) {
  return path.split('.').reduce<unknown>((current, part) => {
    if (current && typeof current === 'object' && part in current) return (current as Record<string, unknown>)[part];
    return undefined;
  }, source);
}

function formatPreviewValue(value: unknown) {
  if (value === undefined) return 'не найдено в примере';
  if (value === null) return 'null';
  return typeof value === 'object' ? JSON.stringify(value) : String(value);
}

function renderTemplatePreview(value: string, scope: Record<string, unknown>) {
  return value.replace(/{{\s*([A-Za-z0-9_А-Яа-яЁё.-]+)\s*}}/g, (match, path: string) => {
    const resolved = readPath(scope, path);
    return resolved === undefined || resolved === null ? match : String(resolved);
  });
}

function unresolvedTemplates(value: string) {
  return Array.from(value.matchAll(/{{\s*([^}]+)\s*}}/g)).map((match) => match[1].trim());
}

function decodeDisplayUrl(value: string) {
  if (!value.includes('%')) return value;
  try {
    return decodeURI(value);
  } catch {
    return value;
  }
}

function odataPath(step: Record<string, unknown>, scope: Record<string, unknown>) {
  const resource = renderTemplatePreview(String(step.resource ?? ''), scope);
  const params = new URLSearchParams();
  const top = step.top === undefined || step.top === null ? '' : String(step.top);
  const filter = renderTemplatePreview(String(step.filter ?? ''), scope);
  const select = Array.isArray(step.select) ? step.select.join(',') : String(step.select ?? '');
  if (top) params.set('$top', top);
  if (filter) params.set('$filter', filter);
  if (select) params.set('$select', select);
  params.set('$format', 'json');
  const query = params.toString().replaceAll('%24', '$').replaceAll('%2C', ',').replaceAll('%7B%7B', '{{').replaceAll('%7D%7D', '}}');
  return decodeDisplayUrl(query ? `${resource}?${query}` : resource);
}

function mockODataValue(step: Record<string, unknown>) {
  const mockItems = Array.isArray(step.mock_items) ? step.mock_items : null;
  if (!mockItems) return undefined;
  return Number(step.top ?? 1) === 1 ? mockItems[0] ?? null : mockItems;
}

function stepSummary(step: Record<string, unknown>, index: number, scope: Record<string, unknown>) {
  const type = String(step.type ?? '');
  if (type === 'read_variable') {
    const path = String(step.path ?? '');
    const value = readPath(scope, path);
    return { title: `Прочитать ${String((step.save_as ?? path) || 'поле')}`, detail: path, preview: formatPreviewValue(value), unresolved: [] };
  }
  if (type === 'odata_query') {
    const resource = String(step.resource ?? '');
    const filter = String(step.filter ?? '');
    const renderedResource = renderTemplatePreview(resource, scope);
    const renderedFilter = filter ? renderTemplatePreview(filter, scope) : '';
    const pathPreview = odataPath(step, scope);
    return {
      title: `OData: ${String(step.name ?? resource ?? `шаг ${index + 1}`)}`,
      detail: resource,
      preview: pathPreview,
      unresolved: [...unresolvedTemplates(renderedResource), ...unresolvedTemplates(renderedFilter), ...unresolvedTemplates(pathPreview)],
    };
  }
  if (type === 'foreach') {
    const nested = (step.step && typeof step.step === 'object' ? step.step : step.do && typeof step.do === 'object' ? step.do : {}) as Record<string, unknown>;
    const source = String(step.items ?? '');
    const itemAs = String(step.item_as ?? 'item');
    let preview = '';
    const sourceItems = readPath(scope, source);
    if (Array.isArray(sourceItems) && sourceItems.length > 0) {
      preview = odataPath(nested, { ...scope, [itemAs]: sourceItems[0], foreach: { item: sourceItems[0], index: 0 } });
    } else if (nested.resource) {
      preview = odataPath(nested, scope);
    }
    return {
      title: `Повтор по массиву: ${String(step.name ?? step.save_as ?? `шаг ${index + 1}`)}`,
      detail: `${source || 'массив не задан'} -> ${String(step.save_as ?? step.id ?? 'result')}`,
      preview,
      unresolved: preview ? unresolvedTemplates(preview) : [],
    };
  }
  if (type === 'return_response') return { title: 'Вернуть результат вызывающей системе', detail: 'Синхронный ответ из собранных данных' };
  if (type === 'call_endpoint') return { title: 'Отправить результат во внешнюю систему', detail: String(step.url ?? step.target ?? '') };
  return { title: String((step.name ?? type) || `Шаг ${index + 1}`), detail: type };
}

function flowStepSummaries(builder: Record<string, unknown> | null, testPayload: Record<string, unknown> | null) {
  const scope: Record<string, unknown> = { request: { body: testPayload ?? {} } };
  return builderSteps(builder).map((step, index) => {
    const summary = stepSummary(step, index, scope);
    if (String(step.type ?? '') === 'read_variable') {
      const saveAs = String(step.save_as ?? '');
      const path = String(step.path ?? '');
      if (saveAs) scope[saveAs] = readPath(scope, path);
    }
    if (String(step.type ?? '') === 'odata_query') {
      const saveAs = String(step.save_as ?? '');
      const value = mockODataValue(step);
      if (saveAs && value !== undefined) scope[saveAs] = value;
    }
    if (String(step.type ?? '') === 'foreach') {
      const nested = (step.step && typeof step.step === 'object' ? step.step : step.do && typeof step.do === 'object' ? step.do : {}) as Record<string, unknown>;
      const source = readPath(scope, String(step.items ?? ''));
      const nestedValue = mockODataValue(nested);
      if (String(step.save_as ?? '') && Array.isArray(source) && nestedValue !== undefined) {
        scope[String(step.save_as)] = source.flatMap(() => Array.isArray(nestedValue) ? nestedValue : nestedValue ? [nestedValue] : []);
      }
    }
    return { step, summary };
  });
}

function targetSummary(builder: Record<string, unknown> | null) {
  const target = builder?.target;
  if (!target || typeof target !== 'object') return null;
  const data = target as Record<string, unknown>;
  return { method: String(data.method ?? 'POST'), url: String(data.url ?? '') };
}

function publicEndpointFromCurl(flow: IntegrationFlow) {
  const match = flow.curl_example.match(/curl\s+-X\s+POST\s+(\S+)/);
  return match?.[1] ?? flow.endpoint_url;
}

function finalActionSummary(flow: IntegrationFlow) {
  const builder = flow.builder_json;
  const target = targetSummary(builder);
  if (target?.url) {
    return {
      title: 'Отправить результат во внешнюю систему',
      line: `${target.method} ${target.url}`,
      detail: 'После выполнения OData-шагов flow отправит собранный результат на этот внешний URL.',
      missingTarget: false,
    };
  }
  const nextAction = String(builder?.next_action ?? '');
  if (nextAction === 'send_result') {
    return {
      title: 'Отправка наружу не завершена',
      line: 'URL внешней системы не задан',
      detail: 'Flow был выбран как отправка результата, но target URL не сохранился. Откройте builder и укажите Method + URL.',
      missingTarget: true,
    };
  }
  return {
    title: 'Вернуть результат вызывающей системе',
    line: `Ответ на входящий POST ${publicEndpointFromCurl(flow)}`,
    detail: 'Отдельного внешнего URL нет: результат возвращается в HTTP-ответ тому, кто вызвал этот endpoint.',
    missingTarget: false,
  };
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
  const installOperationKeyODataChain = useMutation({ mutationFn: integrationFlowsApi.installOperationKeyODataChain, onSuccess: (data) => { setResult(data); setSelectedId(data.id); refresh(); } });
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
  const selectedFinalAction = selected ? finalActionSummary(selected) : null;

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
        <div className="hero-meta" data-tour="flow-presets"><button className="primary-button" onClick={() => installOperationKeyODataChain.mutate()} disabled={installOperationKeyODataChain.isPending}>Install OData chain flow</button><button className="ghost-button" onClick={() => installBuilderPreset.mutate()} disabled={installBuilderPreset.isPending}>{t('integration.flowBuilder.installODataPreset')}</button><button className="ghost-button" onClick={() => installPreset.mutate()} disabled={installPreset.isPending}>{t('integration.flowBuilder.installMarkingPreset')}</button><span className="microcopy">{t('integration.flowBuilder.flowPipeline')}</span></div>
      </section>

      <section className="panel purpose-banner">
        <span className="eyebrow">Назначение страницы</span>
        <h2>Здесь живут уже собранные интеграции</h2>
        <p>Если вы начинаете с бизнес-задачи, лучше открыть “Создать интеграцию” или Workbench. Эта страница нужна для просмотра, теста, дублирования, экспорта в продакшен и тонкой настройки потоков, которые уже появились после мастера.</p>
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
          {[create, installPreset, installBuilderPreset, installOperationKeyODataChain, testMatcher].find((item) => item.error)?.error instanceof Error && <div className="error-state compact">{([create, installPreset, installBuilderPreset, installOperationKeyODataChain, testMatcher].find((item) => item.error)?.error as Error).message}</div>}
        </form>
      </section>

      {selected && <VersionHistoryPanel objectType="integration_flow" objectId={selected.id} compact onChanged={refresh} />}
      {selected && (
        <section className="panel flow-detail" data-tour="flow-detail">
          <div className="panel-toolbar">
            <div>
              <span className="eyebrow">{t('integration.flowBuilder.selectedFlow')}</span>
              <h2>{selected.name}</h2>
              <p>{selected.description}</p>
            </div>
            <StatusBadge status={selected.enabled ? 'ok' : 'cancelled'} label={selected.enabled ? t('integration.flowBuilder.enabled') : t('integration.flowBuilder.disabled')} />
          </div>
          <div className="flow-overview-grid">
            <span>Endpoint<strong>{selected.endpoint_url}</strong></span>
            <span>Trigger key<strong>{(getBodyPathEquals(selected.matcher_group_json, 'operation') ?? getBodyPathEquals(selected.matcher_group_json, 'sinc')) || 'Не задан'}</strong></span>
            <span>{t('integration.flowBuilder.source')}<strong>{humanType(selected.source_type)}</strong></span>
            <span>{t('integration.flowBuilder.target')}<strong>{humanType(selected.target_type)}</strong></span>
          </div>
          <div className="action-row">
            <Link className="primary-button" to={`/integration-flows/${selected.id}/builder`}>{t('integration.flowBuilder.openVisualBuilder')}</Link>
            <button className="primary-button" onClick={() => exportForProduction.mutate(selected)} disabled={exportForProduction.isPending}>{t('integration.flowBuilder.exportProduction')}</button>
            <Link className="ghost-button" to={`/config-history/integration_flow/${selected.id}`}>{t('integration.flowBuilder.releaseControl')}</Link>
            <button className="primary-button" onClick={() => runSelectedFlow(selected)} disabled={testFlow.isPending}>{t('integration.flowBuilder.testThisFlow')}</button>
            <button className="ghost-button" onClick={() => navigator.clipboard?.writeText(selected.endpoint_url)}>{t('integration.flowBuilder.copyUrl')}</button>
            <button className="ghost-button" onClick={() => duplicate.mutate(selected.id)} disabled={duplicate.isPending}>{t('integration.flowBuilder.duplicate')}</button>
            <button className="ghost-button" onClick={() => exportFlow.mutate(selected.id)} disabled={exportFlow.isPending}>{t('integration.flowBuilder.export')}</button>
            {selected.endpoint_id && <Link className="primary-link" to="/test-console">{t('integration.flowBuilder.openTestConsole')}</Link>}
          </div>
          {exportForProduction.error instanceof Error && <div className="error-state compact">{exportForProduction.error.message}</div>}
          <section className="flow-operator-grid">
            <article className="flow-operator-card">
              <span className="eyebrow">Входной JSON</span>
              <JsonBlock title="Test payload" value={selected.test_payload_json ?? {}} searchable={false} />
            </article>
            <article className="flow-operator-card">
              <span className="eyebrow">Цепочка шагов</span>
              <div className="flow-step-list">
                {flowStepSummaries(selected.builder_json, selected.test_payload_json).length === 0 ? <span className="microcopy">Шаги не описаны в builder JSON.</span> : flowStepSummaries(selected.builder_json, selected.test_payload_json).map(({ step, summary }, index) => {
                  const isOData = String(step.type ?? '') === 'odata_query';
                  const isForEach = String(step.type ?? '') === 'foreach';
                  const nestedStep = (step.step && typeof step.step === 'object' ? step.step : step.do && typeof step.do === 'object' ? step.do : {}) as Record<string, unknown>;
                  const unresolved = 'unresolved' in summary ? summary.unresolved ?? [] : [];
                  return (
                    <div className="flow-step-card" key={`${String(step.id ?? step.type)}-${index}`}>
                      <span>{index + 1}</span>
                      <div>
                        <strong>{summary.title}</strong>
                        <small>{summary.detail}</small>
                        {'preview' in summary && summary.preview && <code>{summary.preview}</code>}
                        {isOData && (
                          <dl className="flow-step-settings">
                            <div><dt>Connection</dt><dd>{String(step.connection ?? '')}</dd></div>
                            <div><dt>Resource</dt><dd>{String(step.resource ?? '')}</dd></div>
                            <div><dt>$filter</dt><dd>{String(step.filter ?? '') || 'не задан'}</dd></div>
                            <div><dt>$select</dt><dd>{Array.isArray(step.select) ? step.select.join(', ') : String(step.select ?? '') || 'не задан'}</dd></div>
                            <div><dt>$top</dt><dd>{String(step.top ?? '') || 'не задан'}</dd></div>
                            <div><dt>Pagination</dt><dd>{step.paginate ? 'читать следующие страницы' : 'только первая страница'}</dd></div>
                          </dl>
                        )}
                        {isForEach && (
                          <dl className="flow-step-settings">
                            <div><dt>Array</dt><dd>{String(step.items ?? '') || 'не задан'}</dd></div>
                            <div><dt>Item variable</dt><dd>{String(step.item_as ?? 'item')}</dd></div>
                            <div><dt>Save as</dt><dd>{String(step.save_as ?? step.id ?? '')}</dd></div>
                            <div><dt>Mode</dt><dd>{step.flatten === false ? 'сохранить результат каждой итерации отдельно' : 'объединить все строки в один массив'}</dd></div>
                            <div><dt>Nested OData resource</dt><dd>{String(nestedStep.resource ?? '') || 'не задан'}</dd></div>
                            <div><dt>Nested $filter</dt><dd>{String(nestedStep.filter ?? '') || 'не задан'}</dd></div>
                            <div><dt>Nested $select</dt><dd>{Array.isArray(nestedStep.select) ? nestedStep.select.join(', ') : String(nestedStep.select ?? '') || 'не задан'}</dd></div>
                            <div><dt>Nested $top</dt><dd>{String(nestedStep.top ?? '') || 'не задан'}</dd></div>
                            <div><dt>Nested pagination</dt><dd>{nestedStep.paginate ? 'читать следующие страницы' : 'только первая страница'}</dd></div>
                          </dl>
                        )}
                        {unresolved.length > 0 && <em>Значения появятся после выполнения предыдущих шагов: {unresolved.join(', ')}</em>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </article>
          </section>
          {selectedFinalAction && (
            <section className={`flow-target-card ${selectedFinalAction.missingTarget ? 'warning-card' : ''}`}>
              <span className="eyebrow">Финальное действие</span>
              <strong>{selectedFinalAction.title}</strong>
              <code>{selectedFinalAction.line}</code>
              <p className="microcopy">{selectedFinalAction.detail}</p>
              <Link className="ghost-button" to={`/integration-flows/${selected.id}/builder`}>Редактировать настройки</Link>
            </section>
          )}
          <section className="flow-output-grid">
            <CodeBlock title="curl" code={selected.curl_example} language="bash" />
            <CodeBlock title="1C HTTP" code={selected.onec_http_example} language="bash" />
          </section>
          <details className="technical-details">
            <summary>Технические настройки JSON</summary>
            <section className="flow-output-grid">
              <JsonBlock title="Matcher" value={selected.matcher_group_json} searchable={false} />
              <JsonBlock title="Builder JSON" value={selected.builder_json ?? selected.action_json} searchable={false} />
            </section>
          </details>
        </section>
      )}
      {result !== null && <JsonBlock title={t('integration.flowBuilder.flowResult')} value={(result as Record<string, unknown>) ?? {}} searchable />}
    </div>
  );
}
