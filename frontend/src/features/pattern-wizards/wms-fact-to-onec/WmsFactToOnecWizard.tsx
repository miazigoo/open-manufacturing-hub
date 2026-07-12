import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { ErrorState } from '../../../components/ErrorState';
import { integrationMasterApi } from '../../integration-master/api';
import { slugError, slugify } from '../../integration-master/EndpointSlugEditor';
import type { BusinessKeySuggestion, InputBusinessKey, InputContract, InputContractField, InputMode, InputOperationKey, InputParseResponse, ODataStepConfig, PayloadStepConfig } from '../../integration-master/types';
import { CallerResponseStep, defaultCallerBody } from './CallerResponseStep';
import { InputStep } from './InputStep';
import { OneCHttpServiceStep } from './OneCHttpServiceStep';
import { OneCPayloadStep } from './OneCPayloadStep';
import { OptionalODataStep } from './OptionalODataStep';
import { PreviewStep } from './PreviewStep';
import { SaveStep } from './SaveStep';
import { wmsFactToOnecApi } from './api';
import type { WmsFactToOneCCallerResponseConfig, WmsFactToOneCODataLookupConfig, WmsFactToOneCPatternRequest, WmsFactToOneCServiceConfig } from './types';

const DEFAULT_SAMPLE = `{
  "operation": "shipment_fact",
  "wms_shipment_id": "WMS-SHIP-123",
  "order_number": "260666/6938",
  "status": "shipped",
  "warehouse_code": "MAIN",
  "shipped_at": "2026-07-04T14:30:00",
  "items": [
    {
      "sku": "ABC-123",
      "qty": 10,
      "barcode": "04646151697384"
    }
  ]
}`;

