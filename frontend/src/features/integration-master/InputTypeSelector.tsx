import type { InputMode } from './types';

interface InputTypeSelectorProps { value: InputMode; allowed: InputMode[]; onChange: (value: InputMode) => void }

const inputModeCopy: Record<InputMode, { title: string; description: string }> = {
  json: { title: 'JSON', description: 'Выберите JSON, если вызывающая система отправляет структуру вида {"operation": "..."}.' },
  xml: { title: 'XML', description: 'Выберите XML, если 1С или другой сервис отправляет XML-документ.' },
  raw_text: { title: 'Raw text', description: 'Выберите raw text, если приходит обычная строка, CSV или другой текстовый формат.' },
};

export function InputTypeSelector({ value, allowed, onChange }: InputTypeSelectorProps) {
  const modes: InputMode[] = ['json', 'xml', 'raw_text'];
  return (
    <div className="metadata-grid compact-grid no-margin">
      {modes.map((mode) => {
        const disabled = allowed.length > 0 && !allowed.includes(mode);
        return (
          <button key={mode} type="button" className={`builder-help-card input-mode-card ${value === mode ? 'active' : ''}`} disabled={disabled} onClick={() => onChange(mode)}>
            <strong>{inputModeCopy[mode].title}</strong>
            <span>{inputModeCopy[mode].description}</span>
            {disabled ? <small>Не рекомендуется для выбранного сценария</small> : null}
          </button>
        );
      })}
    </div>
  );
}
