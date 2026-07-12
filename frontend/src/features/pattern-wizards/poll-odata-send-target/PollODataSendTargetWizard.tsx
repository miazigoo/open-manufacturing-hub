import { useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { ErrorState } from '../../../components/ErrorState';
import { slugError } from '../../integration-master/EndpointSlugEditor';
import type { ODataStepConfig, PayloadStepConfig } from '../../integration-master/types';
import { pollODataSendTargetApi } from './api';
import { CursorStep } from './CursorStep';
import { FirstRunStrategyStep } from './FirstRunStrategyStep';
import { JobBasicsStep } from './JobBasicsStep';
import { ManualTestStep } from './ManualTestStep';
import { ODataStep } from './ODataStep';
import { defaultPayloadTemplate, PayloadStep } from './PayloadStep';
import { PreviewStep } from './PreviewStep';
import { SaveStep } from './SaveStep';
import { TargetEndpointStep } from './TargetEndpointStep';
import type { PollODataCursorConfig, PollODataFirstRunStrategyConfig, PollODataJobBasicsConfig, PollODataSendTargetPatternRequest, PollODataTargetConfig } from './types';

export function PollODataSendTargetWizard() {
  const [job, setJob] = useState<PollODataJobBasicsConfig>(() => ({ name: 'Sync 1C orders to WMS', slug: 'sync-1c-orders-to-wms', enabled_after_create: false, schedule_type: 'manual_only', interval_minutes: 5 }));
  const [odataStep, setODataStep] = useState<ODataStepConfig>(() => defaultODataStep());
  const [firstRun, setFirstRun] = useState<PollODataFirstRunStrategyConfig>(() => ({ strategy: 'fixed_start_date', fixed_start_at: '2026-01-01T00:00:00', hours: 24 }));
  const [cursor, setCursor] = useState<PollODataCursorConfig>(() => ({ cursor_type: 'last_success_at', source_field: 'orders[].Date', update_when: 'target_success' }));
  const [payload, setPayload] = useState<PayloadStepConfig>(() => defaultPayloadStep('orders'));
  const [target, setTarget] = useState<PollODataTargetConfig>(() => defaultTarget());
  const [previewSignature, setPreviewSignature] = useState<string | null>(null);
  const [dryRun, setDryRun] = useState(true);
  const [updateCursor, setUpdateCursor] = useState(false);

  const patternRequest = useMemo<PollODataSendTargetPatternRequest>(() => ({ job, odata_step: odataStep, first_run: firstRun, cursor, payload, target }), [job, odataStep, firstRun, cursor, payload, target]);
  const requestSignature = useMemo(() => JSON.stringify(patternRequest), [patternRequest]);

  const preview = useMutation({ mutationFn: () => pollODataSendTargetApi.preview(patternRequest), onSuccess: () => setPreviewSignature(requestSignature) });
  const create = useMutation({ mutationFn: () => pollODataSendTargetApi.create(patternRequest) });
  const testRun = useMutation({
    mutationFn: () => pollODataSendTargetApi.runTest(create.data ? { polling_job_id: create.data.polling_job_id, dry_run: dryRun, update_cursor: updateCursor } : { pattern: patternRequest, dry_run: dryRun, update_cursor: updateCursor }),
  });

  function invalidatePreview() {
    setPreviewSignature(null);
    preview.reset();
    create.reset();
    testRun.reset();
  }

  function patchODataStep(patch: Partial<ODataStepConfig>) {
    setODataStep((current) => ({ ...current, ...patch }));
    if (patch.save_as) {
      setCursor((current) => ({ ...current, source_field: `${patch.save_as}[].Date` }));
      setPayload(defaultPayloadStep(patch.save_as));
    }
    invalidatePreview();
  }

  function changePayload(next: PayloadStepConfig) {
    setPayload(next);
    if (next.body_type !== payload.body_type) {
      setTarget((current) => ({ ...current, body_type: next.body_type === 'raw_text' ? 'raw_text' : next.body_type, headers: defaultHeaders(next.body_type) }));
    }
    invalidatePreview();
  }

  function runManualTest() {
    if (!dryRun && !window.confirm('Будет выполнен real send во внешний endpoint. Cursor обновится только если включен checkbox. Продолжить?')) return;
    testRun.mutate();
  }

  function changeDryRun(value: boolean) {
    setDryRun(value);
    if (value) setUpdateCursor(false);
    testRun.reset();
  }

  const previewError = preview.error instanceof Error ? preview.error.message : null;
  const createError = create.error instanceof Error ? create.error.message : null;
  const testError = testRun.error instanceof Error ? testRun.error.message : null;
  const canPreview = Boolean(job.name.trim() && job.slug.trim() && odataStep.resource.trim() && target.url.trim() && !slugError(job.slug));
  const currentPreviewValid = Boolean(preview.data?.valid && previewSignature === requestSignature);

  if (create.error && !(create.error instanceof Error)) return <ErrorState error={create.error} />;

  return (
    <div className="page-stack integration-master-page poll-odata-send-target-wizard">
      <section className="hero-panel integration-master-hero pattern-wizard-hero">
        <div>
          <span className="eyebrow">Pattern Wizard</span>
          <h1>1С OData по расписанию → внешний сервис</h1>
          <p>Настройте задачу, которая будет сама читать 1С OData и отправлять результат во внешний API.</p>
          <div className="hero-meta">
            <Link className="primary-link" to="/integration-start">Scenario Router</Link>
            <Link className="primary-link" to="/docs/onec/recipes/poll-odata-send-target">Рецепт</Link>
            <Link className="primary-link" to="/training?exampleId=training.polling.odata_orders_to_wms">Training Sandbox</Link>
            <Link className="primary-link" to="/polling">Run History</Link>
          </div>
        </div>
        <div className="pattern-route-diagram" aria-label="Scheduled OData to target flow">
          <span>OMH Scheduler</span><small>every N minutes</small><span>1C OData</span><small>rows</small><span>Payload Builder</span><small>POST/PUT/PATCH</small><span>External API / WMS</span><small>response</small><span>Run History</span>
        </div>
      </section>

      <JobBasicsStep job={job} onChange={(value) => { setJob(value); invalidatePreview(); }} />
      <ODataStep step={odataStep} onChange={patchODataStep} />
      <FirstRunStrategyStep firstRun={firstRun} onChange={(value) => { setFirstRun(value); invalidatePreview(); }} />
      <CursorStep cursor={cursor} saveAs={odataStep.save_as} onChange={(value) => { setCursor(value); invalidatePreview(); }} />
      <PayloadStep payload={payload} saveAs={odataStep.save_as} onChange={changePayload} />
      <TargetEndpointStep target={target} payloadSaveAs={payload.save_as} onChange={(value) => { setTarget(value); invalidatePreview(); }} />
      <PreviewStep preview={preview.data} error={previewError} loading={preview.isPending} disabled={!canPreview} onPreview={() => preview.mutate()} />
      <ManualTestStep result={testRun.data} createResult={create.data} error={testError} loading={testRun.isPending} disabled={!currentPreviewValid} dryRun={dryRun} updateCursor={updateCursor} onDryRunChange={changeDryRun} onUpdateCursorChange={(value) => { setUpdateCursor(value); testRun.reset(); }} onRun={runManualTest} />
      <SaveStep result={create.data} error={createError} loading={create.isPending} disabled={!currentPreviewValid} onCreate={() => create.mutate()} />
    </div>
  );
}

function defaultODataStep(): ODataStepConfig {
  return {
    type: 'odata_query',
    connection_id: null,
    connection_name: 'Training OData ERP',
    resource: 'Document_ЗаказКлиента',
    filter_mode: 'raw',
    filter_rule: null,
    filter: "Date ge datetime'{{cursor.last_success_at}}' and Posted eq true",
    select: ['Ref_Key', 'Number', 'Date', 'Posted', 'Контрагент_Key'],
    top: 100,
    orderby: null,
    paginate: true,
    save_as: 'orders',
    required: false,
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

function defaultTarget(): PollODataTargetConfig {
  return {
    method: 'POST',
    url: 'http://wms.local/api/orders/import',
    headers: { 'Content-Type': 'application/json' },
    body_source: 'target_payload',
    body_type: 'json',
    timeout_seconds: 30,
    empty_result_behavior: 'do_nothing_success',
  };
}

function defaultHeaders(bodyType: PayloadStepConfig['body_type']): Record<string, unknown> {
  if (bodyType === 'xml') return { 'Content-Type': 'application/xml; charset=utf-8' };
  if (bodyType === 'raw_text') return { 'Content-Type': 'text/plain; charset=utf-8' };
  return { 'Content-Type': 'application/json' };
}
