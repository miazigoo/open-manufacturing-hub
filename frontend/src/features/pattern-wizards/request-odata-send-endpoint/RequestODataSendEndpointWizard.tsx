import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { ErrorState } from '../../../components/ErrorState';
import { integrationMasterApi } from '../../integration-master/api';
import { slugError, slugify } from '../../integration-master/EndpointSlugEditor';
import type { BusinessKeySuggestion, FinalActionBodyType, InputBusinessKey, InputContract, InputContractField, InputMode, InputOperationKey, InputParseResponse, ODataStepConfig, PayloadStepConfig } from '../../integration-master/types';
import { PatternIntroPanel } from '../shared/PatternIntroPanel';
import { PatternWizardShell } from '../shared/PatternWizardShell';
import { CallerResponseStep } from './CallerResponseStep';
import { requestODataSendEndpointApi } from './api';
import { defaultPayloadTemplate, PayloadStep } from './PayloadStep';
import { ODataStep } from './ODataStep';
import { PreviewStep } from './PreviewStep';
import { RequestStep } from './RequestStep';
import { SaveStep } from './SaveStep';
import { TargetEndpointStep } from './TargetEndpointStep';
import type { RequestODataSendEndpointPatternRequest, RequestODataSendEndpointResponseConfig, RequestODataSendEndpointTargetConfig } from './types';

const DEFAULT_SAMPLE = `{
  "operation": "send_order_to_site",
  "order_number": "260666/6938",
  "site_code": "B2B"
}`;

