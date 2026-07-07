import { Link } from 'react-router-dom';
import type { ODataMasterSaveResponse } from '../types';

interface IntegrationSaveSuccessProps { result?: ODataMasterSaveResponse }

export function IntegrationSaveSuccess({ result }: IntegrationSaveSuccessProps) {
  if (!result) return null;
  const flowId = typeof result.integration_flow.id === 'string' ? result.integration_flow.id : '';
  return (
    <section className="panel form-panel">
      <span className="eyebrow">Сохранение</span>
      <h2>Интеграция создана</h2>
      <div className="success-note">Endpoint<span>POST {result.endpoint_url}</span></div>
      <div className="metadata-grid compact-grid">
        {result.next_steps.map((step, index) => <div className="builder-help-card" key={step}><strong>{index + 1}. {step}</strong></div>)}
      </div>
      <div className="action-row wrap-actions">
        <button type="button" className="primary-button" onClick={() => navigator.clipboard?.writeText(result.endpoint_url)}>Скопировать endpoint</button>
        <Link className="primary-link" to="/events">Открыть Timeline</Link>
        {flowId && <Link className="primary-link" to={`/integration-flows/${flowId}/builder`}>Открыть детали интеграции</Link>}
      </div>
    </section>
  );
}
