import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { integrationPatternsApi, localized, type IntegrationPattern } from '../../api/integrationPatterns';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { StatusBadge } from '../../components/StatusBadge';
import { BusinessKeySelector } from './BusinessKeySelector';
import { EndpointSlugEditor, slugError, slugify, suggestedSlug } from './EndpointSlugEditor';
import { InputContractPreview } from './InputContractPreview';
import { InputTypeSelector } from './InputTypeSelector';
import { integrationMasterApi } from './api';
import { CompileIntegrationStep } from './compile/CompileIntegrationStep';
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

// Dynamically split pattern wizards so they aren't bundled into the initial IntegrationMaster chunk!
const RequestODataResponseWizard = lazy(() => import('../pattern-wizards/request-odata-response/RequestODataResponseWizard').then((m) => ({ default: m.RequestODataResponseWizard })));
const RequestODataSendEndpointWizard = lazy(() => import('../pattern-wizards/request-odata-send-endpoint/RequestODataSendEndpointWizard').then((m) => ({ default: m.RequestODataSendEndpointWizard })));
const DnpChzCodePoolWizard = lazy(() => import('../pattern-wizards/request-odata-object-foreach-send-endpoint/DnpChzCodePoolWizard').then((m) => ({ default: m.DnpChzCodePoolWizard })));
const SourceWebApiWritebackOnecWizard = lazy(() => import('../pattern-wizards/source-web-api-writeback-onec/SourceWebApiWritebackOnecWizard').then((m) => ({ default: m.SourceWebApiWritebackOnecWizard })));
const RequestMultipleODataResponseWizard = lazy(() => import('../pattern-wizards/request-multiple-odata-response/RequestMultipleODataResponseWizard').then((m) => ({ default: m.RequestMultipleODataResponseWizard })));
const RequestPrintWizard = lazy(() => import('../pattern-wizards/request-print/RequestPrintWizard').then((m) => ({ default: m.RequestPrintWizard })));
const WmsFactToOnecWizard = lazy(() => import('../pattern-wizards/wms-fact-to-onec/WmsFactToOnecWizard').then((m) => ({ default: m.WmsFactToOnecWizard })));
const XmlODataXmlResponseWizard = lazy(() => import('../pattern-wizards/xml-odata-xml-response/XmlODataXmlResponseWizard').then((m) => ({ default: m.XmlODataXmlResponseWizard })));
const XmlRawBridgeWizard = lazy(() => import('../pattern-wizards/xml-raw-bridge/XmlRawBridgeWizard').then((m) => ({ default: m.XmlRawBridgeWizard })));
const PollODataSendTargetWizard = lazy(() => import('../pattern-wizards/poll-odata-send-target/PollODataSendTargetWizard').then((m) => ({ default: m.PollODataSendTargetWizard })));

