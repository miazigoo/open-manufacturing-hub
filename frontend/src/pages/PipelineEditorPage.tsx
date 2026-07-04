import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { asJson } from '../api/client';
import { executionApi } from '../api/execution';
import { workflowsApi } from '../api/workflows';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';

interface Row { name: string; on: string; config: string; enabled: boolean }
const toRows = (steps: Array<string | Record<string, unknown>>): Row[] => steps.map((step) => { const item = typeof step === 'string' ? { name: step } : step; return { name: String(item.name ?? 'receive'), on: String(item.on ?? 'always'), config: asJson(item.config ?? {}), enabled: true }; });
const fromRows = (rows: Row[]) => rows.filter((row) => row.enabled).map((row) => ({ name: row.name, ...(row.on && row.on !== 'always' ? { on: row.on } : {}), config: JSON.parse(row.config || '{}') as Record<string, unknown> }));

export function PipelineEditorPage() {
  const { workflowId = '' } = useParams();
  const queryClient = useQueryClient();
  const workflow = useQuery({ queryKey: ['workflow', workflowId], queryFn: async () => (await workflowsApi.list()).find((item) => item.id === workflowId), enabled: Boolean(workflowId) });
  const steps = useQuery({ queryKey: ['execution-steps'], queryFn: executionApi.steps });
  const [rows, setRows] = useState<Row[] | null>(null);
  const currentRows = rows ?? toRows(workflow.data?.steps_json ?? []);
  const save = useMutation({ mutationFn: () => workflowsApi.patch(workflowId, { steps_json: fromRows(currentRows) }), onSuccess: () => { setRows(null); queryClient.invalidateQueries({ queryKey: ['workflow', workflowId] }); queryClient.invalidateQueries({ queryKey: ['workflows'] }); } });
  const validate = useMutation({ mutationFn: () => workflowsApi.validate(workflowId) });
  const stepNames = useMemo(() => steps.data?.map((step) => step.name) ?? [], [steps.data]);
  if (workflow.isLoading || steps.isLoading) return <LoadingState label="Loading pipeline editor" />;
  const error = workflow.error ?? steps.error;
  if (error) return <ErrorState error={error} />;
  if (!workflow.data) return <ErrorState error={new Error('Workflow not found')} />;
  function update(index: number, patch: Partial<Row>) { setRows(currentRows.map((row, rowIndex) => rowIndex === index ? { ...row, ...patch } : row)); }
  function move(index: number, delta: number) { const next = [...currentRows]; const target = index + delta; if (target < 0 || target >= next.length) return; [next[index], next[target]] = [next[target], next[index]]; setRows(next); }
  return <div className="page-stack"><section className="page-header"><span className="eyebrow">Pipeline Editor</span><h1>{workflow.data.name}</h1><p>Table editor for workflow steps. Validate before saving.</p></section><section className="table-panel"><table><thead><tr><th>Order</th><th>Step</th><th>Condition</th><th>Config JSON</th><th>Enabled</th><th>Actions</th></tr></thead><tbody>{currentRows.map((row, index) => <tr key={`${row.name}-${index}`}><td>{index + 1}</td><td><select value={row.name} onChange={(event) => update(index, { name: event.target.value })}>{stepNames.map((name) => <option key={name} value={name}>{name}</option>)}</select></td><td><select value={row.on} onChange={(event) => update(index, { on: event.target.value })}><option value="always">always</option><option value="on_success">on_success</option><option value="failure">failure</option><option value="on_dry_run">on_dry_run</option></select></td><td><textarea value={row.config} onChange={(event) => update(index, { config: event.target.value })} /></td><td><input type="checkbox" checked={row.enabled} onChange={(event) => update(index, { enabled: event.target.checked })} /></td><td><div className="action-row"><button className="ghost-button" onClick={() => move(index, -1)}>Up</button><button className="ghost-button" onClick={() => move(index, 1)}>Down</button><button className="ghost-button" onClick={() => setRows([...currentRows.slice(0, index + 1), { ...row }, ...currentRows.slice(index + 1)])}>Duplicate</button><button className="ghost-button" onClick={() => setRows(currentRows.filter((_, rowIndex) => rowIndex !== index))}>Remove</button></div></td></tr>)}</tbody></table><div className="action-row"><button className="ghost-button" onClick={() => setRows([...currentRows, { name: 'receive', on: 'always', config: '{}', enabled: true }])}>Add Step</button><button className="ghost-button" onClick={() => validate.mutate()}>Validate</button><button className="primary-button" onClick={() => save.mutate()} disabled={save.isPending}>Save Pipeline</button></div></section><JsonBlock title="Validation" value={validate.data ?? {}} searchable={false} /></div>;
}
