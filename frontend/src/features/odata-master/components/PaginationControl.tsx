interface PaginationControlProps { checked: boolean; top?: number | null; onChange: (checked: boolean) => void }

export function PaginationControl({ checked, top, onChange }: PaginationControlProps) {
  return (
    <label className="success-note check-row" title="Если 1C вернула полную страницу, OMH запросит следующую через $skip до max_pages подключения.">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      <strong>Загружать следующие страницы</strong>
      <span>$top - размер страницы, максимум 500. Сейчас: {top || 100}.</span>
    </label>
  );
}
