import { useState } from 'react';

interface CopyButtonProps {
  value: string;
  label?: string;
  copiedLabel?: string;
  className?: string;
}

export function CopyButton({ value, label = 'Copy', copiedLabel = 'Copied', className = 'ghost-button' }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    await navigator.clipboard?.writeText(value);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  }

  return <button type="button" className={className} onClick={copy}>{copied ? copiedLabel : label}</button>;
}
