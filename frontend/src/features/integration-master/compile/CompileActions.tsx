interface CompileActionsProps {
  enabled: boolean;
  createSavedTestCase: boolean;
  comment: string;
  loading: boolean;
  error?: string | null;
  onEnabledChange: (enabled: boolean) => void;
  onCreateSavedTestCaseChange: (enabled: boolean) => void;
  onCommentChange: (comment: string) => void;
  onCompile: () => void;
}

export function CompileActions({ enabled, createSavedTestCase, comment, loading, error, onEnabledChange, onCreateSavedTestCaseChange, onCommentChange, onCompile }: CompileActionsProps) {
  return (
    <section className="panel stack-form compile-actions-panel">
      <div className="panel-toolbar"><div><span className="eyebrow">Create</span><h3>Создать интеграцию</h3><p className="microcopy">По умолчанию новая интеграция disabled, чтобы сначала выполнить тест.</p></div></div>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label checkbox-label"><input type="checkbox" checked={enabled} onChange={(event) => onEnabledChange(event.target.checked)} /> Включить сразу</label>
        <label className="field-label checkbox-label"><input type="checkbox" checked={createSavedTestCase} onChange={(event) => onCreateSavedTestCaseChange(event.target.checked)} /> Создать saved test case</label>
      </div>
      <label className="field-label">Комментарий<input value={comment} placeholder="Initial integration created from master" onChange={(event) => onCommentChange(event.target.value)} /></label>
      {enabled ? <div className="status-card warning"><strong>Endpoint включится сразу</strong><span>Используйте это только если dry-run уже проверен.</span></div> : <div className="status-card neutral"><strong>Рекомендовано</strong><span>Интеграция будет создана выключенной. После теста включите её отдельной кнопкой.</span></div>}
      {error ? <div className="status-card danger"><strong>Compile failed</strong><span>{error}</span></div> : null}
      <div className="action-row wrap-actions"><button type="button" className="primary-button" disabled={loading} onClick={onCompile}>{loading ? 'Создаю...' : 'Создать интеграцию'}</button></div>
    </section>
  );
}
