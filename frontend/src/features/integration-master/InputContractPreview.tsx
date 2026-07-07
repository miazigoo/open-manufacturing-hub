import { JsonBlock } from '../../components/JsonBlock';
import type { InputContract, InputContractValidationResponse, InputDraftSaveResponse } from './types';

interface InputContractPreviewProps {
  contract: InputContract;
  validation?: InputContractValidationResponse | null;
  saved?: InputDraftSaveResponse | null;
  error?: string | null;
  onValidate: () => void;
  onSave: () => void;
  validating: boolean;
  saving: boolean;
}

export function InputContractPreview({ contract, validation, saved, error, onValidate, onSave, validating, saving }: InputContractPreviewProps) {
  return (
    <section className="panel stack-form input-contract-preview">
      <div className="panel-toolbar">
        <div>
          <span className="eyebrow">Input Contract</span>
          <h2>Что будет сохранено для следующих шагов</h2>
          <p className="microcopy">Это не создаёт боевую интеграцию. Draft фиксирует входящий контракт первого шага.</p>
        </div>
        <div className="toolbar-actions"><button type="button" className="ghost-button" onClick={onValidate} disabled={validating}>{validating ? 'Проверяю...' : 'Проверить'}</button><button type="button" className="primary-button" onClick={onSave} disabled={saving}>{saving ? 'Сохраняю...' : 'Сохранить draft'}</button></div>
      </div>
      {validation ? <div className={validation.valid ? 'success-note' : 'error-state compact'}><strong>{validation.valid ? 'Контракт валиден' : 'Контракт требует правок'}</strong><span>{validation.valid ? validation.endpoint_url : validation.errors.join('; ')}</span></div> : null}
      {saved ? <div className="success-note"><strong>Draft сохранён</strong><span>{saved.draft.id} · {saved.draft.endpoint_url}</span></div> : null}
      {error ? <div className="error-state compact">{error}</div> : null}
      <JsonBlock value={contract} title="Input Contract JSON" searchable />
    </section>
  );
}
