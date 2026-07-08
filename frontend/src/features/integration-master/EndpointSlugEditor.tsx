interface EndpointSlugEditorProps { value: string; onChange: (value: string) => void }

export function EndpointSlugEditor({ value, onChange }: EndpointSlugEditorProps) {
  const error = slugError(value);
  return (
    <div className="endpoint-slug-editor">
      <label className="field-label">Endpoint slug
        <input value={value} onChange={(event) => onChange(slugInput(event.target.value))} onBlur={() => onChange(slugify(value))} placeholder="sync_codes_20260708_ab12" />
        <small>Это техническое имя входящего endpoint. Внешняя система будет отправлять запрос на этот URL.</small>
      </label>
      <span className={error ? 'error-state compact' : 'success-note'}>
        {error ? 'Ошибка slug' : 'Endpoint preview'}
        <span>{error || `POST /api/bus/in/${value || 'slug'}`}</span>
      </span>
      <span className="builder-help-card">
        <strong>Зачем он нужен</strong>
        <span>Slug становится частью URL и должен быть уникальным. OMH генерирует суффикс, чтобы не пересечься с другими интеграциями, но оператор может заменить его на понятное имя. Разрешены a-z, 0-9, дефис и underscore.</span>
      </span>
    </div>
  );
}

export function suggestedSlug(value: string) {
  const base = slugify(value || 'integration') || 'integration';
  const now = new Date();
  const stamp = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, '0'),
    String(now.getDate()).padStart(2, '0'),
    String(now.getHours()).padStart(2, '0'),
    String(now.getMinutes()).padStart(2, '0'),
    String(now.getSeconds()).padStart(2, '0'),
  ].join('');
  return `${base}_${stamp}`.slice(0, 160).replace(/[_-]+$/g, '');
}

export function slugify(value: string) {
  return slugInput(value).replace(/^[_-]+|[_-]+$/g, '');
}

function slugInput(value: string) {
  return value.toLowerCase().trimStart().replace(/[^a-z0-9_-]+/g, '_').slice(0, 160);
}

export function slugError(value: string) {
  if (!value) return 'Введите endpoint slug.';
  if (!/^[a-z0-9](?:[a-z0-9_-]{0,158}[a-z0-9])?$/.test(value)) return 'Slug должен начинаться и заканчиваться буквой или цифрой и содержать только a-z, 0-9, - или _.';
  return null;
}
