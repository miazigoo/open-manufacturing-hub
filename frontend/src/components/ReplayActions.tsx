import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Artifact, EventRun, EventStep, asJson } from '../api/client';
import { replayApi } from '../api/replay';

interface ReplayActionsProps {
  eventId: string;
  selectedRun: EventRun | null;
  selectedStep: EventStep | null;
  selectedArtifact: Artifact | null;
}

export function ReplayActions({ eventId, selectedRun, selectedStep, selectedArtifact }: ReplayActionsProps) {
  const queryClient = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const [jsonDraft, setJsonDraft] = useState('');
  const [startStep, setStartStep] = useState('validate');
  const [message, setMessage] = useState<string | null>(null);

  function refresh() {
    queryClient.invalidateQueries({ queryKey: ['timeline', eventId] });
    queryClient.invalidateQueries({ queryKey: ['events'] });
  }

  const fullReplay = useMutation({ mutationFn: () => replayApi.full(eventId), onSuccess: () => { setMessage('Full replay created'); refresh(); } });
  const dryRun = useMutation({ mutationFn: () => replayApi.dryRun(eventId), onSuccess: () => { setMessage('Dry run completed'); refresh(); } });
  const fromStep = useMutation({
    mutationFn: () => replayApi.fromStep(selectedRun?.id ?? '', selectedStep?.step_name ?? ''),
    onSuccess: () => { setMessage(`Replay from ${selectedStep?.step_name} created`); refresh(); },
  });
  const editReplay = useMutation({
    mutationFn: () => {
      if (!selectedArtifact) throw new Error('Select artifact first');
      return replayApi.editReplay(selectedArtifact.id, JSON.parse(jsonDraft) as Record<string, unknown>, startStep);
    },
    onSuccess: () => { setMessage('Edited replay created'); setEditorOpen(false); refresh(); },
  });

  function openEditor() {
    if (!selectedArtifact) return;
    setJsonDraft(asJson(selectedArtifact.content_json));
    setEditorOpen(true);
  }

  return (
    <section className="action-panel">
      <div>
        <span className="eyebrow">Replay controls</span>
        <h3>Operate this event safely</h3>
      </div>
      <div className="action-row">
        <button className="primary-button" onClick={() => fullReplay.mutate()} disabled={fullReplay.isPending}>Replay</button>
        <button className="ghost-button" onClick={() => fromStep.mutate()} disabled={!selectedRun || !selectedStep || fromStep.isPending}>Replay from step</button>
        <button className="ghost-button" onClick={openEditor} disabled={!selectedArtifact}>Edit & Replay</button>
        <button className="ghost-button" onClick={() => dryRun.mutate()} disabled={dryRun.isPending}>Dry Run</button>
      </div>
      {message && <div className="success-note">{message}</div>}
      {[fullReplay, dryRun, fromStep, editReplay].find((mutation) => mutation.isError)?.error instanceof Error && (
        <div className="error-state compact">{([fullReplay, dryRun, fromStep, editReplay].find((mutation) => mutation.isError)?.error as Error).message}</div>
      )}
      {editorOpen && selectedArtifact && (
        <div className="editor-drawer">
          <div className="panel-toolbar">
            <div><h3>Edit artifact JSON</h3><span className="microcopy">{selectedArtifact.name}</span></div>
            <button className="ghost-button" onClick={() => setEditorOpen(false)}>Close</button>
          </div>
          <label className="field-label">Start from step<input value={startStep} onChange={(event) => setStartStep(event.target.value)} /></label>
          <textarea value={jsonDraft} onChange={(event) => setJsonDraft(event.target.value)} spellCheck={false} />
          <button className="primary-button" onClick={() => editReplay.mutate()} disabled={editReplay.isPending}>Submit edited replay</button>
        </div>
      )}
    </section>
  );
}
