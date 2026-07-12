import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { ErrorState } from '../../../components/ErrorState';
import { integrationMasterApi } from '../../integration-master/api';
import { slugError, slugify } from '../../integration-master/EndpointSlugEditor';
import type { BusinessKeySuggestion, InputBusinessKey, InputContract, InputContractField, InputMode, InputOperationKey, InputParseResponse, OperationKeySuggestion } from '../../integration-master/types';
import { CallerResponseStep } from './CallerResponseStep';
import { InputStep } from './InputStep';
import { LabelsArrayStep } from './LabelsArrayStep';
import { PreviewStep } from './PreviewStep';
import { PrinterSelectionStep } from './PrinterSelectionStep';
import { PrintModeStep } from './PrintModeStep';
import { SaveStep } from './SaveStep';
import { ZplTemplateStep } from './ZplTemplateStep';
import { requestPrintApi } from './api';
import type { RequestPrintCallerResponseConfig, RequestPrintLabelsConfig, RequestPrintPatternRequest, RequestPrintPrinterSelectionConfig, RequestPrintPrintModeConfig, RequestPrintZplConfig } from './types';

const DEFAULT_SAMPLE = `{
  "operation": "print_labels",
  "printer": "TRAINING-PRINTER-01",
  "job_key": "ORDER-123",
  "labels": [
    {
      "sequence_no": 1,
      "sku": "ABC-123",
      "title": "Плата ABC",
      "code": "010464615169738421ABC",
      "qty": 1
    },
    {
      "sequence_no": 2,
      "sku": "XYZ-777",
      "title": "Модуль XYZ",
      "code": "010464615169738421XYZ",
      "qty": 1
    }
  ]
}`;

const DEFAULT_ZPL = `^XA
^CI28
^FO30,30^A0N,30,30^FD{{label.title}}^FS
^FO30,70^A0N,24,24^FDSKU: {{label.sku}}^FS
^FO30,110^BXN,5,200^FD{{label.code}}^FS
^FO30,300^A0N,24,24^FD#{{label.sequence_no}} / {{request.body.job_key}}^FS
^XZ`;

