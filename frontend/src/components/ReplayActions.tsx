import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Artifact, EventRun, EventStep, asJson } from '../api/client';
import { replayApi } from '../api/replay';
import { useT } from '../i18n/useI18n';
import { CodeEditor } from './CodeEditor';

interface ReplayActionsProps {
  eventId: string;
  selectedRun: EventRun | null;
  selectedStep: EventStep | null;
  selectedArtifact: Artifact | null;
}

export function ReplayActions({ eventId, selectedRun, selectedStep, selectedArtifact }: ReplayActionsProps) {
  const t = useT();
  const queryClient = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [jsonDraft, setJsonDraft] = useState('');
  const [startStep, setStartStep] = useState('validate');
  const [message, setMessage] = useState<string | null>(null);

  function refresh() {
    queryClient.invalidateQueries({ queryKey: ['timeline', eventId] });
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
      return replayApi.editReplay(selectedArtifact.id, JSON.parse(jsonDraft) as Record<string, unknown>, startStep);
    },
    onSuccess: () => { setMessage(t('replay.editedCreated')); setEditorOpen(false); refresh(); },
  });

  function openEditor() {
    if (!selectedArtifact) return;
    setJsonDraft(asJson(selectedArtifact.content_json));
    setEditorOpen(true);
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
        <button className="ghost-button" onClick={openEditor} disabled={!selectedArtifact}>{t('replay.edit')}</button>
        <button className="ghost-button" onClick={() => dryRun.mutate()} disabled={dryRun.isPending}>{t('replay.dryRun')}</button>
      </div>
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
          <button className="primary-button" onClick={() => editReplay.mutate()} disabled={editReplay.isPending}>{t('replay.submitEdited')}</button>
        </div>
      )}
    </section>
  );
}
