import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { ErrorState } from '../../../components/ErrorState';
import { integrationMasterApi } from '../../integration-master/api';
import { slugError, slugify } from '../../integration-master/EndpointSlugEditor';
import type { BusinessKeySuggestion, InputBusinessKey, InputContract, InputContractField, InputMode, InputOperationKey, InputParseResponse, ODataStepConfig, OperationKeySuggestion } from '../../integration-master/types';
import { ODataStep } from './ODataStep';
import { PreviewStep } from './PreviewStep';
import { defaultHeaders, defaultTemplate, ResponseBuilderStep } from './ResponseBuilderStep';
import { SaveStep } from './SaveStep';
import { XmlExtractStep } from './XmlExtractStep';
import { XmlInputStep } from './XmlInputStep';
import { xmlODataXmlResponseApi } from './api';
import type { XmlODataXmlExtractConfig, XmlODataXmlResponseConfig, XmlODataXmlResponsePatternRequest } from './types';

const DEFAULT_XML = `<Request>
  <Operation>lookup_order</Operation>
  <Number>260666/6938</Number>
  <Format>xml</Format>
</Request>`;

export function XmlODataXmlResponseWizard() {
  const autoParsed = useRef(false);
  const [name, setName] = useState('XML lookup order');
  const [slug, setSlug] = useState('lookup-order-xml');
  const [sourceSystem, setSourceSystem] = useState('external_api');
  const [inputMode, setInputMode] = useState<InputMode>('xml');
  const [sampleText, setSampleText] = useState(DEFAULT_XML);
  const [parseResult, setParseResult] = useState<InputParseResponse | null>(null);
  const [fields, setFields] = useState<InputContractField[]>([]);
  const [operationKey, setOperationKey] = useState<InputOperationKey>(() => withMatcher({ type: 'field', field_path: 'xml./Request/Operation', value: 'lookup_order', fallback_paths: [], matcher_preview: {} }));
  const [businessKey, setBusinessKey] = useState<InputBusinessKey>({ path: 'xml./Request/Number', fallback_paths: [] });
  const [xmlExtract, setXmlExtract] = useState<XmlODataXmlExtractConfig>(() => defaultExtract());
  const [odataStep, setODataStep] = useState<ODataStepConfig>(() => defaultODataStep());
  const [response, setResponse] = useState<XmlODataXmlResponseConfig>(() => ({ body_type: 'xml', status_code: 200, template: defaultTemplate('xml', 'order'), headers: defaultHeaders('xml') }));
  const [previewSignature, setPreviewSignature] = useState<string | null>(null);

  const parse = useMutation({
    mutationFn: () => integrationMasterApi.parse({ input_mode: inputMode, scenario_key: 'xml_input_odata_xml_response', sample: sampleText }),
    onSuccess: (data) => {
      setParseResult(data);
      setFields(data.fields);
      setOperationKey(operationFromSuggestion(data.suggested_operation_keys.find((item) => item.field_path === 'xml./Request/Operation') ?? data.suggested_operation_keys[0]));
      setBusinessKey(businessFromSuggestion(data.suggested_business_keys.find((item) => item.path === 'xml./Request/Number') ?? data.suggested_business_keys[0]));
      setXmlExtract(extractFromFields(data.fields));
    },
  });

  const contract = useMemo(() => buildContract({ name, slug, inputMode, sourceSystem, sample: parseResult?.normalized_sample ?? sampleText, fields, operationKey, businessKey }), [name, slug, inputMode, sourceSystem, parseResult, sampleText, fields, operationKey, businessKey]);
  const patternRequest = useMemo<XmlODataXmlResponsePatternRequest>(() => ({ name: contract.name, slug: contract.slug, input_contract: contract, xml_extract: xmlExtract, odata_step: odataStep, response }), [contract, xmlExtract, odataStep, response]);
  const requestSignature = useMemo(() => JSON.stringify(patternRequest), [patternRequest]);

  const preview = useMutation({ mutationFn: () => xmlODataXmlResponseApi.preview(patternRequest), onSuccess: () => setPreviewSignature(requestSignature) });
  const create = useMutation({ mutationFn: () => xmlODataXmlResponseApi.create(patternRequest) });

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
    setSampleText(DEFAULT_XML);
    setFields([]);
    setParseResult(null);
    setOperationKey(withMatcher({ type: 'field', field_path: 'xml./Request/Operation', value: 'lookup_order', fallback_paths: [], matcher_preview: {} }));
    setBusinessKey({ path: 'xml./Request/Number', fallback_paths: [] });
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

  const parseError = parse.error instanceof Error ? parse.error.message : null;
  const previewError = preview.error instanceof Error ? preview.error.message : null;
  const createError = create.error instanceof Error ? create.error.message : null;
  const canPreview = fields.length > 0 && xmlExtract.fields.length > 0 && !slugError(contract.slug);
  const currentPreviewValid = Boolean(preview.data?.valid && previewSignature === requestSignature);

  if (create.error && !(create.error instanceof Error)) return <ErrorState error={create.error} />;

  return (
    <div className="page-stack integration-master-page xml-odata-response-wizard">
      <section className="hero-panel integration-master-hero pattern-wizard-hero">
        <div>
          <span className="eyebrow">Pattern Wizard</span>
          <h1>XML → 1С OData → ответ</h1>
          <p>Настройте endpoint, который принимает XML, извлекает поля, делает один OData-запрос в 1С и возвращает XML, JSON или текст.</p>
          <div className="hero-meta">
            <Link className="primary-link" to="/integration-start">Scenario Router</Link>
            <Link className="primary-link" to="/docs/onec/recipes/xml-input-odata-xml-response">Рецепт</Link>
            <Link className="primary-link" to="/training?exampleId=training.onec.xml_lookup_order_response">Training Sandbox</Link>
          </div>
        </div>
        <div className="pattern-route-diagram" aria-label="XML to OData response flow">
          <span>External system / 1C</span>
          <small>HTTP XML</small>
          <span>OMH endpoint</span>
          <small>XML extract</small>
          <span>1C OData</span>
          <small>result</small>
          <span>Response builder</span>
          <small>XML / JSON / raw</small>
          <span>Caller</span>
        </div>
      </section>

      <XmlInputStep
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
      <XmlExtractStep extract={xmlExtract} onChange={(value) => { setXmlExtract(value); invalidatePreview(); }} />
      <ODataStep step={odataStep} extractFields={xmlExtract.fields} onChange={patchODataStep} />
      <ResponseBuilderStep response={response} saveAs={odataStep.save_as} selectFields={odataStep.select} onChange={(value) => { setResponse(value); invalidatePreview(); }} />
      <PreviewStep preview={preview.data} error={previewError} loading={preview.isPending} disabled={!canPreview} onPreview={() => preview.mutate()} />
      <SaveStep result={create.data} error={createError} loading={create.isPending} disabled={!currentPreviewValid} onCreate={() => create.mutate()} />
    </div>
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
  const normalizedSlug = slugify(slug || 'lookup-order-xml') || 'lookup-order-xml';
  return {
    name: name || 'XML lookup order',
    slug: normalizedSlug,
    input_mode: inputMode,
    source_system: sourceSystem,
    scenario_key: 'xml_input_odata_xml_response',
    sample,
    fields,
    operation_key: withMatcher(operationKey),
    business_key: businessKey,
    endpoint_url: `/api/bus/in/${normalizedSlug}`,
  };
}

function defaultExtract(): XmlODataXmlExtractConfig {
  return { fields: [
    { name: 'operation', path: '/Request/Operation', required: true, mode: 'first', example: 'lookup_order' },
    { name: 'order_number', path: '/Request/Number', required: true, mode: 'first', example: '260666/6938' },
    { name: 'format', path: '/Request/Format', required: false, mode: 'first', example: 'xml' },
  ] };
}

function defaultODataStep(): ODataStepConfig {
  return {
    type: 'odata_query',
    connection_id: null,
    connection_name: null,
    resource: 'Document_ЗаказКлиента',
    filter_mode: 'raw',
    filter_rule: { field: 'Number', operator: 'eq', value_type: 'variable', value: 'order_number' },
    filter: "Number eq '{{order_number}}'",
    select: ['Ref_Key', 'Number', 'Date', 'Posted'],
    top: 1,
    orderby: null,
    paginate: false,
    save_as: 'order',
    required: true,
  };
}

function extractFromFields(fields: InputContractField[]): XmlODataXmlExtractConfig {
  const byPath = new Map(fields.map((field) => [field.path.replace(/^xml\./, ''), field]));
  const defaults = defaultExtract().fields;
  return { fields: defaults.map((field) => {
    const parsedField = byPath.get(field.path);
    return parsedField ? { ...field, example: parsedField.example } : field;
  }) };
}

function operationFromSuggestion(suggestion?: OperationKeySuggestion): InputOperationKey {
  return withMatcher({ type: suggestion?.type ?? 'field', field_path: suggestion?.field_path ?? 'xml./Request/Operation', value: suggestion?.value ?? 'lookup_order', fallback_paths: suggestion?.fallback_paths ?? [], matcher_preview: suggestion?.matcher_json ?? {} });
}

function businessFromSuggestion(suggestion?: BusinessKeySuggestion): InputBusinessKey {
  return { path: suggestion?.path ?? 'xml./Request/Number', fallback_paths: suggestion?.fallback_paths?.length ? suggestion.fallback_paths : [] };
}

function withMatcher(key: InputOperationKey): InputOperationKey {
  return { ...key, matcher_preview: matcherPreview(key.field_path ?? null, key.value, key.fallback_paths, key.type) };
}

function matcherPreview(path: string | null, value: unknown, fallbacks: string[] = [], type: InputOperationKey['type'] = 'field') {
  if (type === 'endpoint' || type === 'none' || !path) return { mode: type, rules: [] };
  const rules = [path, ...fallbacks].filter(Boolean).map((candidate) => ({ type: 'xml_path_equals', path: toXmlMatcherPath(candidate), value }));
  return { mode: 'any', rules };
}

function toXmlMatcherPath(path: string) {
  const clean = path.replace(/^xml\./, '');
  if (clean.startsWith('/')) return clean.split('/').filter(Boolean).join('.');
  return clean.replace(/\//g, '.');
}
