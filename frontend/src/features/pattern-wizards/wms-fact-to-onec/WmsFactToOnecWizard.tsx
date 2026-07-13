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

type WmsFactPresetKey = 'shipment_fact' | 'stock_balance' | 'inventory_result' | 'movement_fact';

interface WmsFactPreset {
  key: WmsFactPresetKey;
  label: string;
  description: string;
  name: string;
  slug: string;
  operation: string;
  businessKey: string;
  businessFallbacks: string[];
  odataLookupEnabled: boolean;
  serviceOperation: string;
  servicePath: string;
  eventType: string;
  entityType: string;
  entityIdPath: string;
  correlationPrefix: string;
  sample: string;
}

const WMS_FACT_PRESETS: Record<WmsFactPresetKey, WmsFactPreset> = {
  shipment_fact: {
    key: 'shipment_fact',
    label: 'Отгрузка',
    description: 'WMS сообщает, что заказ отгружен или изменил статус отгрузки.',
    name: 'WMS отправляет складской факт в 1С',
    slug: 'wms-shipment-fact',
    operation: 'shipment_fact',
    businessKey: 'request.body.wms_shipment_id',
    businessFallbacks: ['request.body.order_number'],
    odataLookupEnabled: true,
    serviceOperation: 'update_shipment_status',
    servicePath: '/shipment-facts',
    eventType: 'WmsShipmentFactReceived',
    entityType: 'ShipmentFact',
    entityIdPath: 'request.body.wms_shipment_id',
    correlationPrefix: 'wms-shipment',
    sample: `{
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
}`,
  },
  stock_balance: {
    key: 'stock_balance',
    label: 'Остатки',
    description: 'WMS отправляет актуальный остаток по складу, SKU, партии или ячейке.',
    name: 'WMS отправляет остатки в 1С',
    slug: 'wms-stock-balance-to-1c',
    operation: 'stock_balance',
    businessKey: 'request.body.stock_balance_id',
    businessFallbacks: ['request.body.warehouse_code', 'request.body.moment'],
    odataLookupEnabled: false,
    serviceOperation: 'update_stock_balance',
    servicePath: '/stock-balances',
    eventType: 'WmsStockBalanceReceived',
    entityType: 'StockBalance',
    entityIdPath: 'request.body.stock_balance_id',
    correlationPrefix: 'wms-stock',
    sample: `{
  "operation": "stock_balance",
  "stock_balance_id": "WMS-STOCK-20260713-001",
  "warehouse_code": "MAIN",
  "moment": "2026-07-13T10:00:00",
  "items": [
    {
      "sku": "A-100",
      "quantity": 125.5,
      "uom": "pcs",
      "batch": "BATCH-001",
      "cell": "A-01-01"
    }
  ]
}`,
  },
  inventory_result: {
    key: 'inventory_result',
    label: 'Инвентаризация',
    description: 'WMS передает результат пересчета: ожидали одно количество, фактически нашли другое.',
    name: 'WMS отправляет результат инвентаризации в 1С',
    slug: 'wms-inventory-result-to-1c',
    operation: 'inventory_result',
    businessKey: 'request.body.inventory_id',
    businessFallbacks: ['request.body.warehouse_code'],
    odataLookupEnabled: false,
    serviceOperation: 'send_inventory_result',
    servicePath: '/inventory-results',
    eventType: 'WmsInventoryResultReceived',
    entityType: 'InventoryResult',
    entityIdPath: 'request.body.inventory_id',
    correlationPrefix: 'wms-inventory',
    sample: `{
  "operation": "inventory_result",
  "inventory_id": "WMS-INV-9001",
  "warehouse_code": "MAIN",
  "completed_at": "2026-07-13T12:30:00",
  "items": [
    {
      "sku": "A-100",
      "expected_qty": 120,
      "actual_qty": 118,
      "uom": "pcs",
      "cell": "A-01-01"
    }
  ]
}`,
  },
  movement_fact: {
    key: 'movement_fact',
    label: 'Перемещение',
    description: 'WMS сообщает о перемещении товара между складами, зонами или ячейками.',
    name: 'WMS отправляет перемещение в 1С',
    slug: 'wms-movement-to-1c',
    operation: 'movement_fact',
    businessKey: 'request.body.movement_id',
    businessFallbacks: ['request.body.source_warehouse_code', 'request.body.target_warehouse_code'],
    odataLookupEnabled: false,
    serviceOperation: 'send_movement_fact',
    servicePath: '/movements',
    eventType: 'WmsMovementFactReceived',
    entityType: 'MovementFact',
    entityIdPath: 'request.body.movement_id',
    correlationPrefix: 'wms-movement',
    sample: `{
  "operation": "movement_fact",
  "movement_id": "WMS-MOVE-7001",
  "source_warehouse_code": "MAIN",
  "target_warehouse_code": "PACK",
  "moved_at": "2026-07-13T13:10:00",
  "items": [
    {
      "sku": "A-100",
      "qty": 20,
      "uom": "pcs",
      "source_cell": "A-01-01",
      "target_cell": "P-02-04"
    }
  ]
}`,
  },
};

