import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { BusinessKeySelector } from './BusinessKeySelector';
import { EndpointSlugEditor, slugError, slugify } from './EndpointSlugEditor';
import { InputContractPreview } from './InputContractPreview';
import { InputTypeSelector } from './InputTypeSelector';
import { integrationMasterApi } from './api';
import { FinalActionBuilder } from './final-action/FinalActionBuilder';
import { ForeachODataStepBuilder } from './foreach-odata-step/ForeachODataStepBuilder';
import { MasterStepLayout } from './MasterStepLayout';
import { ODataObjectStepBuilder } from './odata-object-step/ODataObjectStepBuilder';
import { OperationKeySelector } from './OperationKeySelector';
import { ODataStepBuilder } from './odata-step/ODataStepBuilder';
import { PayloadBuilder } from './payload-builder/PayloadBuilder';
import { ParsedFieldsTable } from './ParsedFieldsTable';
import { SampleInputEditor } from './SampleInputEditor';
import { ScenarioChooser } from './ScenarioChooser';
import type { BusinessKeySuggestion, InputBusinessKey, InputContract, InputContractField, InputDraftRead, InputMode, InputOperationKey, InputParseResponse, IntegrationScenario, OperationKeySuggestion } from './types';

export function IntegrationMasterPage() {
  const scenarios = useQuery({ queryKey: ['integration-master-scenarios'], queryFn: integrationMasterApi.scenarios });
  const [selected, setSelected] = useState<IntegrationScenario | null>(null);
  const [inputMode, setInputMode] = useState<InputMode>('json');
  const [sampleText, setSampleText] = useState('');
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [sourceSystem, setSourceSystem] = useState('external_api');
  const [parseResult, setParseResult] = useState<InputParseResponse | null>(null);
  const [savedDraft, setSavedDraft] = useState<InputDraftRead | null>(null);
  const [previousVariables, setPreviousVariables] = useState<Record<string, unknown>>({});
  const [fields, setFields] = useState<InputContractField[]>([]);
  const [operationKey, setOperationKey] = useState<InputOperationKey>({ type: 'endpoint', field_path: null, value: null, fallback_paths: [], matcher_preview: { mode: 'endpoint', rules: [] } });
  const [businessKey, setBusinessKey] = useState<InputBusinessKey>({ path: null, fallback_paths: [] });

  useEffect(() => {
    if (!selected && scenarios.data?.length) applyScenario(scenarios.data[0]);
  }, [scenarios.data, selected]);

  const parse = useMutation({
    mutationFn: () => integrationMasterApi.parse({ input_mode: inputMode, scenario_key: selected?.key, sample: sampleText }),
    onSuccess: (data) => {
      setParseResult(data);
      setFields(data.fields);
      setOperationKey(operationFromSuggestion(data.suggested_operation_keys[0]));
      setBusinessKey(businessFromSuggestion(data.suggested_business_keys[0]));
      setSavedDraft(null);
      setPreviousVariables({});
      saveDraft.reset();
    },
  });

  const validation = useMutation({ mutationFn: (contract: InputContract) => integrationMasterApi.validate(contract) });
  const saveDraft = useMutation({ mutationFn: (contract: InputContract) => integrationMasterApi.saveDraft(contract, parseResult), onSuccess: (data) => { setSavedDraft(data.draft); setPreviousVariables({}); } });
  const contract = useMemo(() => buildContract({ name, slug, inputMode, sourceSystem, selected, sample: parseResult?.normalized_sample ?? sampleText, fields, operationKey, businessKey }), [name, slug, inputMode, sourceSystem, selected, parseResult, sampleText, fields, operationKey, businessKey]);
  const objectVariables = useMemo(() => ({ ...deriveVariablesFromDraft(savedDraft), ...previousVariables }), [savedDraft, previousVariables]);

  if (scenarios.isPending) return <LoadingState label="Загрузка мастера интеграции" />;
  if (scenarios.error) return <ErrorState error={scenarios.error} />;

  function applyScenario(scenario: IntegrationScenario) {
    const mode = scenario.default_input_mode;
    setSelected(scenario);
    setInputMode(mode);
    setName(scenario.title);
    setSlug(scenario.default_slug);
    setSourceSystem(scenario.source_system);
    setSampleText(sampleToText(scenario.sample, mode));
    setParseResult(null);
    setFields([]);
    setSavedDraft(null);
    setPreviousVariables({});
    setOperationKey({ type: 'endpoint', field_path: null, value: null, fallback_paths: [], matcher_preview: { mode: 'endpoint', rules: [] } });
    setBusinessKey({ path: null, fallback_paths: [] });
    validation.reset();
    saveDraft.reset();
  }

  function changeInputMode(mode: InputMode) {
    setInputMode(mode);
    setSampleText(selected && selected.default_input_mode === mode ? sampleToText(selected.sample, mode) : sampleToText(defaultSample(mode), mode));
    setParseResult(null);
    setFields([]);
    setSavedDraft(null);
    setPreviousVariables({});
    validation.reset();
    saveDraft.reset();
  }

  function useOperationField(field: InputContractField) {
    setOperationKey({ type: 'field', field_path: field.path, value: field.example ?? '', fallback_paths: [], matcher_preview: matcherPreview(field.path, field.example ?? '', []) });
  }

  function useBusinessField(field: InputContractField) {
    setBusinessKey({ path: field.path, fallback_paths: [] });
  }

  function validateContract() {
    validation.mutate(contract);
  }

  function saveContractDraft() {
    const error = slugError(slug);
    if (error) {
      validation.mutate(contract);
      return;
    }
    saveDraft.mutate(contract);
  }

  const parseError = parse.error instanceof Error ? parse.error.message : null;
  const saveError = saveDraft.error instanceof Error ? saveDraft.error.message : validation.error instanceof Error ? validation.error.message : null;
  const savedResponse = savedDraft ? { draft: savedDraft, next_steps: saveDraft.data?.next_steps ?? [] } : saveDraft.data ?? null;
  const hasSavedODataQuery = Boolean(savedDraft?.odata_steps.some((step) => !step.type || step.type === 'odata_query'));
  const hasSavedObjectStep = Boolean(savedDraft?.odata_steps.some((step) => step.type === 'odata_object_query'));
  const hasSavedForeachStep = Boolean(savedDraft?.odata_steps.some((step) => step.type === 'foreach_odata'));
  const hasSavedPayloadStep = Boolean(savedDraft?.odata_steps.some((step) => step.type === 'build_payload'));

  return (
    <div className="page-stack integration-master-page">
      <section className="hero-panel integration-master-hero">
        <div>
          <span className="eyebrow">Мастер интеграции</span>
          <h1>С чего начнём?</h1>
          <p>Выберите, кто будет обращаться к OMH и какие данные придут. На основе этого OMH подготовит входящий контракт для дальнейшей настройки интеграции.</p>
          <div className="hero-meta"><span>Первый шаг интеграции — понять входящий request, а не сразу строить OData workflow.</span><Link className="primary-link" to="/docs/reference/integration-master/overview">Инструкция</Link></div>
        </div>
        <div className="hero-instrument"><span>IC</span><small>INPUT CONTRACT</small></div>
      </section>

      <MasterStepLayout index="01" title="Выберите сценарий" description="Карточки описывают реальные интеграции человеческим языком: кто вызывает OMH, что приходит и что обычно будет дальше.">
        <ScenarioChooser scenarios={scenarios.data ?? []} selectedKey={selected?.key} onSelect={applyScenario} />
      </MasterStepLayout>

      <MasterStepLayout index="02" title="Что придёт во входящем запросе" description="Выберите JSON, XML или raw text и вставьте реальный sample. OMH разберёт поля, пути и типы.">
        <InputTypeSelector value={inputMode} allowed={selected?.input_modes ?? []} onChange={changeInputMode} />
        <div className="metadata-grid compact-grid no-margin">
          <label className="field-label">Название контракта<input value={name} onChange={(event) => setName(event.target.value)} /></label>
          <label className="field-label">Source system<select value={sourceSystem} onChange={(event) => setSourceSystem(event.target.value)}><option value="external_api">External API / Website</option><option value="dnp">DnP</option><option value="onec">1C</option><option value="wms">WMS</option><option value="printer">Printer</option><option value="other">Other</option></select></label>
        </div>
        <EndpointSlugEditor value={slug} onChange={setSlug} />
        <SampleInputEditor inputMode={inputMode} value={sampleText} error={parseError} onChange={setSampleText} onParse={() => parse.mutate()} parsing={parse.isPending} />
      </MasterStepLayout>

      <MasterStepLayout index="03" title="Проверьте Input Contract Table" description="Поля из sample считаются required по умолчанию. Здесь можно сделать поле optional и добавить описание для следующих шагов мастера.">
        <ParsedFieldsTable fields={fields} operationPath={operationKey.field_path} businessPath={businessKey.path} onChange={setFields} onUseOperation={useOperationField} onUseBusiness={useBusinessField} />
      </MasterStepLayout>

      <MasterStepLayout index="04" title="Как OMH поймёт, что это этот сценарий" description="Выберите route key. Для DnP по умолчанию это sinc=dnp_sinc_pull_codes с fallback на operation.">
        <OperationKeySelector value={operationKey} suggestions={parseResult?.suggested_operation_keys ?? []} fields={fields} onChange={(value) => setOperationKey(withMatcher(value))} />
      </MasterStepLayout>

      <MasterStepLayout index="05" title="Что считать номером события" description="Business key попадёт в журнал событий и Timeline. Выбирайте поле, по которому оператор потом найдёт конкретный запрос.">
        <BusinessKeySelector value={businessKey} suggestions={parseResult?.suggested_business_keys ?? []} fields={fields} onChange={setBusinessKey} />
      </MasterStepLayout>

      <InputContractPreview contract={contract} validation={validation.data ?? null} saved={savedResponse} error={saveError} onValidate={validateContract} onSave={saveContractDraft} validating={validation.isPending} saving={saveDraft.isPending} />

      {savedDraft ? <ODataStepBuilder contract={savedDraft.contract} draft={savedDraft} onDraftUpdated={setSavedDraft} onVariablesUpdated={(variables) => setPreviousVariables((current) => ({ ...current, ...variables }))} /> : null}

      {savedDraft && hasSavedODataQuery ? <ODataObjectStepBuilder contract={savedDraft.contract} draft={savedDraft} previousVariables={objectVariables} onDraftUpdated={setSavedDraft} onVariablesUpdated={(variables) => setPreviousVariables((current) => ({ ...current, ...variables }))} /> : null}

      {savedDraft && hasSavedObjectStep ? <ForeachODataStepBuilder contract={savedDraft.contract} draft={savedDraft} previousVariables={objectVariables} onDraftUpdated={setSavedDraft} onVariablesUpdated={(variables) => setPreviousVariables((current) => ({ ...current, ...variables }))} /> : null}

      {savedDraft && hasSavedForeachStep ? <PayloadBuilder contract={savedDraft.contract} draft={savedDraft} previousVariables={objectVariables} onDraftUpdated={setSavedDraft} onVariablesUpdated={(variables) => setPreviousVariables((current) => ({ ...current, ...variables }))} /> : null}

      {savedDraft && hasSavedPayloadStep ? <FinalActionBuilder contract={savedDraft.contract} draft={savedDraft} previousVariables={objectVariables} onDraftUpdated={setSavedDraft} /> : null}
    </div>
  );
}

