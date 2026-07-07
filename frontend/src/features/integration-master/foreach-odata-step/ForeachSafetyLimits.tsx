import type { ForeachODataSafetyLimits } from '../types';

interface ForeachSafetyLimitsProps {
  value: ForeachODataSafetyLimits;
  testLimit?: number | null;
  onChange: (value: ForeachODataSafetyLimits) => void;
  onTestLimitChange: (value: number | null) => void;
}

export function ForeachSafetyLimits({ value, testLimit, onChange, onTestLimitChange }: ForeachSafetyLimitsProps) {
  function patch(patchValue: Partial<ForeachODataSafetyLimits>) {
    onChange({ ...value, ...patchValue });
  }

  return (
    <section className="panel stack-form foreach-safety-limits">
      <div><span className="eyebrow">Safety limits</span><h3>Защита от случайного массового запроса</h3><p className="microcopy">Foreach может сделать много OData-вызовов. Лимиты сохраняются в draft и проверяются перед тестом.</p></div>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">max_items<input type="number" min="1" value={value.max_items} onChange={(event) => patch({ max_items: Number(event.target.value || 0) })} /></label>
        <label className="field-label">max_requests<input type="number" min="1" value={value.max_requests} onChange={(event) => patch({ max_requests: Number(event.target.value || 0) })} /></label>
        <label className="field-label">max_result_rows<input type="number" min="1" value={value.max_result_rows} onChange={(event) => patch({ max_result_rows: Number(event.target.value || 0) })} /></label>
        <label className="field-label">test_limit<input type="number" min="1" value={testLimit ?? ''} onChange={(event) => onTestLimitChange(event.target.value ? Number(event.target.value) : null)} /><small>Пусто = проверить весь массив в рамках safety limits.</small></label>
      </div>
    </section>
  );
}
