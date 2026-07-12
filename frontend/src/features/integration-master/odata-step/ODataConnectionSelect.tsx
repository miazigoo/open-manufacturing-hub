import { Link } from 'react-router-dom';
import type { ODataConnectionOption } from '../../../api/odataConnections';

interface ODataConnectionSelectProps {
  value?: string | null;
  options: ODataConnectionOption[];
  loading: boolean;
  error?: unknown;
  onChange: (connectionId: string | null, connectionName?: string | null) => void;
}

export function ODataConnectionSelect({ value, options, loading, error, onChange }: ODataConnectionSelectProps) {
  if (error) {
    const message = error instanceof Error ? error.message : 'Не удалось загрузить OData-подключения.';
    return <div className="error-state compact"><strong>OData connections недоступны</strong><span>{message}</span></div>;
  }

  if (!loading && options.length === 0) {
    return (
      <div className="empty-state compact odata-empty-state">
        <h3>Нет OData-подключений</h3>
        <p>Создайте профиль подключения к 1C OData, затем вернитесь в мастер и выберите его для запроса.</p>
        <div className="action-row wrap-actions"><Link className="primary-button" to="/connection-center">Создать подключение</Link><Link className="ghost-button" to="/docs/onec/academy/create-connection-profiles">Открыть урок</Link></div>
      </div>
    );
  }

  return (
    <label className="field-label">OData connection
      <select value={value ?? ''} disabled={loading} onChange={(event) => {
        const option = options.find((item) => item.id === event.target.value);
        onChange(event.target.value || null, option?.label ?? null);
      }}>
        <option value="">Выберите подключение к 1C OData</option>
        {options.map((option) => <option key={option.id} value={option.id}>{option.label} · {option.base_url}</option>)}
      </select>
      <small>{loading ? 'Загружаю подключения...' : 'Используется профиль из Connection Center. Disabled-профили скрыты, пароли не попадают в draft.'}</small>
    </label>
  );
}
