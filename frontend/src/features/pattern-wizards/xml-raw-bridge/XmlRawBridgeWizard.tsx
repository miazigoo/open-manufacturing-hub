import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { ErrorState } from '../../../components/ErrorState';
import { integrationMasterApi } from '../../integration-master/api';
import { slugError, slugify } from '../../integration-master/EndpointSlugEditor';
import type { BusinessKeySuggestion, InputBusinessKey, InputContract, InputContractField, InputMode, InputOperationKey, InputParseResponse } from '../../integration-master/types';
import { CallerResponseStep, defaultCallerBody } from './CallerResponseStep';
import { InputXmlStep } from './InputXmlStep';
import { PreviewStep } from './PreviewStep';
import { RawXmlPolicyStep } from './RawXmlPolicyStep';
import { SaveStep } from './SaveStep';
import { TargetEndpointStep } from './TargetEndpointStep';
import { xmlRawBridgeApi } from './api';
import type { XmlRawBridgeCallerResponseConfig, XmlRawBridgePatternRequest, XmlRawBridgePolicyConfig, XmlRawBridgeTargetConfig } from './types';

const DEFAULT_XML = `<Документ>
  <Тип>УПД</Тип>
  <Номер>123</Номер>
  <ИНН>7707083893</ИНН>
  <Дата>2026-07-04</Дата>
</Документ>`;

