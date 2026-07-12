import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { ErrorState } from '../../../components/ErrorState';
import { integrationMasterApi } from '../../integration-master/api';
import { slugError, slugify } from '../../integration-master/EndpointSlugEditor';
import type { BusinessKeySuggestion, InputBusinessKey, InputContract, InputContractField, InputMode, InputOperationKey, InputParseResponse, ODataStepConfig, OperationKeySuggestion, PayloadBodyType } from '../../integration-master/types';
import { PatternIntroPanel } from '../shared/PatternIntroPanel';
import { PatternWizardShell } from '../shared/PatternWizardShell';
import { requestODataResponseApi } from './api';
import { ODataLookupStep } from './ODataLookupStep';
import { PreviewStep } from './PreviewStep';
import { RequestStep } from './RequestStep';
import { defaultBody, defaultHeaders } from './ResponseStep';
import { ResponseStep } from './ResponseStep';
import { SaveStep } from './SaveStep';
import type { RequestODataResponsePatternRequest, RequestODataResponseResponseConfig } from './types';

const DEFAULT_SAMPLE = `{
  "operation": "lookup_contractor",
  "inn": "7707083893"
}`;

export function RequestODataResponseWizard() {
  const autoParsed = useRef(false);
  const [name, setName] = useState('Внешний сервис спрашивает контрагента по ИНН');
  const [slug, setSlug] = useState('lookup-contractor');
  const [sourceSystem, setSourceSystem] = useState('external_api');
  const [inputMode, setInputMode] = useState<InputMode>('json');
  const [sampleText, setSampleText] = useState(DEFAULT_SAMPLE);
  const [parseResult, setParseResult] = useState<InputParseResponse | null>(null);
  const [fields, setFields] = useState<InputContractField[]>([]);
  const [operationKey, setOperationKey] = useState<InputOperationKey>({ type: 'field', field_path: 'request.body.operation', value: 'lookup_contractor', fallback_paths: [], matcher_preview: matcherPreview('request.body.operation', 'lookup_contractor', []) });
  const [businessKey, setBusinessKey] = useState<InputBusinessKey>({ path: 'request.body.inn', fallback_paths: [] });
  const [odataStep, setODataStep] = useState<ODataStepConfig>(() => defaultODataStep());
  const [response, setResponse] = useState<RequestODataResponseResponseConfig>(() => ({ type: 'json', status_code: 200, body: defaultBody('json'), headers: defaultHeaders('json') }));
  const [previewSignature, setPreviewSignature] = useState<string | null>(null);

  const parse = useMutation({
    mutationFn: () => integrationMasterApi.parse({ input_mode: inputMode, scenario_key: 'external_contractor_lookup', sample: sampleText }),
    onSuccess: (data) => {
      setParseResult(data);
      setFields(data.fields);
      setOperationKey(operationFromSuggestion(data.suggested_operation_keys[0]));
      setBusinessKey(businessFromSuggestion(data.suggested_business_keys[0]));
    },
  });

  const contract = useMemo(() => buildContract({ name, slug, inputMode, sourceSystem, sample: parseResult?.normalized_sample ?? sampleText, fields, operationKey, businessKey }), [name, slug, inputMode, sourceSystem, parseResult, sampleText, fields, operationKey, businessKey]);
  const patternRequest = useMemo<RequestODataResponsePatternRequest>(() => ({ name: contract.name, slug: contract.slug, input_contract: contract, odata_step: odataStep, response }), [contract, odataStep, response]);
  const requestSignature = useMemo(() => JSON.stringify(patternRequest), [patternRequest]);

  const preview = useMutation({
    mutationFn: () => requestODataResponseApi.preview(patternRequest),
    onSuccess: () => setPreviewSignature(requestSignature),
  });
  const create = useMutation({ mutationFn: () => requestODataResponseApi.create(patternRequest) });

  useEffect(() => {
    if (autoParsed.current) return;
    autoParsed.current = true;
    parse.mutate();
  }, []);

  function invalidatePreview() {
    setPreviewSignature(null);
    preview.reset();
    create.reset();
  }

  function changeInputMode(mode: InputMode) {
    setInputMode(mode);
    setSampleText(defaultSample(mode));
    setFields([]);
    setParseResult(null);
    setOperationKey({ type: mode === 'json' ? 'field' : 'endpoint', field_path: mode === 'json' ? 'request.body.operation' : null, value: mode === 'json' ? 'lookup_contractor' : null, fallback_paths: [], matcher_preview: mode === 'json' ? matcherPreview('request.body.operation', 'lookup_contractor', []) : matcherPreview(null, null, [], 'endpoint') });
    setBusinessKey({ path: mode === 'json' ? 'request.body.inn' : null, fallback_paths: [] });
    invalidatePreview();
  }

  function useOperationField(field: InputContractField) {
    setOperationKey(withMatcher({ type: 'field', field_path: field.path, value: field.example ?? '', fallback_paths: [], matcher_preview: {} }));
    invalidatePreview();
  }

  function useBusinessField(field: InputContractField) {
    setBusinessKey({ path: field.path, fallback_paths: [] });
    invalidatePreview();
  }

  function patchODataStep(patch: Partial<ODataStepConfig>) {
    setODataStep((current) => ({ ...current, ...patch }));
    invalidatePreview();
  }

  function changeResponse(next: RequestODataResponseResponseConfig) {
    setResponse(next);
    invalidatePreview();
  }

  const parseError = parse.error instanceof Error ? parse.error.message : null;
  const previewError = preview.error instanceof Error ? preview.error.message : null;
  const createError = create.error instanceof Error ? create.error.message : null;
  const canPreview = fields.length > 0 && !slugError(contract.slug);
  const currentPreviewValid = Boolean(preview.data?.valid && previewSignature === requestSignature);

  if (create.error && !(create.error instanceof Error)) return <ErrorState error={create.error} />;

  return (
    <PatternWizardShell
      className="request-odata-response-wizard"
      patternId="request_odata_response"
      steps={[
        { id: 'request', label: 'Request' },
        { id: 'odata', label: '1C OData' },
        { id: 'response', label: 'Response' },
        { id: 'preview', label: 'Preview' },
        { id: 'save', label: 'Save' },
      ]}
    >
      <PatternIntroPanel
        title="Внешний сервис → OMH → 1С OData → ответ"
        description="Настройте endpoint, по которому внешний сервис будет спрашивать данные. OMH выполнит OData-запрос в 1С и вернёт JSON, XML или текстовый ответ."
        links={[
          { label: 'Scenario Router', to: '/integration-start' },
          { label: 'Рецепт', to: '/docs/onec/recipes/external-service-lookup-contractor' },
          { label: 'Установить учебный стенд', to: '/training' },
        ]}
        diagram={(
          <div className="pattern-route-diagram" aria-label="External API to OMH to 1C OData response flow">
            <span>External API</span>
            <small>HTTP request</small>
            <span>OMH endpoint</span>
            <small>OData query</small>
            <span>1C OData</span>
            <small>result</small>
            <span>OMH response builder</span>
            <small>JSON/XML/raw response</small>
            <span>External API</span>
          </div>
        )}
      />

      <RequestStep
        name={name}
        slug={slug}
        sourceSystem={sourceSystem}
        inputMode={inputMode}
        sampleText={sampleText}
        fields={fields}
        parseResult={parseResult}
        operationKey={operationKey}
        businessKey={businessKey}
        parseError={parseError}
        parsing={parse.isPending}
        onNameChange={(value) => { setName(value); invalidatePreview(); }}
        onSlugChange={(value) => { setSlug(value); invalidatePreview(); }}
        onSourceSystemChange={(value) => { setSourceSystem(value); invalidatePreview(); }}
        onInputModeChange={changeInputMode}
        onSampleTextChange={(value) => { setSampleText(value); invalidatePreview(); }}
        onFieldsChange={(value) => { setFields(value); invalidatePreview(); }}
        onOperationKeyChange={(value) => { setOperationKey(withMatcher(value)); invalidatePreview(); }}
        onBusinessKeyChange={(value) => { setBusinessKey(value); invalidatePreview(); }}
        onUseOperation={useOperationField}
        onUseBusiness={useBusinessField}
        onParse={() => parse.mutate()}
      />

      <ODataLookupStep contract={contract} step={odataStep} onChange={patchODataStep} />
      <ResponseStep response={response} saveAs={odataStep.save_as} selectFields={odataStep.select} onChange={changeResponse} />
      <PreviewStep preview={preview.data} error={previewError} loading={preview.isPending} disabled={!canPreview} onPreview={() => preview.mutate()} />
      <SaveStep result={create.data} error={createError} loading={create.isPending} disabled={!currentPreviewValid} onCreate={() => create.mutate()} />
    </PatternWizardShell>
  );
}

