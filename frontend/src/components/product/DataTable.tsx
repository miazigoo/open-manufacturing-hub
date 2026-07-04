import type { ReactNode } from 'react';
import { EmptyPanel } from './EmptyPanel';

interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
}

interface DataTableProps<T> {
  rows: T[];
  columns: Column<T>[];
  getRowKey: (row: T) => string;
  emptyTitle?: string;
  emptyDetail?: string;
}

export function DataTable<T>({ rows, columns, getRowKey, emptyTitle = 'No rows', emptyDetail }: DataTableProps<T>) {
  if (rows.length === 0) return <EmptyPanel title={emptyTitle} detail={emptyDetail} />;
  return (
    <div className="table-panel product-data-table">
      <table>
        <thead>
          <tr>{columns.map((column) => <th key={column.key}>{column.header}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row) => <tr key={getRowKey(row)}>{columns.map((column) => <td key={column.key}>{column.render(row)}</td>)}</tr>)}
        </tbody>
      </table>
    </div>
  );
}
