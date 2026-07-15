import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { changeSetsApi } from '../api/changeSets';
import { integrationFlowsApi, IntegrationFlow } from '../api/integrationFlows';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { CodeBlock } from '../components/CodeBlock';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { VersionHistoryPanel } from '../features/configVersions';
import { useTableControls } from '../hooks/useTableControls';
import { useI18n } from '../i18n/useI18n';

const sampleJson = { pool_type: 'DNP', order_id: 'ORD-123', codes: ['010464615169738421ABC', '010464615169738421DEF'] };
const HTTP_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE', 'GET'];

function parseJsonObject(value: string, label: string): Record<string, unknown> {
  const parsed = JSON.parse(value || '{}') as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error(`${label} must be a JSON object`);
  return parsed as Record<string, unknown>;
}

function cloneJson<T>(value: T): T {
  return JSON.parse(JSON.stringify(value ?? {})) as T;
}

function parseNumberInput(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : value;
}

function selectToText(value: unknown) {
  return Array.isArray(value) ? value.join(',') : String(value ?? '');
}

function textToSelect(value: string) {
  return value.split(',').map((item) => item.trim()).filter(Boolean);
}

function flowValidationError(validation: Record<string, unknown> | null | undefined) {
  const errors = Array.isArray(validation?.errors) ? validation.errors : [];
  if (!errors.length) return null;
  return errors.map((item) => {
    const row = item && typeof item === 'object' ? item as Record<string, unknown> : {};
    return [row.step_id, row.message, row.hint].filter(Boolean).join(': ');
  }).join('\n');
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

function jsonInline(value: unknown) {
  if (value === undefined) return '';
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function finalActionFromBuilder(builder: Record<string, unknown> | null) {
  const value = builder?.final_action;
  return value && typeof value === 'object' ? value as Record<string, unknown> : null;
}

function callerResponseForAction(action: Record<string, unknown> | null) {
  if (!action) return null;
  const type = String(action.type ?? '');
  const returnConfig = action.return_to_caller && typeof action.return_to_caller === 'object' ? action.return_to_caller as Record<string, unknown> : {};
  const returnType = type === 'send_and_return_response' ? 'proxy_response' : String(returnConfig.type ?? 'fixed_success');
  const statusCode = Number(returnConfig.status_code ?? (returnType === 'accepted_event' ? 202 : 200));
  if (type === 'return_response') {
    const bodySource = String(action.body_source ?? 'target_payload');
    if (bodySource === 'target_payload') return { label: `HTTP ${statusCode}`, body: '{{target_payload}}', detail: 'OMH вернёт собранный результат предыдущих шагов в ответ на входящий POST.' };
    if (bodySource === 'custom') return { label: `HTTP ${statusCode}`, body: jsonInline(action.custom_body ?? ''), detail: 'OMH вернёт настроенное custom body в ответ на входящий POST.' };
    return { label: `HTTP ${statusCode}`, body: 'без тела ответа', detail: 'OMH завершит запрос без response body.' };
  }
  if (returnType === 'proxy_response') return { label: 'Proxy response', body: '{{response.body}}', detail: 'OMH вернёт вызывающей системе ответ внешнего endpoint.' };
  if (returnType === 'accepted_event') return { label: `HTTP ${statusCode}`, body: '{"accepted":true,"event_id":"{{context.event_id}}"}', detail: 'OMH вернёт быстрый async accepted response.' };
  if (returnType === 'custom_json' || returnType === 'custom_xml' || returnType === 'custom_raw') return { label: `HTTP ${statusCode}`, body: jsonInline(returnConfig.body ?? ''), detail: 'OMH вернёт настроенное custom body вызывающей системе.' };
  return { label: `HTTP ${statusCode}`, body: jsonInline(returnConfig.body ?? { ok: true }) || '{"ok":true}', detail: 'OMH вернёт короткое подтверждение вызывающей системе после выполнения финального действия.' };
}

function finalActionSummary(flow: IntegrationFlow) {
  const builder = flow.builder_json;
  const finalAction = finalActionFromBuilder(builder);
  const callerResponse = callerResponseForAction(finalAction);
  if (finalAction) {
    const type = String(finalAction.type ?? '');
    const method = String(finalAction.method ?? 'POST');
    const url = String(finalAction.url ?? '');
    if (type === 'send_endpoint' || type === 'send_and_return_response') {
      return {
        title: type === 'send_and_return_response' ? 'Отправить результат и вернуть ответ endpoint' : 'Отправить результат во внешнюю систему',
        line: url ? `${method} ${url}` : 'URL внешней системы не задан',
        detail: url ? 'После выполнения OData-шагов flow отправит собранный результат на этот внешний URL.' : 'Flow настроен на отправку наружу, но URL не сохранён.',
        callerResponse,
        missingTarget: !url,
      };
    }
    if (type === 'return_response') {
      return {
        title: 'Вернуть результат вызывающей системе',
        line: `Ответ на входящий POST ${publicEndpointFromCurl(flow)}`,
        detail: 'Отдельного внешнего URL нет: результат возвращается в HTTP-ответ тому, кто вызвал этот endpoint.',
        callerResponse,
        missingTarget: false,
      };
    }
    if (type === 'accepted_event') {
      return {
        title: 'Принять запрос асинхронно',
        line: `Ответ на входящий POST ${publicEndpointFromCurl(flow)}`,
        detail: 'OMH быстро вернёт accepted response и продолжит обработку отдельно.',
        callerResponse,
        missingTarget: false,
      };
    }
  }
  const target = targetSummary(builder);
  if (target?.url) {
    return {
      title: 'Отправить результат во внешнюю систему',
      line: `${target.method} ${target.url}`,
      detail: 'После выполнения OData-шагов flow отправит собранный результат на этот внешний URL.',
      callerResponse: null,
      missingTarget: false,
    };
  }
  const nextAction = String(builder?.next_action ?? '');
  if (nextAction === 'send_result') {
    return {
      title: 'Отправка наружу не завершена',
      line: 'URL внешней системы не задан',
      detail: 'Flow был выбран как отправка результата, но target URL не сохранился. Откройте builder и укажите Method + URL.',
      callerResponse: null,
      missingTarget: true,
    };
  }
  return {
    title: 'Вернуть результат вызывающей системе',
    line: `Ответ на входящий POST ${publicEndpointFromCurl(flow)}`,
    detail: 'Отдельного внешнего URL нет: результат возвращается в HTTP-ответ тому, кто вызвал этот endpoint.',
    callerResponse: null,
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
  const flowList = useMemo(() => flows.data ?? [], [flows.data]);
  const flowTable = useTableControls(flowList, {
    storageKey: 'omh.flows.list.v1',
    searchText: (flow) => [flow.name, flow.endpoint_url].filter(Boolean).join(' '),
    columns: { name: (flow) => flow.name },
  });
  const [result, setResult] = useState<unknown>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [editingFlowId, setEditingFlowId] = useState<string | null>(null);
  const [editBuilder, setEditBuilder] = useState<Record<string, unknown> | null>(null);
  const [editPayloadText, setEditPayloadText] = useState('');
  const [editError, setEditError] = useState<string | null>(null);

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['integration-flows'] });
  const duplicate = useMutation({ mutationFn: integrationFlowsApi.duplicate, onSuccess: (data) => { setResult(data); setSelectedId(data.id); refresh(); } });
  const exportFlow = useMutation({ mutationFn: integrationFlowsApi.export, onSuccess: setResult });
  const exportForProduction = useMutation({
    mutationFn: (flow: IntegrationFlow) => changeSetsApi.createFromDrafts({ name: `Promote ${flow.name}`, description: 'Export for production from Integration Flow detail', object_refs: [{ object_type: 'integration_flow', object_id: flow.id }], include_dependencies: true }),
    onSuccess: (changeSet) => navigate(`/change-sets/${changeSet.id}`),
  });
  const testFlow = useMutation({ mutationFn: (payload: { id: string; body: Record<string, unknown> }) => integrationFlowsApi.test(payload.id, { input_mode: 'json', payload_json: payload.body, dry_run: false }), onSuccess: setResult });
  const testMatcher = useMutation({ mutationFn: (payload: { body: Record<string, unknown>; matcher: Record<string, unknown> }) => integrationFlowsApi.testMatcher({ input_mode: 'json', payload: payload.body, matcher_group: payload.matcher }), onSuccess: setResult });
  const saveSettings = useMutation({
    mutationFn: async (payload: { id: string; builder_json: Record<string, unknown>; test_payload_json: Record<string, unknown> | null }) => {
      const flow = await integrationFlowsApi.patch(payload.id, { builder_json: payload.builder_json, test_payload_json: payload.test_payload_json });
      const validationError = flowValidationError(flow.last_validation_json);
      if (validationError) throw new Error(validationError);
      return flow;
    },
    onSuccess: (flow) => {
      setEditingFlowId(null);
      setEditBuilder(null);
      setEditError(null);
      setResult({ saved: true, flow_id: flow.id, compiled_at: flow.compiled_at, validation: flow.last_validation_json });
      refresh();
    },
  });

  if (flows.isLoading) return <LoadingState label={t('integration.flowBuilder.loading')} />;
  if (flows.error) return <ErrorState error={flows.error} />;

  const selectedFinalAction = selected ? finalActionSummary(selected) : null;

  function runSelectedFlow(flow: IntegrationFlow) {
    setFormError(null);
    try { testFlow.mutate({ id: flow.id, body: parseJsonObject(asJson(flow.test_payload_json ?? sampleJson), 'Flow test payload') }); }
    catch (error) { setFormError(error instanceof Error ? error.message : 'Invalid flow test payload'); }
  }

  function openSettingsEditor(flow: IntegrationFlow) {
    setEditingFlowId(flow.id);
    setEditBuilder(cloneJson(flow.builder_json ?? { version: 1, steps: [] }));
    setEditPayloadText(asJson(flow.test_payload_json ?? {}));
    setEditError(null);
  }

  function updateBuilderStep(index: number, patch: Record<string, unknown>) {
    setEditBuilder((current) => {
      const next = cloneJson(current ?? { version: 1, steps: [] });
      const steps = Array.isArray(next.steps) ? [...next.steps] : [];
      const step = steps[index] && typeof steps[index] === 'object' ? { ...(steps[index] as Record<string, unknown>) } : {};
      Object.entries(patch).forEach(([key, value]) => value === undefined ? delete step[key] : step[key] = value);
      steps[index] = step;
      next.steps = steps;
      return next;
    });
  }

  function updateNestedStep(index: number, patch: Record<string, unknown>) {
    setEditBuilder((current) => {
      const next = cloneJson(current ?? { version: 1, steps: [] });
      const steps = Array.isArray(next.steps) ? [...next.steps] : [];
      const step = steps[index] && typeof steps[index] === 'object' ? { ...(steps[index] as Record<string, unknown>) } : {};
      const nestedKey = step.step && typeof step.step === 'object' ? 'step' : 'do';
      const nested: Record<string, unknown> = step[nestedKey] && typeof step[nestedKey] === 'object' ? { ...(step[nestedKey] as Record<string, unknown>) } : { type: 'odata_query' };
      Object.entries(patch).forEach(([key, value]) => value === undefined ? delete nested[key] : nested[key] = value);
      step[nestedKey] = nested;
      steps[index] = step;
      next.steps = steps;
      return next;
    });
  }

  function updateForeachLimit(index: number, key: string, value: unknown) {
    setEditBuilder((current) => {
      const next = cloneJson(current ?? { version: 1, steps: [] });
      const steps = Array.isArray(next.steps) ? [...next.steps] : [];
      const step = steps[index] && typeof steps[index] === 'object' ? { ...(steps[index] as Record<string, unknown>) } : {};
      const limits = step.limits && typeof step.limits === 'object' ? { ...(step.limits as Record<string, unknown>) } : {};
      if (value === undefined) delete limits[key]; else limits[key] = value;
      step.limits = limits;
      steps[index] = step;
      next.steps = steps;
      return next;
    });
  }

  function updateFinalAction(patch: Record<string, unknown>) {
    setEditBuilder((current) => {
      const next = cloneJson(current ?? { version: 1, steps: [] });
      const finalAction = next.final_action && typeof next.final_action === 'object' ? { ...(next.final_action as Record<string, unknown>) } : {};
      Object.entries(patch).forEach(([key, value]) => value === undefined ? delete finalAction[key] : finalAction[key] = value);
      next.final_action = finalAction;
      if ('method' in patch || 'url' in patch) {
        const steps = Array.isArray(next.steps) ? [...next.steps] : [];
        next.steps = steps.map((step) => {
          if (!step || typeof step !== 'object' || (step as Record<string, unknown>).type !== 'call_endpoint') return step;
          return { ...(step as Record<string, unknown>), ...patch };
        });
      }
      return next;
    });
  }

  function updateCallerResponseBody(value: string) {
    setEditBuilder((current) => {
      const next = cloneJson(current ?? { version: 1, steps: [] });
      const finalAction = next.final_action && typeof next.final_action === 'object' ? { ...(next.final_action as Record<string, unknown>) } : {};
      const returnToCaller = finalAction.return_to_caller && typeof finalAction.return_to_caller === 'object' ? { ...(finalAction.return_to_caller as Record<string, unknown>) } : {};
      try {
        returnToCaller.body = JSON.parse(value) as unknown;
      } catch {
        returnToCaller.body = value;
      }
      finalAction.return_to_caller = returnToCaller;
      next.final_action = finalAction;
      const steps = Array.isArray(next.steps) ? [...next.steps] : [];
      next.steps = steps.map((step) => {
        if (!step || typeof step !== 'object' || (step as Record<string, unknown>).type !== 'return_response') return step;
        return { ...(step as Record<string, unknown>), body: returnToCaller.body };
      });
      return next;
    });
  }

  function saveEditedSettings(flow: IntegrationFlow) {
    setEditError(null);
    try {
      if (!editBuilder) throw new Error('Настройки flow не загружены');
      const testPayload = editPayloadText.trim() ? parseJsonObject(editPayloadText, 'Test payload') : null;
      saveSettings.mutate({ id: flow.id, builder_json: editBuilder, test_payload_json: testPayload });
    } catch (error) {
      setEditError(error instanceof Error ? error.message : 'Не удалось сохранить настройки');
    }
  }

  return (
    <div className="page-stack flow-builder-page">
      <section className="page-header flow-hero">
        <span className="eyebrow">{t('integration.flowBuilder.eyebrow')}</span>
        <h1>{t('integration.flowBuilder.title')}</h1>
        <p>{t('integration.flowBuilder.description')}</p>
        <div className="hero-meta" data-tour="flow-presets"><Link className="primary-button" to="/master">Создать интеграцию</Link><Link className="ghost-button" to="/odata-explorer">Открыть OData Master</Link><span className="microcopy">{t('integration.flowBuilder.flowPipeline')}</span></div>
      </section>

      <section className="panel purpose-banner">
        <span className="eyebrow">Назначение страницы</span>
        <h2>Здесь живут уже собранные интеграции</h2>
        <p>Если вы начинаете с бизнес-задачи, лучше открыть “Создать интеграцию” или Workbench. Эта страница нужна для просмотра, теста, дублирования, экспорта в продакшен и тонкой настройки потоков, которые уже появились после мастера.</p>
      </section>

      <section className="flow-layout">
        <section className="panel flow-list-panel">
          <div className="panel-toolbar"><h2>{t('integration.flowBuilder.flows')}</h2><span className="microcopy">{flows.data?.length ?? 0}</span></div>
          {flowList.length === 0 ? <EmptyState title={t('integration.flowBuilder.noFlows')} detail={t('integration.flowBuilder.noFlowsDetail')} actions={<><Link className="primary-button" to="/onboarding/first-integration">{t('integration.flowBuilder.createFirst')}</Link><Link className="ghost-button" to="/docs/onec/tools/visual-flow-builder">{t('integration.flowBuilder.openGuide')}</Link></>} /> : <>
            {flowList.length > 5 && <input type="search" className="flow-list-search" value={flowTable.search} onChange={(event) => flowTable.setSearch(event.target.value)} placeholder={t('common.table.searchPlaceholder')} aria-label={t('common.table.searchPlaceholder')} />}
            {flowTable.rows.length === 0 ? <EmptyState title={t('common.table.noResults')} detail={t('common.table.noResultsDetail')} /> : <div className="flow-list">{flowTable.rows.map((flow) => <button key={flow.id} className={`flow-list-item ${selected?.id === flow.id ? 'active' : ''}`} onClick={() => setSelectedId(flow.id)}><span><strong>{flow.name}</strong><small>{flow.endpoint_url}</small></span><StatusBadge status={flow.enabled ? 'ok' : 'cancelled'} label={flow.enabled ? t('integration.flowBuilder.enabled') : t('integration.flowBuilder.disabled')} compact /></button>)}</div>}
          </>}
        </section>

        <section className="panel flow-guide-panel" data-tour="flow-create">
          <span className="eyebrow">Создание интеграций</span>
          <h2>Новые flow собираются в Мастере интеграции</h2>
          <p>Эта страница показывает уже опубликованные интеграции: endpoint, trigger key, шаги, финальное действие, тестовый payload и технический JSON. Для нового сценария откройте мастер, пройдите шаги и сохраните интеграцию.</p>
          <div className="action-row wrap-actions"><Link className="primary-button" to="/master">Создать интеграцию</Link><Link className="ghost-button" to="/odata-explorer">Проверить OData</Link></div>
          {selected ? <div className="flow-mini-card"><span>Выбранный endpoint</span><strong>{selected.endpoint_url}</strong><small>{selected.enabled ? 'Интеграция включена' : 'Интеграция выключена'}</small></div> : <span className="microcopy">Выберите интеграцию слева, чтобы посмотреть детали ниже.</span>}
        </section>
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
            <button className="primary-button" onClick={() => openSettingsEditor(selected)}>Изменить настройки</button>
            <button className="primary-button" onClick={() => exportForProduction.mutate(selected)} disabled={exportForProduction.isPending}>{t('integration.flowBuilder.exportProduction')}</button>
            <Link className="ghost-button" to={`/config-history/integration_flow/${selected.id}`}>{t('integration.flowBuilder.releaseControl')}</Link>
            <button className="primary-button" onClick={() => runSelectedFlow(selected)} disabled={testFlow.isPending}>{t('integration.flowBuilder.testThisFlow')}</button>
            <button className="ghost-button" onClick={() => navigator.clipboard?.writeText(selected.endpoint_url)}>{t('integration.flowBuilder.copyUrl')}</button>
            <button className="ghost-button" onClick={() => duplicate.mutate(selected.id)} disabled={duplicate.isPending}>{t('integration.flowBuilder.duplicate')}</button>
            <button className="ghost-button" onClick={() => exportFlow.mutate(selected.id)} disabled={exportFlow.isPending}>{t('integration.flowBuilder.export')}</button>
            {selected.endpoint_id && <Link className="primary-link" to="/test-console">{t('integration.flowBuilder.openTestConsole')}</Link>}
          </div>
          {formError ? <div className="error-state compact">{formError}</div> : null}
          {testFlow.error instanceof Error ? <div className="error-state compact">{testFlow.error.message}</div> : null}
          {duplicate.error instanceof Error ? <div className="error-state compact">{duplicate.error.message}</div> : null}
          {exportFlow.error instanceof Error ? <div className="error-state compact">{exportFlow.error.message}</div> : null}
          {exportForProduction.error instanceof Error && <div className="error-state compact">{exportForProduction.error.message}</div>}
          {saveSettings.error instanceof Error && <div className="error-state compact">{saveSettings.error.message}</div>}
          {editError ? <div className="error-state compact">{editError}</div> : null}
          {editingFlowId === selected.id && editBuilder ? (
            <section className="flow-settings-editor">
              <div className="panel-toolbar">
                <div>
                  <span className="eyebrow">Редактирование настроек</span>
                  <h3>Тонкая настройка опубликованного flow</h3>
                  <p className="microcopy">$top в 1C OData должен быть от 1 до 500. Для 40000+ строк ставьте $top=500, включайте пагинацию и увеличивайте max_result_rows.</p>
                </div>
                <div className="action-row wrap-actions">
                  <button className="ghost-button" onClick={() => { setEditingFlowId(null); setEditBuilder(null); setEditError(null); }}>Закрыть</button>
                  <button className="primary-button" onClick={() => saveEditedSettings(selected)} disabled={saveSettings.isPending}>{saveSettings.isPending ? 'Сохраняю...' : 'Сохранить и пересобрать'}</button>
                </div>
              </div>
              <div className="flow-settings-grid">
                {builderSteps(editBuilder).map((step, index) => {
                  const type = String(step.type ?? '');
                  const nestedStep = (step.step && typeof step.step === 'object' ? step.step : step.do && typeof step.do === 'object' ? step.do : {}) as Record<string, unknown>;
                  const limits = step.limits && typeof step.limits === 'object' ? step.limits as Record<string, unknown> : {};
                  if (type === 'odata_query') {
                    return (
                      <article className="flow-settings-card" key={`${String(step.id ?? type)}-${index}`}>
                        <span className="eyebrow">Шаг {index + 1} · OData</span>
                        <h4>{String(step.name ?? step.id ?? 'OData query')}</h4>
                        <label className="field-label">Resource<input value={String(step.resource ?? '')} onChange={(event) => updateBuilderStep(index, { resource: event.target.value })} /></label>
                        <label className="field-label">$filter<textarea value={String(step.filter ?? '')} onChange={(event) => updateBuilderStep(index, { filter: event.target.value || undefined })} rows={3} /></label>
                        <label className="field-label">$select<input value={selectToText(step.select)} onChange={(event) => updateBuilderStep(index, { select: textToSelect(event.target.value) })} /></label>
                        <div className="metadata-grid compact-grid no-margin">
                          <label className="field-label">$top<input type="number" min={1} max={500} value={String(step.top ?? '')} onChange={(event) => updateBuilderStep(index, { top: parseNumberInput(event.target.value) })} /></label>
                          <label className="toggle-row"><input type="checkbox" checked={Boolean(step.paginate)} onChange={(event) => updateBuilderStep(index, { paginate: event.target.checked })} /> Читать следующие страницы</label>
                        </div>
                      </article>
                    );
                  }
                  if (type === 'foreach') {
                    return (
                      <article className="flow-settings-card wide" key={`${String(step.id ?? type)}-${index}`}>
                        <span className="eyebrow">Шаг {index + 1} · Повтор по массиву</span>
                        <h4>{String(step.name ?? step.id ?? 'Foreach OData')}</h4>
                        <div className="metadata-grid compact-grid no-margin">
                          <label className="field-label">Array<input value={String(step.items ?? '')} onChange={(event) => updateBuilderStep(index, { items: event.target.value })} /></label>
                          <label className="field-label">Item variable<input value={String(step.item_as ?? 'item')} onChange={(event) => updateBuilderStep(index, { item_as: event.target.value })} /></label>
                          <label className="field-label">Save as<input value={String(step.save_as ?? step.id ?? '')} onChange={(event) => updateBuilderStep(index, { save_as: event.target.value })} /></label>
                          <label className="toggle-row"><input type="checkbox" checked={step.flatten !== false} onChange={(event) => updateBuilderStep(index, { flatten: event.target.checked })} /> Объединить все строки в один массив</label>
                        </div>
                        <div className="flow-limit-grid">
                          <label className="field-label">max_items<input type="number" min={1} value={String(limits.max_items ?? '')} onChange={(event) => updateForeachLimit(index, 'max_items', parseNumberInput(event.target.value))} /></label>
                          <label className="field-label">max_requests<input type="number" min={1} value={String(limits.max_requests ?? '')} onChange={(event) => updateForeachLimit(index, 'max_requests', parseNumberInput(event.target.value))} /></label>
                          <label className="field-label">max_result_rows<input type="number" min={1} value={String(limits.max_result_rows ?? '')} onChange={(event) => updateForeachLimit(index, 'max_result_rows', parseNumberInput(event.target.value))} /></label>
                        </div>
                        <div className="builder-help-card">
                          <strong>Nested OData-запрос внутри foreach</strong>
                          <span>Для больших пулов кодов обычно ставим nested $top=500, включаем nested pagination и поднимаем max_result_rows до ожидаемого объема, например 50000.</span>
                        </div>
                        <label className="field-label">Nested resource<input value={String(nestedStep.resource ?? '')} onChange={(event) => updateNestedStep(index, { resource: event.target.value })} /></label>
                        <label className="field-label">Nested $filter<textarea value={String(nestedStep.filter ?? '')} onChange={(event) => updateNestedStep(index, { filter: event.target.value || undefined })} rows={3} /></label>
                        <label className="field-label">Nested $select<input value={selectToText(nestedStep.select)} onChange={(event) => updateNestedStep(index, { select: textToSelect(event.target.value) })} /></label>
                        <div className="metadata-grid compact-grid no-margin">
                          <label className="field-label">Nested $top<input type="number" min={1} max={500} value={String(nestedStep.top ?? '')} onChange={(event) => updateNestedStep(index, { top: parseNumberInput(event.target.value) })} /></label>
                          <label className="toggle-row"><input type="checkbox" checked={Boolean(nestedStep.paginate)} onChange={(event) => updateNestedStep(index, { paginate: event.target.checked })} /> Читать следующие страницы</label>
                        </div>
                      </article>
                    );
                  }
                  return null;
                })}
                {(() => {
                  const finalAction = finalActionFromBuilder(editBuilder);
                  if (!finalAction) return null;
                  const returnToCaller = finalAction.return_to_caller && typeof finalAction.return_to_caller === 'object' ? finalAction.return_to_caller as Record<string, unknown> : {};
                  return (
                    <article className="flow-settings-card wide">
                      <span className="eyebrow">Финальное действие</span>
                      <h4>{String(finalAction.type ?? 'return_response')}</h4>
                      {String(finalAction.type ?? '').startsWith('send') ? (
                        <div className="metadata-grid compact-grid no-margin">
                          <label className="field-label">Method<select value={String(finalAction.method ?? 'POST')} onChange={(event) => updateFinalAction({ method: event.target.value })}>{HTTP_METHODS.map((method) => <option value={method} key={method}>{method}</option>)}</select></label>
                          <label className="field-label">URL<input value={String(finalAction.url ?? '')} onChange={(event) => updateFinalAction({ url: event.target.value })} /></label>
                        </div>
                      ) : null}
                      <label className="field-label">Ответ вызывающей системе<textarea value={asJson(returnToCaller.body ?? { ok: true })} onChange={(event) => updateCallerResponseBody(event.target.value)} rows={5} /></label>
                      <p className="microcopy">Это HTTP-ответ на исходный запрос в OMH. Если flow отправляет данные во внешний endpoint, здесь обычно остается короткое подтверждение вроде {"{\"ok\": true}"}.</p>
                    </article>
                  );
                })()}
                <article className="flow-settings-card wide">
                  <span className="eyebrow">Тестовый входной JSON</span>
                  <h4>Пример для проверки и предпросмотра</h4>
                  <textarea className="code-textarea" value={editPayloadText} onChange={(event) => setEditPayloadText(event.target.value)} rows={8} />
                </article>
              </div>
            </section>
          ) : null}
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
              {selectedFinalAction.callerResponse ? (
                <div className="flow-caller-response">
                  <span>Ответ вызывающей системе: {selectedFinalAction.callerResponse.label}</span>
                  <code>{selectedFinalAction.callerResponse.body}</code>
                  <small>{selectedFinalAction.callerResponse.detail}</small>
                </div>
              ) : null}
              <button className="ghost-button" onClick={() => openSettingsEditor(selected)}>Редактировать настройки</button>
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
