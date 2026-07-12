import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { ErrorState } from '../../../components/ErrorState';
import { integrationMasterApi } from '../../integration-master/api';
import { slugError, slugify } from '../../integration-master/EndpointSlugEditor';
import type { BusinessKeySuggestion, InputBusinessKey, InputContract, InputContractField, InputMode, InputOperationKey, InputParseResponse, ODataObjectStepConfig, ODataStepConfig, OperationKeySuggestion } from '../../integration-master/types';
import { requestMultipleODataResponseApi } from './api';
import { FindOrderStep } from './FindOrderStep';
import { InputStep } from './InputStep';
import { PreviewStep } from './PreviewStep';
import { ReadItemsStep } from './ReadItemsStep';
import { defaultHeaders, defaultTemplate, ResponseBuilderStep } from './ResponseBuilderStep';
import { SaveStep } from './SaveStep';
import type { RequestMultipleODataResponsePatternRequest, RequestMultipleODataResponseResponseConfig } from './types';

const DEFAULT_SAMPLE = `{
  "operation": "lookup_order_products",
  "number": "260666/6938",
  "format": "xml"
}`;

export function RequestMultipleODataResponseWizard() {
  const autoParsed = useRef(false);
  const [name, setName] = useState('Внешний сервис спрашивает заказ из 1С');
  const [slug, setSlug] = useState('lookup-order-products');
  const [sourceSystem, setSourceSystem] = useState('external_api');
  const [inputMode, setInputMode] = useState<InputMode>('json');
  const [sampleText, setSampleText] = useState(DEFAULT_SAMPLE);
  const [parseResult, setParseResult] = useState<InputParseResponse | null>(null);
  const [fields, setFields] = useState<InputContractField[]>([]);
  const [operationKey, setOperationKey] = useState<InputOperationKey>(() => defaultOperationKey());
  const [businessKey, setBusinessKey] = useState<InputBusinessKey>(() => defaultBusinessKey());
  const [findOrder, setFindOrder] = useState<ODataStepConfig>(() => defaultFindOrderStep());
  const [readItems, setReadItems] = useState<ODataObjectStepConfig>(() => defaultReadItemsStep());
  const [response, setResponse] = useState<RequestMultipleODataResponseResponseConfig>(() => ({ type: 'xml', status_code: 200, template: defaultTemplate('xml'), headers: defaultHeaders('xml') }));
  const [previewSignature, setPreviewSignature] = useState<string | null>(null);

  const parse = useMutation({
    mutationFn: () => integrationMasterApi.parse({ input_mode: inputMode, scenario_key: 'external_order_lookup_xml_response', sample: sampleText }),
    onSuccess: (data) => {
      setParseResult(data);
      setFields(data.fields);
      setOperationKey(operationFromSuggestion(data.suggested_operation_keys[0]));
      setBusinessKey(businessFromSuggestion(data.suggested_business_keys[0]));
    },
  });

  const contract = useMemo(() => buildContract({ name, slug, inputMode, sourceSystem, sample: parseResult?.normalized_sample ?? sampleText, fields, operationKey, businessKey }), [name, slug, inputMode, sourceSystem, parseResult, sampleText, fields, operationKey, businessKey]);
  const patternRequest = useMemo<RequestMultipleODataResponsePatternRequest>(() => ({ name: contract.name, slug: contract.slug, input_contract: contract, find_order: findOrder, read_items: readItems, response }), [contract, findOrder, readItems, response]);
  const requestSignature = useMemo(() => JSON.stringify(patternRequest), [patternRequest]);

  const preview = useMutation({
    mutationFn: () => requestMultipleODataResponseApi.preview(patternRequest),
    onSuccess: () => setPreviewSignature(requestSignature),
  });
  const create = useMutation({ mutationFn: () => requestMultipleODataResponseApi.create(patternRequest) });

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
    setOperationKey(mode === 'json' ? defaultOperationKey() : { type: 'endpoint', field_path: null, value: null, fallback_paths: [], matcher_preview: { mode: 'endpoint', rules: [] } });
    setBusinessKey(mode === 'json' ? defaultBusinessKey() : { path: null, fallback_paths: [] });
    invalidatePreview();
  }

  function useOperationField(field: InputContractField) {
    setOperationKey(withMatcher({ type: 'field', field_path: field.path, value: field.example ?? 'lookup_order_products', fallback_paths: [], matcher_preview: {} }));
    invalidatePreview();
  }

  function useBusinessField(field: InputContractField) {
    setBusinessKey({ path: field.path, fallback_paths: [] });
    invalidatePreview();
  }

  function patchFindOrder(patch: Partial<ODataStepConfig>) {
    setFindOrder((current) => {
      const next = { ...current, ...patch };
      if ('connection_id' in patch || 'connection_name' in patch) {
        setReadItems((itemsStep) => ({ ...itemsStep, connection_id: next.connection_id ?? null, connection_name: next.connection_name ?? null }));
      }
      return next;
    });
    invalidatePreview();
  }

  function patchReadItems(patch: Partial<ODataObjectStepConfig>) {
    setReadItems((current) => ({ ...current, ...patch }));
    invalidatePreview();
  }

  function changeResponse(next: RequestMultipleODataResponseResponseConfig) {
    setResponse(next);
    invalidatePreview();
  }

  const parseError = parse.error instanceof Error ? parse.error.message : null;
  const previewError = preview.error instanceof Error ? preview.error.message : null;
  const createError = create.error instanceof Error ? create.error.message : null;
  const canPreview = fields.length > 0 && !slugError(contract.slug);
  const currentPreviewValid = Boolean(preview.data?.valid && previewSignature === requestSignature);
  const orderPreview = preview.data?.order_result ?? { Ref_Key: '66666666-6666-6666-6666-666666666666', Number: '260666/6938' };

  if (create.error && !(create.error instanceof Error)) return <ErrorState error={create.error} />;

  return (
    <div className="page-stack integration-master-page request-multiple-odata-response-wizard">
      <section className="hero-panel integration-master-hero pattern-wizard-hero">
        <div>
          <span className="eyebrow">Pattern Wizard</span>
          <h1>Запрос → несколько OData → ответ</h1>
          <p>Внешний сервис вызывает OMH, OMH находит заказ в 1С OData, читает табличную часть Товары и возвращает XML/JSON/raw ответ caller-у.</p>
          <div className="hero-meta">
            <Link className="primary-link" to="/integration-start">Scenario Router</Link>
            <Link className="primary-link" to="/docs/onec/recipes/request-odata-xml-response">Рецепт</Link>
            <Link className="primary-link" to="/training?exampleId=training.onec.lookup_order_products_xml">Training example</Link>
          </div>
        </div>
        <div className="pattern-route-diagram" aria-label="External API to 1C OData order rows to XML response flow">
          <span>External API</span>
          <small>JSON/XML: number</small>
          <span>OMH endpoint</span>
          <small>lookup_order_products</small>
          <span>OData order</span>
          <small>Document_ЗаказКлиента</small>
          <span>OData rows</span>
          <small>Товары</small>
          <span>Response builder</span>
          <small>XML loop over items</small>
          <span>Caller</span>
        </div>
      </section>

      <InputStep
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

      <FindOrderStep contract={contract} step={findOrder} onChange={patchFindOrder} />
      <ReadItemsStep step={readItems} orderPreview={orderPreview} onChange={patchReadItems} />
      <ResponseBuilderStep response={response} orderSaveAs={findOrder.save_as} itemsSaveAs={readItems.save_as} onChange={changeResponse} />
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
  const normalizedSlug = slugify(slug || 'lookup-order-products') || 'lookup-order-products';
  return {
    name: name || 'Внешний сервис спрашивает заказ из 1С',
    slug: normalizedSlug,
    input_mode: inputMode,
    source_system: sourceSystem,
    scenario_key: 'external_order_lookup_xml_response',
    sample,
    fields,
    operation_key: withMatcher(operationKey),
    business_key: businessKey,
    endpoint_url: `/api/bus/in/${normalizedSlug}`,
  };
}

