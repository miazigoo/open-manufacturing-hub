import { useState } from 'react';

interface CopyButtonProps {
  value: string;
  label?: string;
  copiedLabel?: string;
  failedLabel?: string;
  className?: string;
}

export function CopyButton({ value, label = 'Copy', copiedLabel = 'Copied', failedLabel = 'Copy unavailable', className = 'ghost-button' }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);

  async function copy() {
    const ok = await copyToClipboard(value);
    setFailed(!ok);
    setCopied(ok);
    window.setTimeout(() => {
      setCopied(false);
      setFailed(false);
    }, 1400);
  }

  return <button type="button" className={className} onClick={copy}>{copied ? copiedLabel : failed ? failedLabel : label}</button>;
}

async function copyToClipboard(value: string) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
      return true;
    }
  } catch {
    // Browser or headless test environments can deny clipboard access.
  }
  try {
    const textarea = document.createElement('textarea');
    textarea.value = value;
    textarea.setAttribute('readonly', 'true');
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    textarea.style.top = '0';
    document.body.appendChild(textarea);
    textarea.select();
    const ok = document.execCommand('copy');
    textarea.remove();
    return ok;
  } catch {
    return false;
  }
}
