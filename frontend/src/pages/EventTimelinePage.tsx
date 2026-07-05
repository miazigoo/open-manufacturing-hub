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
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { ReplayActions } from '../components/ReplayActions';
import { StatusBadge } from '../components/StatusBadge';
import { TimelineStep } from '../components/TimelineStep';
import { errorHelp } from '../features/help/errorHelp';
import { useT } from '../i18n/useI18n';
import { formatDateTime, formatDuration } from '../utils';

export function EventTimelinePage() {
  const t = useT();
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
  const requestArtifact = selectedStep?.artifacts.find((artifact) => artifact.artifact_type === 'outgoing_request' || artifact.artifact_type === 'dry_run_request') ?? null;
  const responseArtifact = selectedStep?.artifacts.find((artifact) => artifact.artifact_type === 'incoming_response') ?? null;
  const externalErrorArtifact = selectedStep?.artifacts.find((artifact) => artifact.artifact_type === 'external_error') ?? null;

  if (timeline.isLoading) return <LoadingState label={t('timeline.loading')} />;
  if (timeline.error) return <ErrorState error={timeline.error} />;
  if (!timeline.data) return <EmptyState title={t('timeline.notFound')} />;

  const { event, runs } = timeline.data;
  const failedStep = selectedRun?.steps.find((step) => step.status === 'failed');
  const selectedErrorHelp = errorHelp(selectedStep?.error_code ?? failedStep?.error_code);

  return (
    <div className="timeline-page">
      <header className="timeline-hero">
        <div>
          <Link className="ghost-link" to="/events">← {t('nav.events')}</Link>
          <span className="eyebrow">{t('timeline.eyebrow')}</span>
          <h1>{event.event_type} <span>#{event.entity_id ?? event.id.slice(0, 8)}</span></h1>
          <div className="hero-meta">
            <StatusBadge status={event.status} />
            <span>{event.source_system} → {event.target_system ?? t('common.unknown')}</span>
            <span>{t('events.correlationId')}: <strong>{event.correlation_id ?? '—'}</strong></span>
            <span>{t('timeline.pinned')}: <strong>{event.pinned ? t('common.yes') : t('common.no')}</strong></span>
          </div>
        </div>
        <button className="primary-button" onClick={() => pinMutation.mutate()}>{event.pinned ? t('timeline.unpin') : t('timeline.pin')}</button>
      </header>

      {timeline.data.queue_item && (
        <section className="panel queue-timeline-panel">
          <div className="panel-toolbar">
            <div><span className="eyebrow">Queue Item</span><h2>Runtime processing state</h2></div>
            <StatusBadge status={timeline.data.queue_item.status} label={timeline.data.queue_item.status} />
          </div>
          <div className="metadata-grid compact-grid no-margin">
            <span>Attempts<strong>{timeline.data.queue_item.attempts}/{timeline.data.queue_item.max_attempts}</strong></span>
            <span>Next retry<strong>{timeline.data.queue_item.next_retry_at ?? '—'}</strong></span>
            <span>Locked by<strong>{timeline.data.queue_item.locked_by ?? '—'}</strong></span>
          </div>
          {timeline.data.queue_item.last_error && <div className="error-state compact">{timeline.data.queue_item.last_error}</div>}
        </section>
      )}

      <div className="timeline-layout">
        <aside className="run-rail" data-tour="timeline-runs">
          <h2>{t('timeline.runs')}</h2>
          {runs.map((run) => (
            <button key={run.id} className={`run-card ${run.id === selectedRun?.id ? 'selected' : ''}`} onClick={() => { setSelectedRunId(run.id); setSelectedStepId(null); setSelectedArtifactId(null); }}>
              <span>{t('timeline.run', { number: run.run_number })}</span>
              <strong>{run.mode.replaceAll('_', ' ')}</strong>
              <small>{formatDateTime(run.started_at)} · {formatDuration(run.started_at, run.finished_at)}</small>
              <StatusBadge status={run.status} compact />
            </button>
          ))}
          {selectedRun && <ReplayActions eventId={event.id} selectedRun={selectedRun} selectedStep={selectedStep} selectedArtifact={selectedArtifact} />}
        </aside>

        <section className="timeline-main" data-tour="timeline-steps">
          {selectedRun ? (
            <>
              <div className="run-header"><div><h2>{t('timeline.run', { number: selectedRun.run_number })} · {selectedRun.mode}</h2><p>{formatDateTime(selectedRun.started_at)} · {t('timeline.duration')} {formatDuration(selectedRun.started_at, selectedRun.finished_at)}</p><p>{selectedRun.workflow_name ? `${selectedRun.workflow_name} v${selectedRun.workflow_version ?? 1}` : t('timeline.legacyPipeline')} · {t('nav.mappings')} {Object.keys(selectedRun.mapping_versions_json ?? {}).length}</p></div><StatusBadge status={selectedRun.status} /></div>
              <div className="step-rail">
                {selectedRun.steps.map((step) => <TimelineStep key={step.id} step={step} selected={step.id === selectedStep?.id} onSelect={() => { setSelectedStepId(step.id); setSelectedArtifactId(null); }} />)}
              </div>
              {failedStep && <div className="error-callout"><strong>{failedStep.human_title ?? failedStep.error_code}</strong><span>{failedStep.human_summary ?? failedStep.error_message}</span></div>}
              {selectedStep && (
                <div className="step-detail-card">
                  <div className="panel-toolbar"><div><span className="eyebrow">{t('timeline.selectedStep')}</span><h2>{selectedStep.step_name}</h2></div><StatusBadge status={selectedStep.status} /></div>
                  <div className="metadata-grid compact-grid">
                    <span>{t('timeline.order')}<strong>{selectedStep.step_order}</strong></span>
                    <span>{t('incidents.errorCode')}<strong>{selectedStep.error_code ?? '—'}</strong></span>
                    <span>{t('timeline.artifacts')}<strong>{selectedStep.artifacts.length}</strong></span>
                  </div>
                  {selectedStep.status === 'failed' && (
                    <section className="external-error-panel">
                      <div className="panel-toolbar"><div><span className="eyebrow">{t('timeline.externalError')}</span><h3>{selectedStep.human_title ?? selectedStep.error_code ?? t('common.unknownError')}</h3></div><StatusBadge status="failed" /></div>
                      <div className="error-section-grid">
                        <article><span>{t('timeline.summary')}</span><p>{selectedStep.human_summary ?? selectedStep.error_message ?? '—'}</p></article>
                        <article><span>{t('timeline.normalized')}</span><p><strong>{selectedStep.error_code ?? '—'}</strong><br />{selectedStep.error_message ?? '—'}</p></article>
                        <article><span>{t('timeline.hint')}</span><p>{selectedStep.hint ?? '—'}</p></article>
                      </div>
                      {selectedStep.external_error && (
                        <div className="external-response-card">
                          <div className="metadata-grid compact-grid no-margin">
                            <span>HTTP<strong>{selectedStep.external_error.http_status ?? '—'}</strong></span>
                            <span>{t('common.type')}<strong>{selectedStep.external_error.response_content_type ?? '—'}</strong></span>
                            <span>{t('common.hash')}<strong className="mono">{selectedStep.external_error.response_body_sha256?.slice(0, 12) ?? '—'}</strong></span>
                          </div>
                          <pre>{selectedStep.external_error.response_body_preview ?? selectedStep.external_error.external_error_message ?? selectedStep.external_error.normalized_message}</pre>
                        </div>
                      )}
                      <div className="artifact-quick-grid">
                        {externalErrorArtifact && <JsonBlock title={t('timeline.originalExternalError')} value={externalErrorArtifact.content_json} searchable={false} />}
                        {requestArtifact && <JsonBlock title={t('timeline.request')} value={requestArtifact.content_json} searchable={false} />}
                        {responseArtifact && <JsonBlock title={t('timeline.response')} value={responseArtifact.content_json} searchable={false} />}
                      </div>
                      {selectedErrorHelp && <div className="timeline-help-card"><h3>{selectedErrorHelp.title}</h3><ul>{selectedErrorHelp.checks.map((item) => <li key={item}>{item}</li>)}</ul><Link className="primary-link" to={selectedErrorHelp.docsUrl}>Open troubleshooting docs</Link></div>}
                    </section>
                  )}
                  <div className="artifact-tabs">
                    {selectedStep.artifacts.map((artifact) => <button key={artifact.id} className={artifact.id === selectedArtifact?.id ? 'active' : ''} onClick={() => setSelectedArtifactId(artifact.id)}>{artifact.name}</button>)}
                  </div>
                </div>
              )}
            </>
          ) : <EmptyState title={t('timeline.noRuns')} detail={t('timeline.noRunsDetail')} />}
        </section>

        <aside className="artifact-column" data-tour="timeline-artifacts">
          <ArtifactViewer artifact={selectedArtifact} onDiff={(artifact) => setDiffBase(artifact)} />
          {diffBase && (
            <section className="panel diff-selector">
              <div className="panel-toolbar"><h3>{t('timeline.compareArtifact')}</h3><button className="ghost-button" onClick={() => setDiffBase(null)}>{t('replay.close')}</button></div>
              <select value={diffCompareId} onChange={(event) => setDiffCompareId(event.target.value)}>
                <option value="">{t('timeline.selectArtifact')}</option>
                {allArtifacts.filter((artifact) => artifact.id !== diffBase.id).map((artifact) => <option key={artifact.id} value={artifact.id}>{artifact.name} · {artifact.artifact_type}</option>)}
              </select>
              {diff.isLoading ? <LoadingState label={t('timeline.computingDiff')} /> : <DiffViewer diff={diff.data ?? null} />}
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}
