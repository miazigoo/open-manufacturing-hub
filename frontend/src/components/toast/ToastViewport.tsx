import { useSyncExternalStore } from 'react';
import { useT } from '../../i18n/useI18n';
import { dismissToast, getToasts, subscribeToasts } from './toastStore';

const toneIcon: Record<string, string> = {
  success: '✓',
  error: '!',
  info: 'i',
};

export function ToastViewport() {
  const t = useT();
  const toasts = useSyncExternalStore(subscribeToasts, getToasts, getToasts);
  if (!toasts.length) return null;
  return (
    <div className="toast-viewport" role="region" aria-label={t('common.toast.region')} aria-live="polite">
      {toasts.map((item) => (
        <div key={item.id} className={`toast toast-${item.tone}`} role={item.tone === 'error' ? 'alert' : 'status'}>
          <span className="toast-mark" aria-hidden="true">{toneIcon[item.tone] ?? 'i'}</span>
          <span className="toast-message">{item.message}</span>
          <button type="button" className="toast-dismiss" aria-label={t('common.toast.dismiss')} onClick={() => dismissToast(item.id)}>×</button>
        </div>
      ))}
    </div>
  );
}