export function XmlRawBridgeWizard() {
  const autoParsed = useRef(false);
  const [name, setName] = useState('XML без изменений → endpoint / 1С');
  const [slug, setSlug] = useState('onec-xml-raw-bridge');
  const [sourceSystem, setSourceSystem] = useState('onec');
  const [inputMode, setInputMode] = useState<InputMode>('xml');
  const [sampleText, setSampleText] = useState(DEFAULT_XML);
  const [parseResult, setParseResult] = useState<InputParseResponse | null>(null);
  const [fields, setFields] = useState<InputContractField[]>([]);
  const [operationKey, setOperationKey] = useState<InputOperationKey>(() => withMatcher({ type: 'endpoint', field_path: null, value: null, fallback_paths: [], matcher_preview: {} }));
  const [businessKey, setBusinessKey] = useState<InputBusinessKey>({ path: 'xml./Документ/Номер', fallback_paths: [] });
  const [rawXmlPolicy, setRawXmlPolicy] = useState<XmlRawBridgePolicyConfig>(() => ({ forward_unchanged: true, require_valid_xml: true, validate_xml: true, verify_hash: true }));
  const [target, setTarget] = useState<XmlRawBridgeTargetConfig>(() => defaultTarget());
  const [callerResponse, setCallerResponse] = useState<XmlRawBridgeCallerResponseConfig>(() => ({ type: 'proxy_target_response', status_code: 200, body: defaultCallerBody(), headers: { 'Content-Type': 'application/json' } }));
  const [previewSignature, setPreviewSignature] = useState<string | null>(null);

  const parse = useMutation({
    mutationFn: () => integrationMasterApi.parse({ input_mode: inputMode, scenario_key: 'onec_xml_raw_bridge', sample: sampleText }),
    onSuccess: (data) => {
      setParseResult(data);
      setFields(data.fields);
      setOperationKey(withMatcher({ type: 'endpoint', field_path: null, value: null, fallback_paths: [], matcher_preview: {} }));
      setBusinessKey(businessFromSuggestion(data.suggested_business_keys.find((item) => item.path === 'xml./Документ/Номер') ?? data.suggested_business_keys[0]));
    },
  });

  const contract = useMemo(() => buildContract({ name, slug, inputMode, sourceSystem, sample: parseResult?.normalized_sample ?? sampleText, fields, operationKey, businessKey }), [name, slug, inputMode, sourceSystem, parseResult, sampleText, fields, operationKey, businessKey]);
  const patternRequest = useMemo<XmlRawBridgePatternRequest>(() => ({
    name: contract.name,
    slug: contract.slug,
    input_contract: contract,
    raw_xml_policy: rawXmlPolicy,
    target,
    caller_response: callerResponse,
  }), [contract, rawXmlPolicy, target, callerResponse]);
  const requestSignature = useMemo(() => JSON.stringify(patternRequest), [patternRequest]);

  const preview = useMutation({ mutationFn: () => xmlRawBridgeApi.preview(patternRequest), onSuccess: () => setPreviewSignature(requestSignature) });
  const create = useMutation({ mutationFn: () => xmlRawBridgeApi.create(patternRequest) });

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
    setOperationKey(withMatcher({ type: 'endpoint', field_path: null, value: null, fallback_paths: [], matcher_preview: {} }));
    setBusinessKey({ path: 'xml./Документ/Номер', fallback_paths: [] });
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

  const parseError = parse.error instanceof Error ? parse.error.message : null;
  const previewError = preview.error instanceof Error ? preview.error.message : null;
  const createError = create.error instanceof Error ? create.error.message : null;
  const canPreview = fields.length > 0 && !slugError(contract.slug);
  const currentPreviewValid = Boolean(preview.data?.valid && previewSignature === requestSignature);

  if (create.error && !(create.error instanceof Error)) return <ErrorState error={create.error} />;

  return (
    <div className="page-stack integration-master-page xml-raw-bridge-wizard">
      <section className="hero-panel integration-master-hero pattern-wizard-hero">
        <div>
          <span className="eyebrow">Pattern Wizard</span>
          <h1>XML без изменений → endpoint / 1С</h1>
          <p>Настройте интеграцию, где OMH принимает XML и пересылает его дальше без изменения. Hash check доказывает, что тело не было перестроено.</p>
          <div className="hero-meta">
            <Link className="primary-link" to="/integration-start">Scenario Router</Link>
            <Link className="primary-link" to="/docs/onec/recipes/xml-raw-forwarding">Рецепт</Link>
            <Link className="primary-link" to="/training?exampleId=training.onec.xml_raw_bridge">Training Sandbox</Link>
          </div>
        </div>
        <div className="pattern-route-diagram" aria-label="XML raw bridge flow">
          <span>1C / external XML</span>
          <small>HTTP XML</small>
          <span>OMH endpoint</span>
          <small>save raw XML</small>
          <span>SHA256 check</span>
          <small>unchanged body</small>
          <span>1C HTTP Service</span>
          <small>target response</small>
        </div>
      </section>

      <InputXmlStep
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
      <RawXmlPolicyStep policy={rawXmlPolicy} onChange={(value) => { setRawXmlPolicy(value); invalidatePreview(); }} />
      <TargetEndpointStep target={target} onChange={(value) => { setTarget(value); invalidatePreview(); }} />
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
  const normalizedSlug = slugify(slug || 'onec-xml-raw-bridge') || 'onec-xml-raw-bridge';
  return {
    name: name || 'XML без изменений → endpoint / 1С',
    slug: normalizedSlug,
    input_mode: inputMode,
    source_system: sourceSystem,
    scenario_key: 'onec_xml_raw_bridge',
    sample,
    fields,
    operation_key: withMatcher(operationKey),
    business_key: businessKey,
    endpoint_url: `/api/bus/in/${normalizedSlug}`,
  };
}

function defaultTarget(): XmlRawBridgeTargetConfig {
  return {
    mode: 'raw_url',
    connector_id: null,
    connector_name: '',
    method: 'POST',
    base_url: 'http://1c-server/erp/hs/omh',
    path: '/receive-upd-xml',
    url: 'http://1c-server/erp/hs/omh/receive-upd-xml',
    headers: { 'Content-Type': 'application/xml; charset=utf-8' },
    timeout_seconds: 30,
    save_response_as: 'target_response',
    training_mock_onec_xml_receiver: false,
  };
}

function withMatcher(key: InputOperationKey): InputOperationKey {
  return { ...key, matcher_preview: matcherPreview(key.field_path ?? null, key.value, key.fallback_paths, key.type) };
}

function matcherPreview(path: string | null, value: unknown, fallbacks: string[] = [], type: InputOperationKey['type'] = 'endpoint') {
  if (type === 'endpoint' || type === 'none' || !path) return { mode: type, rules: [] };
  const rules = [path, ...fallbacks].filter(Boolean).map((candidate) => ({ type: 'xml_path_equals', path: toXmlMatcherPath(candidate), value }));
  return { mode: 'any', rules };
}

function toXmlMatcherPath(path: string) {
  const clean = path.replace(/^xml\./, '');
  if (clean.startsWith('/')) return clean.split('/').filter(Boolean).join('.');
  return clean.replace(/\//g, '.');
}

function businessFromSuggestion(suggestion?: BusinessKeySuggestion): InputBusinessKey {
  return { path: suggestion?.path ?? 'xml./Документ/Номер', fallback_paths: suggestion?.fallback_paths?.length ? suggestion.fallback_paths : [] };
}
