import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { retentionApi } from '../api/retention';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';

export function RetentionPage() {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ['retention-preview'], queryFn: retentionApi.preview });
  const cleanup = useMutation({ mutationFn: retentionApi.cleanup, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['retention-preview'] }) });

  if (query.isLoading) return <LoadingState label="Loading retention preview" />;
  if (query.error) return <ErrorState error={query.error} />;

  const preview = cleanup.data ?? query.data;
  return (
    <div className="page-stack">
      <header className="hero-panel retention-hero"><div><span className="eyebrow">Retention</span><h1>Control storage growth without losing pinned evidence.</h1><p>Pinned events will not be deleted. Expired events are marked expired; expired artifacts are removed.</p></div></header>
      <section className="metric-grid">
        <div className="metric-card"><span>Expired artifacts</span><strong>{preview?.expired_artifacts ?? 0}</strong></div>
        <div className="metric-card warn"><span>Expired events</span><strong>{preview?.expired_events ?? 0}</strong></div>
        <div className="metric-card info"><span>Pinned skipped</span><strong>{preview?.pinned_skipped ?? 0}</strong></div>
      </section>
      <section className="panel retention-panel"><h2>Cleanup action</h2><p>This operation deletes only expired artifacts and marks unpinned expired events as expired.</p><button className="primary-button" onClick={() => cleanup.mutate()} disabled={cleanup.isPending}>Run cleanup</button>{cleanup.isSuccess && <div className="success-note">Cleanup completed</div>}</section>
    </div>
  );
}
