import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { ConfirmDialog } from '../../../components/ConfirmDialog';
import { integrationMasterApi } from '../api';
import { AvailableVariablesPanel } from '../payload-builder/AvailableVariablesPanel';
import { CallerResponseConfig } from './CallerResponseConfig';
import { FinalActionPreviewPanel } from './FinalActionPreviewPanel';
import { FinalActionSavePanel } from './FinalActionSavePanel';
import { FinalActionTestPanel } from './FinalActionTestPanel';
import { FinalActionTypeSelect } from './FinalActionTypeSelect';
import { ReturnResponseConfig } from './ReturnResponseConfig';
import { SendEndpointConfig } from './SendEndpointConfig';
import type { FinalActionConfig, FinalActionRequest, FinalActionType, InputContract, InputDraftRead } from '../types';

interface FinalActionBuilderProps {
  contract: InputContract;
  draft: InputDraftRead;
  previousVariables: Record<string, unknown>;
  onDraftUpdated: (draft: InputDraftRead) => void;
}

const DEFAULT_DNP_ENDPOINT = 'http://172.16.3.10/api/v2/integrations/omh/chz/codes/import';

export function FinalActionBuilder({ contract, draft, previousVariables, onDraftUpdated }: FinalActionBuilderProps) {
  const [expanded, setExpanded] = useState(Boolean(draft.final_action));
  const [action, setAction] = useState<FinalActionConfig>(() => draft.final_action ?? defaultFinalAction('send_endpoint'));
  const [realTestConfirmOpen, setRealTestConfirmOpen] = useState(false);

  useEffect(() => {
    if (draft.final_action) {
      setAction(draft.final_action);
      setExpanded(true);
    }
  }, [draft.final_action]);

  const payload = useMemo<FinalActionRequest>(() => ({ input_contract: contract, previous_variables: previousVariables, final_action: action }), [contract, previousVariables, action]);
  const preview = useMutation({ mutationFn: () => integrationMasterApi.previewFinalAction(payload) });
  const test = useMutation({ mutationFn: (dryRun: boolean) => integrationMasterApi.testFinalAction({ ...payload, dry_run: dryRun }) });
  const save = useMutation({
    mutationFn: () => integrationMasterApi.saveFinalAction(draft.id, contract, previousVariables, action),
    onSuccess: (data) => onDraftUpdated(data.draft),
  });

  function changeType(type: FinalActionType) {
    setAction((current) => actionForType(type, current));
    preview.reset();
    test.reset();
    save.reset();
  }

  function realTest() {
    setRealTestConfirmOpen(true);
  }

  function confirmRealTest() {
    setRealTestConfirmOpen(false);
    test.mutate(false);
  }

  function insertVariable(path: string) {
    const placeholder = `{{${path.replace(/\[\]$/, '')}}}`;
    setAction((current) => {
      if (current.body_source === 'custom') return { ...current, custom_body: `${String(current.custom_body ?? '')}${placeholder}` };
      const response = current.return_to_caller;
      if (['custom_json', 'custom_xml', 'custom_raw'].includes(response.type)) return { ...current, return_to_caller: { ...response, body: `${String(response.body ?? '')}${placeholder}` } };
      return { ...current, custom_body: `${String(current.custom_body ?? '')}${placeholder}` };
    });
  }

  const previewError = preview.error instanceof Error ? preview.error.message : null;
  const testError = test.error instanceof Error ? test.error.message : null;
  const saveError = save.error instanceof Error ? save.error.message : null;

  return (
    <section className="wizard-step integration-master-step final-action-builder">
      <span className="step-index">10</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Step 4A</span>
          <h2>Шаг 4A — Что сделать с результатом?</h2>
          <p>Выберите, вернуть ли данные вызывающей системе, отправить их во внешний сервис или сделать оба действия.</p>
        </div>
        <Link className="primary-link" to="/docs/reference/integration-master/overview">Инструкция</Link>
      </div>

      {!expanded ? (
        <div className="final-action-intro panel stack-form">
          <VariableSummary variables={previousVariables} />
          <div className="action-row wrap-actions"><button type="button" className="primary-button" onClick={() => setExpanded(true)}>Добавить финальное действие</button></div>
        </div>
      ) : (
        <>
          <VariableSummary variables={previousVariables} />
          <AvailableVariablesPanel variables={previousVariables} onInsert={insertVariable} />
          <FinalActionTypeSelect value={action.type} onChange={changeType} />
          {action.type === 'return_response' ? <ReturnResponseConfig action={action} onChange={setAction} /> : null}
          {action.type === 'send_endpoint' || action.type === 'send_and_return_response' ? (
            <>
              <SendEndpointConfig action={action} onChange={setAction} />
              <CallerResponseConfig action={action} onChange={setAction} />
            </>
          ) : null}
          {action.type === 'accepted_event' ? <AcceptedEventConfig /> : null}
          <div className="odata-step-panels">
            <FinalActionPreviewPanel preview={preview.data} error={previewError} loading={preview.isPending} onPreview={() => preview.mutate()} />
            <FinalActionTestPanel result={test.data} error={testError} testing={test.isPending} onDryRun={() => test.mutate(true)} onRealTest={realTest} />
            <FinalActionSavePanel draft={draft} action={action} error={saveError} saving={save.isPending} onSave={() => save.mutate()} />
          </div>
          <ConfirmDialog
            open={realTestConfirmOpen}
            title="Отправить реальный HTTP-запрос?"
            description="OMH выполнит запрос на указанный endpoint. Это уже не dry run: внешний сервис может сохранить данные или запустить обработку."
            confirmLabel="Отправить real test"
            loading={test.isPending}
            onCancel={() => setRealTestConfirmOpen(false)}
            onConfirm={confirmRealTest}
          >
            <div className="metadata-grid compact-grid no-margin">
              <span className="status-card neutral"><small>Method</small><strong>{action.method}</strong></span>
              <span className="status-card neutral"><small>Endpoint</small><strong>{action.url || 'URL не указан'}</strong></span>
              <span className="status-card neutral"><small>Body source</small><strong>{action.body_source}</strong></span>
              <span className="status-card neutral"><small>Caller response</small><strong>{action.return_to_caller.type}</strong></span>
            </div>
          </ConfirmDialog>
        </>
      )}
    </section>
  );
}

