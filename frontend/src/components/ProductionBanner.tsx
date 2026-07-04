import { useQuery } from '@tanstack/react-query';
import { productionApi } from '../api/production';

export function ProductionBanner() {
  const status = useQuery({ queryKey: ['production-status'], queryFn: productionApi.status, refetchInterval: 60000, retry: false });
  const data = status.data;
  if (!data || (!data.update_mode_enabled && data.warnings.length === 0)) return null;
  return (
    <div className={`production-banner ${data.update_mode_enabled ? 'update-mode' : ''}`}>
      <strong>{data.update_mode_enabled ? 'Update mode enabled' : 'Production warning'}</strong>
      <span>{data.update_mode_enabled ? 'New requests are queued but not processed.' : data.warnings.slice(0, 2).join(' · ')}</span>
    </div>
  );
}
