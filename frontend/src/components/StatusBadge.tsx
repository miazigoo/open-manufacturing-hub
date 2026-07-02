import { useT } from '../i18n/useI18n';

interface StatusBadgeProps {
  status: string;
  label?: string;
  compact?: boolean;
}

const toneMap: Record<string, string> = {
  success: 'good',
  ok: 'good',
  sent: 'good',
  resolved: 'good',
  failed: 'bad',
  down: 'bad',
  error: 'bad',
  critical: 'bad',
  retry_waiting: 'warn',
  warning: 'warn',
  skipped_cooldown: 'warn',
  dry_run: 'warn',
  maintenance: 'maint',
  processing: 'info',
  running: 'info',
  open: 'info',
  acknowledged: 'info',
  unknown: 'muted',
  pending: 'muted',
  new: 'muted',
  cancelled: 'muted',
  expired: 'muted',
};

export function StatusBadge({ status, label, compact }: StatusBadgeProps) {
  const t = useT();
  const tone = toneMap[status] ?? 'muted';
  const fallback = status.replaceAll('_', ' ');
  const statusLabel = t(`status.${status}`);
  return <span className={`status-badge ${tone} ${compact ? 'compact' : ''}`}>{label ?? (statusLabel === `status.${status}` ? fallback : statusLabel)}</span>;
}