export function RequestODataSendEndpointWizard() {
  const autoParsed = useRef(false);
  const [name, setName] = useState('Найти заказ в 1С и отправить на сайт');
  const [slug, setSlug] = useState('send-order-to-site');
  const [sourceSystem, setSourceSystem] = useState('onec');
  const [inputMode, setInputMode] = useState<InputMode>('json');
  const [sampleText, setSampleText] = useState(DEFAULT_SAMPLE);
  const [parseResult, setParseResult] = useState<InputParseResponse | null>(null);
  const [fields, setFields] = useState<InputContractField[]>([]);
  const [operationKey, setOperationKey] = useState<InputOperationKey>({ type: 'field', field_path: 'request.body.operation', value: 'send_order_to_site', fallback_paths: [], matcher_preview: matcherPreview('request.body.operation', 'send_order_to_site', []) });
  const [businessKey, setBusinessKey] = useState<InputBusinessKey>({ path: 'request.body.order_number', fallback_paths: [] });
  const [odataStep, setODataStep] = useState<ODataStepConfig>(() => defaultODataStep());
  const [payload, setPayload] = useState<PayloadStepConfig>(() => defaultPayloadStep('order'));
  const [target, setTarget] = useState<RequestODataSendEndpointTargetConfig>(() => defaultTarget());
  const [responseToCaller, setResponseToCaller] = useState<RequestODataSendEndpointResponseConfig>(() => ({ type: 'proxy_response', status_code: 200, body: null, headers: {} }));
  const [previewSignature, setPreviewSignature] = useState<string | null>(null);

  const parse = useMutation({
    mutationFn: () => integrationMasterApi.parse({ input_mode: inputMode, scenario_key: 'onec_publish_order_to_site', sample: sampleText }),
    onSuccess: (data) => {
      setParseResult(data);
      setFields(data.fields);
      setOperationKey(withMatcher({ type: 'field', field_path: 'request.body.operation', value: 'send_order_to_site', fallback_paths: [], matcher_preview: {} }));
      setBusinessKey(businessFromSuggestion(data.suggested_business_keys[0]));
    },
  });

  const contract = useMemo(() => buildContract({ name, slug, inputMode, sourceSystem, sample: parseResult?.normalized_sample ?? sampleText, fields, operationKey, businessKey }), [name, slug, inputMode, sourceSystem, parseResult, sampleText, fields, operationKey, businessKey]);
  const patternRequest = useMemo<RequestODataSendEndpointPatternRequest>(() => ({ name: contract.name, slug: contract.slug, input_contract: contract, odata_step: odataStep, payload, target, response_to_caller: responseToCaller }), [contract, odataStep, payload, target, responseToCaller]);
  const requestSignature = useMemo(() => JSON.stringify(patternRequest), [patternRequest]);

  const preview = useMutation({
    mutationFn: () => requestODataSendEndpointApi.preview(patternRequest),
    onSuccess: () => setPreviewSignature(requestSignature),
  });
  const create = useMutation({ mutationFn: () => requestODataSendEndpointApi.create(patternRequest) });

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
    setOperationKey({ type: mode === 'json' ? 'field' : 'endpoint', field_path: mode === 'json' ? 'request.body.operation' : null, value: mode === 'json' ? 'send_order_to_site' : null, fallback_paths: [], matcher_preview: mode === 'json' ? matcherPreview('request.body.operation', 'send_order_to_site', []) : matcherPreview(null, null, [], 'endpoint') });
    setBusinessKey({ path: mode === 'json' ? 'request.body.order_number' : null, fallback_paths: [] });
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
      if (patch.save_as && payload.save_as === 'target_payload') {
        setPayload((currentPayload) => ({ ...currentPayload, template: defaultPayloadTemplate(currentPayload.body_type, patch.save_as) }));
      }
      return next;
    });
    invalidatePreview();
  }

  function changePayload(next: PayloadStepConfig) {
    setPayload(next);
    if (next.body_type !== payload.body_type) {
      setTarget((current) => ({ ...current, body_type: next.body_type as FinalActionBodyType, headers: defaultTargetHeaders(next.body_type) }));
    }
    invalidatePreview();
  }

  function changeTarget(next: RequestODataSendEndpointTargetConfig) {
    setTarget(next);
    invalidatePreview();
  }

  function changeResponse(next: RequestODataSendEndpointResponseConfig) {
    setResponseToCaller(next);
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
      className="request-odata-send-endpoint-wizard"
      patternId="request_odata_send_endpoint"
      steps={[
        { id: 'request', label: 'Request' },
        { id: 'odata', label: '1C OData' },
        { id: 'payload', label: 'Payload' },
        { id: 'target', label: 'Target' },
        { id: 'preview', label: 'Preview' },
        { id: 'save', label: 'Save' },
      ]}
    >
      <PatternIntroPanel
        title="Запрос → 1С OData → внешний endpoint"
        description="OMH примет запрос, найдёт объект в 1С OData, соберёт JSON/XML/raw payload и отправит его во внешний сервис."
        links={[
          { label: 'Scenario Router', to: '/integration-start' },
          { label: 'Рецепт', to: '/docs/onec/recipes/request-odata-send-endpoint' },
          { label: 'Training Sandbox', to: '/training' },
        ]}
        diagram={(
          <div className="pattern-route-diagram" aria-label="Request to OData to external endpoint flow">
            <span>1C / API</span>
            <small>HTTP request</small>
            <span>OMH endpoint</span>
            <small>OData query</small>
            <span>1C OData</span>
            <small>order</small>
            <span>Payload builder</span>
            <small>JSON/XML/raw</small>
            <span>External endpoint</span>
            <small>proxy/fixed/accepted</small>
            <span>Caller</span>
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

      <ODataStep contract={contract} step={odataStep} onChange={patchODataStep} />
      <PayloadStep payload={payload} saveAs={odataStep.save_as} selectFields={odataStep.select} onChange={changePayload} />
      <TargetEndpointStep target={target} payloadSaveAs={payload.save_as} onChange={changeTarget} />
      <CallerResponseStep response={responseToCaller} onChange={changeResponse} />
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
  const normalizedSlug = slugify(slug || 'send-order-to-site') || 'send-order-to-site';
  return {
    name: name || 'Найти данные в 1С и отправить во внешний сервис',
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
    filter_mode: 'builder',
    filter_rule: { field: 'Number', operator: 'eq', value_type: 'variable', value: 'request.body.order_number' },
    filter: null,
    select: ['Ref_Key', 'Number', 'Date', 'Posted'],
    top: 1,
    orderby: null,
    paginate: false,
    save_as: 'order',
    required: true,
  };
}

function defaultPayloadStep(saveAs: string): PayloadStepConfig {
  return {
    type: 'build_payload',
    body_type: 'json',
    save_as: 'target_payload',
    json_mode: 'raw_template',
    template: defaultPayloadTemplate('json', saveAs),
    fields: [],
    dynamic_entries: [],
    overwrite: true,
  };
}

function defaultTarget(): RequestODataSendEndpointTargetConfig {
  return {
    method: 'POST',
    url: 'http://site.local/api/orders/import',
    headers: { 'Content-Type': 'application/json' },
    body_source: 'target_payload',
    body_type: 'json',
    timeout_seconds: 20,
  };
}

function defaultTargetHeaders(type: string) {
  if (type === 'xml') return { 'Content-Type': 'application/xml; charset=utf-8' };
  if (type === 'raw_text') return { 'Content-Type': 'text/plain; charset=utf-8' };
  return { 'Content-Type': 'application/json' };
}

function defaultSample(mode: InputMode) {
  if (mode === 'xml') return '<Request>\n  <Operation>send_order_to_site</Operation>\n  <OrderNumber>260666/6938</OrderNumber>\n  <SiteCode>B2B</SiteCode>\n</Request>';
  if (mode === 'raw_text') return 'operation=send_order_to_site;order_number=260666/6938;site_code=B2B';
  return DEFAULT_SAMPLE;
}

function businessFromSuggestion(suggestion?: BusinessKeySuggestion): InputBusinessKey {
  return { path: suggestion?.path ?? 'request.body.order_number', fallback_paths: suggestion?.fallback_paths ?? [] };
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