function defaultFindOrderStep(): ODataStepConfig {
  return {
    type: 'odata_query',
    connection_id: null,
    connection_name: null,
    resource: 'Document_ЗаказКлиента',
    filter_mode: 'raw',
    filter_rule: { field: 'Number', operator: 'eq', value_type: 'variable', value: 'request.body.number' },
    filter: "Number eq '{{request.body.number}}'",
    select: ['Ref_Key', 'Number', 'Date', 'Posted'],
    top: 1,
    orderby: null,
    paginate: false,
    save_as: 'order',
    required: true,
  };
}

function defaultReadItemsStep(): ODataObjectStepConfig {
  return {
    type: 'odata_object_query',
    connection_id: null,
    connection_name: null,
    object_variable: 'order',
    key_field: 'Ref_Key',
    key_type: 'guid',
    base_resource: 'Document_ЗаказКлиента',
    nested_resource: 'Товары',
    resource_template: "Document_ЗаказКлиента(guid'{{order.Ref_Key}}')/Товары",
    filter: null,
    select: ['Номенклатура_Key', 'Количество', 'Цена', 'Сумма'],
    top: 100,
    paginate: false,
    save_as: 'items',
    required: true,
    overwrite: true,
  };
}

function defaultSample(mode: InputMode) {
  if (mode === 'xml') return '<Request>\n  <Operation>lookup_order_products</Operation>\n  <Number>260666/6938</Number>\n  <Format>xml</Format>\n</Request>';
  return DEFAULT_SAMPLE;
}

function defaultOperationKey(): InputOperationKey {
  return withMatcher({ type: 'field', field_path: 'request.body.operation', value: 'lookup_order_products', fallback_paths: [], matcher_preview: {} });
}

function defaultBusinessKey(): InputBusinessKey {
  return { path: 'request.body.number', fallback_paths: [] };
}

function operationFromSuggestion(suggestion?: OperationKeySuggestion): InputOperationKey {
  if (!suggestion) return defaultOperationKey();
  return withMatcher({ type: suggestion.type, field_path: suggestion.field_path ?? 'request.body.operation', value: suggestion.value ?? 'lookup_order_products', fallback_paths: suggestion.fallback_paths, matcher_preview: suggestion.matcher_json });
}

function businessFromSuggestion(suggestion?: BusinessKeySuggestion): InputBusinessKey {
  if (suggestion?.path === 'request.body.number') return { path: suggestion.path, fallback_paths: suggestion.fallback_paths };
  return defaultBusinessKey();
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