const DEFAULT_PRESET = WMS_FACT_PRESETS.shipment_fact;

export function WmsFactToOnecWizard() {
  const autoParsed = useRef(false);
  const [factPreset, setFactPreset] = useState<WmsFactPresetKey>(DEFAULT_PRESET.key);
  const [name, setName] = useState(DEFAULT_PRESET.name);
  const [slug, setSlug] = useState(DEFAULT_PRESET.slug);
  const [sourceSystem, setSourceSystem] = useState('wms');
  const [inputMode, setInputMode] = useState<InputMode>('json');
  const [sampleText, setSampleText] = useState(DEFAULT_PRESET.sample);
  const [parseResult, setParseResult] = useState<InputParseResponse | null>(null);
  const [fields, setFields] = useState<InputContractField[]>([]);
  const [operationKey, setOperationKey] = useState<InputOperationKey>(() => operationKeyForPreset(DEFAULT_PRESET));
  const [businessKey, setBusinessKey] = useState<InputBusinessKey>({ path: DEFAULT_PRESET.businessKey, fallback_paths: DEFAULT_PRESET.businessFallbacks });
  const [odataLookup, setODataLookup] = useState<WmsFactToOneCODataLookupConfig>(() => ({ enabled: DEFAULT_PRESET.odataLookupEnabled, config: defaultODataStep(), order_ref_key_path: 'request.body.order_ref_key' }));
  const [onecPayload, setOnecPayload] = useState<PayloadStepConfig>(() => defaultOnecPayloadStep('order', DEFAULT_PRESET));
  const [onecHttpService, setOnecHttpService] = useState<WmsFactToOneCServiceConfig>(() => defaultOnecService(DEFAULT_PRESET));
  const [callerResponse, setCallerResponse] = useState<WmsFactToOneCCallerResponseConfig>(() => ({ type: 'normalized', status_code: 200, body: defaultCallerBody(), headers: { 'Content-Type': 'application/json' } }));
  const [previewSignature, setPreviewSignature] = useState<string | null>(null);

  const parse = useMutation({
    mutationFn: () => integrationMasterApi.parse({ input_mode: inputMode, scenario_key: 'wms_shipment_fact', sample: sampleText }),
    onSuccess: (data) => {
      setParseResult(data);
      setFields(data.fields);
      const preset = WMS_FACT_PRESETS[factPreset];
      setOperationKey(operationKeyForPreset(preset));
      setBusinessKey(businessFromSuggestion(data.suggested_business_keys.find((item) => item.path === preset.businessKey) ?? data.suggested_business_keys[0], preset));
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
    const preset = WMS_FACT_PRESETS[factPreset];
    setInputMode(mode);
    setSampleText(preset.sample);
    setFields([]);
    setParseResult(null);
    setOperationKey(operationKeyForPreset(preset));
    setBusinessKey({ path: preset.businessKey, fallback_paths: preset.businessFallbacks });
    invalidatePreview();
  }

  function applyFactPreset(nextPresetKey: WmsFactPresetKey) {
    const preset = WMS_FACT_PRESETS[nextPresetKey];
    setFactPreset(nextPresetKey);
    setName(preset.name);
    setSlug(preset.slug);
    setSampleText(preset.sample);
    setParseResult(null);
    setFields([]);
    setOperationKey(operationKeyForPreset(preset));
    setBusinessKey({ path: preset.businessKey, fallback_paths: preset.businessFallbacks });
    setODataLookup({ enabled: preset.odataLookupEnabled, config: defaultODataStep(), order_ref_key_path: 'request.body.order_ref_key' });
    setOnecPayload(defaultOnecPayloadStep('order', preset));
    setOnecHttpService(defaultOnecService(preset));
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
    if (nextSaveAs !== previousSaveAs) setOnecPayload((payload) => ({ ...payload, template: defaultOnecPayloadTemplate(nextSaveAs, WMS_FACT_PRESETS[factPreset]) }));
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

      <section className="wizard-step integration-master-step">
        <span className="step-index">00</span>
        <div className="odata-step-heading">
          <div>
            <span className="eyebrow">Warehouse fact preset</span>
            <h2>Какой складской факт отправляет WMS</h2>
            <p>Пресет меняет sample, route key, business key, payload и операцию 1С. После выбора нажмите Parse request.</p>
          </div>
          <span className="status-card neutral"><small>Operation</small><strong>{WMS_FACT_PRESETS[factPreset].operation}</strong></span>
        </div>
        <div className="metadata-grid compact-grid no-margin">
          {(Object.values(WMS_FACT_PRESETS) as WmsFactPreset[]).map((preset) => (
            <button
              type="button"
              key={preset.key}
              className={preset.key === factPreset ? 'primary-button' : 'ghost-button'}
              onClick={() => applyFactPreset(preset.key)}
              title={preset.description}
            >
              {preset.label}
            </button>
          ))}
        </div>
        <p className="microcopy">{WMS_FACT_PRESETS[factPreset].description}</p>
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
    name: name || 'WMS отправляет складской факт в 1С',
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

function operationKeyForPreset(preset: WmsFactPreset): InputOperationKey {
  return withMatcher({ type: 'field', field_path: 'request.body.operation', value: preset.operation, fallback_paths: [], matcher_preview: {} });
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

function defaultOnecPayloadStep(orderSaveAs: string, preset: WmsFactPreset): PayloadStepConfig {
  return { type: 'build_payload', body_type: 'json', save_as: 'onec_payload', json_mode: 'raw_template', template: defaultOnecPayloadTemplate(orderSaveAs, preset), fields: [], dynamic_entries: [], overwrite: true };
}

function defaultOnecPayloadTemplate(orderSaveAs: string, preset: WmsFactPreset) {
  const omh = {
    event_id: '{{context.event_id}}',
    run_id: '{{context.run_id}}',
    correlation_id: `${preset.correlationPrefix}:{{${preset.entityIdPath}}}`,
    event_type: preset.eventType,
    entity_type: preset.entityType,
    entity_id: `{{${preset.entityIdPath}}}`,
    source_system: 'WMS',
    target_system: '1C ERP',
  };
  if (preset.key === 'stock_balance') {
    return {
      omh,
      payload: {
        stock_balance_id: '{{request.body.stock_balance_id}}',
        warehouse_code: '{{request.body.warehouse_code}}',
        moment: '{{request.body.moment}}',
        items: '{{request.body.items}}',
      },
    };
  }
  if (preset.key === 'inventory_result') {
    return {
      omh,
      payload: {
        inventory_id: '{{request.body.inventory_id}}',
        warehouse_code: '{{request.body.warehouse_code}}',
        completed_at: '{{request.body.completed_at}}',
        items: '{{request.body.items}}',
      },
    };
  }
  if (preset.key === 'movement_fact') {
    return {
      omh,
      payload: {
        movement_id: '{{request.body.movement_id}}',
        source_warehouse_code: '{{request.body.source_warehouse_code}}',
        target_warehouse_code: '{{request.body.target_warehouse_code}}',
        moved_at: '{{request.body.moved_at}}',
        items: '{{request.body.items}}',
      },
    };
  }
  return {
    omh: {
      ...omh,
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

function defaultOnecService(preset: WmsFactPreset): WmsFactToOneCServiceConfig {
  return { connector_id: null, connector_name: '', operation: preset.serviceOperation, method: 'POST', base_url: 'http://1c-server/erp/hs/omh', path: preset.servicePath, url: '', headers: { 'Content-Type': 'application/json' }, body_source: 'onec_payload', body_type: 'json', timeout_seconds: 30, save_response_as: 'onec_response' };
}

function withMatcher(key: InputOperationKey): InputOperationKey {
  return { ...key, matcher_preview: matcherPreview(key.field_path ?? null, key.value, key.fallback_paths, key.type) };
}

function matcherPreview(path: string | null, value: unknown, fallbacks: string[] = [], type: InputOperationKey['type'] = 'field') {
  if (type === 'endpoint' || type === 'none' || !path) return { mode: type, rules: [] };
  const rules = [path, ...fallbacks].filter(Boolean).map((candidate) => ({ type: 'body_path_equals', path: candidate.replace('request.body.', ''), value }));
  return { mode: 'any', rules };
}

function businessFromSuggestion(suggestion: BusinessKeySuggestion | undefined, preset: WmsFactPreset): InputBusinessKey {
  return { path: suggestion?.path ?? preset.businessKey, fallback_paths: suggestion?.fallback_paths?.length ? suggestion.fallback_paths : preset.businessFallbacks };
}
