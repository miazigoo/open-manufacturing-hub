import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { integrationFlowsApi } from '../api/integrationFlows';
import { odataConnectionsApi } from '../api/odataConnections';
import { odataExplorerApi } from '../api/odataExplorer';
import { operationTemplatesApi, type OperationTemplate } from '../api/operationTemplates';
import { trainingApi } from '../api/training';
import { CodeEditor } from '../components/CodeEditor';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { useI18n } from '../i18n/useI18n';

const draftStorageKey = 'omh.odataExplorer.flowDraft.v1';

interface DraftStep {
  id: string;
  name: string;
  connection: string;
  resource: string;
  filter: string;
  select: string[];
  top: number;
  save_as: string;
  sample: Record<string, unknown> | null;
}

type WizardStep = 'trigger' | 'choose_action' | 'odata' | 'send_result';

interface InputField {
  name: string;
  value: unknown;
}

function slugify(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 80) || 'odata-chain';
}

function keyify(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 120);
}

function variableName(value: string) {
  const clean = value.split('/').pop()?.replace(/^.*_/, '') || value;
  const normalized = clean.toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 40);
  if (!normalized) return 'odata_result';
  return /^[0-9]/.test(normalized) ? `v_${normalized}` : normalized;
}

function variableInput(value: string) {
  const normalized = value.toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_+/, '').slice(0, 40);
  if (!normalized) return '';
  return /^[0-9]/.test(normalized) ? `v_${normalized}` : normalized;
}

function loadDraft(): DraftStep[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(draftStorageKey) || '[]') as unknown;
    return Array.isArray(parsed) ? parsed.filter((item): item is DraftStep => Boolean(item && typeof item === 'object' && 'id' in item)) : [];
  } catch {
    return [];
  }
}

function parseInputSample(value: string): Record<string, unknown> {
  try {
    const parsed = JSON.parse(value) as unknown;
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed as Record<string, unknown> : {};
  } catch {
    return {};
  }
}

function renderInputPlaceholders(value: string, sample: Record<string, unknown>) {
  return value.replace(/{{\s*request\.body\.([A-Za-z0-9_А-Яа-яЁё-]+)\s*}}/g, (_match, field: string) => {
    const raw = sample[field];
    if (raw === undefined || raw === null) return '';
    return typeof raw === 'object' ? JSON.stringify(raw) : String(raw);
  });
}

function renderDraftPlaceholders(value: string, steps: DraftStep[]) {
  return steps.reduce((current, step) => {
    if (!step.sample) return current;
    const escaped = step.save_as.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return current.replace(new RegExp(`{{\\s*${escaped}\\.([A-Za-z0-9_А-Яа-яЁё-]+)\\s*}}`, 'g'), (_match, field: string) => {
      const raw = step.sample?.[field];
      if (raw === undefined || raw === null) return '';
      return typeof raw === 'object' ? JSON.stringify(raw) : String(raw);
    });
  }, value);
}

function renderTestPlaceholders(value: string, sample: Record<string, unknown>, steps: DraftStep[]) {
  return renderDraftPlaceholders(renderInputPlaceholders(value, sample), steps);
}

function hasUnresolvedPlaceholders(value: string) {
  return /{{[^}]+}}/.test(value);
}

function formatInputValue(value: unknown) {
  if (value === undefined || value === null) return '';
  return typeof value === 'object' ? JSON.stringify(value) : String(value);
}

function triggerFieldFromSample(sample: Record<string, unknown>) {
  if (Object.prototype.hasOwnProperty.call(sample, 'sinc')) return 'sinc';
  return 'operation';
}

function triggerValueFromSample(sample: Record<string, unknown>, fallback: string) {
  const field = triggerFieldFromSample(sample);
  const value = sample[field];
  return typeof value === 'string' && value.trim() ? value.trim() : fallback;
}

function normalizeTriggerSample(sample: Record<string, unknown>, operation: string) {
  const field = triggerFieldFromSample(sample);
  const next = { ...sample, [field]: operation };
  if (field === 'sinc' && next.operation === operation) delete next.operation;
  if (field === 'operation' && next.sinc === operation) delete next.sinc;
  return next;
}

