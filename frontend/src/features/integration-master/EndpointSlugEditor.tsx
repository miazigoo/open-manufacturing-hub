interface EndpointSlugEditorProps { value: string; onChange: (value: string) => void }

export function EndpointSlugEditor({ value, onChange }: EndpointSlugEditorProps) {
  const error = slugError(value);
  return (
    <div className="metadata-grid compact-grid no-margin">
      <label className="field-label">Endpoint slug<input value={value} onChange={(event) => onChange(slugify(event.target.value))} placeholder="dnp_sinc_pull_codes" /></label>
      <span className={error ? 'error-state compact' : 'success-note'}>{error ? 'Ошибка slug' : 'Endpoint preview'}<span>{error || `POST /api/bus/in/${value || 'slug'}`}</span></span>
      <span className="builder-help-card"><strong>Правило</strong><span>lowercase letters, numbers, dash и underscore. Без пробелов и спецсимволов.</span></span>
    </div>
  );
}

export function slugify(value: string) {
  return value.toLowerCase().trim().replace(/[^a-z0-9_-]+/g, '_').replace(/^[_-]+|[_-]+$/g, '');
}

export function slugError(value: string) {
  if (!value) return 'Введите endpoint slug.';
  if (!/^[a-z0-9](?:[a-z0-9_-]{0,158}[a-z0-9])?$/.test(value)) return 'Slug должен начинаться и заканчиваться буквой или цифрой и содержать только a-z, 0-9, - или _.';
  return null;
}