export function WmsFactToOnecWizard() {
  const autoParsed = useRef(false);
  const [name, setName] = useState('WMS отправляет факт отгрузки в 1С');
  const [slug, setSlug] = useState('wms-shipment-fact');
  const [sourceSystem, setSourceSystem] = useState('wms');
  const [inputMode, setInputMode] = useState<InputMode>('json');
  const [sampleText, setSampleText] = useState(DEFAULT_SAMPLE);
  const [parseResult, setParseResult] = useState<InputParseResponse | null>(null);
  const [fields, setFields] = useState<InputContractField[]>([]);
  const [operationKey, setOperationKey] = useState<InputOperationKey>(() => withMatcher({ type: 'field', field_path: 'request.body.operation', value: 'shipment_fact', fallback_paths: [], matcher_preview: {} }));
  const [businessKey, setBusinessKey] = useState<InputBusinessKey>({ path: 'request.body.wms_shipment_id', fallback_paths: ['request.body.order_number'] });
  const [odataLookup, setODataLookup] = useState<WmsFactToOneCODataLookupConfig>(() => ({ enabled: true, config: defaultODataStep(), order_ref_key_path: 'request.body.order_ref_key' }));
  const [onecPayload, setOnecPayload] = useState<PayloadStepConfig>(() => defaultOnecPayloadStep('order'));
  const [onecHttpService, setOnecHttpService] = useState<WmsFactToOneCServiceConfig>(() => defaultOnecService());
  const [callerResponse, setCallerResponse] = useState<WmsFactToOneCCallerResponseConfig>(() => ({ type: 'normalized', status_code: 200, body: defaultCallerBody(), headers: { 'Content-Type': 'application/json' } }));
  const [previewSignature, setPreviewSignature] = useState<string | null>(null);

  const parse = useMutation({
    mutationFn: () => integrationMasterApi.parse({ input_mode: inputMode, scenario_key: 'wms_shipment_fact', sample: sampleText }),
    onSuccess: (data) => {
      setParseResult(data);
      setFields(data.fields);
      setOperationKey(withMatcher({ type: 'field', field_path: 'request.body.operation', value: 'shipment_fact', fallback_paths: [], matcher_preview: {} }));
      setBusinessKey(businessFromSuggestion(data.suggested_business_keys.find((item) => item.path === 'request.body.wms_shipment_id') ?? data.suggested_business_keys[0]));
    },
  });

  const contract = useMemo(() => buildContract({ name, slug, inputMode, sourceSystem, sample: parseResult?.normalized_sample ?? sampleText, fields, operationKey, businessKey }), [name, slug, inputMode, sourceSystem, parseResult, sampleText, fields, operationKey, businessKey]);
  const patternRequest = useMemo<WmsFactToOneCPatternRequest>(() => ({
    name: contract.name,
    slug: contract.slug,
    input_contract: contract,
    odata_lookup: odataLookup,
    onec_payload: onecPayload,
    onec_http_service: onecHttpService,
    caller_response: callerResponse,
  }), [contract, odataLookup, onecPayload, onecHttpService, callerResponse]);
  const requestSignature = useMemo(() => JSON.stringify(patternRequest), [patternRequest]);

  const preview = useMutation({ mutationFn: () => wmsFactToOnecApi.preview(patternRequest), onSuccess: () => setPreviewSignature(requestSignature) });
  const create = useMutation({ mutationFn: () => wmsFactToOnecApi.create(patternRequest) });

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
    setSampleText(DEFAULT_SAMPLE);
    setFields([]);
    setParseResult(null);
    setOperationKey(withMatcher({ type: 'field', field_path: 'request.body.operation', value: 'shipment_fact', fallback_paths: [], matcher_preview: {} }));
    setBusinessKey({ path: 'request.body.wms_shipment_id', fallback_paths: ['request.body.order_number'] });
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

  function changeODataLookup(next: WmsFactToOneCODataLookupConfig) {
    const previousSaveAs = odataLookup.config.save_as || 'order';
    setODataLookup(next);
    const nextSaveAs = next.config.save_as || 'order';
    if (nextSaveAs !== previousSaveAs) setOnecPayload((payload) => ({ ...payload, template: defaultOnecPayloadTemplate(nextSaveAs) }));
    invalidatePreview();
  }

  function changeOnecPayload(next: PayloadStepConfig) {
    const previousSaveAs = onecPayload.save_as;
    setOnecPayload(next);
    if (next.save_as !== previousSaveAs && onecHttpService.body_source === previousSaveAs) setOnecHttpService((current) => ({ ...current, body_source: next.save_as }));
    invalidatePreview();
  }

  const parseError = parse.error instanceof Error ? parse.error.message : null;
  const previewError = preview.error instanceof Error ? preview.error.message : null;
  const createError = create.error instanceof Error ? create.error.message : null;
  const canPreview = fields.length > 0 && !slugError(contract.slug);
  const currentPreviewValid = Boolean(preview.data?.valid && previewSignature === requestSignature);

  if (create.error && !(create.error instanceof Error)) return <ErrorState error={create.error} />;

  return (
    <div className="page-stack integration-master-page wms-fact-to-onec-wizard">
      <section className="hero-panel integration-master-hero pattern-wizard-hero">
        <div>
          <span className="eyebrow">Pattern Wizard</span>
          <h1>WMS/API → OMH → 1С HTTP service</h1>
          <p>Настройте endpoint, который принимает факт складской операции, optionally находит заказ в 1С и передаёт payload в HTTP service 1С.</p>
          <div className="hero-meta">
            <Link className="primary-link" to="/integration-start">Scenario Router</Link>
            <Link className="primary-link" to="/docs/onec/recipes/wms-shipment-fact-to-onec">Рецепт</Link>
            <Link className="primary-link" to="/training?exampleId=training.wms.shipment_fact_to_onec">Training Sandbox</Link>
          </div>
        </div>
        <div className="pattern-route-diagram" aria-label="WMS to 1C HTTP service flow">
          <span>WMS / API</span>
          <small>HTTP JSON</small>
          <span>OMH endpoint</span>
          <small>optional OData lookup</small>
          <span>1C OData</span>
          <small>order Ref_Key</small>
          <span>1C HTTP Service</span>
          <small>response to WMS</small>
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
      <OptionalODataStep contract={contract} lookup={odataLookup} onChange={changeODataLookup} />
      <OneCPayloadStep payload={onecPayload} orderSaveAs={odataLookup.config.save_as} onChange={changeOnecPayload} />
      <OneCHttpServiceStep service={onecHttpService} payloadSaveAs={onecPayload.save_as} onChange={(value) => { setOnecHttpService(value); invalidatePreview(); }} />
      <CallerResponseStep response={callerResponse} onChange={(value) => { setCallerResponse(value); invalidatePreview(); }} />
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
  const normalizedSlug = slugify(slug || 'wms-shipment-fact') || 'wms-shipment-fact';
  return {
    name: name || 'WMS отправляет факт отгрузки в 1С',
    slug: normalizedSlug,
    input_mode: inputMode,
    source_system: sourceSystem,
    scenario_key: 'wms_shipment_fact',
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
    resource: 'Document_ЗаказКлиента',
    filter_mode: 'raw',
    filter_rule: { field: 'Number', operator: 'eq', value_type: 'variable', value: 'request.body.order_number' },
    filter: "Number eq '{{request.body.order_number}}'",
    select: ['Ref_Key', 'Number', 'Date', 'Posted'],
    top: 1,
    orderby: null,
    paginate: false,
    save_as: 'order',
    required: true,
  };
}

function defaultOnecPayloadStep(orderSaveAs: string): PayloadStepConfig {
  return { type: 'build_payload', body_type: 'json', save_as: 'onec_payload', json_mode: 'raw_template', template: defaultOnecPayloadTemplate(orderSaveAs), fields: [], dynamic_entries: [], overwrite: true };
}

function defaultOnecPayloadTemplate(orderSaveAs: string) {
  return {
    omh: {
      event_id: '{{context.event_id}}',
      run_id: '{{context.run_id}}',
      correlation_id: 'wms-shipment:{{request.body.wms_shipment_id}}',
      event_type: 'WmsShipmentFactReceived',
      entity_type: 'ShipmentFact',
      entity_id: '{{request.body.wms_shipment_id}}',
      source_system: 'WMS',
      target_system: '1C ERP',
    },
    payload: {
      order_ref_key: `{{${orderSaveAs}.Ref_Key}}`,
      order_number: '{{request.body.order_number}}',
      wms_shipment_id: '{{request.body.wms_shipment_id}}',
      status: '{{request.body.status}}',
      warehouse_code: '{{request.body.warehouse_code}}',
      shipped_at: '{{request.body.shipped_at}}',
      items: '{{request.body.items}}',
    },
  };
}

function defaultOnecService(): WmsFactToOneCServiceConfig {
  return { connector_id: null, connector_name: '', operation: 'update_shipment_status', method: 'POST', base_url: 'http://1c-server/erp/hs/omh', path: '/shipment-facts', url: '', headers: { 'Content-Type': 'application/json' }, body_source: 'onec_payload', body_type: 'json', timeout_seconds: 30, save_response_as: 'onec_response' };
}

function withMatcher(key: InputOperationKey): InputOperationKey {
  return { ...key, matcher_preview: matcherPreview(key.field_path ?? null, key.value, key.fallback_paths, key.type) };
}

function matcherPreview(path: string | null, value: unknown, fallbacks: string[] = [], type: InputOperationKey['type'] = 'field') {
  if (type === 'endpoint' || type === 'none' || !path) return { mode: type, rules: [] };
  const rules = [path, ...fallbacks].filter(Boolean).map((candidate) => ({ type: 'body_path_equals', path: candidate.replace('request.body.', ''), value }));
  return { mode: 'any', rules };
}

function businessFromSuggestion(suggestion?: BusinessKeySuggestion): InputBusinessKey {
  return { path: suggestion?.path ?? 'request.body.wms_shipment_id', fallback_paths: suggestion?.fallback_paths?.length ? suggestion.fallback_paths : ['request.body.order_number'] };
}
