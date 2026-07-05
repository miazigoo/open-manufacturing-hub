import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { asJson } from '../api/client';
import { configVersionsApi } from '../api/configVersions';
import { executionApi } from '../api/execution';
import { WorkflowDefinition, workflowsApi } from '../api/workflows';
import { CodeEditor } from '../components/CodeEditor';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { VersionHistoryPanel } from '../features/configVersions';

interface Row { name: string; on: string; config: string; enabled: boolean }

type ParsedStep = { name: string; on?: string; config: Record<string, unknown> };

const toRows = (steps: Array<string | Record<string, unknown>>): Row[] => steps.map((step) => {
  const item = typeof step === 'string' ? { name: step } : step;
  return { name: String(item.name ?? 'receive'), on: String(item.on ?? 'always'), config: asJson(item.config ?? {}), enabled: true };
});

function parseRows(rows: Row[]): ParsedStep[] {
  return rows.filter((row) => row.enabled).map((row, index) => {
    try {
      return { name: row.name, ...(row.on && row.on !== 'always' ? { on: row.on } : {}), config: JSON.parse(row.config || '{}') as Record<string, unknown> };
    } catch {
      throw new Error(`Step ${index + 1} has invalid config JSON.`);
    }
  });
}

function workflowConfig(workflow: WorkflowDefinition, steps_json: ParsedStep[]): Record<string, unknown> {
  return {
    name: workflow.name,
    description: workflow.description,
    event_type: workflow.event_type,
    source_system: workflow.source_system,
    target_system: workflow.target_system,
    entity_type: workflow.entity_type,
    version: workflow.version,
    enabled: workflow.enabled,
    steps_json,
    validation_json: workflow.validation_json,
    source_mapping_version_id: workflow.source_mapping_version_id,
    target_mapping_version_id: workflow.target_mapping_version_id,
  };
}

export function PipelineEditorPage() {
  const { workflowId = '' } = useParams();
  const queryClient = useQueryClient();
  const workflow = useQuery({ queryKey: ['workflow', workflowId], queryFn: async () => (await workflowsApi.list()).find((item) => item.id === workflowId), enabled: Boolean(workflowId) });
  const steps = useQuery({ queryKey: ['execution-steps'], queryFn: executionApi.steps });
  const [rows, setRows] = useState<Row[] | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const currentRows = rows ?? toRows(workflow.data?.steps_json ?? []);
  const save = useMutation({
    mutationFn: (parsedRows: ParsedStep[]) => configVersionsApi.createDraft('workflow', workflowId, { config_json: workflowConfig(workflow.data!, parsedRows), comment: 'Draft saved from pipeline editor' }),
    onSuccess: () => {
      setRows(null);
      setFormError(null);
      queryClient.invalidateQueries({ queryKey: ['workflow', workflowId] });
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      queryClient.invalidateQueries({ queryKey: ['config-versions', 'workflow', workflowId] });
    },
  });
  const validate = useMutation({ mutationFn: () => workflowsApi.validate(workflowId) });
  const stepNames = useMemo(() => steps.data?.map((step) => step.name) ?? [], [steps.data]);

  if (workflow.isLoading || steps.isLoading) return <LoadingState label="Loading pipeline editor" />;
  const error = workflow.error ?? steps.error;
  if (error) return <ErrorState error={error} />;
  if (!workflow.data) return <ErrorState error={new Error('Workflow not found')} />;

  function update(index: number, patch: Partial<Row>) {
    setRows(currentRows.map((row, rowIndex) => rowIndex === index ? { ...row, ...patch } : row));
  }

  function move(index: number, delta: number) {
    const next = [...currentRows];
    const target = index + delta;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    setRows(next);
  }

  function handleValidate() {
    setFormError(null);
    try {
      parseRows(currentRows);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Pipeline config is invalid.');
      return;
    }
    validate.mutate();
  }

  function handleSave() {
    setFormError(null);
    try {
      save.mutate(parseRows(currentRows));
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Pipeline config is invalid.');
    }
  }

  return (
    <div className="page-stack">
      <section className="page-header">
        <span className="eyebrow">Pipeline Editor</span>
        <h1>{workflow.data.name}</h1>
        <p>Table editor for workflow steps. Changes are saved as a draft and affect runtime only after publish.</p>
      </section>
      <VersionHistoryPanel objectType="workflow" objectId={workflowId} compact onChanged={() => {
        queryClient.invalidateQueries({ queryKey: ['workflow', workflowId] });
        queryClient.invalidateQueries({ queryKey: ['workflows'] });
      }} />
      <section className="table-panel">
        <table>
          <thead><tr><th>Order</th><th>Step</th><th>Condition</th><th>Config JSON</th><th>Enabled</th><th>Actions</th></tr></thead>
          <tbody>
            {currentRows.map((row, index) => (
              <tr key={`${row.name}-${index}`}>
                <td>{index + 1}</td>
                <td><select value={row.name} onChange={(event) => update(index, { name: event.target.value })}>{stepNames.map((name) => <option key={name} value={name}>{name}</option>)}</select></td>
                <td><select value={row.on} onChange={(event) => update(index, { on: event.target.value })}><option value="always">always</option><option value="on_success">on_success</option><option value="failure">failure</option><option value="on_dry_run">on_dry_run</option></select></td>
                <td><CodeEditor value={row.config} onChange={(value) => update(index, { config: value })} language="json" minRows={5} /></td>
                <td><input type="checkbox" checked={row.enabled} onChange={(event) => update(index, { enabled: event.target.checked })} /></td>
                <td>
                  <div className="action-row">
                    <button className="ghost-button" onClick={() => move(index, -1)}>Up</button>
                    <button className="ghost-button" onClick={() => move(index, 1)}>Down</button>
                    <button className="ghost-button" onClick={() => setRows([...currentRows.slice(0, index + 1), { ...row }, ...currentRows.slice(index + 1)])}>Duplicate</button>
                    <button className="ghost-button" onClick={() => setRows(currentRows.filter((_, rowIndex) => rowIndex !== index))}>Remove</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {formError && <div className="error-state compact">{formError}</div>}
        {(save.error instanceof Error || validate.error instanceof Error) && <div className="error-state compact">{(save.error as Error | null)?.message ?? (validate.error as Error | null)?.message}</div>}
        <div className="action-row">
          <button className="ghost-button" onClick={() => setRows([...currentRows, { name: stepNames[0] ?? 'receive', on: 'always', config: '{}', enabled: true }])}>Add Step</button>
          <button className="ghost-button" onClick={handleValidate} disabled={validate.isPending}>Validate</button>
          <button className="primary-button" onClick={handleSave} disabled={save.isPending}>Save Draft</button>
        </div>
      </section>
      <JsonBlock title="Validation" value={validate.data ?? { hint: 'Validate the current workflow before saving production changes.' }} searchable={false} />
    </div>
  );
}
