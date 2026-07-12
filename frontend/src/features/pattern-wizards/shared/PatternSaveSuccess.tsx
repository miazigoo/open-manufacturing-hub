import { Link } from 'react-router-dom';

interface PatternSaveSuccessProps {
  title?: string;
  endpointUrl?: string | null;
  timelineUrl?: string | null;
  detailUrl?: string | null;
}

export function PatternSaveSuccess({ title = 'Интеграция создана disabled', endpointUrl, timelineUrl, detailUrl }: PatternSaveSuccessProps) {
  return (
    <section className="panel pattern-save-success">
      <div className="status-card success">
        <strong>{title}</strong>
        <span>{endpointUrl ?? 'Проверьте тестовый запуск перед production enable.'}</span>
      </div>
      <div className="action-row wrap-actions">
        {detailUrl ? <Link className="primary-link" to={detailUrl}>Открыть интеграцию</Link> : null}
        {timelineUrl ? <Link className="primary-link" to={timelineUrl}>Открыть Timeline</Link> : null}
      </div>
    </section>
  );
}
