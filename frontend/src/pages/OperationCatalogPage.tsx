import { FormEvent, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { connectionCenterApi, type ConnectionProfileOption } from '../api/connectionCenter';
import { dataContractsApi, type DataContract } from '../api/dataContracts';
import { operationCatalogApi, type OperationBodyType, type OperationKind, type OperationMethod, type OperationProfile, type OperationProfilePayload, type OperationTestResponse, type SuccessConditionType } from '../api/operationCatalog';
import { CodeEditor } from '../components/CodeEditor';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { DataContractViewer } from '../features/mapping-center/DataContractViewer';

const kindLabels: Record<OperationKind, string> = {
  rest_api_operation: 'REST API',
  onec_http_operation: '1C HTTP Service',
  printer_operation: 'Printer',
  file_operation: 'File / SMB',
  training_operation: 'Training',
};

const kindFilters = [
  { id: 'all', label: 'Все' },
  { id: 'rest_api_operation', label: 'REST API' },
  { id: 'onec_http_operation', label: '1C HTTP Service' },
  { id: 'printer_operation', label: 'Printer' },
  { id: 'file_operation', label: 'File / SMB' },
  { id: 'training_operation', label: 'Training' },
];

const operationCards: Array<{ kind: OperationKind; title: string; detail: string; planned?: boolean }> = [
  { kind: 'rest_api_operation', title: 'REST API request', detail: 'POST/PUT/PATCH/GET во внешний API, WMS, DNP, CRM или сайт.' },
  { kind: 'onec_http_operation', title: '1C HTTP service call', detail: 'Вызов published HTTP Service в 1С: запись external_id, факт WMS, raw XML.' },
  { kind: 'printer_operation', title: 'Printer operation', detail: 'Операция печати/ZPL. Сейчас каталог + dry-run, production runner позже.', planned: true },
  { kind: 'file_operation', title: 'File/SMB operation', detail: 'Операция записи файла в SMB/local directory. Сейчас каталог + dry-run.', planned: true },
];

interface ConditionForm {
  type: SuccessConditionType;
  status: string;
  path: string;
  value: string;
  text: string;
}

interface ExtractorForm {
  name: string;
  path: string;
  required: boolean;
}

interface OperationFormState {
  name: string;
  code: string;
  description: string;
  kind: OperationKind;
  connection_profile_id: string;
  request_contract_id: string;
  response_contract_id: string;
  method: OperationMethod;
  path: string;
  full_url: string;
  headers_json: string;
  body_type: OperationBodyType;
  request_template_text: string;
  response_body_type: OperationBodyType;
  success_mode: 'all' | 'any';
  conditions: ConditionForm[];
  extractors: ExtractorForm[];
  sample_request_json: string;
  sample_response_json: string;
  timeout_seconds: number;
  tags: string;
  package_id: string;
}

function emptyForm(connection?: ConnectionProfileOption | null): OperationFormState {
  const kind = connectionKindToOperationKind(connection);
  return {
    name: defaultName(kind),
    code: defaultCode(kind),
    description: '',
    kind,
    connection_profile_id: connection?.connector_id ?? '',
    request_contract_id: '',
    response_contract_id: '',
    method: 'POST',
    path: defaultPath(kind),
    full_url: '',
    headers_json: kind === 'onec_http_operation' && defaultPath(kind).includes('xml') ? '{\n  "Content-Type": "application/xml; charset=utf-8"\n}' : '{\n  "Content-Type": "application/json"\n}',
    body_type: kind === 'onec_http_operation' && defaultPath(kind).includes('xml') ? 'xml' : 'json',
    request_template_text: '',
    response_body_type: 'json',
    success_mode: 'all',
    conditions: [{ type: 'http_status_2xx', status: '200', path: 'success', value: 'true', text: '' }],
    extractors: [],
    sample_request_json: '{\n  "example": true\n}',
    sample_response_json: '{\n  "success": true\n}',
    timeout_seconds: kind === 'onec_http_operation' ? 30 : 20,
    tags: kind === 'rest_api_operation' ? 'api' : kind === 'onec_http_operation' ? '1c' : '',
    package_id: kind === 'onec_http_operation' ? 'omh-package-onec' : '',
  };
}

export function OperationCatalogPage() {
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const connectionFilter = searchParams.get('connection');
  const operationsQuery = useQuery({ queryKey: ['operation-catalog-operations'], queryFn: () => operationCatalogApi.list() });
  const connectionsQuery = useQuery({ queryKey: ['connection-center-options'], queryFn: connectionCenterApi.options });
  const contractsQuery = useQuery({ queryKey: ['data-contracts'], queryFn: () => dataContractsApi.list() });
  const [activeTab, setActiveTab] = useState('all');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [wizardStep, setWizardStep] = useState(1);
  const [form, setForm] = useState<OperationFormState>(() => emptyForm());
  const [formError, setFormError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<OperationTestResponse | null>(null);

  const operations = operationsQuery.data ?? [];
  const connectionOptions = connectionsQuery.data?.profiles ?? [];
  const filtered = useMemo(() => operations.filter((operation) => filterOperation(operation, activeTab, connectionFilter)), [operations, activeTab, connectionFilter]);
  const selected = operations.find((operation) => operation.id === selectedId) ?? filtered[0] ?? null;
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['operation-catalog-operations'] });

  const create = useMutation({ mutationFn: operationCatalogApi.create, onSuccess: (operation) => { setSelectedId(operation.id); refresh(); } });
  const createAndTest = useMutation({
    mutationFn: async (payload: OperationProfilePayload) => {
      const operation = await operationCatalogApi.create(payload);
      const test = await operationCatalogApi.test(operation.id, { dry_run: true });
      return { operation, test };
    },
    onSuccess: ({ operation, test }) => {
      setSelectedId(operation.id);
      setLastResult(test);
      setWizardStep(6);
      refresh();
    },
  });
  const test = useMutation({ mutationFn: (operation: OperationProfile) => operationCatalogApi.test(operation.id, { dry_run: true }), onSuccess: (result) => { setLastResult(result); refresh(); } });
  const toggle = useMutation({ mutationFn: (operation: OperationProfile) => operation.enabled ? operationCatalogApi.disable(operation.id) : operationCatalogApi.enable(operation.id), onSuccess: refresh });
  const remove = useMutation({ mutationFn: operationCatalogApi.delete, onSuccess: () => { setSelectedId(null); refresh(); } });
  const installPresets = useMutation({ mutationFn: operationCatalogApi.installPresets, onSuccess: refresh });
  const mutationError = [create.error, createAndTest.error, test.error, toggle.error, remove.error, installPresets.error].find((error): error is Error => error instanceof Error);

  if (operationsQuery.isLoading || connectionsQuery.isLoading || contractsQuery.isLoading) return <LoadingState label="Загружаю каталог операций" />;
  if (operationsQuery.error) return <ErrorState error={operationsQuery.error} />;
  if (connectionsQuery.error) return <ErrorState error={connectionsQuery.error} />;
  if (contractsQuery.error) return <ErrorState error={contractsQuery.error} />;

  function openCreate(connection?: ConnectionProfileOption | null) {
    setForm(emptyForm(connection));
    setFormError(null);
    setLastResult(null);
    setWizardStep(1);
    setWizardOpen(true);
  }

  function duplicate(operation: OperationProfile) {
    setForm(formFromOperation(operation));
    setFormError(null);
    setLastResult(null);
    setWizardStep(1);
    setWizardOpen(true);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    save(false);
  }

  function save(runDryRun: boolean) {
    setFormError(null);
    try {
      const payload = payloadFromForm(form);
      if (runDryRun) createAndTest.mutate(payload);
      else create.mutate(payload, { onSuccess: () => setWizardOpen(false) });
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Неверная форма операции');
    }
  }

  return (
    <div className="page-stack operation-catalog-page">
      <section className="page-header product-page-header connection-center-hero">
        <div>
          <span className="eyebrow">Operation Catalog</span>
          <h1>Операции подключения</h1>
          <p>Connection Profile отвечает “куда ходить”, Operation Profile отвечает “какое действие выполнить”: method, path, headers, body, success condition и extractors.</p>
        </div>
        <div className="product-header-actions">
          <button className="primary-button" onClick={() => openCreate()}>Создать операцию</button>
          <button className="ghost-button" onClick={() => installPresets.mutate()} disabled={installPresets.isPending}>Установить presets</button>
          <Link className="ghost-button" to="/connection-center">Connection Center</Link>
          <Link className="ghost-button" to="/docs/core/operation-catalog">Документация</Link>
        </div>
      </section>

      <section className="guidance-strip">
        <div className="guidance-head">
          <div>
            <span className="eyebrow">Reusable action</span>
            <h2>Операция превращает подключение в готовое действие</h2>
            <p>Один профиль подключения может иметь несколько операций: например, DNP API может принимать коды, возвращать статус и отдавать ошибки разными endpoint’ами.</p>
          </div>
          <div className="action-row wrap-actions">
            <Link className="ghost-button" to="/connection-center">Проверить подключения</Link>
            <Link className="ghost-button" to="/mapping-center">Настроить mapping</Link>
          </div>
        </div>
        <div className="guidance-step-grid">
          <article className="guidance-step-card"><span>1</span><strong>Выберите Connection Profile</strong><p>Если подключения ещё нет, сначала создайте его в Connection Center. Без подключения можно оставить legacy <code>full_url</code>.</p></article>
          <article className="guidance-step-card"><span>2</span><strong>Опишите request/response</strong><p>Укажите method, path, body type и контракты. Контракт нужен, чтобы mapping и wizard могли подсказать поля.</p></article>
          <article className="guidance-step-card"><span>3</span><strong>Задайте критерий успеха</strong><p>Для REST обычно достаточно <code>http_status_2xx</code>; для 1С/внешних API часто полезен <code>json_path_equals</code>.</p></article>
          <article className="guidance-step-card"><span>4</span><strong>Проверьте dry-run</strong><p>Dry-run покажет final URL, headers, body preview и extractors без реального сетевого вызова.</p></article>
        </div>
      </section>

      <section className="panel connection-center-toolbar">
        <div className="component-strip package-capabilities connection-tabs">
          {kindFilters.map((tab) => <button type="button" key={tab.id} className={activeTab === tab.id ? 'primary-button' : 'ghost-button'} onClick={() => setActiveTab(tab.id)}>{tab.label}</button>)}
        </div>
        {connectionFilter && <p className="microcopy">Фильтр по подключению: <code>{connectionFilter}</code></p>}
      </section>

      <section className="panel table-panel connection-profile-table">
        <div className="panel-toolbar"><h2>Сохранённые операции</h2><span className="microcopy">{filtered.length} из {operations.length}</span></div>
        {filtered.length === 0 ? <EmptyState title="Операций пока нет" detail="Создайте операцию вручную или установите presets после создания Connection Profiles." actions={<><button className="primary-button" onClick={() => openCreate()}>Создать операцию</button><button className="ghost-button" onClick={() => installPresets.mutate()} disabled={installPresets.isPending}>Установить presets</button><Link className="ghost-button" to="/connection-center">Connection Center</Link></>} /> : (
          <div className="table-scroll">
            <table>
              <thead><tr><th>Name</th><th>Kind</th><th>Connection</th><th>Method</th><th>Path</th><th>Status</th><th>Last test</th><th>Used by</th><th>Actions</th></tr></thead>
              <tbody>
                {filtered.map((operation) => (
                  <tr key={operation.id} className={selected?.id === operation.id ? 'selected-row' : ''}>
                    <td><strong>{operation.name}</strong><small>{operation.code}</small></td>
                    <td>{kindLabels[operation.kind]}</td>
                    <td><small>{operation.connection_name ?? 'Manual endpoint'}</small></td>
                    <td><code>{operation.method ?? '—'}</code></td>
                    <td><small>{operation.path || operation.full_url || '—'}</small></td>
                    <td><StatusBadge status={operation.enabled ? 'enabled' : 'disabled'} compact /></td>
                    <td><small>{operation.last_test_at ? new Date(operation.last_test_at).toLocaleString() : 'ещё не проверяли'}</small><StatusBadge status={operation.last_test_success == null ? 'unknown' : operation.last_test_success ? 'success' : 'failed'} compact /></td>
                    <td><small>{operation.used_by.slice(0, 3).join(', ') || '—'}</small></td>
                    <td><div className="action-row wrap-actions compact-actions"><button className="ghost-button" onClick={() => setSelectedId(operation.id)}>Open</button><button className="ghost-button" onClick={() => test.mutate(operation)} disabled={test.isPending}>Test</button><button className="ghost-button" onClick={() => duplicate(operation)}>Duplicate</button><button className="ghost-button" onClick={() => toggle.mutate(operation)} disabled={toggle.isPending}>{operation.enabled ? 'Disable' : 'Enable'}</button><button className="ghost-button danger" onClick={() => window.confirm(`Удалить операцию ${operation.name}?`) && remove.mutate(operation.id)} disabled={remove.isPending}>Delete</button></div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {selected && <OperationDetails operation={selected} contracts={contractsQuery.data ?? []} onCreateForConnection={() => openCreate(connectionOptions.find((item) => item.connector_id === selected.connection_profile_id) ?? null)} />}
      {installPresets.data && <JsonBlock title="Presets" value={installPresets.data} searchable={false} />}
      {mutationError && <div className="error-state compact">{mutationError.message}</div>}
      {lastResult && <JsonBlock title="Результат теста операции" value={lastResult} searchable />}

      {wizardOpen && (
        <section className="panel connection-wizard operation-wizard">
          <div className="panel-toolbar"><div><span className="eyebrow">Шаг {wizardStep} из 6</span><h2>Создать операцию</h2><p>{wizardStepTitle(wizardStep)}</p></div><button className="ghost-button" type="button" onClick={() => setWizardOpen(false)}>Закрыть</button></div>
          <form className="stack-form" onSubmit={submit}>
            {wizardStep === 1 && <ConnectionStep form={form} connections={connectionOptions} onChange={setForm} />}
            {wizardStep === 2 && <KindStep form={form} onChange={setForm} />}
            {wizardStep === 3 && <RequestStep form={form} contracts={contractsQuery.data ?? []} onChange={setForm} />}
            {wizardStep === 4 && <SuccessStep form={form} onChange={setForm} />}
            {wizardStep === 5 && <ExtractorStep form={form} onChange={setForm} />}
            {wizardStep === 6 && <ReviewStep form={form} lastResult={lastResult} busy={createAndTest.isPending} onSaveAndTest={() => save(true)} />}
            {formError && <div className="error-state compact">{formError}</div>}
            <div className="action-row wrap-actions">
              {wizardStep > 1 && <button type="button" className="ghost-button" onClick={() => setWizardStep((step) => step - 1)}>Назад</button>}
              {wizardStep < 6 && <button type="button" className="primary-button" onClick={() => setWizardStep((step) => step + 1)}>Дальше</button>}
              {wizardStep === 6 && <><button className="ghost-button" disabled={create.isPending}>Сохранить</button><button type="button" className="primary-button" onClick={() => save(true)} disabled={createAndTest.isPending}>Сохранить и dry-run</button></>}
            </div>
          </form>
        </section>
      )}
    </div>
  );
}

function ConnectionStep({ form, connections, onChange }: { form: OperationFormState; connections: ConnectionProfileOption[]; onChange: (value: OperationFormState) => void }) {
  const selected = connections.find((item) => item.connector_id === form.connection_profile_id) ?? null;
  return <div className="stack-form"><h3>Для какого подключения?</h3><label className="field-label full-span">Connection Profile<select value={form.connection_profile_id} onChange={(event) => { const option = connections.find((item) => item.connector_id === event.target.value) ?? null; const kind = connectionKindToOperationKind(option); onChange({ ...form, connection_profile_id: option?.connector_id ?? '', kind, name: defaultName(kind), code: defaultCode(kind), path: defaultPath(kind), package_id: kind === 'onec_http_operation' ? 'omh-package-onec' : '' }); }}><option value="">Manual endpoint / без подключения</option>{connections.map((connection) => <option key={connection.profile_id} value={connection.connector_id}>{connection.label} · {connection.kind} · {connection.base_url ?? 'configured'}</option>)}</select><small>Operation Profile обычно привязан к Connection Profile. Для legacy raw URL можно оставить пусто и указать full_url.</small></label>{selected && <JsonBlock title="Connection option" value={selected} searchable={false} />}</div>;
}

function KindStep({ form, onChange }: { form: OperationFormState; onChange: (value: OperationFormState) => void }) {
  return <div className="connection-kind-grid">{operationCards.map((card) => <button type="button" key={card.kind} className={`selectable-card ${form.kind === card.kind ? 'active' : ''}`} onClick={() => onChange({ ...form, kind: card.kind, name: form.name || defaultName(card.kind), code: form.code || defaultCode(card.kind), path: form.path || defaultPath(card.kind), body_type: card.kind === 'onec_http_operation' && defaultPath(card.kind).includes('xml') ? 'xml' : form.body_type })}><strong>{card.title}</strong><span>{card.detail}</span>{card.planned && <span className="status-badge info compact">partial</span>}</button>)}</div>;
}

function RequestStep({ form, contracts, onChange }: { form: OperationFormState; contracts: DataContract[]; onChange: (value: OperationFormState) => void }) {
  const patch = (value: Partial<OperationFormState>) => onChange({ ...form, ...value });
  return <div className="stack-form"><div className="metadata-grid compact-grid no-margin"><label className="field-label">Название<input value={form.name} onChange={(event) => patch({ name: event.target.value, code: form.code ? form.code : slugify(event.target.value) })} /></label><label className="field-label">Code<input value={form.code} onChange={(event) => patch({ code: slugify(event.target.value) })} /></label><label className="field-label full-span">Описание<input value={form.description} onChange={(event) => patch({ description: event.target.value })} /></label><label className="field-label">Method<select value={form.method} onChange={(event) => patch({ method: event.target.value as OperationMethod })}>{['POST', 'PUT', 'PATCH', 'DELETE', 'GET'].map((method) => <option key={method} value={method}>{method}</option>)}</select></label><label className="field-label">Body type<select value={form.body_type} onChange={(event) => patch({ body_type: event.target.value as OperationBodyType })}><option value="json">JSON</option><option value="xml">XML</option><option value="raw_text">Raw text</option><option value="form">Form</option><option value="none">No body</option></select></label><label className="field-label">Response type<select value={form.response_body_type} onChange={(event) => patch({ response_body_type: event.target.value as OperationBodyType })}><option value="json">JSON</option><option value="xml">XML</option><option value="raw_text">Raw text</option><option value="none">No body</option></select></label><label className="field-label">Timeout, sec<input type="number" min={1} max={300} value={form.timeout_seconds} onChange={(event) => patch({ timeout_seconds: Number(event.target.value) || 20 })} /></label><label className="field-label full-span">Path внутри подключения<input value={form.path} onChange={(event) => patch({ path: event.target.value })} placeholder="/shipment-facts" /><small>Если выбран Connection Profile, final URL = base_url + path.</small></label><label className="field-label full-span">Manual full URL<input value={form.full_url} onChange={(event) => patch({ full_url: event.target.value })} placeholder="https://legacy.example.local/api/import" /><small>Для обратной совместимости. Если задан full_url, он перекрывает Connection + path.</small></label><label className="field-label">Request contract<select value={form.request_contract_id} onChange={(event) => patch({ request_contract_id: event.target.value })}><option value="">Без контракта / raw template</option>{contracts.filter((contract) => contract.kind === 'operation_request' || contract.kind === 'input').map((contract) => <option key={contract.id} value={contract.id}>{contract.name} · {contract.code}</option>)}</select></label><label className="field-label">Response contract<select value={form.response_contract_id} onChange={(event) => patch({ response_contract_id: event.target.value })}><option value="">Без контракта</option>{contracts.filter((contract) => contract.kind === 'operation_response' || contract.kind === 'output').map((contract) => <option key={contract.id} value={contract.id}>{contract.name} · {contract.code}</option>)}</select></label><label className="field-label">Tags<input value={form.tags} onChange={(event) => patch({ tags: event.target.value })} placeholder="dnp,chz" /></label><label className="field-label">Package ID<input value={form.package_id} onChange={(event) => patch({ package_id: event.target.value })} placeholder="omh-package-onec" /></label></div><label className="field-label">Headers JSON<CodeEditor value={form.headers_json} onChange={(value) => patch({ headers_json: value })} language="json" minRows={5} /></label><label className="field-label">Sample request JSON<CodeEditor value={form.sample_request_json} onChange={(value) => patch({ sample_request_json: value })} language="json" minRows={6} /></label><label className="field-label">Sample response JSON/text<CodeEditor value={form.sample_response_json} onChange={(value) => patch({ sample_response_json: value })} language={form.response_body_type === 'xml' ? 'xml' : form.response_body_type === 'raw_text' ? 'text' : 'json'} minRows={6} /></label></div>;
}

function SuccessStep({ form, onChange }: { form: OperationFormState; onChange: (value: OperationFormState) => void }) {
  const patchCondition = (index: number, patch: Partial<ConditionForm>) => onChange({ ...form, conditions: form.conditions.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item) });
  return <div className="stack-form"><div className="metadata-grid compact-grid no-margin"><label className="field-label">Mode<select value={form.success_mode} onChange={(event) => onChange({ ...form, success_mode: event.target.value as 'all' | 'any' })}><option value="all">all conditions</option><option value="any">any condition</option></select></label><span className="builder-help-card"><strong>Success condition</strong><span>Формат сохраняется как <code>{'{"mode":"all","conditions":[...]}'}</code>.</span></span></div>{form.conditions.map((condition, index) => <article className="builder-help-card" key={`${condition.type}-${index}`}><div className="panel-toolbar compact-toolbar"><strong>Condition {index + 1}</strong><button type="button" className="ghost-button danger" onClick={() => onChange({ ...form, conditions: form.conditions.filter((_, itemIndex) => itemIndex !== index) })} disabled={form.conditions.length === 1}>Удалить</button></div><div className="metadata-grid compact-grid no-margin"><label className="field-label">Type<select value={condition.type} onChange={(event) => patchCondition(index, { type: event.target.value as SuccessConditionType })}>{['http_status_2xx', 'http_status_equals', 'json_path_equals', 'json_path_exists', 'response_contains_text', 'always_success'].map((type) => <option key={type} value={type}>{type}</option>)}</select></label>{condition.type === 'http_status_equals' && <label className="field-label">Status<input value={condition.status} onChange={(event) => patchCondition(index, { status: event.target.value })} /></label>}{condition.type.startsWith('json_path') && <label className="field-label">JSON path<input value={condition.path} onChange={(event) => patchCondition(index, { path: event.target.value })} placeholder="success" /></label>}{condition.type === 'json_path_equals' && <label className="field-label">Expected JSON value<input value={condition.value} onChange={(event) => patchCondition(index, { value: event.target.value })} placeholder="true" /></label>}{condition.type === 'response_contains_text' && <label className="field-label">Text<input value={condition.text} onChange={(event) => patchCondition(index, { text: event.target.value })} /></label>}</div></article>)}<button type="button" className="ghost-button" onClick={() => onChange({ ...form, conditions: [...form.conditions, { type: 'json_path_exists', status: '200', path: 'success', value: 'true', text: '' }] })}>Добавить условие</button></div>;
}

function ExtractorStep({ form, onChange }: { form: OperationFormState; onChange: (value: OperationFormState) => void }) {
  const patchExtractor = (index: number, patch: Partial<ExtractorForm>) => onChange({ ...form, extractors: form.extractors.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item) });
  return <div className="stack-form"><div className="status-card neutral"><strong>Response extractors</strong><span>Extractors сохраняют значения из ответа для следующих шагов: <code>{'[{name,path,required}]'}</code>. Required extractor делает test failed, если поля нет.</span></div>{form.extractors.length === 0 && <EmptyState title="Extractors не заданы" detail="Это нормально, если результат ответа не нужен следующим шагам." />}{form.extractors.map((extractor, index) => <article className="builder-help-card" key={`${extractor.name}-${index}`}><div className="panel-toolbar compact-toolbar"><strong>Extractor {index + 1}</strong><button type="button" className="ghost-button danger" onClick={() => onChange({ ...form, extractors: form.extractors.filter((_, itemIndex) => itemIndex !== index) })}>Удалить</button></div><div className="metadata-grid compact-grid no-margin"><label className="field-label">Name<input value={extractor.name} onChange={(event) => patchExtractor(index, { name: event.target.value })} placeholder="external_id" /></label><label className="field-label">Path<input value={extractor.path} onChange={(event) => patchExtractor(index, { path: event.target.value })} placeholder="external_id" /></label><label className="check-row"><input type="checkbox" checked={extractor.required} onChange={(event) => patchExtractor(index, { required: event.target.checked })} />Required</label></div></article>)}<button type="button" className="ghost-button" onClick={() => onChange({ ...form, extractors: [...form.extractors, { name: 'external_id', path: 'external_id', required: true }] })}>Добавить extractor</button></div>;
}

function ReviewStep({ form, lastResult, busy, onSaveAndTest }: { form: OperationFormState; lastResult: OperationTestResponse | null; busy: boolean; onSaveAndTest: () => void }) {
  let payload: OperationProfilePayload | Record<string, unknown>;
  try { payload = payloadFromForm(form); } catch (error) { payload = { error: error instanceof Error ? error.message : 'Invalid payload' }; }
  return <div className="stack-form"><div className="status-card neutral"><strong>Test/save</strong><span>Dry-run сохранит операцию и покажет final URL, headers, body preview, success condition и extractors без сетевого запроса.</span></div><JsonBlock title="Operation payload" value={payload} searchable={false} /><button type="button" className="primary-button" onClick={onSaveAndTest} disabled={busy}>{busy ? 'Сохраняю и проверяю...' : 'Сохранить и dry-run'}</button>{lastResult && <JsonBlock title="Dry-run result" value={lastResult} searchable={false} />}</div>;
}

function OperationDetails({ operation, contracts, onCreateForConnection }: { operation: OperationProfile; contracts: DataContract[]; onCreateForConnection: () => void }) {
  const requestContract = contracts.find((contract) => contract.id === operation.request_contract_id) ?? null;
  const responseContract = contracts.find((contract) => contract.id === operation.response_contract_id) ?? null;
  return <section className="panel flow-detail"><div className="panel-toolbar"><div><span className="eyebrow">Выбранная операция</span><h2>{operation.name}</h2><p>{operation.description || 'Описание не задано'}</p></div><StatusBadge status={operation.enabled ? 'enabled' : 'disabled'} /></div><div className="metadata-grid compact-grid"><span>Kind<strong>{kindLabels[operation.kind]}</strong></span><span>Code<strong>{operation.code}</strong></span><span>Connection<strong>{operation.connection_name ?? 'Manual endpoint'}</strong></span><span>Final URL<strong>{operation.final_url ?? '—'}</strong></span><span>Request contract<strong>{requestContract?.name ?? 'raw template'}</strong></span><span>Response contract<strong>{responseContract?.name ?? '—'}</strong></span><span>Used by<strong>{operation.used_by.join(', ') || '—'}</strong></span><span>Last test<strong>{operation.last_test_at ? new Date(operation.last_test_at).toLocaleString() : '—'}</strong></span></div><div className="action-row wrap-actions"><button className="ghost-button" type="button" onClick={onCreateForConnection}>Создать ещё для этого подключения</button><Link className="ghost-button" to={`/mapping-center?operation=${encodeURIComponent(operation.id)}`}>Сопоставления операции</Link><Link className="ghost-button" to={`/mapping-center/mappings/new?operation=${encodeURIComponent(operation.id)}`}>Создать mapping</Link><Link className="ghost-button" to={`/connection-center?selected=${operation.connection_profile_id ?? ''}`}>Открыть подключение</Link></div><div className="metadata-grid no-margin"><DataContractViewer contract={requestContract} title="Request contract" compact /><DataContractViewer contract={responseContract} title="Response contract" compact /></div><JsonBlock title="Operation config" value={operation} searchable /></section>;
}

function payloadFromForm(form: OperationFormState): OperationProfilePayload {
  const headers = parseJsonObject(form.headers_json, 'Headers JSON');
  const sampleRequest = parseOptionalJson(form.sample_request_json, 'Sample request JSON');
  const sampleResponse = parseOptionalResponse(form.sample_response_json, 'Sample response JSON/text', form.response_body_type);
  return {
    name: form.name.trim(),
    code: slugify(form.code),
    kind: form.kind,
    connection_profile_id: form.connection_profile_id || null,
    request_contract_id: form.request_contract_id || null,
    response_contract_id: form.response_contract_id || null,
    description: form.description.trim() || null,
    enabled: true,
    method: form.method,
    path: form.path.trim() || null,
    full_url: form.full_url.trim() || null,
    headers_json: headers,
    body_type: form.body_type,
    request_template_json: null,
    request_template_text: form.request_template_text.trim() || null,
    response_body_type: form.response_body_type,
    success_condition_json: { mode: form.success_mode, conditions: form.conditions.map(conditionPayload) },
    response_extractors_json: form.extractors.map((extractor) => ({ name: extractor.name.trim(), path: extractor.path.trim(), required: extractor.required })).filter((item) => item.name && item.path),
    sample_request_json: sampleRequest,
    sample_response_json: sampleResponse,
    timeout_seconds: Number(form.timeout_seconds) || 20,
    tags_json: splitTags(form.tags),
    package_id: form.package_id.trim() || null,
  };
}

function conditionPayload(condition: ConditionForm): Record<string, unknown> {
  if (condition.type === 'http_status_equals') return { type: condition.type, status: Number(condition.status) || 200 };
  if (condition.type === 'json_path_exists') return { type: condition.type, path: condition.path.trim() || 'success' };
  if (condition.type === 'json_path_equals') return { type: condition.type, path: condition.path.trim() || 'success', value: parseJsonValue(condition.value) };
  if (condition.type === 'response_contains_text') return { type: condition.type, text: condition.text };
  return { type: condition.type };
}

function formFromOperation(operation: OperationProfile): OperationFormState {
  return {
    name: `${operation.name} copy`,
    code: `${operation.code}_copy`,
    description: operation.description ?? '',
    kind: operation.kind,
    connection_profile_id: operation.connection_profile_id ?? '',
    request_contract_id: operation.request_contract_id ?? '',
    response_contract_id: operation.response_contract_id ?? '',
    method: (operation.method as OperationMethod | null) ?? 'POST',
    path: operation.path ?? '',
    full_url: operation.full_url ?? '',
    headers_json: asJson(operation.headers_json ?? { 'Content-Type': 'application/json' }),
    body_type: (operation.body_type as OperationBodyType | null) ?? 'json',
    request_template_text: operation.request_template_text ?? '',
    response_body_type: (operation.response_body_type as OperationBodyType | null) ?? 'json',
    success_mode: successMode(operation.success_condition_json),
    conditions: conditionsFromConfig(operation.success_condition_json),
    extractors: extractorsFromConfig(operation.response_extractors_json),
    sample_request_json: asJson(operation.sample_request_json ?? {}),
    sample_response_json: typeof operation.sample_response_json === 'string' ? operation.sample_response_json : asJson(operation.sample_response_json ?? { success: true }),
    timeout_seconds: operation.timeout_seconds ?? 20,
    tags: (operation.tags_json ?? []).join(','),
    package_id: operation.package_id ?? '',
  };
}

function conditionsFromConfig(config: unknown): ConditionForm[] {
  if (!isRecord(config) || !Array.isArray(config.conditions)) return [{ type: 'http_status_2xx', status: '200', path: 'success', value: 'true', text: '' }];
  return config.conditions.map((item): ConditionForm => {
    const record = isRecord(item) ? item : {};
    const type = String(record.type ?? 'http_status_2xx') as SuccessConditionType;
    return { type, status: String(record.status ?? '200'), path: String(record.path ?? 'success'), value: typeof record.value === 'undefined' ? 'true' : asJson(record.value), text: String(record.text ?? '') };
  });
}

function extractorsFromConfig(config: unknown): ExtractorForm[] {
  if (!Array.isArray(config)) return [];
  return config.filter(isRecord).map((item) => ({ name: String(item.name ?? ''), path: String(item.path ?? ''), required: Boolean(item.required) })).filter((item) => item.name && item.path);
}

function successMode(config: unknown): 'all' | 'any' {
  return isRecord(config) && config.mode === 'any' ? 'any' : 'all';
}

function filterOperation(operation: OperationProfile, tab: string, connectionFilter: string | null) {
  if (connectionFilter && operation.connection_profile_id !== connectionFilter) return false;
  if (tab === 'all') return true;
  return operation.kind === tab;
}

function connectionKindToOperationKind(connection?: ConnectionProfileOption | null): OperationKind {
  if (!connection) return 'rest_api_operation';
  if (connection.kind === 'onec_http_service') return 'onec_http_operation';
  if (connection.kind === 'printer') return 'printer_operation';
  if (connection.kind === 'smb_share' || connection.kind === 'local_directory') return 'file_operation';
  if (connection.kind === 'training_mock') return 'training_operation';
  return 'rest_api_operation';
}

function defaultName(kind: OperationKind) {
  return ({ rest_api_operation: 'DNP import CHZ codes', onec_http_operation: '1C writeback operation', printer_operation: 'Print labels', file_operation: 'Write file to SMB', training_operation: 'Training API operation' } as Record<OperationKind, string>)[kind];
}

function defaultCode(kind: OperationKind) {
  return ({ rest_api_operation: 'dnp_import_chz_codes', onec_http_operation: 'onec_write_order_external_id', printer_operation: 'printer_print_labels', file_operation: 'file_write_payload', training_operation: 'training_operation' } as Record<OperationKind, string>)[kind];
}

function defaultPath(kind: OperationKind) {
  return ({ rest_api_operation: '/api/v2/integrations/omh/chz/codes/import', onec_http_operation: '/order-external-id', printer_operation: '/print', file_operation: '/outbox', training_operation: '/api/training/mock-dnp/marking/pools' } as Record<OperationKind, string>)[kind];
}

function parseJsonObject(value: string, label: string): Record<string, unknown> {
  const parsed = parseJsonValue(value || '{}');
  if (!isRecord(parsed)) throw new Error(`${label} должен быть JSON object`);
  return parsed;
}

function parseOptionalJson(value: string, label: string): Record<string, unknown> | unknown[] | null {
  if (!value.trim()) return null;
  const parsed = parseJsonValue(value);
  if (isRecord(parsed) || Array.isArray(parsed)) return parsed;
  throw new Error(`${label} должен быть JSON object или array`);
}

function parseOptionalResponse(value: string, label: string, bodyType: OperationBodyType): Record<string, unknown> | unknown[] | string | null {
  if (!value.trim()) return null;
  if (bodyType === 'xml' || bodyType === 'raw_text') return value;
  const parsed = parseJsonValue(value);
  if (isRecord(parsed) || Array.isArray(parsed) || typeof parsed === 'string') return parsed;
  throw new Error(`${label} должен быть JSON object, array или string`);
}

function parseJsonValue(value: string): unknown {
  try { return JSON.parse(value); } catch { return value; }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value));
}

function splitTags(value: string) {
  return value.split(',').map((item) => item.trim()).filter(Boolean);
}

function slugify(value: string) {
  const slug = value.toLowerCase().replace(/[^a-z0-9_.-]+/g, '_').replace(/^[_\-.]+|[_\-.]+$/g, '');
  return slug || 'operation';
}

function wizardStepTitle(step: number) {
  if (step === 1) return 'Для какого подключения?';
  if (step === 2) return 'Какой тип действия выполняет операция?';
  if (step === 3) return 'Method, path, headers, body и samples.';
  if (step === 4) return 'Что считать успешным ответом.';
  if (step === 5) return 'Какие значения забрать из ответа.';
  return 'Проверка и сохранение.';
}