export function IntegrationMasterPage() {
  const [searchParams] = useSearchParams();
  const patternId = searchParams.get('pattern');
  const scenarios = useQuery({ queryKey: ['integration-master-scenarios'], queryFn: integrationMasterApi.scenarios });
  const pattern = useQuery({ queryKey: ['integration-pattern', patternId], queryFn: () => integrationPatternsApi.get(patternId || ''), enabled: Boolean(patternId) });
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
  const fieldsStepRef = useRef<HTMLDivElement | null>(null);
  const odataStepRef = useRef<HTMLDivElement | null>(null);
  const scrolledDraftId = useRef<string | null>(null);

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
      window.setTimeout(() => fieldsStepRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0);
    },
  });

  const validation = useMutation({ mutationFn: (contract: InputContract) => integrationMasterApi.validate(contract) });
  const saveDraft = useMutation({ mutationFn: (contract: InputContract) => integrationMasterApi.saveDraft(contract, parseResult), onSuccess: (data) => { setSavedDraft(data.draft); setSlug(data.draft.slug); setPreviousVariables({}); } });
  const contract = useMemo(() => buildContract({ name, slug, inputMode, sourceSystem, selected, sample: parseResult?.normalized_sample ?? sampleText, fields, operationKey, businessKey }), [name, slug, inputMode, sourceSystem, selected, parseResult, sampleText, fields, operationKey, businessKey]);
  const objectVariables = useMemo(() => ({ ...deriveVariablesFromDraft(savedDraft), ...previousVariables }), [savedDraft, previousVariables]);

  useEffect(() => {
    if (!savedDraft?.id || scrolledDraftId.current === savedDraft.id) return;
    scrolledDraftId.current = savedDraft.id;
    window.setTimeout(() => odataStepRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 80);
  }, [savedDraft?.id]);

  useEffect(() => {
    if (patternId === 'request_odata_response' || patternId === 'request_multiple_odata_response' || patternId === 'request_odata_send_endpoint' || patternId === 'request_odata_object_foreach_send_endpoint' || patternId === 'request_print' || patternId === 'source_web_api_writeback_onec' || patternId === 'wms_fact_to_onec' || patternId === 'xml_raw_bridge' || patternId === 'xml_odata_xml_response' || patternId === 'poll_odata_send_target') return;
    if (!pattern.data || selected || !scenarios.data?.length) return;
    const exampleSet = new Set(pattern.data.examples);
    const matched = scenarios.data.find((scenario) => exampleSet.has(scenario.key));
    if (matched) applyScenario(matched);
  }, [pattern.data, patternId, scenarios.data, selected]);

  if (patternId === 'request_odata_response') return <Suspense fallback={<LoadingState label="Загрузка мастера..." />}><RequestODataResponseWizard /></Suspense>;
  if (patternId === 'request_multiple_odata_response') return <Suspense fallback={<LoadingState label="Загрузка мастера..." />}><RequestMultipleODataResponseWizard /></Suspense>;
  if (patternId === 'request_odata_send_endpoint') return <Suspense fallback={<LoadingState label="Загрузка мастера..." />}><RequestODataSendEndpointWizard /></Suspense>;
  if (patternId === 'request_odata_object_foreach_send_endpoint') return <Suspense fallback={<LoadingState label="Загрузка мастера..." />}><DnpChzCodePoolWizard /></Suspense>;
  if (patternId === 'request_print') return <Suspense fallback={<LoadingState label="Загрузка мастера..." />}><RequestPrintWizard /></Suspense>;
  if (patternId === 'source_web_api_writeback_onec') return <Suspense fallback={<LoadingState label="Загрузка мастера..." />}><SourceWebApiWritebackOnecWizard /></Suspense>;
  if (patternId === 'wms_fact_to_onec') return <Suspense fallback={<LoadingState label="Загрузка мастера..." />}><WmsFactToOnecWizard /></Suspense>;
  if (patternId === 'xml_raw_bridge') return <Suspense fallback={<LoadingState label="Загрузка мастера..." />}><XmlRawBridgeWizard /></Suspense>;
  if (patternId === 'xml_odata_xml_response') return <Suspense fallback={<LoadingState label="Загрузка мастера..." />}><XmlODataXmlResponseWizard /></Suspense>;
  if (patternId === 'poll_odata_send_target') return <Suspense fallback={<LoadingState label="Загрузка мастера..." />}><PollODataSendTargetWizard /></Suspense>;
  if (scenarios.isPending) return <LoadingState label="Загрузка мастера интеграции" />;
  if (scenarios.error || pattern.error) return <ErrorState error={scenarios.error ?? pattern.error} />;

  function applyScenario(scenario: IntegrationScenario) {
    const mode = scenario.default_input_mode;
    setSelected(scenario);
    setInputMode(mode);
    setName(scenario.title);
    setSlug(suggestedSlug(scenario.default_slug));
    setSourceSystem(scenario.source_system);
    setSampleText(sampleToText(scenario.sample, mode));
    setParseResult(null);
    setFields([]);
    setSavedDraft(null);
    setPreviousVariables({});
    scrolledDraftId.current = null;
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
    scrolledDraftId.current = null;
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

      {pattern.data && <PatternIntentPanel pattern={pattern.data} />}

      {!selected ? (
        <MasterStepLayout index="01" title="Выберите сценарий" description="Карточки описывают реальные интеграции человеческим языком: кто вызывает OMH, что приходит и что обычно будет дальше.">
          <ScenarioChooser scenarios={scenarios.data ?? []} selectedKey={undefined} onSelect={applyScenario} />
        </MasterStepLayout>
      ) : (
        <>
          <SelectedScenarioPanel scenario={selected} onBack={() => setSelected(null)} />

          <MasterStepLayout index="02" title="Что придёт во входящем запросе" description="Выберите JSON, XML или raw text и вставьте реальный sample. OMH разберёт поля, пути и типы.">
            <InputTypeSelector value={inputMode} allowed={selected.input_modes} onChange={changeInputMode} />
            <div className="metadata-grid compact-grid no-margin">
              <label className="field-label">Название контракта<input value={name} onChange={(event) => setName(event.target.value)} /></label>
              <label className="field-label">Source system<select value={sourceSystem} onChange={(event) => setSourceSystem(event.target.value)}><option value="external_api">External API / Website</option><option value="dnp">DnP</option><option value="onec">1C</option><option value="wms">WMS</option><option value="printer">Printer</option><option value="other">Other</option></select></label>
            </div>
            <EndpointSlugEditor value={slug} onChange={setSlug} />
            <SampleInputEditor inputMode={inputMode} value={sampleText} error={parseError} onChange={setSampleText} onParse={() => parse.mutate()} parsing={parse.isPending} />
          </MasterStepLayout>

          <div ref={fieldsStepRef}>
            <MasterStepLayout index="03" title="Проверьте Input Contract Table" description="Поля из sample считаются required по умолчанию. Здесь можно сделать поле optional и добавить описание для следующих шагов мастера.">
              <ParsedFieldsTable fields={fields} operationPath={operationKey.field_path} businessPath={businessKey.path} onChange={setFields} onUseOperation={useOperationField} onUseBusiness={useBusinessField} />
            </MasterStepLayout>
          </div>

          <MasterStepLayout index="04" title="Как OMH поймёт, что это этот сценарий" description="Выберите route key. Например, входящий JSON может нести поле sinc или operation с кодовой фразой сценария.">
            <OperationKeySelector value={operationKey} suggestions={parseResult?.suggested_operation_keys ?? []} fields={fields} onChange={(value) => setOperationKey(withMatcher(value))} />
          </MasterStepLayout>

          <MasterStepLayout index="05" title="Что считать номером события" description="Business key попадёт в журнал событий и Timeline. Выбирайте поле, по которому оператор потом найдёт конкретный запрос.">
            <BusinessKeySelector value={businessKey} suggestions={parseResult?.suggested_business_keys ?? []} fields={fields} onChange={setBusinessKey} />
          </MasterStepLayout>

          <InputContractPreview contract={contract} validation={validation.data ?? null} saved={savedResponse} error={saveError} onValidate={validateContract} onSave={saveContractDraft} validating={validation.isPending} saving={saveDraft.isPending} />

          {savedDraft ? <div ref={odataStepRef}><ODataStepBuilder contract={savedDraft.contract} draft={savedDraft} onDraftUpdated={setSavedDraft} onVariablesUpdated={(variables) => setPreviousVariables((current) => ({ ...current, ...variables }))} /></div> : null}

          {savedDraft && hasSavedODataQuery ? <ODataObjectStepBuilder contract={savedDraft.contract} draft={savedDraft} previousVariables={objectVariables} onDraftUpdated={setSavedDraft} onVariablesUpdated={(variables) => setPreviousVariables((current) => ({ ...current, ...variables }))} /> : null}

          {savedDraft && hasSavedObjectStep ? <ForeachODataStepBuilder contract={savedDraft.contract} draft={savedDraft} previousVariables={objectVariables} onDraftUpdated={setSavedDraft} onVariablesUpdated={(variables) => setPreviousVariables((current) => ({ ...current, ...variables }))} /> : null}

          {savedDraft && hasSavedForeachStep ? <PayloadBuilder contract={savedDraft.contract} draft={savedDraft} previousVariables={objectVariables} onDraftUpdated={setSavedDraft} onVariablesUpdated={(variables) => setPreviousVariables((current) => ({ ...current, ...variables }))} /> : null}

          {savedDraft && hasSavedPayloadStep ? <FinalActionBuilder contract={savedDraft.contract} draft={savedDraft} previousVariables={objectVariables} onDraftUpdated={setSavedDraft} /> : null}

          {savedDraft?.final_action ? <CompileIntegrationStep draft={savedDraft} /> : null}
        </>
      )}
    </div>
  );
}

