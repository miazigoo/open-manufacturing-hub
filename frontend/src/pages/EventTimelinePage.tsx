import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { Artifact, EventRun, EventStep } from '../api/client';
import { artifactsApi } from '../api/artifacts';
import { eventsApi } from '../api/events';
import { ArtifactViewer } from '../components/ArtifactViewer';
import { DiffViewer } from '../components/DiffViewer';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { ReplayActions } from '../components/ReplayActions';
import { StatusBadge } from '../components/StatusBadge';
import { TimelineStep } from '../components/TimelineStep';
import { formatDateTime, formatDuration } from '../utils';

export function EventTimelinePage() {
  const { eventId = '' } = useParams();
  const queryClient = useQueryClient();
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null);
  const [diffBase, setDiffBase] = useState<Artifact | null>(null);
  const [diffCompareId, setDiffCompareId] = useState('');

  const timeline = useQuery({ queryKey: ['timeline', eventId], queryFn: () => eventsApi.timeline(eventId), enabled: Boolean(eventId) });
  const diff = useQuery({
    queryKey: ['artifact-diff', diffBase?.id, diffCompareId],
    queryFn: () => artifactsApi.diff(diffBase?.id ?? '', diffCompareId),
    enabled: Boolean(diffBase?.id && diffCompareId),
  });

  const pinMutation = useMutation({
    mutationFn: () => timeline.data?.event.pinned ? eventsApi.unpin(eventId) : eventsApi.pin(eventId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['timeline', eventId] }),
  });

  useEffect(() => {
    const latestRun = timeline.data?.runs.at(-1);
    if (!selectedRunId && latestRun) setSelectedRunId(latestRun.id);
  }, [timeline.data, selectedRunId]);

  const selectedRun: EventRun | null = useMemo(() => timeline.data?.runs.find((run) => run.id === selectedRunId) ?? timeline.data?.runs.at(-1) ?? null, [timeline.data, selectedRunId]);
  const selectedStep: EventStep | null = useMemo(() => selectedRun?.steps.find((step) => step.id === selectedStepId) ?? selectedRun?.steps[0] ?? null, [selectedRun, selectedStepId]);
  const selectedArtifact: Artifact | null = useMemo(() => {
    const artifacts = selectedStep?.artifacts ?? [];
    return artifacts.find((artifact) => artifact.id === selectedArtifactId) ?? artifacts[0] ?? null;
  }, [selectedStep, selectedArtifactId]);

  useEffect(() => {
    if (selectedStep?.artifacts.length && !selectedArtifactId) {
      setSelectedArtifactId(selectedStep.artifacts[0].id);
    }
  }, [selectedStep, selectedArtifactId]);
  const allArtifacts = timeline.data?.runs.flatMap((run) => run.artifacts) ?? [];

  if (timeline.isLoading) return <LoadingState label="Loading event timeline" />;
  if (timeline.error) return <ErrorState error={timeline.error} />;
  if (!timeline.data) return <EmptyState title="Timeline not found" />;

  const { event, runs } = timeline.data;
  const failedStep = selectedRun?.steps.find((step) => step.status === 'failed');

  return (
    <div className="timeline-page">
      <header className="timeline-hero">
        <div>
          <Link className="ghost-link" to="/events">← Event Journal</Link>
          <span className="eyebrow">Event Timeline</span>
          <h1>{event.event_type} <span>#{event.entity_id ?? event.id.slice(0, 8)}</span></h1>
          <div className="hero-meta">
            <StatusBadge status={event.status} />
            <span>{event.source_system} → {event.target_system ?? 'unknown'}</span>
            <span>Correlation: <strong>{event.correlation_id ?? '—'}</strong></span>
            <span>Pinned: <strong>{event.pinned ? 'yes' : 'no'}</strong></span>
          </div>
        </div>
        <button className="primary-button" onClick={() => pinMutation.mutate()}>{event.pinned ? 'Unpin' : 'Pin'}</button>
      </header>

      <div className="timeline-layout">
        <aside className="run-rail">
          <h2>Runs</h2>
          {runs.map((run) => (
            <button key={run.id} className={`run-card ${run.id === selectedRun?.id ? 'selected' : ''}`} onClick={() => { setSelectedRunId(run.id); setSelectedStepId(null); setSelectedArtifactId(null); }}>
              <span>Run #{run.run_number}</span>
              <strong>{run.mode.replaceAll('_', ' ')}</strong>
              <small>{formatDateTime(run.started_at)} · {formatDuration(run.started_at, run.finished_at)}</small>
              <StatusBadge status={run.status} compact />
            </button>
          ))}
          {selectedRun && <ReplayActions eventId={event.id} selectedRun={selectedRun} selectedStep={selectedStep} selectedArtifact={selectedArtifact} />}
        </aside>

        <section className="timeline-main">
          {selectedRun ? (
            <>
              <div className="run-header"><div><h2>Run #{selectedRun.run_number} · {selectedRun.mode}</h2><p>{formatDateTime(selectedRun.started_at)} · duration {formatDuration(selectedRun.started_at, selectedRun.finished_at)}</p><p>{selectedRun.workflow_name ? `${selectedRun.workflow_name} v${selectedRun.workflow_version ?? 1}` : 'Legacy pipeline'} · mappings {Object.keys(selectedRun.mapping_versions_json ?? {}).length}</p></div><StatusBadge status={selectedRun.status} /></div>
              <div className="step-rail">
                {selectedRun.steps.map((step) => <TimelineStep key={step.id} step={step} selected={step.id === selectedStep?.id} onSelect={() => { setSelectedStepId(step.id); setSelectedArtifactId(null); }} />)}
              </div>
              {failedStep && <div className="error-callout"><strong>{failedStep.error_code}</strong><span>{failedStep.error_message}</span></div>}
              {selectedStep && (
                <div className="step-detail-card">
                  <div className="panel-toolbar"><div><span className="eyebrow">Selected step</span><h2>{selectedStep.step_name}</h2></div><StatusBadge status={selectedStep.status} /></div>
                  <div className="metadata-grid compact-grid">
                    <span>Order<strong>{selectedStep.step_order}</strong></span>
                    <span>Error code<strong>{selectedStep.error_code ?? '—'}</strong></span>
                    <span>Artifacts<strong>{selectedStep.artifacts.length}</strong></span>
                  </div>
                  <div className="artifact-tabs">
                    {selectedStep.artifacts.map((artifact) => <button key={artifact.id} className={artifact.id === selectedArtifact?.id ? 'active' : ''} onClick={() => setSelectedArtifactId(artifact.id)}>{artifact.name}</button>)}
                  </div>
                </div>
              )}
            </>
          ) : <EmptyState title="No runs" detail="This event has no execution runs yet." />}
        </section>

        <aside className="artifact-column">
          <ArtifactViewer artifact={selectedArtifact} onDiff={(artifact) => setDiffBase(artifact)} />
          {diffBase && (
            <section className="panel diff-selector">
              <div className="panel-toolbar"><h3>Compare artifact</h3><button className="ghost-button" onClick={() => setDiffBase(null)}>Close</button></div>
              <select value={diffCompareId} onChange={(event) => setDiffCompareId(event.target.value)}>
                <option value="">Select artifact</option>
                {allArtifacts.filter((artifact) => artifact.id !== diffBase.id).map((artifact) => <option key={artifact.id} value={artifact.id}>{artifact.name} · {artifact.artifact_type}</option>)}
              </select>
              {diff.isLoading ? <LoadingState label="Computing diff" /> : <DiffViewer diff={diff.data ?? null} />}
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}