interface BuildContractInput {
  name: string;
  slug: string;
  inputMode: InputMode;
  sourceSystem: string;
  selected: IntegrationScenario | null;
  sample: unknown;
  fields: InputContractField[];
  operationKey: InputOperationKey;
  businessKey: InputBusinessKey;
}

function buildContract({ name, slug, inputMode, sourceSystem, selected, sample, fields, operationKey, businessKey }: BuildContractInput): InputContract {
  return {
    name: name || selected?.title || 'Новый входящий контракт',
    slug: slugify(slug || selected?.default_slug || 'new_integration'),
    input_mode: inputMode,
    source_system: sourceSystem,
    scenario_key: selected?.key ?? null,
    sample,
    fields,
    operation_key: withMatcher(operationKey),
    business_key: businessKey,
    endpoint_url: `/api/bus/in/${slugify(slug || selected?.default_slug || 'new_integration')}`,
  };
}

function operationFromSuggestion(suggestion?: OperationKeySuggestion): InputOperationKey {
  if (!suggestion) return { type: 'endpoint', field_path: null, value: null, fallback_paths: [], matcher_preview: { mode: 'endpoint', rules: [] } };
  return { type: suggestion.type, field_path: suggestion.field_path ?? null, value: suggestion.value ?? null, fallback_paths: suggestion.fallback_paths, matcher_preview: suggestion.matcher_json };
}

