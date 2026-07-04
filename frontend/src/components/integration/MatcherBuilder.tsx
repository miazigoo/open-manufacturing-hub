interface MatcherBuilderProps {
  mode: string;
  matcherType: string;
  path: string;
  value: string;
  matcherTypes: string[];
  onChange: (patch: Partial<{ mode: string; matcherType: string; path: string; value: string }>) => void;
}

export function MatcherBuilder({ mode, matcherType, path, value, matcherTypes, onChange }: MatcherBuilderProps) {
  const types = matcherTypes.length > 0 ? matcherTypes : ['always', 'body_path_equals', 'body_path_exists', 'xml_contains', 'text_contains', 'regex'];
  return (
    <div className="integration-block matcher-block">
      <div className="panel-toolbar"><div><span className="eyebrow">Match</span><h3>When should this route run?</h3></div></div>
      <div className="form-grid form-grid-4">
        <label className="field-label">Mode<select value={mode} onChange={(event) => onChange({ mode: event.target.value })}><option value="all">All rules</option><option value="any">Any rule</option><option value="none">None</option></select></label>
        <label className="field-label">Rule<select value={matcherType} onChange={(event) => onChange({ matcherType: event.target.value })}>{types.map((type) => <option key={type} value={type}>{type.replaceAll('_', ' ')}</option>)}</select></label>
        <label className="field-label">Path<input value={path} onChange={(event) => onChange({ path: event.target.value })} placeholder="payload.inn" /></label>
        <label className="field-label">Value<input value={value} onChange={(event) => onChange({ value: event.target.value })} placeholder="DNP" /></label>
      </div>
    </div>
  );
}