export function RequestPrintWizard() {
  const autoParsed = useRef(false);
  const [name, setName] = useState('Запрос → печать этикеток');
  const [slug, setSlug] = useState('print-labels');
  const [sourceSystem, setSourceSystem] = useState('onec');
  const [inputMode] = useState<InputMode>('json');
  const [sampleText, setSampleText] = useState(DEFAULT_SAMPLE);
  const [parseResult, setParseResult] = useState<InputParseResponse | null>(null);
  const [fields, setFields] = useState<InputContractField[]>([]);
  const [operationKey, setOperationKey] = useState<InputOperationKey>({ type: 'field', field_path: 'request.body.operation', value: 'print_labels', fallback_paths: [], matcher_preview: matcherPreview('request.body.operation', 'print_labels', []) });
  const [businessKey, setBusinessKey] = useState<InputBusinessKey>({ path: 'request.body.job_key', fallback_paths: [] });
  const [printerSelection, setPrinterSelection] = useState<RequestPrintPrinterSelectionConfig>({ mode: 'from_request', path: 'request.body.printer', fixed_printer_name: 'LINE-1-ZEBRA' });
  const [labels, setLabels] = useState<RequestPrintLabelsConfig>({ path: 'request.body.labels', item_as: 'label', required_fields: ['code'], optional_fields: ['sku', 'title', 'qty', 'sequence_no'] });
  const [zpl, setZpl] = useState<RequestPrintZplConfig>({ template: DEFAULT_ZPL });
  const [printMode, setPrintMode] = useState<RequestPrintPrintModeConfig>({ mode: 'dry_run' });
  const [response, setResponse] = useState<RequestPrintCallerResponseConfig>({ type: 'normalized_print_status', status_code: 200, body: defaultResponseBody(), headers: { 'Content-Type': 'application/json' } });
  const [previewSignature, setPreviewSignature] = useState<string | null>(null);

  const parse = useMutation({
    mutationFn: () => integrationMasterApi.parse({ input_mode: inputMode, scenario_key: 'onec_print_request', sample: sampleText }),
    onSuccess: (data) => {
      setParseResult(data);
      setFields(data.fields);
      setOperationKey(operationFromSuggestion(data.suggested_operation_keys.find((item) => item.field_path === 'request.body.operation') ?? data.suggested_operation_keys[0]));
      setBusinessKey(businessFromSuggestion(data.suggested_business_keys.find((item) => item.path === 'request.body.job_key') ?? data.suggested_business_keys[0]));
    },
  });

  const contract = useMemo(() => buildContract({ name, slug, inputMode, sourceSystem, sample: parseResult?.normalized_sample ?? safeJson(sampleText), fields, operationKey, businessKey }), [name, slug, inputMode, sourceSystem, parseResult, sampleText, fields, operationKey, businessKey]);
  const patternRequest = useMemo<RequestPrintPatternRequest>(() => ({ name: contract.name, slug: contract.slug, input_contract: contract, printer_selection: printerSelection, labels, zpl, print_mode: printMode, response }), [contract, printerSelection, labels, zpl, printMode, response]);
  const requestSignature = useMemo(() => JSON.stringify(patternRequest), [patternRequest]);

  const preview = useMutation({ mutationFn: () => requestPrintApi.preview(patternRequest), onSuccess: () => setPreviewSignature(requestSignature) });
  const create = useMutation({ mutationFn: () => requestPrintApi.create(patternRequest) });
  const testPrint = useMutation({ mutationFn: () => requestPrintApi.testPrint({ ...patternRequest, dry_run: printMode.mode === 'dry_run', limit: printMode.mode === 'print_all' ? 1000 : 1 }) });

  useEffect(() => {
    if (autoParsed.current) return;
    autoParsed.current = true;
    parse.mutate();
  }, []);

  function invalidatePreview() {
    setPreviewSignature(null);
    preview.reset();
    create.reset();
    testPrint.reset();
  }

  function runTestPrint() {
    if (printMode.mode !== 'dry_run') {
      const printer = printerSelection.mode === 'fixed' ? printerSelection.fixed_printer_name : 'printer from request.body.printer';
      if (!window.confirm(`Будет отправлена реальная этикетка на принтер ${printer}. Продолжить?`)) return;
    }
    testPrint.mutate();
  }

  const parseError = parse.error instanceof Error ? parse.error.message : null;
  const previewError = preview.error instanceof Error ? preview.error.message : null;
  const createError = create.error instanceof Error ? create.error.message : null;
  const testPrintError = testPrint.error instanceof Error ? testPrint.error.message : null;
  const canPreview = fields.length > 0 && !slugError(contract.slug);
  const currentPreviewValid = Boolean(preview.data?.valid && previewSignature === requestSignature);

  if (create.error && !(create.error instanceof Error)) return <ErrorState error={create.error} />;

  return (
    <div className="page-stack integration-master-page request-print-wizard">
      <section className="hero-panel integration-master-hero pattern-wizard-hero">
        <div>
          <span className="eyebrow">Pattern Wizard</span>
          <h1>Запрос → печать этикеток</h1>
          <p>Настройте endpoint, который принимает JSON-запрос на печать, строит ZPL по labels[] и возвращает print job status.</p>
          <div className="hero-meta"><Link className="primary-link" to="/integration-start">Scenario Router</Link><Link className="primary-link" to="/docs/onec/recipes/onec-print-labels">Рецепт</Link><Link className="primary-link" to="/training?exampleId=training.print.labels">Training Sandbox</Link></div>
        </div>
        <div className="pattern-route-diagram" aria-label="Request to printer flow"><span>1C / WMS / API</span><small>HTTP JSON</small><span>OMH endpoint</span><small>labels[]</small><span>ZPL template</span><small>ZPL</small><span>Printer connector</span><small>print status</small></div>
      </section>

      <InputStep name={name} slug={slug} sourceSystem={sourceSystem} inputMode={inputMode} sampleText={sampleText} fields={fields} parseResult={parseResult} operationKey={operationKey} businessKey={businessKey} parseError={parseError} parsing={parse.isPending} onNameChange={(value) => { setName(value); invalidatePreview(); }} onSlugChange={(value) => { setSlug(value); invalidatePreview(); }} onSourceSystemChange={(value) => { setSourceSystem(value); invalidatePreview(); }} onSampleTextChange={(value) => { setSampleText(value); setParseResult(null); setFields([]); invalidatePreview(); }} onParse={() => parse.mutate()} />
      <PrinterSelectionStep selection={printerSelection} onChange={(value) => { setPrinterSelection(value); invalidatePreview(); }} />
      <LabelsArrayStep labels={labels} onChange={(value) => { setLabels(value); invalidatePreview(); }} />
      <ZplTemplateStep zpl={zpl} onChange={(value) => { setZpl(value); invalidatePreview(); }} />
      <PrintModeStep mode={printMode} onChange={(value) => { setPrintMode(value); invalidatePreview(); }} />
      <CallerResponseStep response={response} onChange={(value) => { setResponse(value); invalidatePreview(); }} />
      <PreviewStep preview={preview.data} error={previewError} loading={preview.isPending} disabled={!canPreview} testPrint={testPrint.data} testPrintError={testPrintError} testPrintLoading={testPrint.isPending} onPreview={() => preview.mutate()} onTestPrint={runTestPrint} />
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
  const normalizedSlug = slugify(slug || 'print-labels') || 'print-labels';
  return { name: name || 'Запрос → печать этикеток', slug: normalizedSlug, input_mode: inputMode, source_system: sourceSystem, scenario_key: 'onec_print_request', sample, fields, operation_key: withMatcher(operationKey), business_key: businessKey, endpoint_url: `/api/bus/in/${normalizedSlug}` };
}

function withMatcher(key: InputOperationKey): InputOperationKey {
  return { ...key, matcher_preview: matcherPreview(key.field_path ?? null, key.value, key.fallback_paths, key.type) };
}

function matcherPreview(path: string | null, value: unknown, fallbacks: string[] = [], type: InputOperationKey['type'] = 'field') {
  if (type === 'endpoint' || type === 'none' || !path) return { mode: type, rules: [] };
  const rules = [path, ...fallbacks].filter(Boolean).map((candidate) => ({ type: 'body_path_equals', path: candidate.replace(/^request\.body\./, ''), value }));
  return { mode: 'any', rules };
}

function operationFromSuggestion(suggestion?: OperationKeySuggestion): InputOperationKey {
  if (!suggestion) return { type: 'field', field_path: 'request.body.operation', value: 'print_labels', fallback_paths: [], matcher_preview: matcherPreview('request.body.operation', 'print_labels', []) };
  return { type: suggestion.type, field_path: suggestion.field_path ?? null, value: suggestion.value ?? null, fallback_paths: suggestion.fallback_paths, matcher_preview: suggestion.matcher_json };
}

function businessFromSuggestion(suggestion?: BusinessKeySuggestion): InputBusinessKey {
  if (!suggestion) return { path: 'request.body.job_key', fallback_paths: [] };
  return { path: suggestion.path, fallback_paths: suggestion.fallback_paths };
}

function safeJson(value: string) {
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

function defaultResponseBody() {
  return { success: true, print_job_id: '{{print_job.id}}', labels_count: '{{labels.length}}', printer: '{{selected_printer.name}}', status: '{{print_job.status}}' };
}
