import { KeyboardEvent, useMemo, useRef } from 'react';
import { highlightCode, normalizeLanguage } from './codeSyntax';

interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  language?: string;
  minRows?: number;
  placeholder?: string;
  title?: string;
  className?: string;
  spellCheck?: boolean;
}

const pairs: Record<string, string> = { '{': '}', '[': ']', '(': ')', '"': '"', "'": "'" };
const closing = new Set(Object.values(pairs));

export function CodeEditor({ value, onChange, language = 'json', minRows = 8, placeholder, title, className = '', spellCheck = false }: CodeEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const highlightRef = useRef<HTMLPreElement | null>(null);
  const normalized = normalizeLanguage(language);
  const highlighted = useMemo(() => highlightCode(value || placeholder || '', normalized), [value, placeholder, normalized]);
  const invalidJson = normalized === 'json' && value.trim().length > 0 ? getJsonError(value) : null;

  function replaceSelection(nextText: string, cursorOffset = nextText.length) {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const next = `${value.slice(0, start)}${nextText}${value.slice(end)}`;
    onChange(next);
    requestAnimationFrame(() => {
      textarea.selectionStart = start + cursorOffset;
      textarea.selectionEnd = start + cursorOffset;
      textarea.focus();
    });
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    const textarea = event.currentTarget;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = value.slice(start, end);

    if (event.key === 'Tab') {
      event.preventDefault();
      replaceSelection('  ');
      return;
    }

    if (event.key === 'Enter') {
      const before = value.slice(0, start);
      const after = value.slice(end);
      const indent = before.match(/(^|\n)([ \t]*)[^\n]*$/)?.[2] ?? '';
      const previous = before.trimEnd().at(-1);
      const next = after.trimStart().at(0);
      if ((previous === '{' && next === '}') || (previous === '[' && next === ']')) {
        event.preventDefault();
        replaceSelection(`\n${indent}  \n${indent}`, indent.length + 3);
      }
      return;
    }

    if (pairs[event.key]) {
      if ((event.key === '"' || event.key === "'") && value[start - 1] === '\\') return;
      event.preventDefault();
      replaceSelection(`${event.key}${selected}${pairs[event.key]}`, selected ? selected.length + 2 : 1);
      return;
    }

    if (closing.has(event.key) && value[start] === event.key && start === end) {
      event.preventDefault();
      textarea.selectionStart = start + 1;
      textarea.selectionEnd = start + 1;
    }
  }

  return (
    <div className={`code-editor-shell code-language-${normalized} ${className}`}>
      <div className="code-editor-head">
        <span>{normalized}</span>
        <span>{invalidJson ? invalidJson : 'syntax highlight · auto-close pairs · Tab indent'}</span>
      </div>
      <div className="code-editor-frame" style={{ minHeight: `${minRows * 22 + 28}px` }}>
        <pre ref={highlightRef} aria-hidden="true" className={`code-editor-highlight ${value ? '' : 'placeholder'}`}><code>{highlighted}</code></pre>
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          onScroll={(event) => {
            if (!highlightRef.current) return;
            highlightRef.current.scrollTop = event.currentTarget.scrollTop;
            highlightRef.current.scrollLeft = event.currentTarget.scrollLeft;
          }}
          placeholder={placeholder}
          spellCheck={spellCheck}
          title={title}
        />
      </div>
    </div>
  );
}

function getJsonError(value: string) {
  try {
    JSON.parse(value);
    return null;
  } catch (error) {
    return error instanceof Error ? error.message : 'Invalid JSON';
  }
}
