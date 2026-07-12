import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { ErrorState } from '../../../components/ErrorState';
import { integrationMasterApi } from '../../integration-master/api';
import { slugError, slugify } from '../../integration-master/EndpointSlugEditor';
import type { BusinessKeySuggestion, FinalActionBodyType, ForeachODataStepConfig, InputBusinessKey, InputContract, InputContractField, InputMode, InputOperationKey, InputParseResponse, ODataObjectStepConfig, ODataStepConfig, PayloadStepConfig } from '../../integration-master/types';
import { BuildPayloadStep } from './BuildPayloadStep';
import { FindCodesStep } from './FindCodesStep';
import { FindOrderStep } from './FindOrderStep';
import { InputStep } from './InputStep';
import { PreviewStep } from './PreviewStep';
import { ReadProductsStep } from './ReadProductsStep';
import { SaveStep } from './SaveStep';
import { SendDnpStep } from './SendDnpStep';
import { dnpChzCodePoolApi } from './api';
import type { DnpCallerResponseConfig, DnpChzPatternRequest, DnpTargetConfig } from './types';

const DEFAULT_SAMPLE = `{
  "operation": "dnp_sinc_pull_codes",
  "sinc": "dnp_sinc_pull_codes",
  "order_id": 10271,
  "order_name": "26-0666/6938",
  "Number": "260666/6938"
}`;

const FULL_CODE_SELECT = [
  'КодМаркировки',
  'ПолныйКодМаркировки',
  'ХешСуммаКодаМаркировки',
  'Статус',
  'Организация_Key',
  'СтанцияУправленияЗаказами_Key',
  'Номенклатура_Key',
  'Характеристика_Key',
  'ДатаЭмиссииУниверсальная',
  'ДатаПечатиУниверсальная',
  'ШтрихкодУпаковки_Key',
  'GTIN',
  'МаксимальнаяРозничнаяЦена',
  'СпособВводаВОборот',
  'Шаблон',
  'ХешСуммаУпаковки',
  'ТипШтрихкода',
  'МаркировкаОстатков',
  'СрокГодности',
  'ЗаказНаЭмиссию_Key',
  'ИдентификаторЗаказаСУЗ',
  'ИдентификаторБлокаСУЗ',
  'ВидКИЗ',
  'РазмерКИЗ',
  'ДокументОснование',
  'ДокументОснование_Type',
];

const FOREACH_FILTER = "Номенклатура_Key eq guid'{{product.Номенклатура_Key}}' and ДокументОснование eq cast(guid'{{order.Ref_Key}}', 'Document_ЗаказНаПроизводство2_2')";

