import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { ErrorState } from '../../../components/ErrorState';
import { integrationMasterApi } from '../../integration-master/api';
import { slugError, slugify } from '../../integration-master/EndpointSlugEditor';
import type { BusinessKeySuggestion, InputBusinessKey, InputContract, InputContractField, InputMode, InputOperationKey, InputParseResponse, ODataStepConfig, PayloadStepConfig } from '../../integration-master/types';
import { CallerResponseStep, defaultCallerBody } from './CallerResponseStep';
import { InputStep } from './InputStep';
import { ODataStep } from './ODataStep';
import { OneCHttpServiceStep } from './OneCHttpServiceStep';
import { OneCWritebackPayloadStep } from './OneCWritebackPayloadStep';
import { PreviewStep } from './PreviewStep';
import { SaveStep } from './SaveStep';
import { SiteEndpointStep } from './SiteEndpointStep';
import { SitePayloadStep } from './SitePayloadStep';
import { SiteResponseExtractionStep } from './SiteResponseExtractionStep';
import { sourceWebApiWritebackOnecApi } from './api';
import type { SourceWebApiWritebackCallerResponseConfig, SourceWebApiWritebackEndpointConfig, SourceWebApiWritebackExtractionConfig, SourceWebApiWritebackOneCPatternRequest, SourceWebApiWritebackOneCServiceConfig } from './types';

const DEFAULT_SAMPLE = `{
  "operation": "publish_order_to_site",
  "order_number": "260666/6938",
  "site_code": "B2B"
}`;

