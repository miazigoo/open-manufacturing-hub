import type { ODataWizardStep } from '../types';

interface WizardStepSummaryProps { steps: ODataWizardStep[]; onEdit?: (index: number) => void; onRemove?: (index: number) => void }

export function WizardStepSummary({ steps, onEdit, onRemove }: WizardStepSummaryProps) {
  if (!steps.length) return <div className="success-note">OData-шагов пока нет<span>Добавьте поиск заказа, чтение табличной части или foreach по массиву.</span></div>;
  return (
    <div className="stack-form">
      {steps.map((step, index) => (
        <div className="success-note draft-step-card" key={`${step.type}:${step.save_as}:${index}`}>
          <strong>{index + 1}. {title(step)}</strong>
          <span><code>{step.save_as}</code> · {step.type} · top {step.top || 100}{step.paginate ? ' · pagination' : ''}</span>
          <span>{resource(step)}</span>
          {'filter' in step && step.filter && <span>$filter: {step.filter}</span>}
          <div className="action-row wrap-actions">
            {onEdit && <button type="button" className="ghost-button" onClick={() => onEdit(index)}>Изменить</button>}
            {onRemove && <button type="button" className="ghost-button danger" onClick={() => onRemove(index)}>Удалить</button>}
          </div>
        </div>
      ))}
    </div>
  );
}

function title(step: ODataWizardStep) {
  if (step.name) return step.name;
  if (step.type === 'foreach_odata') return `Повторить OData по ${step.items}`;
  if (step.type === 'odata_object_query') return `Табличная часть ${step.tabular_part || ''}`;
  return `OData ${step.resource}`;
}

function resource(step: ODataWizardStep) {
  if (step.type === 'odata_object_query') return `${step.base_resource}(guid'{{${step.object_key}}}')/${step.tabular_part || ''}`;
  return step.resource;
}