export function DnpChzCodePoolWizard() {
  const autoParsed = useRef(false);
  const [name, setName] = useState('DnP запрашивает пул кодов Честного знака');
  const [slug, setSlug] = useState('dnp_sinc_pull_codes');
  const [sourceSystem, setSourceSystem] = useState('dnp');
  const [inputMode, setInputMode] = useState<InputMode>('json');
  const [sampleText, setSampleText] = useState(DEFAULT_SAMPLE);
  const [parseResult, setParseResult] = useState<InputParseResponse | null>(null);
  const [fields, setFields] = useState<InputContractField[]>([]);
  const [operationKey, setOperationKey] = useState<InputOperationKey>(() => defaultOperationKey());
  const [businessKey, setBusinessKey] = useState<InputBusinessKey>(() => defaultBusinessKey());
  const [findOrder, setFindOrder] = useState<ODataStepConfig>(() => defaultFindOrderStep());
  const [readProducts, setReadProducts] = useState<ODataObjectStepConfig>(() => defaultReadProductsStep());
  const [findCodes, setFindCodes] = useState<ForeachODataStepConfig>(() => defaultFindCodesStep());
  const [payload, setPayload] = useState<PayloadStepConfig>(() => defaultPayloadStep());
  const [target, setTarget] = useState<DnpTargetConfig>(() => defaultTarget());
  const [responseToCaller, setResponseToCaller] = useState<DnpCallerResponseConfig>(() => defaultResponseToCaller());
  const [previewSignature, setPreviewSignature] = useState<string | null>(null);

  const parse = useMutation({
    mutationFn: () => integrationMasterApi.parse({ input_mode: inputMode, scenario_key: 'dnp_chz_code_pool', sample: sampleText }),
    onSuccess: (data) => {
      setParseResult(data);
      setFields(data.fields);
      setOperationKey(defaultOperationKey());
      setBusinessKey(businessFromSuggestion(data.suggested_business_keys[0]));
    },
  });

  const contract = useMemo(
    () => buildContract({ name, slug, inputMode, sourceSystem, sample: parseResult?.normalized_sample ?? sampleText, fields, operationKey, businessKey }),
    [name, slug, inputMode, sourceSystem, parseResult, sampleText, fields, operationKey, businessKey],
  );
  const patternRequest = useMemo<DnpChzPatternRequest>(
    () => ({ name: contract.name, slug: contract.slug, input_contract: contract, find_order: findOrder, read_products: readProducts, find_codes: findCodes, payload, target, response_to_caller: responseToCaller }),
    [contract, findOrder, readProducts, findCodes, payload, target, responseToCaller],
  );
  const requestSignature = useMemo(() => JSON.stringify(patternRequest), [patternRequest]);

  const preview = useMutation({
    mutationFn: () => dnpChzCodePoolApi.preview(patternRequest),
    onSuccess: () => setPreviewSignature(requestSignature),
  });
  const create = useMutation({ mutationFn: () => dnpChzCodePoolApi.create(patternRequest) });

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
    setSampleText(mode === 'json' ? DEFAULT_SAMPLE : '');
    setFields([]);
    setParseResult(null);
    setOperationKey(defaultOperationKey());
    setBusinessKey(defaultBusinessKey());
    invalidatePreview();
  }

  function useOperationField(field: InputContractField) {
    setOperationKey(withMatcher({ type: 'field', field_path: field.path, value: field.example ?? 'dnp_sinc_pull_codes', fallback_paths: [], matcher_preview: {} }));
    invalidatePreview();
  }

  function useBusinessField(field: InputContractField) {
    setBusinessKey({ path: field.path, fallback_paths: ['request.body.Number'].filter((path) => path !== field.path) });
    invalidatePreview();
  }

  function patchFindOrder(patch: Partial<ODataStepConfig>) {
    setFindOrder((current) => {
      const next = { ...current, ...patch };
      if ('connection_id' in patch || 'connection_name' in patch) {
        setReadProducts((productStep) => ({ ...productStep, connection_id: next.connection_id ?? null, connection_name: next.connection_name ?? null }));
        setFindCodes((codesStep) => ({ ...codesStep, connection_id: next.connection_id ?? null, connection_name: next.connection_name ?? null }));
      }
      return next;
    });
    invalidatePreview();
  }

  function patchReadProducts(patch: Partial<ODataObjectStepConfig>) {
    setReadProducts((current) => ({ ...current, ...patch }));
    invalidatePreview();
  }

  function patchFindCodes(patch: Partial<ForeachODataStepConfig>) {
    setFindCodes((current) => ({ ...current, ...patch }));
    invalidatePreview();
  }

  function changePayload(next: PayloadStepConfig) {
    setPayload(next);
    if (next.body_type !== payload.body_type) {
      setTarget((current) => ({ ...current, body_type: next.body_type as FinalActionBodyType, headers: defaultTargetHeaders(next.body_type) }));
    }
    invalidatePreview();
  }

  function changeTarget(next: DnpTargetConfig) {
    setTarget(next);
    invalidatePreview();
  }

  function changeResponse(next: DnpCallerResponseConfig) {
    setResponseToCaller(next);
    invalidatePreview();
  }

  const parseError = parse.error instanceof Error ? parse.error.message : null;
  const previewError = preview.error instanceof Error ? preview.error.message : null;
  const createError = create.error instanceof Error ? create.error.message : null;
  const canPreview = fields.length > 0 && !slugError(contract.slug);
  const currentPreviewValid = Boolean(preview.data?.valid && previewSignature === requestSignature);
  const orderPreview = preview.data?.order_result ?? { Ref_Key: 'c3335ee4-43d0-11f1-8388-000c29b755c7', Number: '260666/6938' };

  if (create.error && !(create.error instanceof Error)) return <ErrorState error={create.error} />;

  return (
    <div className="page-stack integration-master-page request-odata-object-foreach-send-endpoint-wizard">
      <section className="hero-panel integration-master-hero pattern-wizard-hero dnp-chz-hero">
        <div>
          <span className="eyebrow">Pattern Wizard</span>
          <h1>Запрос → OData → строки документа → повтор OData → внешний endpoint</h1>
          <p>DnP вызывает OMH, OMH находит заказ производства в 1С, читает продукцию, собирает коды Честного знака через foreach OData и отправляет массив в DnP endpoint.</p>
          <div className="hero-meta">
            <Link className="primary-link" to="/integration-start">Scenario Router</Link>
            <Link className="primary-link" to="/docs/onec/recipes/dnp-chz-code-pool-sync">Рецепт</Link>
            <Link className="primary-link" to="/training">Training Sandbox</Link>
          </div>
        </div>
        <div className="pattern-route-diagram" aria-label="DnP CHZ code pool sync flow">
          <span>Incoming Request</span>
          <small>DnP JSON: Number, order_name</small>
          <span>OData order</span>
          <small>Document_ЗаказНаПроизводство2_2</small>
          <span>OData object rows</span>
          <small>Продукция</small>
          <span>Foreach OData codes</span>
          <small>InformationRegister_ПулКодовМаркировкиСУЗ</small>
          <span>Payload Builder</span>
          <small>target_payload.payload.rows[]</small>
          <span>Send Endpoint</span>
          <small>DnP import API</small>
          <span>Caller Response</span>
          <small>{'{"ok": true}'}</small>
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
      <ReadProductsStep step={readProducts} orderPreview={orderPreview} onChange={patchReadProducts} />
      <FindCodesStep step={findCodes} onChange={patchFindCodes} />
      <BuildPayloadStep payload={payload} onChange={changePayload} />
      <SendDnpStep target={target} response={responseToCaller} onTargetChange={changeTarget} onResponseChange={changeResponse} />
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
  const normalizedSlug = slugify(slug || 'dnp_sinc_pull_codes') || 'dnp_sinc_pull_codes';
  return {
    name: name || 'DnP запрашивает пул кодов Честного знака',
    slug: normalizedSlug,
    input_mode: inputMode,
    source_system: sourceSystem,
    scenario_key: 'dnp_chz_code_pool',
    sample,
    fields,
    operation_key: withMatcher(operationKey),
    business_key: businessKey,
    endpoint_url: `/api/bus/in/${normalizedSlug}`,
  };
}

