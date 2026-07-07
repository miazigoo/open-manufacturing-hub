interface ODataSelectBuilderProps { value: string[]; onChange: (value: string[]) => void; placeholder?: string }

export function ODataSelectBuilder({ value, onChange, placeholder = 'Ref_Key,Number,Date,Posted' }: ODataSelectBuilderProps) {
  return (
    <label className="field-label">
      Что забрать из OData ($select)
      <input value={value.join(',')} onChange={(event) => onChange(event.target.value.split(',').map((item) => item.trim()).filter(Boolean))} placeholder={placeholder} />
      <span className="field-hint">Оставляйте только нужные поля, чтобы не грузить 1C и не засорять artifacts.</span>
    </label>
  );
}
