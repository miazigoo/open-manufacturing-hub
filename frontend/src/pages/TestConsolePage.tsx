import { FormEvent, type ReactNode, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { integrationBusApi } from '../api/integrationBus';
import type { IntegrationEndpoint } from '../api/integrationBus';
import { integrationFlowsApi, type FlowBuilderPreviewResponse, type IntegrationFlow } from '../api/integrationFlows';
import { odataConnectionsApi } from '../api/odataConnections';
import { testConsoleApi } from '../api/testConsole';
import { xmlToolkitApi, type XmlPathItem } from '../api/xmlToolkit';
import { CodeEditor } from '../components/CodeEditor';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { XmlPathPicker } from '../components/xml/XmlPathPicker';
import { XmlResponseBuilder } from '../components/xml/XmlResponseBuilder';
import { getExternalErrorTranslation } from '../i18n/errors';
import { useI18n } from '../i18n/useI18n';

const jsonSample = asJson({ operation: 'lookup_order_products', Number: '260666/6938', device_type: 'toodoo' });
const xmlSample = '<Request>\n  <Operation>lookup_order_products</Operation>\n  <Number>260666/6938</Number>\n  <DeviceType>toodoo</DeviceType>\n</Request>';
const rawSample = 'lookup_order_products Number=260666/6938 device_type=toodoo';
const defaultJsonResponse = asJson({ success: true, order_uuid: '{{order.Ref_Key}}', order_number: '{{order.Number}}', products: '{{products}}' });
const defaultXmlResponse = '<Response>\n  <Success>true</Success>\n  <OrderUUID>{{order.Ref_Key}}</OrderUUID>\n  <OrderNumber>{{order.Number}}</OrderNumber>\n</Response>';
const defaultRawResponse = 'OK {{order.Ref_Key}}';

type PageMode = 'quick' | 'build';
type ResponseBodyType = 'json' | 'xml' | 'raw_text';

interface ODataStepDraft {
  id: string;
  name: string;
  connection: string;
  resource: string;
  filter: string;
  select: string;
  top: string;
  save_as: string;
  required: boolean;
}

interface ExtractedField { path: string; value: unknown }
interface XmlMappingDraft { name: string; path: string; required: boolean; mode: 'first' | 'all' }

function sampleForMode(mode: string) {
  if (mode === 'xml') return xmlSample;
  if (mode === 'raw_text') return rawSample;
  return jsonSample;
}

function normalizeTimelineUrl(url: string) {
  if (url.startsWith('/events/')) return url;
  if (/^[a-f0-9-]{20,}$/i.test(url)) return `/events/${url}`;
  return url;
}

function slugify(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 120) || 'request-response-flow';
}

function variableName(value: string) {
  const normalized = value.toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 48);
  if (!normalized) return 'odata_result';
  return /^[0-9]/.test(normalized) ? `v_${normalized}` : normalized;
}

function variableNameFromXmlPath(path: string, index = 0) {
  const last = (path.split('/').filter(Boolean).pop() || `field_${index + 1}`).replace(/\[\d+\]$/, '').replace(/^@/, '').split(':').pop() || `field_${index + 1}`;
  const aliases: Record<string, string> = { Номер: 'number', ИНН: 'inn', КПП: 'kpp', Код: 'code', Артикул: 'article', Количество: 'quantity', Документ: 'document', Operation: 'operation', Number: 'number', DeviceType: 'device_type' };
  const normalized = variableName(last);
  return aliases[last] || (normalized === 'odata_result' ? `field_${index + 1}` : normalized);
}

function parseJsonObject(value: string, label: string): Record<string, unknown> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(value || '{}') as unknown;
  } catch {
    throw new Error(`${label}: JSON не читается. Проверьте кавычки, запятые и закрывающие скобки.`);
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error(`${label}: нужен JSON-объект вида {"key":"value"}, а не массив или строка.`);
  return parsed as Record<string, unknown>;
}

function parseSample(inputMode: string, sample: string): Record<string, unknown> {
  if (inputMode === 'json') return parseJsonObject(sample, 'Пример входящего запроса');
  if (inputMode === 'xml') return { xml: sample };
  return { text: sample };
}

function extractFields(inputMode: string, sample: string): ExtractedField[] {
  if (inputMode === 'json') {
    try {
      const parsed = parseJsonObject(sample, 'Пример входящего запроса');
      return flattenJson(parsed).map(([path, value]) => ({ path: `request.body.${path}`, value }));
    } catch {
      return [];
    }
  }
  if (inputMode === 'xml') return [];
  return [{ path: 'request.raw_text', value: sample.slice(0, 140) }];
}

function flattenJson(value: unknown, prefix = ''): Array<[string, unknown]> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return prefix ? [[prefix, value]] : [];
  return Object.entries(value as Record<string, unknown>).flatMap(([key, child]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    if (child && typeof child === 'object' && !Array.isArray(child)) return flattenJson(child, path);
    return [[path, child]];
  });
}

