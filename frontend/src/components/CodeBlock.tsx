import { useMemo } from 'react';
import { CopyButton } from './product/CopyButton';
import { highlightCode, normalizeLanguage } from './codeSyntax';

interface CodeBlockProps {
  code: string;
  language?: string;
  title?: string;
  copyLabel?: string;
  copiedLabel?: string;
  failedLabel?: string;
  searchable?: boolean;
  showToolbar?: boolean;
}

export function CodeBlock({ code, language = 'text', title, copyLabel = 'Copy', copiedLabel = 'Copied', failedLabel = 'Copy unavailable', showToolbar = true }: CodeBlockProps) {
  const normalized = normalizeLanguage(language);
  const highlighted = useMemo(() => highlightCode(code, normalized), [code, normalized]);
  const lines = code.split('\n').length;

  return (
    <div className={`code-panel code-language-${normalized}`}>
      {showToolbar && <div className="code-toolbar">
        <div>
          {title && <h3>{title}</h3>}
          <span>{normalized}</span>
        </div>
        <div className="toolbar-actions">
          <span className="microcopy">{lines.toLocaleString()} lines</span>
          <CopyButton value={code} label={copyLabel} copiedLabel={copiedLabel} failedLabel={failedLabel} />
        </div>
      </div>}
      <pre className="code-block"><code>{highlighted}</code></pre>
    </div>
  );
}
