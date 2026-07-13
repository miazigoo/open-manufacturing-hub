import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { dataContractsApi, type DataContract } from '../api/dataContracts';
import { mappingCenterApi, type MappingFieldRule, type MappingJson, type MappingProfile, type MappingRenderResponse, type MappingSourceType } from '../api/mappingCenter';
import { operationCatalogApi } from '../api/operationCatalog';
import { CodeEditor } from '../components/CodeEditor';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { DataContractViewer } from '../features/mapping-center/DataContractViewer';
import { flattenVariables, getPath, mappedSources, parseJsonObject, safeJson } from '../features/mapping-center/utils';

interface BuilderForm {
  name: string;
  code: string;
  description: string;
  target_contract_id: string;
  operation_profile_id: string;
  package_id: string;
  source_context_json: string;
  mapping_json: string;
}

const sourceTypes: MappingSourceType[] = ['variable', 'constant', 'template', 'dynamic_object_entry'];

export function MappingBuilderPage() {
  const { mappingId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isNew = !mappingId;
  const presetCode = searchParams.get('preset');
  const operationParam = searchParams.get('operation');
  const [selectedRule, setSelectedRule] = useState(0);
  const [loadedKey, setLoadedKey] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [form, setForm] = useState<BuilderForm>(() => emptyForm());
  const mappingQuery = useQuery({ queryKey: ['mapping-center-mapping', mappingId], queryFn: () => mappingCenterApi.get(String(mappingId)), enabled: !isNew });
  const contractsQuery = useQuery({ queryKey: ['data-contracts'], queryFn: () => dataContractsApi.list() });
  const operationsQuery = useQuery({ queryKey: ['operation-catalog-options'], queryFn: operationCatalogApi.options });
  const presetsQuery = useQuery({ queryKey: ['mapping-center-presets'], queryFn: mappingCenterApi.presets });
  const preview = useMutation({ mutationFn: previewRequest });
  const validate = useMutation({ mutationFn: validateRequest });
  const save = useMutation({ mutationFn: saveMapping, onSuccess: (mapping) => { queryClient.invalidateQueries({ queryKey: ['mapping-center-mappings'] }); navigate(`/mapping-center/mappings/${mapping.id}`); } });
  const contracts = contractsQuery.data ?? [];
  const operations = operationsQuery.data?.operations ?? [];
  const selectedContract = contracts.find((contract) => contract.id === form.target_contract_id) ?? null;
  const sourceContext = parseJsonObject<Record<string, unknown>>(form.source_context_json, {});
  const mappingJson = parseJsonObject<MappingJson>(form.mapping_json, defaultMapping());
  const variables = useMemo(() => flattenVariables(sourceContext), [sourceContext]);
  const groupedVariables = useMemo(() => groupVariables(variables), [variables]);
  const fields = Array.isArray(mappingJson.fields) ? mappingJson.fields : [];
  const rendered = preview.data as MappingRenderResponse | undefined;

  useEffect(() => {
    if (!isNew || !presetCode || !presetsQuery.data || loadedKey === `preset:${presetCode}`) return;
    const preset = presetsQuery.data.mappings.find((item) => item.code === presetCode);
    if (!preset) return;
    const contract = contracts.find((item) => item.code === preset.target_contract_code);
    const operation = operations.find((item) => item.code === preset.operation_profile_code);
    setForm({
      name: String(preset.name ?? 'New mapping'),
      code: String(preset.code ?? 'new_mapping'),
      description: String(preset.description ?? ''),
      target_contract_id: contract?.id ?? '',
      operation_profile_id: operation?.id ?? '',
      package_id: String(preset.package_id ?? ''),
      source_context_json: safeJson(preset.source_context_json ?? {}),
      mapping_json: safeJson(preset.mapping_json ?? defaultMapping()),
    });
    setLoadedKey(`preset:${presetCode}`);
  }, [contracts, isNew, loadedKey, operations, presetCode, presetsQuery.data]);

  useEffect(() => {
    if (!isNew || presetCode || !operationParam || loadedKey === `operation:${operationParam}`) return;
    const operation = operations.find((item) => item.id === operationParam);
    if (!operation) return;
    setForm((current) => ({
      ...current,
      name: `${operation.name} mapping`,
      code: `mapping_${operation.code}`,
      operation_profile_id: operation.id,
      target_contract_id: operation.request_contract_id ?? '',
      description: `Payload mapping для операции ${operation.name}.`,
    }));
    setLoadedKey(`operation:${operationParam}`);
  }, [isNew, loadedKey, operationParam, operations, presetCode]);

  useEffect(() => {
    if (isNew || !mappingQuery.data || loadedKey === mappingQuery.data.id) return;
    setForm(formFromMapping(mappingQuery.data));
    setLoadedKey(mappingQuery.data.id);
  }, [isNew, loadedKey, mappingQuery.data]);

  if (mappingQuery.isLoading || contractsQuery.isLoading || operationsQuery.isLoading) return <LoadingState label="Загружаю builder" />;
  if (mappingQuery.error) return <ErrorState error={mappingQuery.error} />;
  if (contractsQuery.error) return <ErrorState error={contractsQuery.error} />;
  if (operationsQuery.error) return <ErrorState error={operationsQuery.error} />;

  function patch(patchValue: Partial<BuilderForm>) {
    setForm((current) => ({ ...current, ...patchValue }));
  }

  async function previewRequest() {
    return mappingCenterApi.preview({ target_contract_id: form.target_contract_id || null, source_context_json: parseRequiredObject(form.source_context_json, 'Пример данных'), mapping_json: parseRequiredObject(form.mapping_json, 'Mapping JSON') });
  }

  async function validateRequest() {
    return mappingCenterApi.validate({ target_contract_id: form.target_contract_id || null, source_context_json: parseRequiredObject(form.source_context_json, 'Пример данных'), mapping_json: parseRequiredObject(form.mapping_json, 'Mapping JSON') });
  }

  async function saveMapping() {
    setFormError(null);
    const payload = {
      name: form.name.trim(),
      code: slugify(form.code),
      description: form.description.trim() || null,
      target_contract_id: form.target_contract_id || null,
      operation_profile_id: form.operation_profile_id || null,
      package_id: form.package_id.trim() || null,
      source_context_json: parseRequiredObject(form.source_context_json, 'Пример данных'),
      mapping_json: parseRequiredObject(form.mapping_json, 'Mapping JSON'),
    };
    if (!payload.name || !payload.code) throw new Error('Укажите name и code mapping profile.');
    return isNew ? mappingCenterApi.create(payload) : mappingCenterApi.patch(String(mappingId), payload);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    save.mutate(undefined, { onError: (error) => setFormError(error instanceof Error ? error.message : 'Не удалось сохранить mapping') });
  }

  function updateRule(index: number, patchValue: Partial<MappingFieldRule>) {
    const next = normalizeMapping(mappingJson);
    next.fields = next.fields.map((field, fieldIndex) => fieldIndex === index ? { ...field, ...patchValue } : field);
    patch({ mapping_json: asJson(next) });
  }

  function addRule(targetPath = selectedContract?.fields?.[0]?.path ?? 'payload.field') {
    const next = normalizeMapping(mappingJson);
    next.fields = [...next.fields, { target_path: targetPath, source_type: 'variable', source: variables[0]?.path ?? '', preserve_type: true }];
    setSelectedRule(next.fields.length - 1);
    patch({ mapping_json: asJson(next) });
  }

  function removeRule(index: number) {
    const next = normalizeMapping(mappingJson);
    next.fields = next.fields.filter((_, fieldIndex) => fieldIndex !== index);
    setSelectedRule(Math.max(0, index - 1));
    patch({ mapping_json: asJson(next) });
  }

  function useSource(path: string) {
    if (!fields[selectedRule]) return;
    updateRule(selectedRule, { source: path, source_type: fields[selectedRule].source_type === 'constant' ? 'variable' : fields[selectedRule].source_type });
  }

  return (
    <form className="page-stack mapping-builder-page" onSubmit={submit}>
      <section className="page-header product-page-header connection-center-hero">
        <div>
          <span className="eyebrow">Mapping Builder</span>
          <h1>{isNew ? 'Новое сопоставление' : form.name}</h1>
          <p>Сопоставьте source variables с target contract и проверьте rendered payload до использования в wizard.</p>
        </div>
        <div className="product-header-actions">
          <button className="primary-button" disabled={save.isPending}>{save.isPending ? 'Сохраняю...' : 'Сохранить'}</button>
          <button type="button" className="ghost-button" onClick={() => preview.mutate()} disabled={preview.isPending}>Preview</button>
          <button type="button" className="ghost-button" onClick={() => validate.mutate()} disabled={validate.isPending}>Validate</button>
          <Link className="ghost-button" to="/mapping-center">Назад</Link>
        </div>
      </section>

      <section className="panel">
        <div className="metadata-grid compact-grid no-margin">
          <label className="field-label">Название<input value={form.name} onChange={(event) => patch({ name: event.target.value, code: form.code || slugify(event.target.value) })} /></label>
          <label className="field-label">Code<input value={form.code} onChange={(event) => patch({ code: slugify(event.target.value) })} /></label>
          <label className="field-label">Целевой контракт<select value={form.target_contract_id} onChange={(event) => patch({ target_contract_id: event.target.value })}><option value="">Raw template / без контракта</option>{contracts.map((contract) => <option key={contract.id} value={contract.id}>{contract.name} · {contract.code}</option>)}</select></label>
          <label className="field-label">Операция<select value={form.operation_profile_id} onChange={(event) => patch({ operation_profile_id: event.target.value })}><option value="">Не привязано к операции</option>{operations.map((operation) => <option key={operation.id} value={operation.id}>{operation.name} · {operation.code}</option>)}</select></label>
          <label className="field-label full-span">Описание<input value={form.description} onChange={(event) => patch({ description: event.target.value })} /></label>
          <label className="field-label">Package ID<input value={form.package_id} onChange={(event) => patch({ package_id: event.target.value })} placeholder="omh-package-onec" /></label>
          <span className="builder-help-card"><strong>Raw fallback</strong><span>Если контракта нет, mapping всё равно можно сохранить и использовать как raw template. Проверка required полей будет недоступна.</span></span>
        </div>
      </section>

      <section className="guidance-strip">
        <div className="guidance-head">
          <div>
            <span className="eyebrow">Как заполнить builder</span>
            <h2>Работайте слева направо</h2>
            <p>Сначала задайте пример данных, затем выберите source variable, target field и проверьте rendered payload. Raw JSON ниже нужен только для advanced правок.</p>
          </div>
          <div className="action-row wrap-actions">
            <button type="button" className="ghost-button" onClick={() => preview.mutate()} disabled={preview.isPending}>Preview now</button>
            <button type="button" className="ghost-button" onClick={() => validate.mutate()} disabled={validate.isPending}>Validate</button>
          </div>
        </div>
        <div className="guidance-step-grid">
          <article className="guidance-step-card"><span>Source</span><strong>Пример данных</strong><p>Заполните <code>Source context editor</code>: request, OData results, foreach arrays and context. Builder сам разложит это на переменные.</p></article>
          <article className="guidance-step-card"><span>Map</span><strong>Mapping table</strong><p>Кликните source variable слева, затем выберите target field. Для массивов включайте <code>preserve_type</code>, чтобы не превратить массив в строку.</p></article>
          <article className="guidance-step-card"><span>Check</span><strong>Preview & Validate</strong><p><code>Preview</code> показывает итоговый payload, <code>Validate</code> проверяет required поля target contract.</p></article>
        </div>
      </section>

      <section className="panel mapping-workbench-grid">
        <div className="panel-toolbar"><h2>Builder</h2><span className="microcopy">Source variables to target operation payload</span></div>
        <div className="metadata-grid no-margin">
          <section className="builder-help-card">
            <div className="panel-toolbar compact-toolbar"><div><span className="eyebrow">Left</span><h3>Source variables</h3></div><StatusBadge status="ready" compact /></div>
            {Object.entries(groupedVariables).map(([group, items]) => (
              <details key={group} open={group === 'request' || group === 'order'}>
                <summary>{group} <strong>{items.length}</strong></summary>
                <div className="odata-variable-grid">
                  {items.slice(0, 40).map((item) => <button key={item.path} type="button" className="builder-help-card" onClick={() => useSource(item.path)}><strong>{item.path}</strong><span>{item.type} · {formatShort(item.value)}</span></button>)}
                </div>
              </details>
            ))}
            {variables.length === 0 && <EmptyState title="Source variables не найдены" detail="Заполните пример данных для проверки ниже." />}
          </section>

          <section className="builder-help-card">
            <div className="panel-toolbar compact-toolbar"><div><span className="eyebrow">Center</span><h3>Mapping table</h3></div><button type="button" className="ghost-button" onClick={() => addRule()}>Добавить поле</button></div>
            <div className="table-scroll">
              <table>
                <thead><tr><th>Target field</th><th>Source type</th><th>Source/value</th><th>Preview</th><th>Status</th><th></th></tr></thead>
                <tbody>
                  {fields.map((field, index) => {
                    const value = getPath(rendered?.payload, field.target_path);
                    const sourceValue = field.source_type === 'constant' ? asJson(field.value ?? null) : field.source ?? '';
                    const issue = [...(rendered?.errors ?? []), ...(rendered?.warnings ?? [])].find((item) => item.path === field.target_path || item.path === field.source);
                    return (
                      <tr key={`${field.target_path}-${index}`} className={selectedRule === index ? 'selected-row' : ''} onClick={() => setSelectedRule(index)}>
                        <td><select value={field.target_path} onChange={(event) => updateRule(index, { target_path: event.target.value })}>{targetOptions(selectedContract, field.target_path).map((path) => <option key={path} value={path}>{path}</option>)}</select></td>
                        <td><select value={field.source_type} onChange={(event) => updateRule(index, { source_type: event.target.value as MappingSourceType })}>{sourceTypes.map((type) => <option key={type} value={type}>{type}</option>)}</select></td>
                        <td><input value={sourceValue} onChange={(event) => updateRule(index, field.source_type === 'constant' ? { value: parseConstant(event.target.value) } : { source: event.target.value })} /></td>
                        <td><small>{typeof value === 'undefined' ? '—' : formatShort(value)}</small></td>
                        <td><StatusBadge status={issue ? (issue.severity === 'warning' ? 'warning' : 'failed') : value === undefined ? 'unknown' : 'ready'} label={issue?.error_code ?? (value === undefined ? 'not rendered' : 'mapped')} compact /></td>
                        <td><button type="button" className="ghost-button danger" onClick={() => removeRule(index)}>Delete</button></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>

          <DataContractViewer contract={selectedContract} mappedSources={mappedSources(mappingJson)} title="Right: target contract" compact />
        </div>
      </section>

      <section className="panel">
        <div className="panel-toolbar"><div><span className="eyebrow">Пример данных для проверки</span><h2>Source context editor</h2></div><StatusBadge status={variables.length ? 'ready' : 'missing'} compact /></div>
        <CodeEditor value={form.source_context_json} onChange={(value) => patch({ source_context_json: value })} language="json" minRows={10} />
      </section>

      <section className="panel">
        <div className="panel-toolbar"><div><span className="eyebrow">Advanced mode</span><h2>Raw mapping JSON</h2></div><StatusBadge status="experimental" compact /></div>
        <CodeEditor value={form.mapping_json} onChange={(value) => patch({ mapping_json: value })} language="json" minRows={12} />
      </section>

      <section className="panel">
        <div className="panel-toolbar"><h2>Rendered preview</h2><div className="action-row"><button type="button" className="ghost-button" onClick={() => preview.mutate()} disabled={preview.isPending}>Обновить preview</button><button type="button" className="ghost-button" onClick={() => validate.mutate()} disabled={validate.isPending}>Проверить mapping</button></div></div>
        {preview.error && <div className="error-state compact">{preview.error instanceof Error ? preview.error.message : 'Preview failed'}</div>}
        {validate.error && <div className="error-state compact">{validate.error instanceof Error ? validate.error.message : 'Validation failed'}</div>}
        {formError && <div className="error-state compact">{formError}</div>}
        {validate.data && <JsonBlock title="Validation result" value={validate.data} searchable={false} />}
        {preview.data ? <JsonBlock title="Rendered payload" value={preview.data} searchable /> : <EmptyState title="Preview ещё не запускали" detail="Нажмите Preview, чтобы увидеть payload, errors и warnings." />}
      </section>
    </form>
  );
}

function emptyForm(): BuilderForm {
  return {
    name: 'DNP — импорт кодов ЧЗ',
    code: 'mapping_dnp_chz_codes_import',
    description: '',
    target_contract_id: '',
    operation_profile_id: '',
    package_id: 'omh-package-onec',
    source_context_json: asJson({ context: { run_id: 'run-001', event_id: 'evt-001' }, request: { body: { order_name: '260666/6938' } }, order: { Ref_Key: '4f1f5c6d-2d3a-11ef-9c7a-005056a1b2c3', Number: '260666/6938' }, codes: [{ code: '0104600439937818215ABC' }] }),
    mapping_json: asJson(defaultMapping()),
  };
}

function defaultMapping(): MappingJson {
  return { version: 1, fields: [{ target_path: 'payload.rows', source_type: 'variable', source: 'codes', preserve_type: true }], dynamic_entries: [] };
}

function formFromMapping(mapping: MappingProfile): BuilderForm {
  return {
    name: mapping.name,
    code: mapping.code,
    description: mapping.description ?? '',
    target_contract_id: mapping.target_contract_id ?? '',
    operation_profile_id: mapping.operation_profile_id ?? '',
    package_id: mapping.package_id ?? '',
    source_context_json: safeJson(mapping.source_context_json ?? {}),
    mapping_json: safeJson(mapping.mapping_json ?? defaultMapping()),
  };
}

function normalizeMapping(mapping: MappingJson | Record<string, unknown>): MappingJson {
  const fields = Array.isArray((mapping as { fields?: unknown }).fields) ? (mapping as { fields: MappingFieldRule[] }).fields : [];
  const dynamicEntries = Array.isArray((mapping as { dynamic_entries?: unknown }).dynamic_entries) ? (mapping as MappingJson).dynamic_entries : [];
  return { version: 1, target_contract_code: typeof (mapping as { target_contract_code?: unknown }).target_contract_code === 'string' ? (mapping as { target_contract_code: string }).target_contract_code : null, fields, dynamic_entries: dynamicEntries };
}

function targetOptions(contract: DataContract | null, current: string) {
  const paths = contract?.fields?.map((field) => field.path) ?? [];
  return paths.includes(current) ? paths : [current, ...paths].filter(Boolean);
}

function groupVariables(variables: ReturnType<typeof flattenVariables>) {
  return variables.reduce<Record<string, typeof variables>>((acc, item) => {
    acc[item.group] = acc[item.group] ?? [];
    acc[item.group].push(item);
    return acc;
  }, {});
}

function parseRequiredObject(value: string, label: string): Record<string, unknown> {
  const parsed = JSON.parse(value || '{}');
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error(`${label} должен быть JSON object`);
  return parsed;
}

function parseConstant(value: string): unknown {
  try { return JSON.parse(value); } catch { return value; }
}

function formatShort(value: unknown) {
  if (typeof value === 'string') return value;
  if (typeof value === 'undefined') return '—';
  return asJson(value).slice(0, 180);
}

function slugify(value: string) {
  const slug = value.toLowerCase().replace(/[^a-z0-9_.-]+/g, '_').replace(/^[_\-.]+|[_\-.]+$/g, '');
  return slug || 'mapping_profile';
}
