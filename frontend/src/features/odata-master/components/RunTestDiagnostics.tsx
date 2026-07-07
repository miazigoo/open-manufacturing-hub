import { Link } from 'react-router-dom';
import { JsonBlock } from '../../../components/JsonBlock';
import type { ODataMasterRunTestResponse } from '../types';

interface RunTestDiagnosticsProps { result?: ODataMasterRunTestResponse }

export function RunTestDiagnostics({ result }: RunTestDiagnosticsProps) {
  if (!result) return null;
  const diagnostics = result.diagnostics;
  return (
    <section className="panel form-panel">
      <div className="panel-toolbar">
        <div>
          <span className="eyebrow">Run test</span>
          <h2>{diagnostics?.timeline_url ? 'Тест создал событие в Timeline' : 'Preview без Timeline'}</h2>
          <p className="microcopy">Откройте artifacts из checklist, чтобы понять, что OMH отправил, получил и вернул вызывающему.</p>
        </div>
        <div className="toolbar-actions">
          {diagnostics?.timeline_url ? <Link className="primary-link" to={diagnostics.timeline_url}>Открыть Timeline</Link> : null}
        </div>
      </div>
      {diagnostics ? (
        <div className="stack-form">
          <div className="metadata-grid compact-grid no-margin">
            <div className="builder-help-card"><strong>Status</strong><span>{diagnostics.status || 'unknown'}</span></div>
            {diagnostics.event_id ? <div className="builder-help-card"><strong>Event ID</strong><span>{diagnostics.event_id}</span></div> : null}
          </div>
          <div className="metadata-grid compact-grid">
            {diagnostics.artifact_checklist.map((item) => (
              <div className="builder-help-card" key={item.step_id}>
                <strong>{item.step_name}</strong>
                <span>{item.step_type}</span>
                <small>{item.artifacts.join(', ')}</small>
              </div>
            ))}
          </div>
          <div className="success-note">
            <strong>Следующие действия</strong>
            <span>{diagnostics.next_actions.join(' ')}</span>
          </div>
        </div>
      ) : null}
      <details className="variable-card">
        <summary><span>Raw result</span><strong>JSON</strong></summary>
        <JsonBlock title="Run test result" value={result.result} searchable />
      </details>
    </section>
  );
}
