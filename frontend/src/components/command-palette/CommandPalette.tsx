import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useT } from '../../i18n/useI18n';
import { groupKey, navModel } from '../../navigation/navModel';

interface CommandItem {
  id: string;
  route: string;
  title: string;
  group: string;
}

function isEditableTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target.isContentEditable;
}

export function CommandPalette() {
  const t = useT();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const items = useMemo<CommandItem[]>(() => {
    const seen = new Set<string>();
    return navModel
      .filter((item) => {
        if (seen.has(item.route)) return false;
        seen.add(item.route);
        return true;
      })
      .map((item) => ({
        id: item.id,
        route: item.route,
        title: item.titleKey ? t(item.titleKey) : item.title,
        group: t(groupKey[item.group] ?? item.group),
      }));
  }, [t]);

  const results = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return items;
    return items.filter((item) =>
      item.title.toLowerCase().includes(term) ||
      item.group.toLowerCase().includes(term) ||
      item.route.toLowerCase().includes(term),
    );
  }, [items, query]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setOpen((value) => !value);
        return;
      }
      if (event.key === '/' && !isEditableTarget(event.target) && !event.ctrlKey && !event.metaKey && !event.altKey) {
        event.preventDefault();
        setOpen(true);
      }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  useEffect(() => {
    if (open) {
      setQuery('');
      setActiveIndex(0);
      const frame = window.requestAnimationFrame(() => inputRef.current?.focus());
      return () => window.cancelAnimationFrame(frame);
    }
    return undefined;
  }, [open]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  if (!open) return null;

  function close() {
    setOpen(false);
  }

  function go(route: string) {
    close();
    navigate(route);
  }

  function onListKeyDown(event: React.KeyboardEvent) {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex((index) => Math.min(index + 1, Math.max(results.length - 1, 0)));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex((index) => Math.max(index - 1, 0));
    } else if (event.key === 'Enter') {
      event.preventDefault();
      const item = results[activeIndex];
      if (item) go(item.route);
    } else if (event.key === 'Escape') {
      event.preventDefault();
      close();
    }
  }

  return (
    <div className="command-palette-backdrop" role="presentation" onMouseDown={close}>
      <div
        className="command-palette"
        role="dialog"
        aria-modal="true"
        aria-label={t('navigation.commandPalette.title')}
        onMouseDown={(event) => event.stopPropagation()}
        onKeyDown={onListKeyDown}
      >
        <input
          ref={inputRef}
          className="command-palette-input"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={t('navigation.commandPalette.placeholder')}
          aria-label={t('navigation.commandPalette.placeholder')}
          type="text"
        />
        <div className="command-palette-list" role="listbox">
          {results.length === 0 ? (
            <div className="command-palette-empty">{t('navigation.commandPalette.empty')}</div>
          ) : (
            results.map((item, index) => (
              <button
                key={item.id}
                type="button"
                role="option"
                aria-selected={index === activeIndex}
                className={`command-palette-item ${index === activeIndex ? 'active' : ''}`}
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => go(item.route)}
              >
                <span className="command-palette-item-title">{item.title}</span>
                <span className="command-palette-item-group">{item.group}</span>
              </button>
            ))
          )}
        </div>
        <div className="command-palette-footer">
          <span>{t('navigation.commandPalette.footerNavigate')}</span>
          <span>{t('navigation.commandPalette.footerHint')}</span>
        </div>
      </div>
    </div>
  );
}
