interface AvailableVariablesPanelProps {
  variables: Record<string, unknown>;
  onInsert: (path: string) => void;
}

const FRIENDLY_PATHS = [
  ['Request body', ['request.body.order_id', 'request.body.order_name', 'request.body.Number']],
  ['Order', ['order.Ref_Key', 'order.Number', 'order.Date']],
  ['Products', ['products[]', 'products[0].Номенклатура_Key']],
  ['Codes', ['codes[]', 'codes.length', 'codes[0].ПолныйКодМаркировки', 'codes[0].ДокументОснование', 'codes[0].Номенклатура_Key', 'codes[0].Статус']],
  ['Context', ['context.run_id', 'context.event_id']],
] as const;

export function AvailableVariablesPanel({ variables, onInsert }: AvailableVariablesPanelProps) {
  const discovered = discoverPaths(variables);
  return (
    <section className="panel stack-form">
      <div className="panel-toolbar"><div><span className="eyebrow">Variables</span><h3>Доступные переменные</h3><p className="microcopy">{'Вставляйте путь как {{path}}. Точный JSON placeholder сохраняет массивы и объекты.'}</p></div></div>
      <div className="metadata-grid compact-grid no-margin">
        {FRIENDLY_PATHS.map(([group, paths]) => (
          <div key={group} className="status-card neutral">
            <strong>{group}</strong>
            <div className="chip-row">
      {paths.map((path) => <VariableChip key={path} path={path} available={isAvailable(path, variables)} onInsert={onInsert} />)}
            </div>
          </div>
        ))}
      </div>
      {discovered.length ? <details><summary>Все найденные пути</summary><div className="chip-row">{discovered.map((path) => <VariableChip key={path} path={path} available onInsert={onInsert} />)}</div></details> : null}
    </section>
  );
}

function VariableChip({ path, available, onInsert }: { path: string; available: boolean; onInsert: (path: string) => void }) {
  async function copyPath() {
    try {
      await navigator.clipboard?.writeText(path);
    } catch {
      // Clipboard may be unavailable in non-secure local contexts.
    }
  }

  return (
    <span className={`pill ${available ? 'success' : 'muted'}`}>
      <code>{path}</code>
      {available ? <button type="button" className="link-button" onClick={() => onInsert(path)}>insert</button> : <small>нет в sample</small>}
      <button type="button" className="link-button" onClick={copyPath}>copy</button>
    </span>
  );
}

function isAvailable(path: string, variables: Record<string, unknown>) {
  if (path.endsWith('[]')) return Array.isArray(resolvePath(variables, path.slice(0, -2)));
  if (path.endsWith('.length')) {
    const value = resolvePath(variables, path.slice(0, -7));
    return Array.isArray(value) || typeof value === 'string';
  }
  return resolvePath(variables, path) !== undefined;
}

function resolvePath(root: unknown, path: string) {
  const parts = path.replace(/\[(\d+)\]/g, '.$1').split('.').filter(Boolean);
  let current: unknown = root;
  for (const part of parts) {
    if (Array.isArray(current) && /^\d+$/.test(part)) current = current[Number(part)];
    else if (current && typeof current === 'object' && part in current) current = (current as Record<string, unknown>)[part];
    else return undefined;
  }
  return current;
}

function discoverPaths(variables: Record<string, unknown>) {
  const paths: string[] = [];
  for (const [key, value] of Object.entries(variables)) collect(key, value, paths, 0);
  return Array.from(new Set(paths)).slice(0, 80);
}

function collect(prefix: string, value: unknown, paths: string[], depth: number) {
  if (depth > 3) return;
  if (Array.isArray(value)) {
    paths.push(`${prefix}[]`);
    paths.push(`${prefix}.length`);
    if (value[0] && typeof value[0] === 'object') {
      for (const key of Object.keys(value[0] as Record<string, unknown>).slice(0, 8)) collect(`${prefix}[0].${key}`, (value[0] as Record<string, unknown>)[key], paths, depth + 1);
    }
    return;
  }
  paths.push(prefix);
  if (value && typeof value === 'object') {
    for (const [key, item] of Object.entries(value as Record<string, unknown>).slice(0, 10)) collect(`${prefix}.${key}`, item, paths, depth + 1);
  }
}