function businessFromSuggestion(suggestion?: BusinessKeySuggestion): InputBusinessKey {
  return { path: suggestion?.path ?? null, fallback_paths: suggestion?.fallback_paths ?? [] };
}

function withMatcher(value: InputOperationKey): InputOperationKey {
  return { ...value, matcher_preview: matcherPreview(value.field_path ?? null, value.value, value.fallback_paths, value.type) };
}

function matcherPreview(path?: string | null, value?: unknown, fallbackPaths: string[] = [], type = 'field') {
  if (type === 'endpoint') return { mode: 'endpoint', rules: [] };
  if (type === 'none') return { mode: 'none', rules: [] };
  const rules = path && value !== null && value !== undefined && value !== '' ? [{ type: 'body_path_equals', path: relativePath(path), value }, ...fallbackPaths.map((fallback) => ({ type: 'body_path_equals', path: relativePath(fallback), value }))] : [];
  return { mode: 'any', rules };
}

function relativePath(path: string) {
  return path.replace(/^request\.body\./, '').replace(/^request\.raw_text\./, '').replace(/^xml\./, '');
}

function sampleToText(sample: unknown, mode: InputMode) {
  if (typeof sample === 'string') return sample;
  if (mode === 'json') return JSON.stringify(sample ?? {}, null, 2);
  return String(sample ?? '');
}

