import type { ReactNode } from 'react';
import { useT } from '../../i18n/useI18n';
import type { SortState } from '../../hooks/useTableControls';

interface SearchToolbarProps {
  value: string;
  onChange: (value: string) => void;
  shown: number;
  total: number;
  isFiltered?: boolean;
  onReset?: () => void;
  placeholder?: string;
  children?: ReactNode;
}

export function SearchToolbar({ value, onChange, shown, total, isFiltered, onReset, placeholder, children }: SearchToolbarProps) {
  const t = useT();
  return (
    <div className="table-controls">
      <div className="table-search">
        <input
          type="search"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder ?? t('common.table.searchPlaceholder')}
          aria-label={placeholder ?? t('common.table.searchPlaceholder')}
        />
        <span className="table-search-count">{t('common.table.showing', { shown, total })}</span>
      </div>
      <div className="table-controls-actions">
        {children}
        {isFiltered && onReset ? (
          <button type="button" className="ghost-button" onClick={onReset}>{t('common.table.reset')}</button>
        ) : null}
      </div>
    </div>
  );
}

interface SortableThProps {
  columnKey: string;
  sort: SortState;
  onSort: (key: string) => void;
  children: ReactNode;
}

export function SortableTh({ columnKey, sort, onSort, children }: SortableThProps) {
  const active = sort.key === columnKey;
  const indicator = active ? (sort.direction === 'asc' ? '▲' : '▼') : '↕';
  return (
    <th aria-sort={active ? (sort.direction === 'asc' ? 'ascending' : 'descending') : 'none'}>
      <button type="button" className={`th-sort ${active ? 'active' : ''}`} onClick={() => onSort(columnKey)}>
        <span>{children}</span>
        <span className="th-sort-indicator" aria-hidden="true">{indicator}</span>
      </button>
    </th>
  );
}
