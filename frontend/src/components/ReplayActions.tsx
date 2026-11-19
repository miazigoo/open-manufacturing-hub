import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Artifact, ArtifactSummary, EventRun, EventStep, asJson } from '../api/client';
import { artifactsApi } from '../api/artifacts';
import { replayApi } from '../api/replay';
import { useT } from '../i18n/useI18n';
import { CodeEditor } from './CodeEditor';
import { LoadingState } from './LoadingState';

interface ReplayActionsProps {
  eventId: string;
  selectedRun: EventRun | null;
  selectedStep: EventStep | null;
  selectedArtifact: Artifact | ArtifactSummary | null;
}

export function ReplayActions({ eventId, selectedRun, selectedStep, selectedArtifact }: ReplayActionsProps) {
  const t = useT();
  const queryClient = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [isLoadingArtifact, setIsLoadingArtifact] = useState(false);
  const [jsonDraft, setJsonDraft] = useState('');
  const [startStep, setStartStep] = useState('validate');
  const [message, setMessage] = useState<string | null>(null);

  function refresh() {
    queryClient.invalidateQueries({ queryKey: ['event-overview', eventId] });
    queryClient.invalidateQueries({ queryKey: ['timeline', eventId] });
    queryClient.invalidateQueries({ queryKey: ['events-journal'] });
    queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
    queryClient.invalidateQueries({ queryKey: ['events'] });
  }

  const fullReplay = useMutation({ mutationFn: () => replayApi.full(eventId), onSuccess: () => { setMessage(t('replay.fullCreated')); refresh(); } });
  const dryRun = useMutation({ mutationFn: () => replayApi.dryRun(eventId), onSuccess: () => { setMessage(t('replay.dryRunCompleted')); refresh(); } });
  const fromStep = useMutation({
    mutationFn: () => replayApi.fromStep(selectedRun?.id ?? '', selectedStep?.step_name ?? ''),
    onSuccess: () => { setMessage(t('replay.fromStepCreated', { step: selectedStep?.step_name ?? '' })); refresh(); },
  });
  const editReplay = useMutation({
    mutationFn: () => {
      if (!selectedArtifact) throw new Error(t('replay.selectArtifact'));
      const parsed = JSON.parse(jsonDraft) as Record<string, unknown>;
      return replayApi.editReplay(selectedArtifact.id, parsed, startStep);
    },
    onSuccess: () => { setMessage(t('replay.editedCreated')); setEditorOpen(false); refresh(); },
  });

  async function openEditor() {
    if (!selectedArtifact) return;
    setIsLoadingArtifact(true);
    try {
      const fullArtifact = await queryClient.fetchQuery({ queryKey: ['artifact-content', selectedArtifact.id], queryFn: () => artifactsApi.get(selectedArtifact.id), staleTime: 60_000 });
      setJsonDraft(asJson(fullArtifact.content_json ?? {}));
      setEditorOpen(true);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoadingArtifact(false);
    }
  }

  return (
    <section className="action-panel">
      <div>
        <span className="eyebrow">{t('replay.eyebrow')}</span>
        <h3>{t('replay.title')}</h3>
      </div>
      <div className="action-row">
        <button className="primary-button" onClick={() => fullReplay.mutate()} disabled={fullReplay.isPending}>{t('replay.replay')}</button>
        <button className="ghost-button" onClick={() => fromStep.mutate()} disabled={!selectedRun || !selectedStep || fromStep.isPending}>{t('replay.fromStep')}</button>
        <button className="ghost-button" onClick={openEditor} disabled={!selectedArtifact || isLoadingArtifact}>
          {isLoadingArtifact ? t('common.loading') : t('replay.edit')}
        </button>
        <button className="ghost-button" onClick={() => dryRun.mutate()} disabled={dryRun.isPending}>{t('replay.dryRun')}</button>
      </div>
      {isLoadingArtifact && <LoadingState label={t('common.loading')} />}
      {message && <div className="success-note">{message}</div>}
      {[fullReplay, dryRun, fromStep, editReplay].find((mutation) => mutation.isError)?.error instanceof Error && (
        <div className="error-state compact">{([fullReplay, dryRun, fromStep, editReplay].find((mutation) => mutation.isError)?.error as Error).message}</div>
      )}
      {editorOpen && selectedArtifact && (
        <div className="editor-drawer">
          <div className="panel-toolbar">
            <div><h3>{t('replay.editJson')}</h3><span className="microcopy">{selectedArtifact.name}</span></div>
            <button className="ghost-button" onClick={() => setEditorOpen(false)}>{t('replay.close')}</button>
          </div>
          <label className="field-label">{t('replay.startFromStep')}<input value={startStep} onChange={(event) => setStartStep(event.target.value)} /></label>
          <CodeEditor value={jsonDraft} onChange={setJsonDraft} language="json" minRows={10} />
          <button
            className="primary-button"
            onClick={() => editReplay.mutate()}
            disabled={editReplay.isPending || !jsonDraft.trim()}
          >
            {editReplay.isPending ? t('common.loading') : t('replay.submitEdited')}
          </button>
        </div>
      )}
    </section>
  );
}