function defaultOperationKey(): InputOperationKey {
  return withMatcher({ type: 'field', field_path: 'request.body.sinc', value: 'dnp_sinc_pull_codes', fallback_paths: ['request.body.operation'], matcher_preview: {} });
}

function defaultBusinessKey(): InputBusinessKey {
  return { path: 'request.body.order_name', fallback_paths: ['request.body.Number'] };
}

function businessFromSuggestion(suggestion?: BusinessKeySuggestion): InputBusinessKey {
  return { path: suggestion?.path ?? 'request.body.order_name', fallback_paths: suggestion?.fallback_paths?.length ? suggestion.fallback_paths : ['request.body.Number'] };
}

function defaultFindOrderStep(): ODataStepConfig {
  return {
    type: 'odata_query',
    connection_id: null,
    connection_name: null,
    resource: 'Document_ЗаказНаПроизводство2_2',
    filter_mode: 'raw',
    filter_rule: { field: 'Number', operator: 'eq', value_type: 'variable', value: 'request.body.Number' },
    filter: "Number eq '{{request.body.Number}}'",
    select: ['Ref_Key', 'Number', 'Date', 'Posted'],
    top: 1,
    orderby: null,
    paginate: false,
    save_as: 'order',
    required: true,
  };
}

function defaultReadProductsStep(): ODataObjectStepConfig {
  return {
    type: 'odata_object_query',
    connection_id: null,
    connection_name: null,
    object_variable: 'order',
    key_field: 'Ref_Key',
    key_type: 'guid',
    base_resource: 'Document_ЗаказНаПроизводство2_2',
    nested_resource: 'Продукция',
    filter: null,
    select: ['Номенклатура_Key', 'Количество', 'КоличествоУпаковок'],
    top: 100,
    paginate: false,
    save_as: 'products',
    required: true,
    overwrite: true,
  };
}

