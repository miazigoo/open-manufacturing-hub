import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { integrationMasterApi } from '../api';
import type { InputDraftRead } from '../types';
import { CompileActions } from './CompileActions';
import { CompilePreviewPanel } from './CompilePreviewPanel';
import { CompileSuccessPanel } from './CompileSuccessPanel';
import { CompileValidationPanel } from './CompileValidationPanel';

interface CompileIntegrationStepProps {
  draft: InputDraftRead;
}

export function CompileIntegrationStep({ draft }: CompileIntegrationStepProps) {
  const [enabled, setEnabled] = useState(false);
  const [createSavedTestCase, setCreateSavedTestCase] = useState(true);
  const [comment, setComment] = useState('Initial integration created from master');
  const validation = useMutation({ mutationFn: () => integrationMasterApi.validateForCompile(draft.id) });
  const preview = useMutation({ mutationFn: () => integrationMasterApi.compilePreview(draft.id) });
  const compile = useMutation({ mutationFn: () => integrationMasterApi.compileDraft(draft.id, { enabled, create_saved_test_case: createSavedTestCase, comment: comment || null }) });
  const summary = useMemo(() => buildSummary(draft), [draft]);

  if (compile.data) return <CompileSuccessPanel result={compile.data} />;

  return (
    <section className="wizard-step integration-master-step compile-integration-step">
      <span className="step-index">11</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Step 5A</span>
          <h2>Шаг 5 — Создание интеграции</h2>
          <p>Проверяем draft и создаём реальные OMH objects: endpoint, route, integration flow, workflow и saved test case.</p>
        </div>
        <Link className="primary-link" to="/docs/onec/academy/create-real-integration-from-master">Инструкция</Link>
      </div>
      <section className="panel stack-form compile-summary-panel">
        <div className="panel-toolbar"><div><span className="eyebrow">Summary</span><h3>{draft.name}</h3><p className="microcopy">Endpoint: POST {draft.endpoint_url}</p></div></div>
        <ol className="compile-summary-list">{summary.map((item) => <li key={item}>{item}</li>)}</ol>
      </section>
      <div className="odata-step-panels">
        <CompileValidationPanel validation={validation.data} error={validation.error instanceof Error ? validation.error.message : null} loading={validation.isPending} onValidate={() => validation.mutate()} />
        <CompilePreviewPanel preview={preview.data} error={preview.error instanceof Error ? preview.error.message : null} loading={preview.isPending} onPreview={() => preview.mutate()} />
        <CompileActions enabled={enabled} createSavedTestCase={createSavedTestCase} comment={comment} loading={compile.isPending} error={compile.error instanceof Error ? compile.error.message : null} onEnabledChange={setEnabled} onCreateSavedTestCaseChange={setCreateSavedTestCase} onCommentChange={setComment} onCompile={() => compile.mutate()} />
      </div>
    </section>
  );
}

function buildSummary(draft: InputDraftRead) {
  const items = [`Принимает ${draft.input_mode.toUpperCase()} от ${draft.source_system}.`];
  for (const step of draft.odata_steps) {
    if (!step.type || step.type === 'odata_query') items.push(`Ищет данные в 1C OData и сохраняет ${step.save_as}.`);
    else if (step.type === 'odata_object_query') items.push(`Читает табличную часть и сохраняет массив ${step.save_as}.`);
    else if (step.type === 'foreach_odata') items.push(`По массиву ${step.items} выполняет OData lookup и сохраняет ${step.save_as}.`);
    else if (step.type === 'build_payload') items.push(`Собирает ${step.body_type} payload в ${step.save_as}.`);
  }
  if (draft.final_action?.type === 'send_endpoint') items.push('Отправляет результат во внешний endpoint и возвращает ответ caller-у.');
  else if (draft.final_action?.type === 'send_and_return_response') items.push('Отправляет результат во внешний endpoint и проксирует response caller-у.');
  else if (draft.final_action?.type === 'return_response') items.push('Возвращает собранный payload вызывающей системе.');
  else if (draft.final_action?.type === 'accepted_event') items.push('Возвращает async accepted response с event_id.');
  return items;
}
