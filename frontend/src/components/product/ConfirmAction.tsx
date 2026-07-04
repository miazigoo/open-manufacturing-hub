import { useState } from 'react';

interface ConfirmActionProps {
  label: string;
  confirmLabel?: string;
  onConfirm: () => void;
  className?: string;
}

export function ConfirmAction({ label, confirmLabel = 'Confirm', onConfirm, className = 'ghost-button danger' }: ConfirmActionProps) {
  const [armed, setArmed] = useState(false);
  return (
    <button
      type="button"
      className={className}
      onClick={() => {
        if (!armed) {
          setArmed(true);
          window.setTimeout(() => setArmed(false), 2200);
          return;
        }
        setArmed(false);
        onConfirm();
      }}
    >
      {armed ? confirmLabel : label}
    </button>
  );
}