function PatternIntentPanel({ pattern }: { pattern: IntegrationPattern }) {
  return (
    <section className="wizard-step pattern-intent-panel">
      <div className="panel-toolbar">
        <div>
          <span className="eyebrow">Pattern выбран Scenario Router</span>
          <h2>{localized(pattern.title)}</h2>
          <p>{localized(pattern.description)}</p>
        </div>
        <StatusBadge status={pattern.status} label={pattern.status === 'available' ? 'доступен' : 'скоро'} />
      </div>
      <div className="pattern-flow compact">
        {pattern.initial_steps.map((step) => <span key={step}>{step}</span>)}
      </div>
      <div className="metadata-grid compact-grid no-margin">
        <span>Примеры<strong>{pattern.examples.length ? pattern.examples.join(', ') : '—'}</strong></span>
        <span>Документация<strong><Link className="primary-link" to={pattern.docs_link}>Открыть</Link></strong><small>{pattern.docs_link}</small></span>
        <span>Что тестировать<strong>{pattern.test_plan.map((item) => localized(item)).join(' · ') || 'см. steps'}</strong></span>
      </div>
    </section>
  );
}

function SelectedScenarioPanel({ scenario, onBack }: { scenario: IntegrationScenario; onBack: () => void }) {
  return (
    <section className="wizard-step integration-master-step selected-scenario-panel">
      <div className="panel-toolbar">
        <div>
          <span className="eyebrow">Выбран сценарий</span>
          <h2>{scenario.title}</h2>
          <p>{scenario.description}</p>
        </div>
        <button type="button" className="ghost-button" onClick={onBack}>Вернуться к сценариям</button>
      </div>
      <dl className="scenario-card-meta selected-scenario-meta">
        <div><dt>Кто вызывает OMH</dt><dd>{scenario.caller}</dd></div>
        <div><dt>Что приходит</dt><dd>{scenario.incoming}</dd></div>
        <div className="wide"><dt>Что делает OMH дальше</dt><dd>{scenario.next_action}</dd></div>
      </dl>
    </section>
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
