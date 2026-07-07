import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { odataConnectionsApi } from '../../../api/odataConnections';

export function useODataConnections() {
  const query = useQuery({ queryKey: ['odata-connections'], queryFn: odataConnectionsApi.list });
  const enabledConnections = useMemo(() => (query.data ?? []).filter((item) => item.enabled), [query.data]);
  return { ...query, enabledConnections };
}
