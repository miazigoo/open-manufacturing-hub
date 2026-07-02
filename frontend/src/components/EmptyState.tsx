interface EmptyStateProps {
  title: string;
  detail?: string;
}

export function EmptyState({ title, detail }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <div className="empty-mark">Ø</div>
      <h3>{title}</h3>
      {detail && <p>{detail}</p>}
    </div>
  );
}
