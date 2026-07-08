import type { CompilePreviewResponse } from '../types';
import { CompileAdvancedDetails } from './CompileAdvancedDetails';

interface CompilePreviewPanelProps {
  preview?: CompilePreviewResponse | null;
  error?: string | null;
  loading: boolean;
  onPreview: () => void;
}

export function CompilePreviewPanel({ preview, error, loading, onPreview }: CompilePreviewPanelProps) {
  return (
    <section className="panel stack-form compile-preview-panel">
      <div className="panel-toolbar">
        <div><span className="eyebrow">Preview</span><h3>Что будет создано</h3><p className="microcopy">Preview не пишет в БД. Он показывает endpoint, route, flow, workflow и saved test case.</p></div>
        <button type="button" className="primary-button" disabled={loading} onClick={onPreview}>{loading ? 'Собираю...' : 'Показать preview'}</button>
      </div>
      {error ? <div className="status-card danger"><strong>Preview request failed</strong><span>{error}</span></div> : null}
      {preview ? <PreviewBody preview={preview} /> : <p className="microcopy">Откройте preview перед созданием, чтобы проверить slug, matcher и количество шагов.</p>}
    </section>
  );
}

function PreviewBody({ preview }: { preview: CompilePreviewResponse }) {
  if (!preview.valid) {
    return <div className="status-card danger"><strong>Preview недоступен</strong><span>{preview.errors.map((item) => item.message).join('; ')}</span></div>;
  }
  const endpoint = readObject(preview.will_create.integration_endpoint);
  const route = readObject(preview.will_create.integration_route);
  const flow = readObject(preview.will_create.integration_flow);
  const workflow = readObject(preview.will_create.workflow);
  const testCase = readObject(preview.will_create.saved_test_case);
  return (
    <div className="stack-form">
      <div className="metadata-grid compact-grid no-margin">
        <PreviewCard title="Endpoint" value={`${endpoint.method ?? 'POST'} ${endpoint.url ?? endpoint.slug ?? ''}`} />
        <PreviewCard title="Route" value={String(route.matcher ?? 'matcher configured')} />
        <PreviewCard title="Integration Flow" value={`${flow.name ?? 'Flow'} · ${flow.steps_count ?? 0} steps`} />
        <PreviewCard title="Workflow" value={`${workflow.steps_count ?? 0} compiled steps`} />
        <PreviewCard title="Saved Test Case" value={String(testCase.name ?? 'will be created')} />
      </div>
      <CompileAdvancedDetails advanced={preview.advanced} />
    </div>
  );
}

function PreviewCard({ title, value }: { title: string; value: string }) {
  return <span className="status-card success"><small>Будет создано</small><strong>{title}</strong><code>{value}</code></span>;
}

function readObject(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? value as Record<string, unknown> : {};
}