function defaultSample(mode: InputMode) {
  if (mode === 'xml') return '<Документ>\n  <Тип>УПД</Тип>\n  <Номер>123</Номер>\n  <ИНН>7707083893</ИНН>\n</Документ>';
  if (mode === 'raw_text') return 'operation=dnp_sinc_pull_codes;Number=260666/6938';
  return { operation: 'lookup_contractor', inn: '7707083893' };
}

function deriveVariablesFromDraft(draft: InputDraftRead | null): Record<string, unknown> {
  const variables: Record<string, unknown> = draft ? {
    request: requestVariableFromDraft(draft),
    context: { run_id: 'preview-run-001', event_id: 'preview-event-001', queue_item_id: 'preview-queue-item-001' },
  } : {};
  for (const step of draft?.odata_steps ?? []) {
    if (step.type === 'build_payload') {
      variables[step.save_as] = step.body_type === 'json' ? {} : '';
      continue;
    }
    if (step.type === 'odata_object_query') {
      variables[step.save_as] = [];
      continue;
    }
    if (step.type === 'foreach_odata') {
      variables[step.save_as] = [];
      continue;
    }
    const fields = step.select.length ? step.select : ['Ref_Key'];
    variables[step.save_as] = Object.fromEntries(fields.map((field) => [field, null]));
  }
  return variables;
}

function requestVariableFromDraft(draft: InputDraftRead) {
  if (draft.contract.input_mode === 'json' && draft.contract.sample && typeof draft.contract.sample === 'object') {
    return { body: draft.contract.sample };
  }
  if (draft.contract.input_mode === 'raw_text') {
    return { body: {}, raw_text: String(draft.contract.sample ?? '') };
  }
  return { body: {}, xml: String(draft.contract.sample ?? '') };
}
