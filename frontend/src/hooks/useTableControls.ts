import { useMemo } from 'react';
import { usePersistentState } from './usePersistentState';

export type SortDirection = 'asc' | 'desc';

export interface SortState {
  key: string | null;
  direction: SortDirection;
}

type Accessor<T> = (row: T) => string | number | null | undefined;

interface TableControlsState {
  search: string;
  sort: SortState;
}

interface TableControlsOptions<T> {
  /** localStorage key so search + sort survive reloads / sessions. */
  storageKey: string;
  /** Text used for the free-text search box. */
  searchText: (row: T) => string;
  /** Sortable columns keyed by column id. */
  columns?: Record<string, Accessor<T>>;
  defaultSort?: SortState;
}

function compareValues(left: string | number | null | undefined, right: string | number | null | undefined) {
  const a = left ?? '';
  const b = right ?? '';
  if (typeof a === 'number' && typeof b === 'number') return a - b;
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: 'base' });
}

export function useTableControls<T>(rows: T[], options: TableControlsOptions<T>) {
  const { storageKey, searchText, columns, defaultSort } = options;
  const [state, setState, reset] = usePersistentState<TableControlsState>(storageKey, {
    search: '',
    sort: defaultSort ?? { key: null, direction: 'asc' },
  });

  const setSearch = (search: string) => setState((prev) => ({ ...prev, search }));

  const toggleSort = (key: string) =>
    setState((prev) => {
      if (prev.sort.key !== key) return { ...prev, sort: { key, direction: 'asc' } };
      if (prev.sort.direction === 'asc') return { ...prev, sort: { key, direction: 'desc' } };
      return { ...prev, sort: { key: null, direction: 'asc' } };
    });

  const processed = useMemo(() => {
    const term = state.search.trim().toLowerCase();
    let result = rows;
    if (term) {
      result = result.filter((row) => searchText(row).toLowerCase().includes(term));
    }
    const accessor = state.sort.key ? columns?.[state.sort.key] : undefined;
    if (accessor) {
      const factor = state.sort.direction === 'desc' ? -1 : 1;
      result = [...result].sort((left, right) => compareValues(accessor(left), accessor(right)) * factor);
    }
    return result;
  }, [rows, state.search, state.sort.key, state.sort.direction, searchText, columns]);

  const isFiltered = state.search.trim().length > 0 || state.sort.key !== null;

  return {
    search: state.search,
    setSearch,
    sort: state.sort,
    toggleSort,
    rows: processed,
    total: rows.length,
    shown: processed.length,
    isFiltered,
    reset,
  };
}
