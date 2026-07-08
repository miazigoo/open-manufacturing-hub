import { ReactNode } from 'react';
import { createPortal } from 'react-dom';

export interface ToastMessage {
  id: string;
  tone: 'success' | 'danger' | 'warning' | 'neutral';
  title: string;
  message?: ReactNode;
}

interface ToastStackProps {
  items: ToastMessage[];
  onClose: (id: string) => void;
}

export function ToastStack({ items, onClose }: ToastStackProps) {
  if (!items.length) return null;

  return createPortal(
    <div className="toast-stack" role="status" aria-live="polite">
      {items.map((item) => (
        <article key={item.id} className={`toast-message toast-${item.tone}`}>
          <div>
            <strong>{item.title}</strong>
            {item.message ? <span>{item.message}</span> : null}
          </div>
          <button type="button" className="toast-close" aria-label="Закрыть уведомление" onClick={() => onClose(item.id)}>×</button>
        </article>
      ))}
    </div>,
    document.body,
  );
}
