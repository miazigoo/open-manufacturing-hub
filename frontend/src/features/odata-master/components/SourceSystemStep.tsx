import type { ODataConnection } from '../../../api/odataConnections';

interface SourceSystemStepProps { connections: ODataConnection[]; selected: string; onSelect: (name: string) => void }

export function SourceSystemStep({ connections, selected, onSelect }: SourceSystemStepProps) {
  return (
    <section className="panel form-panel">
      <div className="panel-toolbar">
        <div>
          <span className="eyebrow">OData connection</span>
          <h2>Где искать данные в 1C OData?</h2>
          <p className="microcopy">Выберите именованное подключение. В flow сохраняется имя подключения, credentials остаются в профиле.</p>
        </div>
      </div>
      <label className="field-label">OData connection<select value={selected} onChange={(event) => onSelect(event.target.value)}><option value="">Выберите подключение</option>{connections.map((connection) => <option key={connection.id} value={connection.name}>{connection.name} · {connection.base_url}</option>)}</select></label>
      {connections.length === 0 && <div className="success-note">Нет активных OData подключений<span>Создайте профиль на странице OData Connections, затем вернитесь в мастер.</span></div>}
    </section>
  );
}