export function ODataExplorerPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const requestedConnection = searchParams.get('connection') ?? '';
  const connections = useQuery({ queryKey: ['odata-connections'], queryFn: odataConnectionsApi.list });
  const operationKeys = useQuery({ queryKey: ['operation-templates'], queryFn: operationTemplatesApi.list });
  const training = useQuery({ queryKey: ['training-status'], queryFn: trainingApi.status, retry: false });
  const enabledConnections = useMemo(() => (connections.data ?? []).filter((item) => item.enabled), [connections.data]);
  const [connectorId, setConnectorId] = useState(requestedConnection);
  const [formError, setFormError] = useState<string | null>(null);
  const [query, setQuery] = useState({ resource: 'Catalog_Контрагенты', top: '10', filter: "ИНН eq '1234567890'", select: 'Ref_Key,Description', orderby: '' });
  const [paginate, setPaginate] = useState(false);
  const [filters, setFilters] = useState([{ field: 'ИНН', operator: 'eq', value: '1234567890' }]);
  const [lookup, setLookup] = useState({ name: 'Find contractor by INN', filter_template: "ИНН eq '{inn}'", extract_json: '{"contractor_uuid":"Ref_Key","contractor_name":"Description"}' });
  const [draftSteps, setDraftSteps] = useState<DraftStep[]>(loadDraft);
  const [stepSaveAs, setStepSaveAs] = useState('result');
  const [stepSaveAsTouched, setStepSaveAsTouched] = useState(false);
  const [flowForm, setFlowForm] = useState({ name: 'Order products lookup', slug: 'order-products-lookup', operation: 'lookup_order_products', description: 'Lookup 1C order data through chained OData requests.' });
  const [newKey, setNewKey] = useState({ name: 'Lookup order products', operation: 'lookup_order_products', description: 'External system asks OMH to run this flow.', example_request_json: '{\n  "operation": "lookup_order_products",\n  "Number": "260666/6938",\n  "device_type": "toodoo"\n}' });
  const [newKeyTouched, setNewKeyTouched] = useState(false);
  const [showTriggerModal, setShowTriggerModal] = useState(false);
  const [nextAction, setNextAction] = useState<'continue_odata' | 'return_all' | 'send_result'>('continue_odata');
  const tabularPart = 'Продукция';
  const [wizardStep, setWizardStep] = useState<WizardStep>('trigger');
  const [target, setTarget] = useState({ method: 'POST', url: '' });
  const [inputSampleText, setInputSampleText] = useState('{\n  "operation": "lookup_order_products",\n  "Number": "260666/6938",\n  "device_type": "toodoo"\n}');
  const resources = useQuery({ queryKey: ['odata-resources', connectorId], queryFn: () => odataExplorerApi.resources(connectorId), enabled: Boolean(connectorId) });
  const run = useMutation({
    mutationFn: () => {
      const sample = parseInputSample(inputSampleText);
      return odataExplorerApi.query(connectorId, {
        resource: renderTestPlaceholders(query.resource, sample, draftSteps),
        top: Number(query.top) || 10,
        filter: query.filter ? renderTestPlaceholders(query.filter, sample, draftSteps) : null,
        select: query.select || null,
        orderby: query.orderby || null,
        paginate,
      });
    },
  });
  const createLookup = useMutation({ mutationFn: (extractJson: Record<string, string>) => odataExplorerApi.createLookup(connectorId, { name: lookup.name, resource: query.resource, filter_template: lookup.filter_template, extract_json: extractJson }) });
  const createOperationKey = useMutation({
    mutationFn: () => operationTemplatesApi.create({
      name: newKey.name,
      operation: newKey.operation,
      operation_code: newKey.operation,
      system_type: 'operation_key',
      direction: 'inbound',
      input_mode: 'json',
      output_mode: 'json',
      description: newKey.description,
      enabled: true,
      request_template_json: { operation: newKey.operation },
      example_request_json: { ...parseInputSample(newKey.example_request_json), operation: newKey.operation },
    }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['operation-templates'] });
      setFlowForm((current) => ({ ...current, operation: data.operation }));
      setInputSampleText(asJson(operationExample(data)));
      setShowTriggerModal(false);
    },
  });
  const saveFlow = useMutation({
    mutationFn: () => integrationFlowsApi.create(buildFlowPayload()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['integration-flows'] });
      localStorage.removeItem(draftStorageKey);
      setDraftSteps([]);
    },
  });
  const installTraining = useMutation({
    mutationFn: trainingApi.install,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['training-status'] });
      queryClient.invalidateQueries({ queryKey: ['odata-connections'] });
    },
  });

  useEffect(() => {
    if (requestedConnection) setConnectorId(requestedConnection);
  }, [requestedConnection]);

  useEffect(() => {
    if (!connectorId && enabledConnections[0]) setConnectorId(enabledConnections[0].id);
  }, [connectorId, enabledConnections]);

  useEffect(() => {
    if (!stepSaveAsTouched) setStepSaveAs(variableName(query.resource));
  }, [query.resource, stepSaveAsTouched]);

  if (connections.isLoading) return <LoadingState label={t('integration.odataExplorer.loading')} />;
  if (connections.error) return <ErrorState error={connections.error} />;

  function submit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    const sample = parseInputSample(inputSampleText);
    const resourcePreview = renderTestPlaceholders(query.resource, sample, draftSteps);
    const filterPreview = query.filter ? renderTestPlaceholders(query.filter, sample, draftSteps) : '';
    const unresolved = [resourcePreview, filterPreview].find(hasUnresolvedPlaceholders);
    if (unresolved) {
      setFormError(`В запросе осталась неподставленная переменная: ${unresolved}. Откройте карточку предыдущего шага и вставьте переменную с точным именем из заголовка.`);
      return;
    }
    run.mutate();
  }

  function handleCreateLookup() {
    setFormError(null);
    try {
      createLookup.mutate(JSON.parse(lookup.extract_json || '{}') as Record<string, string>);
    } catch {
      setFormError(t('integration.odataExplorer.extractInvalid'));
    }
  }

  function compileFilters() {
    return filters
      .map((filter) => {
        const field = filter.field.trim();
        const operator = filter.operator || 'eq';
        const value = filter.value.replaceAll("'", "''").trim();
        if (!field || !value) return '';
        return ['contains', 'startswith', 'endswith'].includes(operator) ? `${operator}(${field}, '${value}')` : `${field} ${operator} '${value}'`;
      })
      .filter(Boolean)
      .join(' and ');
  }

  function applyFilters() {
    const compiled = compileFilters();
    setQuery({ ...query, filter: compiled });
    setLookup({ ...lookup, filter_template: compiled.replaceAll("'1234567890'", "'{inn}'").replaceAll("'ABC-123'", "'{article}'") });
  }

  function setFilter(index: number, patch: Partial<{ field: string; operator: string; value: string }>) {
    setFilters(filters.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item));
  }

  function updateDraft(next: DraftStep[]) {
    setDraftSteps(next);
    localStorage.setItem(draftStorageKey, JSON.stringify(next));
  }

  function operationExample(operationKey: OperationTemplate) {
    const example = operationKey.example_request_json && Object.keys(operationKey.example_request_json).length > 0 ? operationKey.example_request_json : operationKey.request_template_json;
    return normalizeTriggerSample(example, operationKey.operation);
  }

  function selectOperationKey(operation: string) {
    const operationKey = operationKeyRows.find((item) => item.operation === operation);
    const sample = operationKey ? operationExample(operationKey) : normalizeTriggerSample(parseInputSample(inputSampleText), operation);
    const triggerValue = triggerValueFromSample(sample, operation);
    setFlowForm({ ...flowForm, operation: triggerValue, name: flowForm.name, slug: flowForm.slug });
    setInputSampleText(asJson(normalizeTriggerSample(sample, triggerValue)));
  }

  function requestInputFields(): InputField[] {
    return Object.entries(parseInputSample(inputSampleText))
      .filter(([key]) => !['operation', 'sinc'].includes(key))
      .map(([name, value]) => ({ name, value }));
  }

  function insertRequestPlaceholder(target: 'resource' | 'filter' | 'filter_value', field: string) {
    const placeholder = `{{request.body.${field}}}`;
    if (target === 'resource') setQuery({ ...query, resource: `${query.resource}${placeholder}` });
    else if (target === 'filter') setQuery({ ...query, filter: `${query.filter}${query.filter ? ' ' : ''}${placeholder}` });
    else setFilters(filters.map((item, index) => index === 0 ? { ...item, value: placeholder } : item));
  }

  function useRequestFieldAsFilter(field: string) {
    const placeholder = `{{request.body.${field}}}`;
    setFilters([{ field, operator: 'eq', value: placeholder }]);
    setQuery({ ...query, filter: `${field} eq '${placeholder}'` });
  }

  function updateInputSampleField(field: string, value: string) {
    const sample = parseInputSample(inputSampleText);
    setInputSampleText(asJson({ ...sample, [field]: value }));
  }

  function startODataStep() {
    setNextAction('continue_odata');
    setQuery({ resource: '', top: '10', filter: '', select: '', orderby: '' });
    setFilters([{ field: '', operator: 'eq', value: '' }]);
    setStepSaveAs('odata_result');
    setStepSaveAsTouched(false);
    run.reset();
    setWizardStep('odata');
  }

  function chooseSendResult() {
    setNextAction('send_result');
    setWizardStep('send_result');
  }

  function chooseReturnAll() {
    setNextAction('return_all');
    setWizardStep('send_result');
  }

  function addResultAsStep() {
    if (!selectedConnection || !run.data) return;
    const saveAs = variableName(stepSaveAs || query.resource);
    const step: DraftStep = {
      id: `odata_${draftSteps.length + 1}`,
      name: `OData ${draftSteps.length + 1}: ${query.resource}`,
      connection: selectedConnection.name,
      resource: query.resource,
      filter: query.filter,
      select: query.select.split(',').map((item) => item.trim()).filter(Boolean),
      top: Number(query.top) || 10,
      save_as: saveAs,
      sample: run.data.items?.[0] ?? null,
    };
    updateDraft([...draftSteps, step]);
    setStepSaveAs(variableName(query.resource));
    setStepSaveAsTouched(false);
    setWizardStep('choose_action');
  }

  function insertPlaceholder(target: 'resource' | 'filter', step: DraftStep, field: string) {
    const placeholder = `{{${step.save_as}.${field}}}`;
    if (target === 'resource') setQuery({ ...query, resource: `${query.resource}${placeholder}` });
    else setQuery({ ...query, filter: `${query.filter}${query.filter ? ' ' : ''}${placeholder}` });
  }

  function useAsOneCObjectResource(step: DraftStep, field: string) {
    const part = tabularPart.trim();
    const suffix = part ? `/${part}` : '';
    const baseResource = step.resource.split('?')[0].split('(')[0];
    setQuery({ ...query, resource: `${baseResource}(guid'{{${step.save_as}.${field}}}')${suffix}`, filter: '' });
  }

  function clearDraft() {
    updateDraft([]);
  }

  function editDraftStep(index: number) {
    const step = draftSteps[index];
    if (!step) return;
    const matchingConnection = enabledConnections.find((connection) => connection.name === step.connection);
    if (matchingConnection) setConnectorId(matchingConnection.id);
    setQuery({ resource: step.resource, top: String(step.top), filter: step.filter, select: step.select.join(','), orderby: '' });
    setStepSaveAs(step.save_as);
    setStepSaveAsTouched(true);
    run.reset();
    updateDraft(draftSteps.slice(0, index));
    setWizardStep('odata');
  }

  function buildFlowPayload() {
    if (draftSteps.length === 0) throw new Error('Add at least one OData step');
    const responseBody = draftSteps.reduce<Record<string, string>>((acc, step) => ({ ...acc, [step.save_as]: `{{${step.save_as}}}` }), { operation_key: '{{operation_key}}' });
    const inputFields = requestInputFields();
    const rawSample = parseInputSample(inputSampleText);
    const triggerValue = triggerValueFromSample(rawSample, flowForm.operation);
    const triggerSample = normalizeTriggerSample(rawSample, triggerValue);
    const triggerField = triggerFieldFromSample(triggerSample);
    return {
      name: flowForm.name,
      slug: flowForm.slug,
      description: flowForm.description,
      enabled: true,
      source_type: 'external_api',
      target_type: 'odata_lookup',
      endpoint: { input_mode: 'json', response_mode: 'sync_response', auth_mode: 'none', auth_config_json: {} },
      matcher_group_json: { mode: 'any', rules: [{ type: 'body_path_equals', path: triggerField, value: triggerValue }, { type: 'body_path_equals', path: triggerField === 'sinc' ? 'operation' : 'sinc', value: triggerValue }] },
      action_json: { type: 'create_event_only', operation: triggerValue, business_object: 'ODataChainedLookup', description: flowForm.description },
      response_config_json: { response_mode: 'sync_response' },
      builder_json: {
        version: 1,
        input: { endpoint_slug: flowForm.slug, input_mode: 'json', response_mode: 'sync_response' },
        next_action: nextAction,
        target: nextAction === 'send_result' ? target : null,
        variables: [{ name: 'operation_key', source: `request.body.${triggerField}` }, ...inputFields.map((field) => ({ name: field.name, source: `request.body.${field.name}` }))],
        steps: [
          { id: 'read_operation_key', type: 'read_variable', name: 'Read operation key', path: `request.body.${triggerField}`, fallback_paths: [triggerField === 'sinc' ? 'request.body.operation' : 'request.body.sinc'], save_as: 'operation_key' },
          ...inputFields.map((field) => ({ id: `read_${variableInput(field.name)}`, type: 'read_variable', name: `Read ${field.name}`, path: `request.body.${field.name}`, save_as: variableInput(field.name) })),
          ...draftSteps.map((step) => ({
            id: step.id,
            type: 'odata_query',
            name: step.name,
            connection: step.connection,
            resource: step.resource,
            filter: step.filter,
            select: step.select,
            top: step.top,
            save_as: step.save_as,
            required: true,
          })),
          { id: 'return_response', type: 'return_response', name: 'Return response', body: responseBody },
        ],
      },
      test_payload_json: triggerSample,
    };
  }

  function useTrainingConnection(name: string) {
    const connection = enabledConnections.find((item) => item.name === name);
    if (!connection) return;
    setConnectorId(connection.id);
    if (name.includes('ERP')) {
      setQuery({ resource: 'Catalog_Контрагенты', top: '10', filter: "ИНН eq '7707083893' and DeletionMark eq false", select: 'Ref_Key,Description,ИНН', orderby: 'Description asc' });
      setFilters([{ field: 'ИНН', operator: 'eq', value: '7707083893' }, { field: 'DeletionMark', operator: 'eq', value: 'false' }]);
    } else {
      setQuery({ resource: 'InformationRegister_Остатки', top: '10', filter: '', select: 'Склад_Key,Ячейка_Key,Номенклатура_Key,Количество', orderby: '' });
      setFilters([{ field: 'Склад_Key', operator: 'eq', value: 'wms-main' }]);
    }
  }

  const runtimeError = resources.error ?? run.error ?? createLookup.error ?? installTraining.error;
  const trainingErp = enabledConnections.find((item) => item.name === 'Training OData ERP');
  const trainingWms = enabledConnections.find((item) => item.name === 'Training OData WMS');
  const selectedConnection = enabledConnections.find((item) => item.id === connectorId);
  const firstResult = run.data?.items?.[0] ?? null;
  const operationKeyRows = (operationKeys.data ?? []).filter((item) => item.system_type === 'operation_key' || item.direction === 'inbound');
  const latestDraftStep = draftSteps[draftSteps.length - 1] ?? null;
  const inputFields = requestInputFields();
  const inputSample = parseInputSample(inputSampleText);

  function goToActionChoice() {
    run.reset();
    setQuery({ resource: '', top: '10', filter: '', select: '', orderby: '' });
    setFilters([{ field: '', operator: 'eq', value: '' }]);
    setWizardStep('choose_action');
  }

  function renderTriggerModal() {
    if (!showTriggerModal) return null;
    return (
      <div className="help-panel-backdrop" onClick={() => setShowTriggerModal(false)}>
        <aside className="help-panel" role="dialog" aria-label="Add trigger" onClick={(event) => event.stopPropagation()}>
          <div className="panel-toolbar">
            <div>
              <span className="eyebrow">Trigger</span>
              <h2>Add trigger key</h2>
            <p className="microcopy">Создайте ключ, который внешний сервис будет отправлять в поле <code>operation</code> или <code>sinc</code>.</p>
            </div>
            <button type="button" className="ghost-button" onClick={() => setShowTriggerModal(false)}>Close</button>
          </div>
          <div className="stack-form">
            <label className="field-label">Name<input value={newKey.name} onChange={(event) => setNewKey({ ...newKey, name: event.target.value, operation: newKeyTouched ? newKey.operation : keyify(event.target.value) })} /></label>
            <label className="field-label">Key<input value={newKey.operation} onChange={(event) => { setNewKeyTouched(true); setNewKey({ ...newKey, operation: keyify(event.target.value) }); }} /></label>
            <label className="field-label">Description<input value={newKey.description} onChange={(event) => setNewKey({ ...newKey, description: event.target.value })} /></label>
            <label className="field-label">Example JSON<CodeEditor value={newKey.example_request_json} onChange={(value) => setNewKey({ ...newKey, example_request_json: value })} language="json" minRows={6} /></label>
            <div className="success-note">Example request<span><code>{`{"operation":"${newKey.operation || 'your_key'}","Number":"260666/6938","device_type":"toodoo"}`}</code></span></div>
            <button type="button" className="primary-button" onClick={() => createOperationKey.mutate()} disabled={createOperationKey.isPending || !newKey.operation}>Create trigger</button>
            {createOperationKey.error instanceof Error && <div className="error-state compact">{createOperationKey.error.message}</div>}
          </div>
        </aside>
      </div>
    );
  }

  function renderDraftSummary() {
    if (draftSteps.length === 0) return <div className="success-note">Шагов пока нет<span>После успешного OData-запроса нажмите “Следующий шаг”, и результат сохранится в черновик.</span></div>;
    return (
      <div className="stack-form">
        {draftSteps.map((step, index) => (
          <button type="button" className="success-note draft-step-card" key={step.id} onClick={() => editDraftStep(index)}>
            <strong>{index + 1}. {step.name}</strong>
            <span><code>{step.save_as}</code> · {step.connection} · top {step.top}</span>
            <span>{step.resource}</span>
            {step.filter && <span>$filter: {step.filter}</span>}
            <small>Нажмите, чтобы открыть и изменить этот шаг</small>
          </button>
        ))}
      </div>
    );
  }

  function renderActionChoice() {
    return (
      <section className="panel form-panel centered-panel">
        <span className="eyebrow">Next step</span>
        <h1>Что дальше?</h1>
        <p className="microcopy">Выберите следующее действие. Экран будет показывать только нужные поля для выбранного шага.</p>
        <div className="metadata-grid">
          <button type="button" className="builder-help-card action-card" onClick={startODataStep}>
            <strong>Продолжить работу с OData</strong>
            <span>Собрать следующий ресурс, фильтр или select на основе уже полученных данных.</span>
          </button>
          <button type="button" className="builder-help-card action-card" onClick={chooseReturnAll} disabled={draftSteps.length === 0}>
            <strong>Отправить весь результат</strong>
            <span>Передать наружу весь результат последнего шага.</span>
          </button>
          <button type="button" className="builder-help-card action-card" onClick={chooseSendResult} disabled={draftSteps.length === 0}>
            <strong>Отправить выбранный результат</strong>
            <span>Указать внешний URL и метод отправки.</span>
          </button>
        </div>
        {latestDraftStep && <div className="success-note">Последний сохраненный результат<span><code>{latestDraftStep.save_as}</code> из {latestDraftStep.resource}</span></div>}
        <div className="action-row wrap-actions">
          <button type="button" className="ghost-button" onClick={() => setWizardStep('trigger')}>Назад к ключу</button>
          <button type="button" className="ghost-button danger" onClick={clearDraft} disabled={draftSteps.length === 0}>Очистить черновик</button>
        </div>
      </section>
    );
  }

  function renderODataStep() {
    return (
      <section className="panel form-panel">
        <div className="panel-toolbar">
          <div>
            <span className="eyebrow">OData step</span>
            <h1>Соберите OData-запрос</h1>
            <p className="microcopy">Выполните запрос. Если результат подходит, нажмите “Следующий шаг”, чтобы сохранить его в черновик.</p>
          </div>
          <Link className="primary-link" to="/docs/onec/tools/odata-chaining-fields">Примеры OData</Link>
        </div>
        <form className="stack-form" onSubmit={submit} data-tour="odata-query">
          <label className="field-label">
            {t('integration.odataExplorer.connection')}
            <select value={connectorId} onChange={(event) => setConnectorId(event.target.value)}>
              <option value="">{t('integration.odataExplorer.selectConnection')}</option>
              {enabledConnections.map((connection) => <option key={connection.id} value={connection.id}>{connection.name} · {connection.base_url}</option>)}
            </select>
          </label>
          {enabledConnections.length === 0 && <div className="success-note">{t('integration.odataExplorer.createProfileFirst')}<span>{t('integration.odataExplorer.createProfileFirstDetail')}</span></div>}
          {draftSteps.length > 0 && (
            <div className="builder-help-card">
              <strong>Переменные предыдущих шагов</strong>
              <span>Нажмите поле, чтобы вставить переменную. Для документа 1C используйте кнопку <code>1C object resource</code>, она соберет ресурс вида <code>Document_...(guid'{'{{'}order.Ref_Key{'}}'}')/Продукция</code>.</span>
              <div className="variable-card-list">
                {draftSteps.map((step, index) => (
                  <details className="variable-card" key={step.id} open={index === draftSteps.length - 1}>
                    <summary>
                      <span>Step {index + 1}</span>
                      <strong>{step.save_as}</strong>
                      <small>{step.resource}</small>
                    </summary>
                    {step.sample ? (
                      <div className="stack-form">
                        <JsonBlock title={`Artifact: ${step.save_as}`} value={step.sample} searchable={false} />
                        <div className="hint-chip-row">
                          {Object.keys(step.sample).slice(0, 18).map((field) => (
                            <span key={field} className="action-row wrap-actions">
                              <button type="button" className="hint-chip" onClick={() => insertPlaceholder('resource', step, field)}>Resource: {field}</button>
                              <button type="button" className="hint-chip" onClick={() => insertPlaceholder('filter', step, field)}>Filter: {field}</button>
                              <button type="button" className="hint-chip" onClick={() => navigator.clipboard?.writeText(`{{${step.save_as}.${field}}}`)}>Copy: {field}</button>
                              {field.endsWith('_Key') || field === 'Ref_Key' ? <button type="button" className="hint-chip" onClick={() => useAsOneCObjectResource(step, field)}>1C object resource: {field}</button> : null}
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : <div className="success-note">Artifact empty<span>У этого шага нет первого элемента результата.</span></div>}
                  </details>
                ))}
              </div>
            </div>
          )}
          <div className="builder-help-card">
            <strong>Входные параметры из JSON</strong>
            <span>Эти значения придут от внешней системы вместе с trigger key. В flow они сохраняются как шаблоны <code>{'{{request.body.Number}}'}</code>, а для тестового запуска здесь подставляются из примера ниже.</span>
            <div className="stack-form">
              {inputFields.length === 0 ? <span className="microcopy">Добавьте поля в пример JSON на первом шаге.</span> : inputFields.map((field) => (
                <div key={field.name} className="metadata-grid compact-grid no-margin">
                  <label className="field-label">Test value: {field.name}<input value={formatInputValue(field.value)} onChange={(event) => updateInputSampleField(field.name, event.target.value)} /></label>
                  <button type="button" className="hint-chip" onClick={() => useRequestFieldAsFilter(field.name)}>Filter: {field.name} eq value</button>
                  <button type="button" className="hint-chip" onClick={() => insertRequestPlaceholder('resource', field.name)}>Insert into resource</button>
                </div>
              ))}
            </div>
          </div>
          <label className="field-label">
            {t('integration.odataExplorer.resource')}
            <input list="odata-resources" value={query.resource} onChange={(event) => setQuery({ ...query, resource: event.target.value })} placeholder="Document_ЗаказНаПроизводство2_2" />
            <datalist id="odata-resources">{(resources.data?.resources ?? []).map((resource) => <option key={resource} value={resource} />)}</datalist>
          </label>
          <div className="metadata-grid compact-grid no-margin">
            <label className="field-label">$top<input value={query.top} onChange={(event) => setQuery({ ...query, top: event.target.value })} /></label>
            <label className="field-label">$select<input value={query.select} onChange={(event) => setQuery({ ...query, select: event.target.value })} placeholder="Ref_Key,Number,Date,Posted" /></label>
            <label className="field-label">$orderby<input value={query.orderby} onChange={(event) => setQuery({ ...query, orderby: event.target.value })} /></label>
          </div>
          <label className="field-label">$filter<input value={query.filter} onChange={(event) => setQuery({ ...query, filter: event.target.value })} placeholder="Number eq '260666/6938'" title={t('integration.odataExplorer.filterTitle')} /></label>
          {query.resource && <div className="success-note">Test resource preview<span>{renderTestPlaceholders(query.resource, inputSample, draftSteps)}</span></div>}
          {query.filter && <div className="success-note">Test filter preview<span>{renderTestPlaceholders(query.filter, inputSample, draftSteps)}</span></div>}
          <div className="odata-filter-builder">
            <div className="panel-toolbar compact-toolbar"><h3>{t('integration.odataExplorer.filterBuilder')}</h3><button type="button" className="ghost-button" onClick={() => setFilters([...filters, { field: '', operator: 'eq', value: '' }])}>{t('integration.odataExplorer.addCondition')}</button></div>
            {filters.map((filter, index) => (
              <div className="metadata-grid compact-grid no-margin" key={index}>
                <label className="field-label">{t('integration.odataExplorer.field')}<input value={filter.field} onChange={(event) => setFilter(index, { field: event.target.value })} placeholder="Number" /></label>
                <label className="field-label">{t('integration.odataExplorer.operator')}<select value={filter.operator} onChange={(event) => setFilter(index, { operator: event.target.value })}><option value="eq">eq</option><option value="ne">ne</option><option value="contains">contains</option><option value="startswith">startswith</option><option value="endswith">endswith</option><option value="gt">gt</option><option value="lt">lt</option><option value="ge">ge</option><option value="le">le</option></select></label>
                <label className="field-label">{t('integration.odataExplorer.value')}<input value={filter.value} onChange={(event) => setFilter(index, { value: event.target.value })} placeholder="260666/6938" /></label>
                <button type="button" className="ghost-button danger" onClick={() => setFilters(filters.filter((_, itemIndex) => itemIndex !== index))} disabled={filters.length === 1}>{t('integration.odataExplorer.remove')}</button>
              </div>
            ))}
            <div className="action-row wrap-actions"><button type="button" className="ghost-button" onClick={applyFilters}>{t('integration.odataExplorer.applyFilter')}</button><span className="microcopy">{t('integration.odataExplorer.conditionsJoined')}</span></div>
          </div>
          <label className="check-row" title={t('integration.odataExplorer.paginationHint')}>
            <input type="checkbox" checked={paginate} onChange={(event) => setPaginate(event.target.checked)} />
            {t('integration.odataExplorer.pagination')}
          </label>
          <div className="action-row wrap-actions">
            <button type="submit" className="primary-button" disabled={!connectorId || !query.resource || run.isPending}>{t('integration.odataExplorer.runQuery')}</button>
            <button type="button" className="ghost-button" onClick={() => setWizardStep('choose_action')}>Назад</button>
          </div>
        </form>
        {formError && <div className="error-state compact">{formError}</div>}
        {run.error instanceof Error && <div className="error-state compact">{run.error.message}</div>}
        {run.data && (
          <div className="stack-form">
            <JsonBlock title={t('integration.odataExplorer.queryResult')} value={run.data} searchable />
            <div className="builder-help-card">
              <strong>Результат подходит?</strong>
              <span>Сохраните его как переменную шага. Потом поля можно будет вставлять в следующий OData-ресурс или фильтр.</span>
              <div className="metadata-grid compact-grid no-margin">
                <label className="field-label">Save as<input value={stepSaveAs} onChange={(event) => { setStepSaveAsTouched(true); setStepSaveAs(variableInput(event.target.value)); }} /></label>
                <button type="button" className="primary-button" onClick={addResultAsStep} disabled={!selectedConnection}>Следующий шаг</button>
              </div>
            </div>
          </div>
        )}
      </section>
    );
  }

  function renderSendResultStep() {
    return (
      <section className="panel form-panel centered-panel odata-final-step">
        <span className="eyebrow">Final step</span>
        <h1>Куда отправить результат?</h1>
        <p className="microcopy">Укажите адрес внешней системы. Сейчас сохраняем это как настройку интеграции вместе с собранными OData-шагами.</p>
        <div className="metadata-grid compact-grid odata-final-grid">
          <label className="field-label">Method<select value={target.method} onChange={(event) => setTarget({ ...target, method: event.target.value })}><option value="POST">POST</option><option value="PUT">PUT</option><option value="PATCH">PATCH</option></select></label>
          <label className="field-label">URL<input value={target.url} onChange={(event) => setTarget({ ...target, url: event.target.value })} placeholder="https://example.local/api/result" /></label>
        </div>
        <div className="metadata-grid compact-grid odata-final-grid">
          <label className="field-label">Flow name<input value={flowForm.name} onChange={(event) => setFlowForm({ ...flowForm, name: event.target.value, slug: slugify(event.target.value) })} /></label>
          <label className="field-label">
            Slug
            <input
              value={flowForm.slug}
              onChange={(event) => setFlowForm({ ...flowForm, slug: slugify(event.target.value) })}
              title="Технический код интеграции: латиница, цифры и дефисы. Используется как внутренний идентификатор flow и часть endpoint-настроек. Можно оставить автозначение."
            />
            <span className="field-hint">Технический код flow: латиница, цифры, дефисы. Можно оставить автозначение.</span>
          </label>
        </div>
        <label className="field-label">Description<input value={flowForm.description} onChange={(event) => setFlowForm({ ...flowForm, description: event.target.value })} /></label>
        <div className="success-note">Trigger для сохранения<span><code>{triggerFieldFromSample(parseInputSample(inputSampleText))}</code> = <code>{triggerValueFromSample(parseInputSample(inputSampleText), flowForm.operation)}</code></span></div>
        {renderDraftSummary()}
        <div className="action-row wrap-actions">
          <button type="button" className="primary-button" onClick={() => saveFlow.mutate()} disabled={saveFlow.isPending || draftSteps.length === 0 || !target.url.trim()}>Сохранить интеграцию</button>
          <button type="button" className="ghost-button" onClick={() => setWizardStep('choose_action')}>Назад</button>
          <Link className="primary-link" to="/integration-flows">Open Integration Flows</Link>
        </div>
        {saveFlow.error instanceof Error && <div className="error-state compact">{saveFlow.error.message}</div>}
        {saveFlow.data && <JsonBlock title="Saved flow" value={saveFlow.data} searchable={false} />}
      </section>
    );
  }

  function renderWizard() {
    return (
      <div className="page-stack odata-wizard-page">
        <section className="panel form-panel">
          <div className="panel-toolbar">
            <div>
              <span className="eyebrow">{t('integration.odataExplorer.eyebrow')}</span>
              <h1>{t('integration.odataExplorer.title')}</h1>
              <p className="microcopy">Соберите интеграцию пошагово: trigger key, OData-запросы, затем отправка результата.</p>
              <p className="microcopy"><strong>Create OData Connection.</strong> Choose the 1C base where OMH will search data.</p>
            </div>
            <div className="toolbar-actions">
              <Link className="primary-link" to="/operation-keys">Operation keys</Link>
              <Link className="primary-link" to="/docs/onec/academy/test-odata-explorer">{t('integration.odataExplorer.lesson')}</Link>
            </div>
          </div>
        </section>
        {wizardStep === 'trigger' && (
          <section className="panel form-panel centered-panel">
            <span className="eyebrow">Step 1</span>
            <h1>Trigger key</h1>
            <p className="microcopy">Выберите ключ, который придет от внешней системы в JSON-поле <code>operation</code> или <code>sinc</code>.</p>
            <label className="field-label">Operation key<select value={flowForm.operation} onChange={(event) => selectOperationKey(event.target.value)}><option value="">Выберите ключ</option>{operationKeyRows.map((item) => <option key={item.id} value={item.operation}>{item.operation} · {item.name}</option>)}</select></label>
            <label className="field-label">
              Пример входящего JSON
              <CodeEditor value={inputSampleText} onChange={setInputSampleText} language="json" minRows={6} title="Укажите пример того, что внешний backend будет отправлять в OMH. Поля кроме operation/sinc можно вставлять в OData filter/resource." />
            </label>
            <div className="success-note">Доступные параметры<span>{inputFields.length ? inputFields.map((field) => `${field.name}=${String(field.value)}`).join(', ') : 'Пока нет параметров кроме operation/sinc'}</span></div>
            <div className="builder-help-card odata-filter-builder">
              <strong>Safe OData workflow</strong>
              <span>Конструктор фильтра помогает собрать `$filter`, а `$select` ограничивает ответ 1C только нужными полями. Сначала проверьте query здесь, потом сохраняйте его как шаг интеграции.</span>
              <div className="hint-chip-row">
                <button type="button" className="hint-chip" onClick={() => setWizardStep('odata')}>Filter builder</button>
                <button type="button" className="hint-chip" onClick={() => setWizardStep('odata')}>$select fields</button>
                <button type="button" className="hint-chip" onClick={() => setWizardStep('odata')}>Run OData query</button>
              </div>
            </div>
            <div className="action-row wrap-actions">
              <button type="button" className="ghost-button" onClick={() => setShowTriggerModal(true)}>Добавить trigger</button>
              <button type="button" className="primary-button" onClick={goToActionChoice} disabled={!flowForm.operation}>Следующий шаг</button>
            </div>
            {createOperationKey.error instanceof Error && <div className="error-state compact">{createOperationKey.error.message}</div>}
          </section>
        )}
        {wizardStep === 'choose_action' && renderActionChoice()}
        {wizardStep === 'odata' && renderODataStep()}
        {wizardStep === 'send_result' && renderSendResultStep()}
        {wizardStep !== 'odata' && <section className="panel form-panel">
          <div className="panel-toolbar">
            <div>
              <span className="eyebrow">Draft</span>
              <h2>Черновик интеграции</h2>
            </div>
            <button type="button" className="ghost-button danger" onClick={clearDraft} disabled={draftSteps.length === 0}>Clear</button>
          </div>
          {renderDraftSummary()}
        </section>}
        {renderTriggerModal()}
      </div>
    );
  }

  return renderWizard();
}
