import { JsonBlock } from '../../../components/JsonBlock';
import type { ODataMasterPreviewResponse } from '../types';

interface IntegrationPreviewProps { preview?: ODataMasterPreviewResponse; error?: Error | null; pending?: boolean }

export function IntegrationPreview({ preview, error, pending }: IntegrationPreviewProps) {
  if (pending) return <div className="success-note">Проверка выполняется<span>OMH компилирует мастер и строит preview запросов/ответов.</span></div>;
  if (error) return <div className="error-state compact">{error.message}</div>;
  if (!preview) return <div className="success-note">Проверка ещё не запускалась<span>Нажмите “Проверить интеграцию”, чтобы увидеть вход, OData-запросы, endpoint request и ответ вызывающему.</span></div>;
  const steps = Array.isArray(preview.preview.steps) ? preview.preview.steps as Array<Record<string, unknown>> : [];
  return (
    <section className="panel form-panel">
      <div className="panel-toolbar">
        <div>
          <span className="eyebrow">Проверка</span>
          <h2>{preview.preview.valid ? 'Preview без ошибок' : 'Preview требует внимания'}</h2>
          <p className="microcopy">Ниже показан человеческий путь интеграции. Raw builder JSON скрыт в advanced details.</p>
        </div>
      </div>
      <div className="stack-form">
        {steps.map((step) => (
          <div className={`success-note ${step.status === 'failed' ? 'error-state compact' : ''}`} key={String(step.id)}>
            <strong>{String(step.name || step.id)} · {String(step.type)}</strong>
            <span>Статус: {String(step.status)}</span>
            {step.request_preview ? <JsonBlock title="Что OMH запросит" value={step.request_preview} searchable={false} /> : null}
            {step.result_preview ? <JsonBlock title="Что OMH получил/собрал" value={step.result_preview} searchable={false} /> : null}
            {step.error ? <JsonBlock title="Ошибка" value={step.error} searchable={false} /> : null}
          </div>
        ))}
        {preview.preview.target_request_preview ? <JsonBlock title="Outgoing endpoint request" value={preview.preview.target_request_preview} searchable={false} /> : null}
        <details className="variable-card">
          <summary><span>Advanced details</span><strong>builder_json</strong></summary>
          <JsonBlock title="Raw builder JSON" value={preview.builder_json} searchable />
        </details>
      </div>
    </section>
  );
}
