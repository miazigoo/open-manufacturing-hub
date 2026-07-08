import { ReactNode, useEffect } from 'react';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  cancelLabel?: string;
  tone?: 'warning' | 'danger';
  loading?: boolean;
  children?: ReactNode;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({ open, title, description, confirmLabel, cancelLabel = 'Отмена', tone = 'warning', loading = false, children, onConfirm, onCancel }: ConfirmDialogProps) {
  useEffect(() => {
    if (!open) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onCancel();
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div className="confirm-dialog-backdrop" role="presentation" onMouseDown={onCancel}>
      <section className={`confirm-dialog confirm-dialog-${tone}`} role="dialog" aria-modal="true" aria-labelledby="confirm-dialog-title" onMouseDown={(event) => event.stopPropagation()}>
        <div className="panel-toolbar">
          <div>
            <span className="eyebrow">{tone === 'danger' ? 'Danger action' : 'Confirmation'}</span>
            <h2 id="confirm-dialog-title">{title}</h2>
            <p className="microcopy">{description}</p>
          </div>
        </div>
        {children ? <div className="confirm-dialog-body">{children}</div> : null}
        <div className="action-row wrap-actions confirm-dialog-actions">
          <button type="button" className="ghost-button" disabled={loading} onClick={onCancel}>{cancelLabel}</button>
          <button type="button" className={tone === 'danger' ? 'primary-button danger-button' : 'primary-button'} disabled={loading} onClick={onConfirm}>{loading ? 'Выполняю...' : confirmLabel}</button>
        </div>
      </section>
    </div>
  );
}