export function SourceWebApiWritebackOnecWizard() {
  const autoParsed = useRef(false);
  const [name, setName] = useState('Отправить данные на сайт и записать ответ обратно в 1С');
  const [slug, setSlug] = useState('publish-order-to-site');
  const [sourceSystem, setSourceSystem] = useState('onec');
  const [inputMode, setInputMode] = useState<InputMode>('json');
  const [sampleText, setSampleText] = useState(DEFAULT_SAMPLE);
  const [parseResult, setParseResult] = useState<InputParseResponse | null>(null);
  const [fields, setFields] = useState<InputContractField[]>([]);
  const [operationKey, setOperationKey] = useState<InputOperationKey>(() => withMatcher({ type: 'field', field_path: 'request.body.operation', value: 'publish_order_to_site', fallback_paths: [], matcher_preview: {} }));
  const [businessKey, setBusinessKey] = useState<InputBusinessKey>({ path: 'request.body.order_number', fallback_paths: [] });
  const [odataStep, setODataStep] = useState<ODataStepConfig>(() => defaultODataStep());
  const [sitePayload, setSitePayload] = useState<PayloadStepConfig>(() => defaultSitePayloadStep('order'));
  const [siteEndpoint, setSiteEndpoint] = useState<SourceWebApiWritebackEndpointConfig>(() => defaultSiteEndpoint());
  const [siteResponseExtraction, setSiteResponseExtraction] = useState<SourceWebApiWritebackExtractionConfig>(() => defaultExtraction());
  const [onecWritebackPayload, setOnecWritebackPayload] = useState<PayloadStepConfig>(() => defaultOnecWritebackPayloadStep('order', 'site_response'));
  const [onecHttpService, setOnecHttpService] = useState<SourceWebApiWritebackOneCServiceConfig>(() => defaultOnecService());
  const [callerResponse, setCallerResponse] = useState<SourceWebApiWritebackCallerResponseConfig>(() => ({ type: 'custom_json', status_code: 200, body: defaultCallerBody(), headers: { 'Content-Type': 'application/json' } }));
  const [previewSignature, setPreviewSignature] = useState<string | null>(null);

  const parse = useMutation({
    mutationFn: () => integrationMasterApi.parse({ input_mode: inputMode, scenario_key: 'onec_publish_order_to_site', sample: sampleText }),
    onSuccess: (data) => {
      setParseResult(data);
      setFields(data.fields);
      setOperationKey(withMatcher({ type: 'field', field_path: 'request.body.operation', value: 'publish_order_to_site', fallback_paths: [], matcher_preview: {} }));
      setBusinessKey(businessFromSuggestion(data.suggested_business_keys.find((item) => item.path === 'request.body.order_number') ?? data.suggested_business_keys[0]));
    },
  });

  const contract = useMemo(() => buildContract({ name, slug, inputMode, sourceSystem, sample: parseResult?.normalized_sample ?? sampleText, fields, operationKey, businessKey }), [name, slug, inputMode, sourceSystem, parseResult, sampleText, fields, operationKey, businessKey]);
  const patternRequest = useMemo<SourceWebApiWritebackOneCPatternRequest>(() => ({
    name: contract.name,
    slug: contract.slug,
    input_contract: contract,
    odata_step: odataStep,
    site_payload: sitePayload,
    site_endpoint: siteEndpoint,
    site_response_extraction: siteResponseExtraction,
    onec_writeback_payload: onecWritebackPayload,
    onec_http_service: onecHttpService,
    caller_response: callerResponse,
  }), [contract, odataStep, sitePayload, siteEndpoint, siteResponseExtraction, onecWritebackPayload, onecHttpService, callerResponse]);
  const requestSignature = useMemo(() => JSON.stringify(patternRequest), [patternRequest]);

  const preview = useMutation({ mutationFn: () => sourceWebApiWritebackOnecApi.preview(patternRequest), onSuccess: () => setPreviewSignature(requestSignature) });
  const create = useMutation({ mutationFn: () => sourceWebApiWritebackOnecApi.create(patternRequest) });

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
    setOperationKey(withMatcher({ type: 'field', field_path: 'request.body.operation', value: 'publish_order_to_site', fallback_paths: [], matcher_preview: {} }));
    setBusinessKey({ path: 'request.body.order_number', fallback_paths: [] });
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
    setODataStep((current) => {
      const next = { ...current, ...patch };
      if (patch.save_as && patch.save_as !== current.save_as) {
        setSitePayload((payload) => ({ ...payload, template: defaultSitePayloadTemplate(patch.save_as || 'order') }));
        setOnecWritebackPayload((payload) => ({ ...payload, template: defaultOnecWritebackPayloadTemplate(patch.save_as || 'order', siteEndpoint.save_response_as || 'site_response') }));
      }
      return next;
    });
    invalidatePreview();
  }

  function changeSitePayload(next: PayloadStepConfig) {
    const previousSaveAs = sitePayload.save_as;
    setSitePayload(next);
    if (next.save_as !== previousSaveAs && siteEndpoint.body_source === previousSaveAs) setSiteEndpoint((current) => ({ ...current, body_source: next.save_as }));
    invalidatePreview();
  }

  function changeSiteEndpoint(next: SourceWebApiWritebackEndpointConfig) {
    const previousSaveAs = siteEndpoint.save_response_as || 'site_response';
    setSiteEndpoint(next);
    if ((next.save_response_as || 'site_response') !== previousSaveAs) {
      const responseAs = next.save_response_as || 'site_response';
      setSiteResponseExtraction((current) => ({
        ...current,
        external_id_path: current.external_id_path.replace(previousSaveAs, responseAs),
        status_path: current.status_path.replace(previousSaveAs, responseAs),
        success_condition: { ...current.success_condition, path: current.success_condition.path.replace(previousSaveAs, responseAs) },
      }));
    }
    invalidatePreview();
  }

  function changeOnecWritebackPayload(next: PayloadStepConfig) {
    const previousSaveAs = onecWritebackPayload.save_as;
    setOnecWritebackPayload(next);
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
    <div className="page-stack integration-master-page source-web-api-writeback-onec-wizard">
      <section className="hero-panel integration-master-hero pattern-wizard-hero">
        <div>
          <span className="eyebrow">Pattern Wizard</span>
          <h1>1С → сайт → запись ответа в 1С</h1>
          <p>OMH принимает запрос 1С, находит заказ в OData, отправляет JSON на сайт, извлекает external_id/status и вызывает HTTP service 1С для writeback.</p>
          <div className="hero-meta">
            <Link className="primary-link" to="/integration-start">Scenario Router</Link>
            <Link className="primary-link" to="/docs/onec/recipes/onec-site-writeback">Рецепт</Link>
            <Link className="primary-link" to="/training">Training Sandbox</Link>
          </div>
        </div>
        <div className="pattern-route-diagram" aria-label="1C to website to 1C writeback flow">
          <span>1C</span>
          <small>publish_order_to_site</small>
          <span>OMH endpoint</span>
          <small>OData enrichment</small>
          <span>Website API</span>
          <small>external_id/status</small>
          <span>1C HTTP service</span>
          <small>writeback saved</small>
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

      <ODataStep contract={contract} step={odataStep} onChange={patchODataStep} />
      <SitePayloadStep payload={sitePayload} orderSaveAs={odataStep.save_as} selectFields={odataStep.select} onChange={changeSitePayload} />
      <SiteEndpointStep endpoint={siteEndpoint} payloadSaveAs={sitePayload.save_as} onChange={changeSiteEndpoint} />
      <SiteResponseExtractionStep extraction={siteResponseExtraction} siteResponseAs={siteEndpoint.save_response_as} onChange={(value) => { setSiteResponseExtraction(value); invalidatePreview(); }} />
      <OneCWritebackPayloadStep payload={onecWritebackPayload} orderSaveAs={odataStep.save_as} siteResponseAs={siteEndpoint.save_response_as} onChange={changeOnecWritebackPayload} />
      <OneCHttpServiceStep service={onecHttpService} payloadSaveAs={onecWritebackPayload.save_as} onChange={(value) => { setOnecHttpService(value); invalidatePreview(); }} />
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
  const normalizedSlug = slugify(slug || 'publish-order-to-site') || 'publish-order-to-site';
  return {
    name: name || 'Отправить данные на сайт и записать ответ обратно в 1С',
    slug: normalizedSlug,
    input_mode: inputMode,
    source_system: sourceSystem,
    scenario_key: 'onec_publish_order_to_site',
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

function defaultSitePayloadStep(orderSaveAs: string): PayloadStepConfig {
  return { type: 'build_payload', body_type: 'json', save_as: 'site_payload', json_mode: 'raw_template', template: defaultSitePayloadTemplate(orderSaveAs), fields: [], dynamic_entries: [], overwrite: true };
}

function defaultSitePayloadTemplate(orderSaveAs: string) {
  return JSON.stringify({
    source: 'OMH',
    site_code: '{{request.body.site_code}}',
    order: {
      uuid: `{{${orderSaveAs}.Ref_Key}}`,
      number: `{{${orderSaveAs}.Number}}`,
      date: `{{${orderSaveAs}.Date}}`,
      posted: `{{${orderSaveAs}.Posted}}`,
    },
  }, null, 2);
}

function defaultSiteEndpoint(): SourceWebApiWritebackEndpointConfig {
  return { method: 'POST', url: 'http://site.local/api/orders/import', headers: { 'Content-Type': 'application/json' }, body_source: 'site_payload', body_type: 'json', timeout_seconds: 20, save_response_as: 'site_response' };
}

function defaultExtraction(): SourceWebApiWritebackExtractionConfig {
  return { external_id_path: 'site_response.external_id', status_path: 'site_response.status', success_condition: { path: 'site_response.success', operator: 'eq', value: true }, sample_response: { success: true, external_id: 'SITE-ORDER-260666-6938', status: 'accepted' } };
}

function defaultOnecWritebackPayloadStep(orderSaveAs: string, siteResponseAs: string): PayloadStepConfig {
  return { type: 'build_payload', body_type: 'json', save_as: 'onec_writeback_payload', json_mode: 'raw_template', template: defaultOnecWritebackPayloadTemplate(orderSaveAs, siteResponseAs), fields: [], dynamic_entries: [], overwrite: true };
}

function defaultOnecWritebackPayloadTemplate(orderSaveAs: string, siteResponseAs: string) {
  return JSON.stringify({
    order_ref_key: `{{${orderSaveAs}.Ref_Key}}`,
    order_number: `{{${orderSaveAs}.Number}}`,
    external_system: '{{request.body.site_code}}',
    external_id: `{{${siteResponseAs}.external_id}}`,
    status: `{{${siteResponseAs}.status}}`,
  }, null, 2);
}

function defaultOnecService(): SourceWebApiWritebackOneCServiceConfig {
  return { method: 'POST', connector_id: null, connector_name: null, base_url: 'http://1c-server/erp/hs/omh', path: '/order-external-id', url: '', headers: { 'Content-Type': 'application/json' }, body_source: 'onec_writeback_payload', body_type: 'json', timeout_seconds: 20, save_response_as: 'onec_writeback_response' };
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
  return { path: suggestion?.path ?? 'request.body.order_number', fallback_paths: suggestion?.fallback_paths ?? [] };
}
