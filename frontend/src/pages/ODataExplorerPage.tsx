import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { integrationFlowsApi } from '../api/integrationFlows';
import { odataConnectionsApi } from '../api/odataConnections';
import { odataExplorerApi } from '../api/odataExplorer';
import { operationTemplatesApi } from '../api/operationTemplates';
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

function slugify(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 80) || 'odata-chain';
}

function keyify(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 120);
}

function variableName(value: string) {
  const clean = value.split('/').pop()?.replace(/^.*_/, '') || value;
  return clean.toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 40) || 'odata_result';
}

function variableInput(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9_]+/g, '_').slice(0, 40);
}

function loadDraft(): DraftStep[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(draftStorageKey) || '[]') as unknown;
    return Array.isArray(parsed) ? parsed.filter((item): item is DraftStep => Boolean(item && typeof item === 'object' && 'id' in item)) : [];
  } catch {
    return [];
  }
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
  const [newKey, setNewKey] = useState({ name: 'Lookup order products', operation: 'lookup_order_products', description: 'External system asks OMH to run this flow.' });
  const [newKeyTouched, setNewKeyTouched] = useState(false);
  const [showTriggerModal, setShowTriggerModal] = useState(false);
  const [nextAction, setNextAction] = useState<'continue_odata' | 'return_all' | 'send_result'>('continue_odata');
  const [tabularPart, setTabularPart] = useState('Продукция');
  const resources = useQuery({ queryKey: ['odata-resources', connectorId], queryFn: () => odataExplorerApi.resources(connectorId), enabled: Boolean(connectorId) });
  const run = useMutation({ mutationFn: () => odataExplorerApi.query(connectorId, { resource: query.resource, top: Number(query.top) || 10, filter: query.filter || null, select: query.select || null, orderby: query.orderby || null, paginate }) });
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
      example_request_json: { operation: newKey.operation, Number: '260666/6938' },
    }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['operation-templates'] });
      setFlowForm((current) => ({ ...current, operation: data.operation }));
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
  }

  function insertPlaceholder(target: 'resource' | 'filter', step: DraftStep, field: string) {
    const placeholder = `{{${step.save_as}.${field}}}`;
    if (target === 'resource') setQuery({ ...query, resource: `${query.resource}${placeholder}` });
    else setQuery({ ...query, filter: `${query.filter}${query.filter ? ' ' : ''}${placeholder}` });
  }

  function useAsOneCObjectResource(step: DraftStep, field: string) {
    const part = tabularPart.trim();
    const suffix = part ? `/${part}` : '';
    setQuery({ ...query, resource: `${step.resource}(guid'{{${step.save_as}.${field}}}')${suffix}`, filter: '' });
  }

  function clearDraft() {
    updateDraft([]);
  }

  function buildFlowPayload() {
    if (draftSteps.length === 0) throw new Error('Add at least one OData step');
    const responseBody = draftSteps.reduce<Record<string, string>>((acc, step) => ({ ...acc, [step.save_as]: `{{${step.save_as}}}` }), { operation_key: '{{operation_key}}' });
    return {
      name: flowForm.name,
      slug: flowForm.slug,
      description: flowForm.description,
      enabled: true,
      source_type: 'external_api',
      target_type: 'odata_lookup',
      endpoint: { input_mode: 'json', response_mode: 'sync_response', auth_mode: 'none', auth_config_json: {} },
      matcher_group_json: { mode: 'any', rules: [{ type: 'body_path_equals', path: 'operation', value: flowForm.operation }, { type: 'body_path_equals', path: 'sinc', value: flowForm.operation }] },
      action_json: { type: 'create_event_only', operation: flowForm.operation, business_object: 'ODataChainedLookup', description: flowForm.description },
      response_config_json: { response_mode: 'sync_response' },
      builder_json: {
        version: 1,
        input: { endpoint_slug: flowForm.slug, input_mode: 'json', response_mode: 'sync_response' },
        next_action: nextAction,
        variables: [{ name: 'operation_key', source: 'request.body.operation' }],
        steps: [
          { id: 'read_operation_key', type: 'read_variable', name: 'Read operation key', path: 'request.body.operation', fallback_paths: ['request.body.sinc'], save_as: 'operation_key' },
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
      test_payload_json: { operation: flowForm.operation, Number: '260666/6938' },
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

  return (
    <div className="page-stack two-column-page">
      <section className="panel form-panel">
        <div className="panel-toolbar">
          <div>
            <span className="eyebrow">{t('integration.odataExplorer.eyebrow')}</span>
            <h1>{t('integration.odataExplorer.title')}</h1>
            <p className="microcopy">{t('integration.odataExplorer.description')}</p>
          </div>
          <div className="toolbar-actions">
            <Link className="primary-link" to="/odata-connections">{t('integration.odataExplorer.createConnection')}</Link>
            <Link className="primary-link" to="/operation-keys">Operation keys</Link>
            <Link className="primary-link" to="/docs/onec/academy/test-odata-explorer">{t('integration.odataExplorer.lesson')}</Link>
          </div>
        </div>
        <div className="builder-help-card training-quickstart">
          <strong>{t('integration.odataExplorer.trainingTitle')}</strong>
          <span>{t('integration.odataExplorer.trainingDesc')}</span>
          <div className="action-row wrap-actions">
            {trainingErp ? <button type="button" className="ghost-button" onClick={() => useTrainingConnection('Training OData ERP')}>{t('integration.odataExplorer.useTrainingErp')}</button> : null}
            {trainingWms ? <button type="button" className="ghost-button" onClick={() => useTrainingConnection('Training OData WMS')}>{t('integration.odataExplorer.useTrainingWms')}</button> : null}
            {!trainingErp && !trainingWms && <button type="button" className="primary-button" onClick={() => installTraining.mutate()} disabled={installTraining.isPending}>{t('integration.odataExplorer.installTraining')}</button>}
            {training.data?.sandbox_installed && <Link className="primary-link" to="/training">{t('integration.odataExplorer.openTraining')}</Link>}
          </div>
        </div>
        <form className="stack-form" onSubmit={submit} data-tour="odata-query">
          <label className="field-label" data-tour="odata-connector">
            {t('integration.odataExplorer.connection')}
            <select value={connectorId} onChange={(event) => setConnectorId(event.target.value)}>
              <option value="">{t('integration.odataExplorer.selectConnection')}</option>
              {enabledConnections.map((connection) => <option key={connection.id} value={connection.id}>{connection.name} · {connection.base_url}</option>)}
            </select>
            <span className="microcopy">{t('integration.odataExplorer.connectionHint')}</span>
          </label>
          {enabledConnections.length === 0 && <div className="success-note">{t('integration.odataExplorer.createProfileFirst')}<span>{t('integration.odataExplorer.createProfileFirstDetail')}</span></div>}
          <label className="field-label">
            {t('integration.odataExplorer.resource')}
            <input list="odata-resources" value={query.resource} onChange={(event) => setQuery({ ...query, resource: event.target.value })} />
            <datalist id="odata-resources">{(resources.data?.resources ?? []).map((resource) => <option key={resource} value={resource} />)}</datalist>
          </label>
          <div className="builder-help-card">
            <strong>{t('integration.odataExplorer.safeWorkflow')}</strong>
            <span>{t('integration.odataExplorer.safeWorkflowDesc')}</span>
          </div>
          <div className="odata-filter-builder">
            <div className="panel-toolbar compact-toolbar"><h3>{t('integration.odataExplorer.filterBuilder')}</h3><button type="button" className="ghost-button" onClick={() => setFilters([...filters, { field: '', operator: 'eq', value: '' }])}>{t('integration.odataExplorer.addCondition')}</button></div>
            {filters.map((filter, index) => (
              <div className="metadata-grid compact-grid no-margin" key={index}>
                <label className="field-label">{t('integration.odataExplorer.field')}<input value={filter.field} onChange={(event) => setFilter(index, { field: event.target.value })} placeholder="ИНН" title={t('integration.odataExplorer.fieldHint')} /></label>
                <label className="field-label">{t('integration.odataExplorer.operator')}<select value={filter.operator} onChange={(event) => setFilter(index, { operator: event.target.value })}><option value="eq">eq</option><option value="ne">ne</option><option value="contains">contains</option><option value="startswith">startswith</option><option value="endswith">endswith</option><option value="gt">gt</option><option value="lt">lt</option><option value="ge">ge</option><option value="le">le</option></select></label>
                <label className="field-label">{t('integration.odataExplorer.value')}<input value={filter.value} onChange={(event) => setFilter(index, { value: event.target.value })} placeholder="7707083893" title={t('integration.odataExplorer.valueHint')} /></label>
                <button type="button" className="ghost-button danger" onClick={() => setFilters(filters.filter((_, itemIndex) => itemIndex !== index))} disabled={filters.length === 1}>{t('integration.odataExplorer.remove')}</button>
              </div>
            ))}
            <div className="action-row wrap-actions"><button type="button" className="primary-button" onClick={applyFilters}>{t('integration.odataExplorer.applyFilter')}</button><span className="microcopy">{t('integration.odataExplorer.conditionsJoined')}</span></div>
          </div>
          <label className="field-label">$filter<input value={query.filter} onChange={(event) => setQuery({ ...query, filter: event.target.value })} title={t('integration.odataExplorer.filterTitle')} /></label>
          <div className="metadata-grid compact-grid no-margin">
            <label className="field-label">$top<input value={query.top} onChange={(event) => setQuery({ ...query, top: event.target.value })} /></label>
            <label className="field-label">$select<input value={query.select} onChange={(event) => setQuery({ ...query, select: event.target.value })} title={t('integration.odataExplorer.selectTitle')} /></label>
            <label className="field-label">$orderby<input value={query.orderby} onChange={(event) => setQuery({ ...query, orderby: event.target.value })} /></label>
          </div>
          <div className="hint-chip-row">
            {['Ref_Key,Description,ИНН', 'Ref_Key,Description,Артикул', 'Ref_Key,Number,Date,Posted', 'Ref_Key,Склад_Key,Номенклатура_Key,Количество'].map((select) => <button key={select} type="button" className="hint-chip" onClick={() => setQuery({ ...query, select })}>{select}</button>)}
          </div>
          <label className="check-row" title={t('integration.odataExplorer.paginationHint')}>
            <input type="checkbox" checked={paginate} onChange={(event) => setPaginate(event.target.checked)} />
            {t('integration.odataExplorer.pagination')}
          </label>
          <div className="success-note">{t('integration.odataExplorer.paginationTitle')}<span>{t('integration.odataExplorer.paginationHint')}</span></div>
          <button className="primary-button" disabled={!connectorId || run.isPending}>{t('integration.odataExplorer.runQuery')}</button>
        </form>
        <hr />
        <div className="stack-form" data-tour="odata-lookup">
          <h2>{t('integration.odataExplorer.lookupTitle')}</h2>
          <label className="field-label">{t('integration.odataExplorer.lookupName')}<input value={lookup.name} onChange={(event) => setLookup({ ...lookup, name: event.target.value })} /></label>
          <label className="field-label">{t('integration.odataExplorer.filterTemplate')}<input value={lookup.filter_template} onChange={(event) => setLookup({ ...lookup, filter_template: event.target.value })} title={t('integration.odataExplorer.filterTemplateHint')} /></label>
          <label className="field-label">{t('integration.odataExplorer.extractJson')}<CodeEditor value={lookup.extract_json} onChange={(value) => setLookup({ ...lookup, extract_json: value })} language="json" minRows={5} title={t('integration.odataExplorer.extractJsonHint')} /></label>
          <div className="hint-chip-row">
            <button type="button" className="hint-chip" onClick={() => setLookup({ ...lookup, extract_json: '{"contractor_uuid":"Ref_Key","contractor_name":"Description","inn":"ИНН"}' })}>{t('integration.odataExplorer.contractorExtract')}</button>
            <button type="button" className="hint-chip" onClick={() => setLookup({ ...lookup, extract_json: '{"product_uuid":"Ref_Key","product_name":"Description","article":"Артикул"}' })}>{t('integration.odataExplorer.productExtract')}</button>
          </div>
          {formError && <div className="error-state compact">{formError}</div>}
          {runtimeError instanceof Error && <div className="error-state compact">{runtimeError.message}</div>}
          <button type="button" className="ghost-button" disabled={!connectorId || createLookup.isPending} onClick={handleCreateLookup}>{t('integration.odataExplorer.createLookup')}</button>
        </div>
      </section>
      <section className="page-stack">
        <JsonBlock title={t('integration.odataExplorer.resources')} value={resources.data ?? { hint: t('integration.odataExplorer.resourcesHint') }} searchable={false} />
        {run.error instanceof Error && <div className="error-state compact">{run.error.message}</div>}
        <JsonBlock title={t('integration.odataExplorer.queryResult')} value={run.data ?? { hint: t('integration.odataExplorer.queryResultHint') }} searchable />
        <section className="panel stack-form">
          <div className="panel-toolbar">
            <div>
              <span className="eyebrow">Draft flow</span>
              <h2>Пошаговая сборка интеграции</h2>
              <p className="microcopy">Сначала выберите trigger key, затем проверяйте OData-запросы. Flow сохранится только по кнопке Save as Integration Flow.</p>
            </div>
            <button type="button" className="ghost-button danger" onClick={clearDraft} disabled={draftSteps.length === 0}>Clear</button>
          </div>
          <div className="builder-help-card">
            <strong>Step 1. Trigger key</strong>
            <span>Этот ключ придет во входящем JSON в поле <code>operation</code> или <code>sinc</code>. По нему OMH поймет, какой flow запускать.</span>
            <div className="metadata-grid compact-grid no-margin">
              <label className="field-label">Operation key<select value={flowForm.operation} onChange={(event) => setFlowForm({ ...flowForm, operation: event.target.value })}><option value={flowForm.operation}>{flowForm.operation}</option>{operationKeyRows.map((item) => <option key={item.id} value={item.operation}>{item.operation} · {item.name}</option>)}</select></label>
              <button type="button" className="ghost-button" onClick={() => setShowTriggerModal(true)}>Add trigger</button>
            </div>
          </div>
          {run.data && <div className="builder-help-card">
            <strong>Step 2. Add current OData result as a step</strong>
            <span>Save as - имя переменной результата. Потом используйте поля как <code>{`{{${stepSaveAs}.Ref_Key}}`}</code>.</span>
            <div className="metadata-grid compact-grid no-margin">
              <label className="field-label">Save as<input value={stepSaveAs} onChange={(event) => { setStepSaveAsTouched(true); setStepSaveAs(variableInput(event.target.value)); }} /></label>
              <button type="button" className="primary-button" onClick={addResultAsStep} disabled={!selectedConnection}>Add as OData step</button>
            </div>
          </div>}
          {firstResult && <div className="hint-chip-row">
            {Object.keys(firstResult).slice(0, 16).map((field) => <button key={field} type="button" className="hint-chip" onClick={() => navigator.clipboard?.writeText(field)}>{field}</button>)}
          </div>}
          {draftSteps.length === 0 ? <div className="success-note">Черновик пуст<span>Выполните OData query и нажмите Add as OData step.</span></div> : draftSteps.map((step, index) => (
            <article className="success-note" key={step.id}>
              <strong>{index + 1}. {step.name}</strong>
              <span><code>{step.save_as}</code> · {step.connection} · top {step.top}</span>
              <span>{step.resource}</span>
              {step.filter && <span>$filter: {step.filter}</span>}
              <div className="builder-help-card">
                <strong>Step 3. Choose how to use this result</strong>
                <span>Если нужно открыть табличную часть документа 1C, выберите поле `Ref_Key`, укажите tabular part и нажмите `1C object resource`.</span>
                <label className="field-label">1C tabular part<input value={tabularPart} onChange={(event) => setTabularPart(event.target.value)} placeholder="Продукция" /></label>
                <div className="segmented-control">
                  <button type="button" className={nextAction === 'continue_odata' ? 'active' : ''} onClick={() => setNextAction('continue_odata')}>Continue OData</button>
                  <button type="button" className={nextAction === 'return_all' ? 'active' : ''} onClick={() => setNextAction('return_all')}>Return all</button>
                  <button type="button" className={nextAction === 'send_result' ? 'active' : ''} onClick={() => setNextAction('send_result')}>Send result</button>
                </div>
              </div>
              {step.sample && <div className="hint-chip-row">
                {Object.keys(step.sample).slice(0, 12).map((field) => (
                  <span key={field} className="action-row wrap-actions">
                    <button type="button" className="hint-chip" onClick={() => insertPlaceholder('resource', step, field)}>Resource: {field}</button>
                    <button type="button" className="hint-chip" onClick={() => insertPlaceholder('filter', step, field)}>Filter: {field}</button>
                    {field.endsWith('_Key') || field === 'Ref_Key' ? <button type="button" className="hint-chip" onClick={() => useAsOneCObjectResource(step, field)}>1C object resource: {field}</button> : null}
                  </span>
                ))}
              </div>}
            </article>
          ))}
          <hr />
          <div className="metadata-grid compact-grid no-margin">
            <label className="field-label">Flow name<input value={flowForm.name} onChange={(event) => setFlowForm({ ...flowForm, name: event.target.value, slug: slugify(event.target.value) })} /></label>
            <label className="field-label">Slug<input value={flowForm.slug} onChange={(event) => setFlowForm({ ...flowForm, slug: slugify(event.target.value) })} /></label>
          </div>
          <div className="action-row wrap-actions">
            <button type="button" className="primary-button" onClick={() => saveFlow.mutate()} disabled={saveFlow.isPending || draftSteps.length === 0}>Save as Integration Flow</button>
            <Link className="primary-link" to="/integration-flows">Open Integration Flows</Link>
            <Link className="primary-link" to="/docs/onec/tools/odata-chaining-fields">Open OData chaining guide</Link>
          </div>
          {createOperationKey.error instanceof Error && <div className="error-state compact">{createOperationKey.error.message}</div>}
          {saveFlow.error instanceof Error && <div className="error-state compact">{saveFlow.error.message}</div>}
          {saveFlow.data && <JsonBlock title="Saved flow" value={saveFlow.data} searchable={false} />}
        </section>
        <JsonBlock title={t('integration.odataExplorer.createdLookup')} value={createLookup.data ?? {}} searchable={false} />
      </section>
      {showTriggerModal && <div className="help-panel-backdrop" onClick={() => setShowTriggerModal(false)}>
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
            <div className="success-note">Example request<span><code>{`{"operation":"${newKey.operation || 'your_key'}","Number":"260666/6938"}`}</code></span></div>
            <button type="button" className="primary-button" onClick={() => createOperationKey.mutate()} disabled={createOperationKey.isPending || !newKey.operation}>Create trigger</button>
            {createOperationKey.error instanceof Error && <div className="error-state compact">{createOperationKey.error.message}</div>}
          </div>
        </aside>
      </div>}
    </div>
  );
}