interface BuildContractInput {
  name: string;
  slug: string;
  inputMode: InputMode;
  sourceSystem: string;
  sample: unknown;
  fields: InputContractField[];
  operationKey: InputOperationKey;
  businessKey: InputBusinessKey;
}

function buildContract({ name, slug, inputMode, sourceSystem, sample, fields, operationKey, businessKey }: BuildContractInput): InputContract {
  const normalizedSlug = slugify(slug || 'lookup-contractor') || 'lookup-contractor';
  return {
    name: name || 'Внешний сервис спрашивает данные из 1С',
    slug: normalizedSlug,
    input_mode: inputMode,
    source_system: sourceSystem,
    scenario_key: 'external_contractor_lookup',
    sample,
    fields,
    operation_key: withMatcher(operationKey),
    business_key: businessKey,
    endpoint_url: `/api/bus/in/${normalizedSlug}`,
  };
}

function defaultODataStep(): ODataStepConfig {
  return {
    type: 'odata_query',
    connection_id: null,
    connection_name: null,
    resource: 'Catalog_Контрагенты',
    filter_mode: 'builder',
    filter_rule: { field: 'ИНН', operator: 'eq', value_type: 'variable', value: 'request.body.inn' },
    filter: null,
    select: ['Ref_Key', 'Description', 'ИНН', 'КПП'],
    top: 1,
    orderby: null,
    paginate: false,
    save_as: 'contractor',
    required: true,
  };
}

function defaultSample(mode: InputMode) {
  if (mode === 'xml') return '<Request>\n  <Operation>lookup_contractor</Operation>\n  <INN>7707083893</INN>\n</Request>';
  if (mode === 'raw_text') return 'operation=lookup_contractor;inn=7707083893';
  return DEFAULT_SAMPLE;
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