function previewValue(value: unknown) {
  if (value === null || value === undefined) return '';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function contentTypeFor(type: ResponseBodyType) {
  if (type === 'xml') return 'application/xml';
  if (type === 'raw_text') return 'text/plain';
  return 'application/json';
}

function bodyForType(type: ResponseBodyType) {
  if (type === 'xml') return defaultXmlResponse;
  if (type === 'raw_text') return defaultRawResponse;
  return defaultJsonResponse;
}

export function TestConsolePage() {
  const { language, t } = useI18n();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const exampleId = searchParams.get('exampleId');
  const trainingExampleId = searchParams.get('trainingExampleId');
  const requestedMode = searchParams.get('mode') === 'build' ? 'build' : 'quick';
  const requestedInput = searchParams.get('input') === 'xml' ? 'xml' : searchParams.get('input') === 'raw_text' ? 'raw_text' : 'json';
  const endpoints = useQuery({ queryKey: ['bus-endpoints'], queryFn: integrationBusApi.endpoints });
  const odataConnections = useQuery({ queryKey: ['odata-connections'], queryFn: odataConnectionsApi.list });
  const docsExample = useQuery({ queryKey: ['docs-example', exampleId], queryFn: () => testConsoleApi.docsExample(exampleId!), enabled: Boolean(exampleId) });
  const trainingExample = useQuery({ queryKey: ['training-example', trainingExampleId], queryFn: () => testConsoleApi.trainingExample(trainingExampleId!), enabled: Boolean(trainingExampleId) });
  const [mode, setMode] = useState<PageMode>(requestedMode);
  const [form, setForm] = useState({ endpoint_id: '', input_mode: requestedInput, headers_json: '{}', body: sampleForMode(requestedInput) });
  const [formError, setFormError] = useState<string | null>(null);
  const [builderError, setBuilderError] = useState<string | null>(null);
  const [createdFlow, setCreatedFlow] = useState<IntegrationFlow | null>(null);
  const [builderResult, setBuilderResult] = useState<Record<string, unknown> | FlowBuilderPreviewResponse | IntegrationFlow | null>(null);
  const [wizard, setWizard] = useState({
    source: 'external_api',
    name: 'Lookup order products',
    slug: 'lookup-order-products',
    authMode: 'none',
    token: '',
    inputMode: requestedInput,
    sample: sampleForMode(requestedInput),
    action: 'odata_multiple',
    responseMode: 'sync_response',
    responseType: (requestedInput === 'xml' ? 'xml' : 'json') as ResponseBodyType,
    statusCode: '200',
    headers: `{\n  "Content-Type": "${requestedInput === 'xml' ? 'application/xml' : 'application/json'}"\n}`,
    responseBody: requestedInput === 'xml' ? defaultXmlResponse : defaultJsonResponse,
  });
  const [odataSteps, setODataSteps] = useState<ODataStepDraft[]>([
    { id: 'get_order', name: 'Найти заказ по номеру', connection: '', resource: 'Document_ЗаказНаПроизводство2_2', filter: "Number eq '{{request.body.Number}}'", select: 'Ref_Key,Number,Date,Posted', top: '1', save_as: 'order', required: true },
  ]);
  const [xmlMappings, setXmlMappings] = useState<XmlMappingDraft[]>([]);
  const xmlParse = useQuery({ queryKey: ['workbench-xml-parse', wizard.sample], queryFn: () => xmlToolkitApi.parse(wizard.sample), enabled: wizard.inputMode === 'xml' && wizard.sample.trim().includes('<') });

  const send = useMutation({
    mutationFn: (payload: { dry_run: boolean; headers: Record<string, string>; bodyJson: Record<string, unknown> | null }) =>
      testConsoleApi.send({
        endpoint_id: form.endpoint_id,
        input_mode: form.input_mode,
        headers_json: payload.headers,
        body_text: form.body,
        body_json: payload.bodyJson,
        dry_run: payload.dry_run,
      }),
  });
  const preview = useMutation({ mutationFn: () => integrationFlowsApi.previewBuilder({ builder_json: buildBuilderJson(), sample_request: sampleForPreview(), run_real_queries: false }), onSuccess: setBuilderResult });
  const createFlow = useMutation({
    mutationFn: () => integrationFlowsApi.create(buildFlowPayload()),
    onSuccess: (flow) => {
      setCreatedFlow(flow);
      setBuilderResult(flow);
      queryClient.invalidateQueries({ queryKey: ['bus-endpoints'] });
      queryClient.invalidateQueries({ queryKey: ['integration-flows'] });
    },
  });
  const testCreated = useMutation({
    mutationFn: () => {
      if (!createdFlow) throw new Error('Сначала сохраните интеграцию, потом отправьте тестовый запрос.');
      return integrationFlowsApi.test(createdFlow.id, {
        input_mode: wizard.inputMode,
        payload_json: wizard.inputMode === 'json' ? parseJsonObject(wizard.sample, 'Пример входящего запроса') : null,
        payload_text: wizard.inputMode === 'json' ? null : wizard.sample,
        headers_json: headersForWizard(),
        dry_run: false,
      });
    },
    onSuccess: setBuilderResult,
  });

  useEffect(() => {
    const loadedExample = trainingExample.data ?? docsExample.data;
    if (!loadedExample || endpoints.isLoading) return;
    const endpoint = endpoints.data?.find((item) => item.slug === loadedExample.endpoint_slug);
    setForm({ endpoint_id: endpoint?.id ?? '', input_mode: loadedExample.input_mode, headers_json: JSON.stringify(loadedExample.headers ?? {}, null, 2), body: loadedExample.input_mode === 'json' ? JSON.stringify(loadedExample.body ?? {}, null, 2) : loadedExample.body_text ?? '' });
  }, [docsExample.data, trainingExample.data, endpoints.data, endpoints.isLoading]);

  useEffect(() => {
    if (odataSteps[0]?.connection || !odataConnections.data?.length) return;
    const first = odataConnections.data.find((item) => item.enabled) ?? odataConnections.data[0];
    setODataSteps((steps) => steps.map((step) => ({ ...step, connection: first.name })));
  }, [odataConnections.data, odataSteps]);

  const timelineUrl = send.data?.timeline_url ? normalizeTimelineUrl(send.data.timeline_url) : null;
  const testTimelineUrl = (builderResult as { bus_response?: { timeline_url?: string } } | null)?.bus_response?.timeline_url ? normalizeTimelineUrl((builderResult as { bus_response: { timeline_url: string } }).bus_response.timeline_url) : null;
  const externalError = send.data?.external_error as { code?: string } | undefined;
  const translatedError = externalError ? getExternalErrorTranslation(externalError.code, t) : null;
  const selectedEndpoint = endpoints.data?.find((item) => item.id === form.endpoint_id) ?? null;
  const loadedExample = trainingExample.data ?? docsExample.data;
  const xmlFields = useMemo<ExtractedField[]>(() => (xmlParse.data?.paths ?? []).map((field, index) => ({ path: variableNameFromXmlPath(field.path, index), value: field.value_preview ?? field.type })), [xmlParse.data]);
  const extractedFields = useMemo(() => wizard.inputMode === 'xml' ? xmlFields : extractFields(wizard.inputMode, wizard.sample), [wizard.inputMode, wizard.sample, xmlFields]);
  const xmlFieldsForBuild = useMemo(() => xmlMappings.length ? xmlMappings : (xmlParse.data?.paths ?? []).slice(0, 12).map((field, index) => ({ name: variableNameFromXmlPath(field.path, index), path: field.path, required: index === 0, mode: 'first' as const })), [xmlMappings, xmlParse.data]);
  const responsePreview = useMemo(() => renderLocalResponsePreview(wizard.responseBody, wizard.responseType, wizard.sample, wizard.inputMode, odataSteps, extractedFields), [wizard.responseBody, wizard.responseType, wizard.sample, wizard.inputMode, odataSteps, extractedFields]);

  if (endpoints.isLoading) return <LoadingState label={t('integration.testConsoleLoading')} />;
  if (endpoints.error) return <ErrorState error={endpoints.error} />;

  function parsePayload(dryRun: boolean) {
    setFormError(null);
    let headers: Record<string, string>;
    let bodyJson: Record<string, unknown> | null = null;
    try { headers = JSON.parse(form.headers_json || '{}') as Record<string, string>; } catch { setFormError(t('integration.invalidHeaders')); return null; }
    if (form.input_mode === 'json') {
      try { bodyJson = JSON.parse(form.body || '{}') as Record<string, unknown>; } catch { setFormError(t('integration.invalidBody')); return null; }
    }
    return { dry_run: dryRun, headers, bodyJson };
  }

  function run(dryRun: boolean) {
    const payload = parsePayload(dryRun);
    if (payload) send.mutate(payload);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    run(false);
  }

  function updateWizard(patch: Partial<typeof wizard>) {
    setWizard((current) => ({ ...current, ...patch }));
  }

  function changeInputMode(inputMode: string) {
    updateWizard({ inputMode, sample: sampleForMode(inputMode) });
    if (inputMode === 'xml') {
      setODataSteps((steps) => steps.map((step, index) => index === 0 ? { ...step, filter: "Number eq '{{number}}'" } : step));
    }
    if (inputMode === 'json') {
      setODataSteps((steps) => steps.map((step, index) => index === 0 ? { ...step, filter: "Number eq '{{request.body.Number}}'" } : step));
    }
    setXmlMappings([]);
  }

  function changeResponseType(responseType: ResponseBodyType) {
    updateWizard({ responseType, responseBody: bodyForType(responseType), headers: JSON.stringify({ 'Content-Type': contentTypeFor(responseType) }, null, 2) });
  }

  function addODataStep() {
    const previous = odataSteps[odataSteps.length - 1];
    const nextIndex = odataSteps.length + 1;
    setODataSteps([...odataSteps, { id: `odata_${nextIndex}`, name: `OData шаг ${nextIndex}`, connection: previous?.connection || '', resource: "Document_ЗаказНаПроизводство2_2(guid'{{order.Ref_Key}}')/Продукция", filter: '', select: 'Ref_Key,LineNumber,Номенклатура_Key,Количество', top: '100', save_as: 'products', required: true }]);
  }

  function updateODataStep(index: number, patch: Partial<ODataStepDraft>) {
    setODataSteps(odataSteps.map((step, itemIndex) => itemIndex === index ? { ...step, ...patch } : step));
  }

  function headersForWizard(): Record<string, string> {
    return parseJsonObject(wizard.headers, 'Заголовки ответа') as Record<string, string>;
  }

  function sampleForPreview() {
    return parseSample(wizard.inputMode, wizard.sample);
  }

  function buildBuilderJson() {
    const responseBody = wizard.responseType === 'json' ? parseJsonObject(wizard.responseBody, 'Тело ответа') : undefined;
    const headers = headersForWizard();
    const readSteps = wizard.inputMode === 'xml'
      ? [{
          id: 'extract_xml_fields',
          type: 'xml_extract',
          name: 'Extract XML fields',
          source: 'request.xml',
          fields: xmlFieldsForBuild,
        }]
      : extractedFields
      .filter((field) => field.path.startsWith('request.body.') || field.path.startsWith('xml.'))
      .slice(0, 12)
      .map((field) => {
        const name = variableName(field.path.split('.').pop() || field.path);
        const path = field.path;
        return { id: `read_${name}`, type: 'read_variable', name: `Read ${name}`, path, save_as: name };
      });
    return {
      version: 1,
      input: { endpoint_slug: wizard.slug, input_mode: wizard.inputMode, response_mode: wizard.responseMode },
      steps: [
        ...readSteps,
        ...odataSteps.map((step) => ({ id: step.id, type: 'odata_query', name: step.name, connection: step.connection, resource: step.resource, filter: step.filter, select: step.select.split(',').map((item) => item.trim()).filter(Boolean), top: Number(step.top) || 1, save_as: variableName(step.save_as), required: step.required })),
        wizard.responseType === 'json'
          ? { id: 'return_response', type: 'return_response', name: 'Return JSON response', response_body_type: 'json', status_code: Number(wizard.statusCode) || 200, headers, body: responseBody }
          : { id: 'return_response', type: 'return_response', name: `Return ${wizard.responseType} response`, response_body_type: wizard.responseType, status_code: Number(wizard.statusCode) || 200, headers, body_template: wizard.responseBody },
      ],
    };
  }

  function buildFlowPayload() {
    setBuilderError(null);
    const sample = wizard.inputMode === 'json' ? parseJsonObject(wizard.sample, 'Пример входящего запроса') : null;
    const builder = buildBuilderJson();
    return {
      name: wizard.name,
      slug: slugify(wizard.slug),
      description: 'Created from Request/Response Workbench: receive request, run OData lookups and return a synchronous response.',
      enabled: true,
      source_type: wizard.source,
      target_type: 'odata_lookup',
      endpoint: { input_mode: wizard.inputMode, response_mode: wizard.responseMode, auth_mode: wizard.authMode, auth_config_json: wizard.authMode === 'static_token' ? { token: wizard.token } : {} },
      matcher_group_json: { mode: 'all', rules: [{ type: 'always' }] },
      action_json: { type: 'return_response', operation: slugify(wizard.slug).replaceAll('-', '_'), business_object: 'RequestResponseIntegration' },
      response_config_json: { response_mode: wizard.responseMode, response_body_type: wizard.responseType, status_code: Number(wizard.statusCode) || 200, headers: headersForWizard() },
      builder_json: builder,
      test_payload_json: sample,
      test_payload_text: wizard.inputMode === 'json' ? null : wizard.sample,
    };
  }

  function safePreview() {
    setBuilderError(null);
    try { preview.mutate(); } catch (error) { setBuilderError(error instanceof Error ? error.message : 'Не удалось собрать preview интеграции. Проверьте входящий JSON, заголовки и тело ответа.'); }
  }

  function safeCreate() {
    setBuilderError(null);
    try { createFlow.mutate(); } catch (error) { setBuilderError(error instanceof Error ? error.message : 'Не удалось сохранить интеграцию. Проверьте обязательные поля и OData-шаги.'); }
  }

  function addXmlMapping(field: XmlPathItem) {
    const index = xmlMappings.length;
    const name = variableNameFromXmlPath(field.path, index);
    if (xmlMappings.some((item) => item.path === field.path)) return;
    setXmlMappings([...xmlMappings, { name, path: field.path, required: index === 0, mode: field.repeated ? 'all' : 'first' }]);
  }

  return (
    <div className="page-stack request-response-workbench">
      <section className="page-header enterprise-hero request-response-hero">
        <span className="eyebrow">{language === 'en' ? 'Request/Response Workbench' : language === 'zh' ? '请求/响应工作台' : 'Мастер запроса и ответа'}</span>
        <h1>{language === 'en' ? 'Receive a request, run OData, return the answer.' : language === 'zh' ? '接收请求，查询 OData，并返回响应。' : 'Внешний сервис вызывает OMH, OMH делает OData и сразу отвечает.'}</h1>
        <p>{language === 'en' ? 'Use one page to test an inbound endpoint or build a real synchronous integration from a sample request.' : language === 'zh' ? '在一个页面测试入口端点，或从样例请求创建同步集成。' : 'Одна вкладка для реального сценария: вставить входящий запрос, выбрать OData-действия, собрать JSON/XML/raw ответ, проверить и сохранить интеграцию.'}</p>
        <div className="hero-meta"><span className="microcopy">POST /api/bus/in/{mode === 'build' ? slugify(wizard.slug) : selectedEndpoint?.slug || 'endpoint'}</span></div>
      </section>

      <section className="guidance-strip">
        <div className="guidance-head">
          <div>
            <span className="eyebrow">Как выбрать режим</span>
            <h2>Проверяйте существующий endpoint или собирайте интеграцию пошагово</h2>
            <p>Если endpoint уже опубликован, используйте быструю проверку: выберите endpoint, вставьте тело запроса и откройте Timeline. Если интеграции ещё нет, включите сборку: мастер проведёт от примера payload до OData-шагов, ответа и сохранённого flow.</p>
          </div>
          <div className="action-row wrap-actions">
            <button type="button" className={mode === 'quick' ? 'primary-button' : 'ghost-button'} onClick={() => setMode('quick')}>Проверить endpoint</button>
            <button type="button" className={mode === 'build' ? 'primary-button' : 'ghost-button'} onClick={() => setMode('build')}>Собрать интеграцию</button>
            <Link className="ghost-button" to="/training">Учебный пример</Link>
          </div>
        </div>
        <div className="guidance-step-grid">
          <div className="guidance-step-card"><span>Quick</span><strong>Endpoint уже есть</strong><small>Подходит для smoke-test, проверки token/header/body и разбора ответа.</small></div>
          <div className="guidance-step-card"><span>Build</span><strong>Endpoint ещё нужен</strong><small>Подходит для новой синхронной интеграции с OData lookup и JSON/XML/raw ответом.</small></div>
          <div className="guidance-step-card"><span>After run</span><strong>Смотрите Timeline</strong><small>После отправки запроса проверяйте шаги, внешние ответы и понятную диагностику.</small></div>
        </div>
      </section>

      <div className="segmented-control request-response-mode"><button className={mode === 'quick' ? 'active' : ''} onClick={() => setMode('quick')}>Проверить endpoint</button><button className={mode === 'build' ? 'active' : ''} onClick={() => setMode('build')}>Собрать интеграцию</button></div>

      {mode === 'quick' ? renderQuickSend() : renderBuildIntegration()}
    </div>
  );

  function renderQuickSend() {
    return (
      <div className="two-column-page">
        <form className="panel form-panel stack-form" onSubmit={submit}>
          <span className="eyebrow">Быстрая проверка</span>
          <h2>Проверить существующий endpoint</h2>
          <p className="microcopy">Быстрый режим: выберите endpoint, вставьте JSON/XML/raw body и посмотрите ответ с Timeline.</p>
          {loadedExample && <div className="docs-example-loaded"><strong>{t(trainingExample.data ? 'integration.loadedTrainingExample' : 'integration.loadedDocsExample', { title: loadedExample.title[language] ?? loadedExample.title.en ?? loadedExample.id })}</strong><span>{t('integration.endpointSlug', { slug: loadedExample.endpoint_slug })}</span>{!form.endpoint_id && <small>{t('integration.endpointMissing')}</small>}</div>}
          {docsExample.error instanceof Error && <div className="error-state compact">{docsExample.error.message}</div>}
          {trainingExample.error instanceof Error && <div className="error-state compact">{trainingExample.error.message}</div>}
          <label className="field-label" data-tour="test-endpoint">{t('integration.endpoint')}<select value={form.endpoint_id} onChange={(event) => { const endpoint = endpoints.data?.find((item) => item.id === event.target.value); const nextMode = endpoint?.input_mode ?? form.input_mode; setForm({ ...form, endpoint_id: event.target.value, input_mode: nextMode, body: sampleForMode(nextMode) }); }}><option value="">{t('integration.selectEndpoint')}</option>{(endpoints.data ?? []).map((endpoint) => <option key={endpoint.id} value={endpoint.id}>{endpointLabel(endpoint)}</option>)}</select></label>
          {selectedEndpoint && <div className="endpoint-select-preview"><strong>{endpointDisplayName(selectedEndpoint)}</strong><span>/api/bus/in/{selectedEndpoint.slug}</span><small>{selectedEndpoint.input_mode.toUpperCase()} · {responseModeLabel(selectedEndpoint.response_mode)} · {selectedEndpoint.auth_mode === 'static_token' ? 'защищено token' : 'без token для входящего запроса'}</small></div>}
          <label className="field-label">{t('integration.inputMode')}<select value={form.input_mode} onChange={(event) => setForm({ ...form, input_mode: event.target.value, body: sampleForMode(event.target.value) })}><option value="json">json</option><option value="xml">xml</option><option value="raw_text">raw_text</option></select></label>
          <label className="field-label">{t('integration.headersJson')}<CodeEditor value={form.headers_json} onChange={(value) => setForm({ ...form, headers_json: value })} language="json" minRows={5} /></label>
          <label className="field-label" data-tour="test-body">{t('integration.body')}<CodeEditor value={form.body} onChange={(value) => setForm({ ...form, body: value })} language={form.input_mode === 'json' ? 'json' : form.input_mode === 'xml' ? 'xml' : 'text'} minRows={11} /></label>
          {formError && <div className="error-state compact">{formError}</div>}
          {send.error instanceof Error && <div className="error-state compact">{send.error.message}</div>}
          <div className="action-row" data-tour="test-actions"><button className="primary-button" disabled={!form.endpoint_id || send.isPending}>{t('integration.send')}</button><button type="button" className="ghost-button" disabled={!form.endpoint_id || send.isPending} onClick={() => run(true)}>{t('common.buttons.dryRun')}</button></div>
        </form>
        <section className="page-stack">
          {timelineUrl && <Link className="primary-link" to={timelineUrl}>{t('integration.openLastTimeline')}</Link>}
          {translatedError && <div className="error-state compact"><strong>{translatedError.title}</strong><span>{translatedError.hint}</span></div>}
          {send.data?.external_error && <JsonBlock title={t('integration.externalError')} value={send.data.external_error} searchable={false} />}
          {send.data ? <JsonBlock title={t('integration.response')} value={send.data} searchable /> : <div className="test-console-empty-response"><span className="eyebrow">{t('integration.response')}</span><strong>{t('integration.responseEmptyTitle')}</strong><p>{t('integration.responseEmptyDetail')}</p></div>}
        </section>
      </div>
    );
  }

  function renderBuildIntegration() {
    return (
      <div className="request-response-grid">
        <section className="panel stack-form request-response-builder">
          <WizardStep index="01" title="Кто будет вызывать OMH" description="Опишите внешний сервис и endpoint, который он будет дергать.">
            <div className="metadata-grid compact-grid no-margin"><label className="field-label">Кто обращается<select value={wizard.source} onChange={(event) => updateWizard({ source: event.target.value })}><option value="external_api">Внешний API / сайт</option><option value="onec">1C</option><option value="wms">WMS</option><option value="webhook">Webhook</option><option value="manual">Другое</option></select></label><label className="field-label">Название интеграции<input value={wizard.name} onChange={(event) => updateWizard({ name: event.target.value, slug: slugify(event.target.value) })} /></label><label className="field-label">Адрес endpoint<input value={wizard.slug} onChange={(event) => updateWizard({ slug: slugify(event.target.value) })} /></label></div>
            <div className="metadata-grid compact-grid no-margin"><label className="field-label">Защита входящего запроса<select value={wizard.authMode} onChange={(event) => updateWizard({ authMode: event.target.value })}><option value="none">без token</option><option value="static_token">статический token</option></select></label>{wizard.authMode === 'static_token' && <label className="field-label">Token<input value={wizard.token} onChange={(event) => updateWizard({ token: event.target.value })} /></label>}<span className="success-note">Куда отправлять запрос<span>POST /api/bus/in/{slugify(wizard.slug)}</span></span></div>
          </WizardStep>

          <WizardStep index="02" title="Что приходит во входящем запросе" description="Вставьте пример JSON, XML или raw text. Ниже сразу появятся поля, которые можно использовать в OData filter и ответе.">
            <label className="field-label">Формат входящего запроса<select value={wizard.inputMode} onChange={(event) => changeInputMode(event.target.value)}><option value="json">JSON</option><option value="xml">XML</option><option value="raw_text">raw text</option></select></label>
            <CodeEditor value={wizard.sample} onChange={(value) => updateWizard({ sample: value })} language={wizard.inputMode === 'json' ? 'json' : wizard.inputMode === 'xml' ? 'xml' : 'text'} minRows={8} />
            {wizard.inputMode === 'xml' && <XmlPathPicker xml={wizard.sample} onUseField={addXmlMapping} compact />}
            {wizard.inputMode === 'xml' && <SelectedXmlMappings mappings={xmlFieldsForBuild} onRemove={(path) => setXmlMappings(xmlMappings.filter((item) => item.path !== path))} />}
            <ExtractedFields fields={extractedFields} />
          </WizardStep>

          <WizardStep index="03" title="Что должен сделать OMH" description="Для этой задачи полноценно реализованы один или несколько OData-запросов. Остальные действия оставлены как будущие расширения.">
            <div className="metadata-grid request-action-cards">
              {[
                { title: 'Сразу вернуть входящий запрос', enabled: false },
                { title: 'Сделать один OData-запрос', enabled: true, value: 'odata_single' },
                { title: 'Сделать несколько OData-запросов', enabled: true, value: 'odata_multiple' },
                { title: 'Вызвать внешний API', enabled: false },
                { title: 'Вызвать HTTP-сервис 1C', enabled: false },
                { title: 'Напечатать этикетку', enabled: false },
                { title: 'Только создать событие', enabled: false },
              ].map((action) => <button type="button" key={action.title} className={`builder-help-card action-card ${action.enabled ? 'active' : ''}`} disabled={!action.enabled} onClick={() => updateWizard({ action: action.value ?? 'odata_multiple' })}><strong>{action.title}</strong><span>{action.enabled ? 'Доступно сейчас' : 'Будет позже, через advanced builder'}</span></button>)}
            </div>
            <div className="stack-form">
              {odataSteps.map((step, index) => <ODataStepEditor key={step.id} index={index} step={step} connections={odataConnections.data ?? []} fields={extractedFields} onChange={(patch) => updateODataStep(index, patch)} onRemove={() => setODataSteps(odataSteps.filter((_, itemIndex) => itemIndex !== index))} />)}
              <button type="button" className="ghost-button" onClick={addODataStep}>Добавить OData-запрос</button>
            </div>
          </WizardStep>

          <WizardStep index="04" title="Что вернуть внешнему сервису" description="Выберите sync/proxy/accepted mode и соберите тело ответа. JSON, XML и raw text поддерживаются здесь же.">
            <div className="metadata-grid compact-grid no-margin"><label className="field-label">Как отвечать<select value={wizard.responseMode} onChange={(event) => updateWizard({ responseMode: event.target.value })}><option value="sync_response">Вернуть свой ответ сразу</option><option value="proxy_response">Вернуть ответ target-системы</option><option value="accepted_event">Принять в очередь и вернуть event_id</option></select></label><label className="field-label">Формат ответа<select value={wizard.responseType} onChange={(event) => changeResponseType(event.target.value as ResponseBodyType)}><option value="json">JSON</option><option value="xml">XML</option><option value="raw_text">raw text</option></select></label><label className="field-label">HTTP статус<input value={wizard.statusCode} onChange={(event) => updateWizard({ statusCode: event.target.value })} /></label></div>
            <label className="field-label">Заголовки ответа<CodeEditor value={wizard.headers} onChange={(value) => updateWizard({ headers: value })} language="json" minRows={4} /></label>
            {wizard.responseType === 'xml'
              ? <XmlResponseBuilder value={wizard.responseBody} onChange={(value) => updateWizard({ responseBody: value })} variables={previewVariables(wizard.sample, wizard.inputMode, odataSteps, extractedFields)} hints={['{{order.Ref_Key}}', '{{order.Number}}', '{{products}}', '{{number}}']} />
              : <label className="field-label">Тело ответа<CodeEditor value={wizard.responseBody} onChange={(value) => updateWizard({ responseBody: value })} language={wizard.responseType === 'json' ? 'json' : 'text'} minRows={8} /></label>}
            <div className="hint-chip-row">{['{{order.Ref_Key}}', '{{order.Number}}', '{{products}}', '{{steps.get_order.first.Ref_Key}}', '{{request.body.Number}}'].map((hint) => <button key={hint} type="button" className="hint-chip" onClick={() => navigator.clipboard?.writeText(hint)}>{hint}</button>)}</div>
            <ResponsePreview type={wizard.responseType} value={responsePreview} status={wizard.statusCode} headers={wizard.headers} />
          </WizardStep>

          <WizardStep index="05" title="Проверить, сохранить и протестировать" description="Сначала preview без реального запроса, потом создать integration flow и отправить тестовый запрос с этой же страницы.">
            <div className="action-row wrap-actions"><button type="button" className="ghost-button" onClick={safePreview} disabled={preview.isPending}>Проверить без сохранения</button><button type="button" className="primary-button" onClick={safeCreate} disabled={createFlow.isPending || odataSteps.length === 0}>Сохранить интеграцию</button><button type="button" className="primary-button" onClick={() => testCreated.mutate()} disabled={!createdFlow || testCreated.isPending}>Отправить тестовый запрос</button>{createdFlow && <Link className="primary-link" to="/integration-flows">Открыть список интеграций</Link>}{testTimelineUrl && <Link className="primary-link" to={testTimelineUrl}>Открыть Timeline</Link>}</div>
            {builderError && <div className="error-state compact">{builderError}</div>}
            {preview.error instanceof Error && <div className="error-state compact">{preview.error.message}</div>}
            {createFlow.error instanceof Error && <div className="error-state compact">{createFlow.error.message}</div>}
            {testCreated.error instanceof Error && <div className="error-state compact">{testCreated.error.message}</div>}
            {createdFlow && <div className="success-note"><strong>Интеграция сохранена</strong><span>{createdFlow.endpoint_url} · {wizard.responseMode} · {wizard.responseType}</span></div>}
          </WizardStep>
        </section>

        <aside className="request-response-sidecar">
          <section className="panel stack-form"><div className="panel-toolbar"><div><span className="eyebrow">Понятный preview</span><h2>Что будет происходить</h2></div><Link className="primary-link" to="/odata-explorer">Открыть Мастер OData</Link></div><PreviewStory fields={extractedFields} steps={odataSteps} responseType={wizard.responseType} endpointSlug={slugify(wizard.slug)} /></section>
          {builderResult ? <JsonBlock title="Preview / результат" value={builderResult} searchable /> : <div className="test-console-empty-response"><span className="eyebrow">Preview</span><strong>Пока ничего не запускали</strong><p>Нажмите “Проверить без сохранения”, чтобы увидеть переменные, OData-запросы и готовый ответ.</p></div>}
          {createdFlow && <section className="panel stack-form"><h2>Готовые примеры запросов</h2><CodeEditor value={createdFlow.curl_example} onChange={() => undefined} language="bash" minRows={6} /><CodeEditor value={createdFlow.onec_http_example} onChange={() => undefined} language="text" minRows={7} /></section>}
        </aside>
      </div>
    );
  }
}

function WizardStep({ index, title, description, children }: { index: string; title: string; description: string; children: ReactNode }) {
  return <section className="wizard-step request-response-step"><span className="step-index">{index}</span><div><h2>{title}</h2><p>{description}</p></div>{children}</section>;
}

function ExtractedFields({ fields }: { fields: ExtractedField[] }) {
  return <div className="builder-help-card"><strong>Извлеченные поля</strong><span>Эти пути можно вставлять в OData filter, resource или response template.</span><div className="variable-card-list compact-list">{fields.length === 0 ? <span className="microcopy">Пока нет распознанных полей.</span> : fields.map((field) => <button type="button" className="hint-chip" key={field.path} onClick={() => navigator.clipboard?.writeText(`{{${field.path}}}`)}>{field.path} = {previewValue(field.value)}</button>)}</div></div>;
}

function ODataStepEditor({ index, step, connections, fields, onChange, onRemove }: { index: number; step: ODataStepDraft; connections: Array<{ id: string; name: string; enabled: boolean }>; fields: ExtractedField[]; onChange: (patch: Partial<ODataStepDraft>) => void; onRemove: () => void }) {
  return <article className="builder-help-card odata-workbench-step"><div className="panel-toolbar compact-toolbar"><div><span className="eyebrow">OData {index + 1}</span><h3>{step.name}</h3></div><button type="button" className="ghost-button danger" onClick={onRemove} disabled={index === 0}>Удалить</button></div><div className="metadata-grid compact-grid no-margin"><label className="field-label">Название шага<input value={step.name} onChange={(event) => onChange({ name: event.target.value })} /></label><label className="field-label">OData-подключение<select value={step.connection} onChange={(event) => onChange({ connection: event.target.value })}><option value="">Выберите OData-подключение</option>{connections.filter((item) => item.enabled).map((item) => <option key={item.id} value={item.name}>{item.name}</option>)}</select></label><label className="field-label">Сохранить результат как<input value={step.save_as} onChange={(event) => onChange({ save_as: variableName(event.target.value) })} /></label></div><label className="field-label">Ресурс OData<input value={step.resource} onChange={(event) => onChange({ resource: event.target.value })} placeholder="Document_ЗаказНаПроизводство2_2" /></label><div className="metadata-grid compact-grid no-margin"><label className="field-label">$filter<input value={step.filter} onChange={(event) => onChange({ filter: event.target.value })} placeholder="Number eq '{{request.body.Number}}'" /></label><label className="field-label">$select<input value={step.select} onChange={(event) => onChange({ select: event.target.value })} placeholder="Ref_Key,Number" /></label><label className="field-label">$top<input value={step.top} onChange={(event) => onChange({ top: event.target.value })} /></label></div><label className="check-row"><input type="checkbox" checked={step.required} onChange={(event) => onChange({ required: event.target.checked })} /> Обязательный шаг: остановить интеграцию, если OData ничего не вернула</label><div className="hint-chip-row">{fields.slice(0, 8).map((field) => <button type="button" className="hint-chip" key={field.path} onClick={() => onChange({ filter: `${field.path.split('.').pop()} eq '{{${field.path}}}'` })}>Фильтр из {field.path}</button>)}<button type="button" className="hint-chip" onClick={() => navigator.clipboard?.writeText(`{{${step.save_as}.Ref_Key}}`)}>{`{{${step.save_as}.Ref_Key}}`}</button><button type="button" className="hint-chip" onClick={() => navigator.clipboard?.writeText(`{{steps.${step.id}.first.Ref_Key}}`)}>{`{{steps.${step.id}.first.Ref_Key}}`}</button></div></article>;
}

function ResponsePreview({ type, value, status, headers }: { type: ResponseBodyType; value: unknown; status: string; headers: string }) {
  return <div className="builder-help-card"><strong>Preview готового ответа</strong><span>HTTP {status || 200} · {contentTypeFor(type)}</span>{type === 'json' ? <JsonBlock title="JSON ответ" value={value as Record<string, unknown>} searchable={false} /> : <CodeEditor value={String(value ?? '')} onChange={() => undefined} language={type === 'xml' ? 'xml' : 'text'} minRows={6} />}<details><summary>Заголовки</summary><CodeEditor value={headers} onChange={() => undefined} language="json" minRows={4} /></details></div>;
}

function PreviewStory({ fields, steps, responseType, endpointSlug }: { fields: ExtractedField[]; steps: ODataStepDraft[]; responseType: ResponseBodyType; endpointSlug: string }) {
  return <div className="request-preview-list"><div className="success-note"><strong>1. Входящий запрос</strong><span>POST /api/bus/in/{endpointSlug}</span></div><div className="success-note"><strong>2. Извлечённые переменные</strong><span>{fields.slice(0, 5).map((field) => field.path).join(' · ') || 'нет полей'}</span></div>{steps.map((step, index) => <div className="success-note" key={step.id}><strong>{index + 3}. Запрос в OData: {step.save_as}</strong><span>{step.connection || 'OData-подключение'} · {step.resource} · {step.filter || 'без фильтра'}</span></div>)}<div className="success-note"><strong>{steps.length + 3}. Вернуть ответ</strong><span>{responseType.toUpperCase()} ответ вызывающей системе</span></div></div>;
}

function SelectedXmlMappings({ mappings, onRemove }: { mappings: XmlMappingDraft[]; onRemove: (path: string) => void }) {
  return <div className="builder-help-card xml-selected-fields"><strong>XML → переменные</strong><span>Эти переменные будут созданы шагом `xml_extract` перед OData. Если ничего не выбирать вручную, Workbench возьмет первые распознанные XML-поля.</span><div className="variable-card-list compact-list">{mappings.length === 0 ? <span className="microcopy">Пока XML-поля не выбраны.</span> : mappings.map((field) => <button key={field.path} type="button" className="hint-chip active" onClick={() => onRemove(field.path)} title="Нажмите, чтобы убрать поле">{field.name} ← {field.path}</button>)}</div></div>;
}

function previewVariables(sample: string, inputMode: string, steps: ODataStepDraft[], fields: ExtractedField[]) {
  const scope = previewScope(sample, inputMode, steps, fields);
  return { ...scope, request: { body: inputMode === 'json' ? scope : { xml: sample }, xml: inputMode === 'xml' ? sample : undefined } };
}

function renderLocalResponsePreview(template: string, type: ResponseBodyType, sample: string, inputMode: string, steps: ODataStepDraft[], fields: ExtractedField[]) {
  const scope = previewScope(sample, inputMode, steps, fields);
  const rendered = template.replace(/{{\s*([^{}]+?)\s*}}/g, (_match, expression: string) => {
    const value = resolvePreviewPath(scope, expression.trim());
    if (typeof value === 'object') return JSON.stringify(value, null, type === 'json' ? 0 : 2);
    return value === undefined || value === null ? '' : String(value);
  });
  if (type !== 'json') return rendered;
  try { return JSON.parse(rendered) as Record<string, unknown>; } catch { return { preview_error: 'JSON ответа пока невалидный. Проверьте кавычки, запятые и переменные в шаблоне.', rendered }; }
}

function previewScope(sample: string, inputMode: string, steps: ODataStepDraft[], fields: ExtractedField[]) {
  const scope: Record<string, unknown> = {};
  try { Object.assign(scope, parseSample(inputMode, sample)); } catch { /* preview stays best-effort */ }
  if (inputMode === 'xml') fields.forEach((field) => { scope[field.path] = field.value; });
  for (const step of steps) scope[step.save_as] = { Ref_Key: `${step.save_as}-ref-key`, Number: (scope.Number as string) || '260666/6938', Description: `${step.save_as} preview` };
  scope.products = [{ Ref_Key: 'line-1', Quantity: 1 }, { Ref_Key: 'line-2', Quantity: 2 }];
  return scope;
}

function resolvePreviewPath(scope: Record<string, unknown>, path: string): unknown {
  const clean = path.replace(/^request\.body\./, '').replace(/^xml\./, '');
  const parts = clean.split('.').filter(Boolean);
  let current: unknown = scope;
  for (const part of parts) {
    if (!current || typeof current !== 'object') return undefined;
    current = (current as Record<string, unknown>)[part];
  }
  return current;
}

function endpointLabel(endpoint: IntegrationEndpoint) {
  return `${endpointDisplayName(endpoint)} - /api/bus/in/${endpoint.slug}`;
}

function endpointDisplayName(endpoint: IntegrationEndpoint) {
  const name = endpoint.name.replace(/\s*\[[^\]]+\]\s*/g, '').replace(/\s*Endpoint:\s*\/api\/.*$/i, '').trim();
  if (/xml/i.test(endpoint.input_mode) && /raw/i.test(endpoint.response_mode + endpoint.name)) return '1C XML -> 1C raw bridge';
  if (/print|zebra/i.test(endpoint.name + endpoint.slug)) return '1C print request -> Zebra';
  if (/wms/i.test(endpoint.name + endpoint.slug)) return 'WMS shipment fact -> 1C';
  if (/website|site/i.test(endpoint.name + endpoint.slug)) return 'Website/API -> 1C OData';
  return name || endpoint.slug;
}

function responseModeLabel(mode: string) {
  if (mode === 'sync_response') return 'сразу вернуть свой ответ';
  if (mode === 'proxy_response') return 'вернуть ответ target-системы';
  if (mode === 'accepted_message') return 'принято сообщением';
  return 'принято событием';
}