function defaultFindCodesStep(): ForeachODataStepConfig {
  return {
    type: 'foreach_odata',
    items: 'products',
    item_as: 'product',
    connection_id: null,
    connection_name: null,
    resource: 'InformationRegister_ПулКодовМаркировкиСУЗ',
    filter: FOREACH_FILTER,
    select: FULL_CODE_SELECT,
    top: 500,
    paginate: true,
    merge: 'flatten',
    save_as: 'codes',
    required: true,
    limits: { max_items: 100, max_requests: 100, max_result_rows: 10000 },
    test_limit: null,
    overwrite: true,
  };
}

function defaultPayloadStep(): PayloadStepConfig {
  return {
    type: 'build_payload',
    body_type: 'json',
    save_as: 'target_payload',
    json_mode: 'raw_template',
    template: defaultDnpPayloadTemplate(),
    fields: [],
    dynamic_entries: [],
    overwrite: true,
  };
}

function defaultTarget(): DnpTargetConfig {
  return {
    method: 'POST',
    url: 'http://172.16.3.10/api/v2/integrations/omh/chz/codes/import',
    headers: { 'Content-Type': 'application/json' },
    body_source: 'target_payload',
    body_type: 'json',
    timeout_seconds: 30,
  };
}

function defaultResponseToCaller(): DnpCallerResponseConfig {
  return { type: 'fixed_success', status_code: 200, body: { ok: true }, headers: { 'Content-Type': 'application/json' } };
}

function defaultTargetHeaders(type: string) {
  if (type === 'xml') return { 'Content-Type': 'application/xml; charset=utf-8' };
  if (type === 'raw_text') return { 'Content-Type': 'text/plain; charset=utf-8' };
  return { 'Content-Type': 'application/json' };
}

function defaultDnpPayloadTemplate() {
  return `{
  "omh": {
    "run_id": "{{context.run_id}}",
    "event_id": "{{context.event_id}}",
    "entity_id": "{{request.body.order_name}}",
    "event_type": "ChestniyZnakCodesSyncRequested",
    "entity_type": "DnPOrder",
    "source_system": "Open Manufacturing Hub",
    "target_system": "DnP",
    "correlation_id": "dnp-chz-sync:{{request.body.order_name}}"
  },
  "payload": {
    "rows": "{{codes}}",
    "order_id": "{{request.body.order_id}}",
    "odata_url": "http://172.16.3.19/erp_ptc/odata/standard.odata/InformationRegister_ПулКодовМаркировкиСУЗ",
    "order_name": "{{request.body.order_name}}",
    "onec_order_number": "{{order.Number}}",
    "order_numbers_by_basis": {
      "{{order.Ref_Key}}": "{{order.Number}}"
    }
  }
}`;
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
