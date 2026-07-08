import type { CompileDraftValidationResponse, CompileIssue } from '../types';

interface CompileValidationPanelProps {
  validation?: CompileDraftValidationResponse | null;
  error?: string | null;
  loading: boolean;
  onValidate: () => void;
}

export function CompileValidationPanel({ validation, error, loading, onValidate }: CompileValidationPanelProps) {
  return (
    <section className="panel stack-form compile-validation-panel">
      <div className="panel-toolbar">
        <div><span className="eyebrow">Validation</span><h3>Проверить перед созданием</h3><p className="microcopy">Проверяем контракт, OData-зависимости, payload, final action и builder_json.</p></div>
        <button type="button" className="primary-button" disabled={loading} onClick={onValidate}>{loading ? 'Проверяю...' : 'Проверить'}</button>
      </div>
      {error ? <div className="status-card danger"><strong>Validation request failed</strong><span>{error}</span></div> : null}
      {validation ? <ValidationResult validation={validation} /> : <p className="microcopy">Нажмите проверку, чтобы увидеть blockers до создания endpoint.</p>}
    </section>
  );
}

function ValidationResult({ validation }: { validation: CompileDraftValidationResponse }) {
  return (
    <div className="stack-form">
      <div className={`status-card ${validation.valid ? 'success' : 'danger'}`}><strong>{validation.valid ? 'Draft готов к созданию' : 'Нужно исправить ошибки'}</strong><span>{validation.valid ? 'Можно открыть preview и создать интеграцию.' : `${validation.errors.length} error(s)`}</span></div>
      <IssueList title="Ошибки" issues={validation.errors} tone="danger" />
      <IssueList title="Предупреждения" issues={validation.warnings} tone="warning" />
    </div>
  );
}

function IssueList({ title, issues, tone }: { title: string; issues: CompileIssue[]; tone: 'danger' | 'warning' }) {
  if (!issues.length) return null;
  return <div className={`status-card ${tone}`}><strong>{title}</strong><span>{issues.map(issueText).join('; ')}</span></div>;
}

function issueText(issue: CompileIssue) {
  return `${issue.section}${issue.field ? `.${issue.field}` : ''}: ${issue.message}`;
}