function VariableSummary({ variables }: { variables: Record<string, unknown> }) {
  return (
    <section className="panel stack-form final-action-variable-summary">
      <div className="panel-toolbar"><div><span className="eyebrow">Variables</span><h3>Что доступно финальному действию</h3><p className="microcopy">Step 4A работает с результатом payload builder и входящим request.</p></div></div>
      <div className="metadata-grid compact-grid no-margin">
        <VariableCard name="target_payload" value={variables.target_payload} required />
        <VariableCard name="request.body" value={resolvePath(variables, 'request.body')} required />
        <VariableCard name="context" value={variables.context} />
      </div>
    </section>
  );
}

function VariableCard({ name, value, required = false }: { name: string; value: unknown; required?: boolean }) {
  const available = value !== undefined;
  return (
    <span className={`status-card ${available ? 'success' : required ? 'danger' : 'neutral'}`}>
      <small>{required ? 'required' : 'optional'}</small>
      <strong>{name}</strong>
      <code>{available ? previewValue(value) : 'not found'}</code>
    </span>
  );
}

function AcceptedEventConfig() {
  return (
    <section className="panel stack-form final-action-config-card">
      <div className="status-card success"><strong>Accepted async response</strong><span>OMH вернёт вызывающей системе event_id и queue_item_id. Реальная очередь, retry/DLQ и Timeline будут реализованы отдельными этапами.</span></div>
    </section>
  );
}

function defaultFinalAction(type: FinalActionType): FinalActionConfig {
  const base: FinalActionConfig = {
    type,
    method: 'POST',
    url: DEFAULT_DNP_ENDPOINT,
    headers: { 'Content-Type': 'application/json' },
    body_type: 'json',
    body_source: 'target_payload',
    custom_body: null,
    timeout_seconds: 30,
    return_to_caller: { type: 'fixed_success', body: { ok: true }, status_code: 200, headers: {} },
    last_test_status: null,
  };
  return actionForType(type, base);
}

function actionForType(type: FinalActionType, current: FinalActionConfig): FinalActionConfig {
  if (type === 'accepted_event') {
    return {
      ...current,
      type,
      body_source: 'none',
      return_to_caller: { type: 'accepted_event', body: {}, status_code: 202, headers: {} },
    };
  }
  if (type === 'return_response') {
    return {
      ...current,
      type,
      url: null,
      body_source: current.body_source === 'none' ? 'target_payload' : current.body_source,
      return_to_caller: { ...current.return_to_caller, type: 'fixed_success', status_code: current.return_to_caller.status_code || 200 },
    };
  }
  if (type === 'send_and_return_response') {
    return {
      ...current,
      type,
      url: current.url || DEFAULT_DNP_ENDPOINT,
      body_source: current.body_source === 'none' ? 'target_payload' : current.body_source,
      return_to_caller: { ...current.return_to_caller, type: 'proxy_response', status_code: current.return_to_caller.status_code || 200 },
    };
  }
  return {
    ...current,
    type,
    url: current.url || DEFAULT_DNP_ENDPOINT,
    body_source: current.body_source === 'none' ? 'target_payload' : current.body_source,
    return_to_caller: { ...current.return_to_caller, type: current.return_to_caller.type === 'proxy_response' ? 'fixed_success' : current.return_to_caller.type },
  };
}

function resolvePath(root: unknown, path: string) {
  const parts = path.split('.');
  let current: unknown = root;
  for (const part of parts) {
    if (current && typeof current === 'object' && part in current) current = (current as Record<string, unknown>)[part];
    else return undefined;
  }
  return current;
}

function previewValue(value: unknown) {
  if (value === null) return 'null';
  if (typeof value === 'string') return value.slice(0, 120);
  try {
    return (JSON.stringify(value) ?? String(value)).slice(0, 160);
  } catch {
    return String(value);
  }
}
