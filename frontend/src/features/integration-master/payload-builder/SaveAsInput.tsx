interface SaveAsInputProps {
  value: string;
  overwrite: boolean;
  onChange: (value: string) => void;
  onOverwriteChange: (value: boolean) => void;
}

export function SaveAsInput({ value, overwrite, onChange, onOverwriteChange }: SaveAsInputProps) {
  return (
    <div className="metadata-grid compact-grid no-margin">
      <label className="field-label">Сохранить body как
        <input value={value} onChange={(event) => onChange(event.target.value)} placeholder="target_payload" />
        <small>Латиница, цифры и underscore. По умолчанию `target_payload`.</small>
      </label>
      <label className="check-row odata-check"><input type="checkbox" checked={overwrite} onChange={(event) => onOverwriteChange(event.target.checked)} /> Разрешить overwrite существующей переменной</label>
    </div>
  );
}
