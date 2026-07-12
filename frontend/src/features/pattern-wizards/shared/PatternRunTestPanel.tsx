import type { ReactNode } from 'react';

interface PatternRunTestPanelProps {
  title?: string;
  description?: string;
  disabled?: boolean;
  loading?: boolean;
  onRun?: () => void;
  children?: ReactNode;
}

export function PatternRunTestPanel({ title = 'Тестовый запуск', description, disabled, loading, onRun, children }: PatternRunTestPanelProps) {
  return (
    <section className="panel pattern-run-test-panel">
      <div className="panel-toolbar">
        <div><span className="eyebrow">Run test</span><h3>{title}</h3>{description ? <p className="microcopy">{description}</p> : null}</div>
        {onRun ? <button type="button" className="primary-button" disabled={disabled || loading} onClick={onRun}>{loading ? 'Проверяю...' : 'Запустить тест'}</button> : null}
      </div>
      {children}
    </section>
  );
}
