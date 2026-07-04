interface EmptyPanelProps {
  title: string;
  detail?: string;
  action?: React.ReactNode;
}

export function EmptyPanel({ title, detail, action }: EmptyPanelProps) {
  return (
    <div className="empty-state product-empty-panel">
      <div className="empty-mark">Ø</div>
      <h3>{title}</h3>
      {detail && <p>{detail}</p>}
      {action && <div className="action-row">{action}</div>}
    </div>
  );
}
