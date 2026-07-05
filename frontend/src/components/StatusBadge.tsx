import { useT } from '../i18n/useI18n';
import { getStatusLabel } from '../i18n/status';

interface StatusBadgeProps {
  status?: string | null;
  label?: string;
  compact?: boolean;
}

const toneMap: Record<string, string> = {
  success: 'good',
  ok: 'good',
  sent: 'good',
  enabled: 'good',
  installed: 'good',
  available: 'good',
  resolved: 'good',
  failed: 'bad',
  down: 'bad',
  error: 'bad',
  critical: 'bad',
  incompatible: 'bad',
  deprecated: 'bad',
  retry_waiting: 'warn',
  warning: 'warn',
  experimental: 'warn',
  skipped_cooldown: 'warn',
  dry_run: 'warn',
  maintenance: 'maint',
  processing: 'info',
  running: 'info',
  open: 'info',
  acknowledged: 'info',
  in_development: 'info',
  coming_soon: 'info',
  unknown: 'muted',
  pending: 'muted',
  disabled: 'muted',
  new: 'muted',
  cancelled: 'muted',
  expired: 'muted',
};

export function StatusBadge({ status, label, compact }: StatusBadgeProps) {
  const t = useT();
  const safeStatus = status || 'unknown';
  const tone = toneMap[safeStatus] ?? 'muted';
  return <span className={`status-badge ${tone} ${compact ? 'compact' : ''}`}>{label ?? getStatusLabel(safeStatus, t)}</span>;
}
