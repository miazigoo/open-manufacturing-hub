import { FormEvent, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { businessRulesApi } from '../api/businessRules';
import { configVersionsApi } from '../api/configVersions';
import { CodeEditor } from '../components/CodeEditor';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { VersionHistoryPanel } from '../features/configVersions';

function parseObject(value: string, label: string): Record<string, unknown> {
  const parsed = JSON.parse(value || '{}') as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error(`${label} must be a JSON object`);
  return parsed as Record<string, unknown>;
}

export function BusinessRuleDetailsPage() {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const rule = useQuery({ queryKey: ['business-rule-set', id], queryFn: () => businessRulesApi.get(id!), enabled: Boolean(id) });
  const [rulesText, setRulesText] = useState('{}');
  const [sampleText, setSampleText] = useState(asJson({ pool_type: 'DNP', inn: '1234567890' }));
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { if (rule.data) setRulesText(asJson(rule.data.rules_json)); }, [rule.data]);
  const save = useMutation({
    mutationFn: () => configVersionsApi.createDraft('business_rule', id!, {
      config_json: {
        name: rule.data!.name,
        description: rule.data!.description,
        enabled: rule.data!.enabled,
        scope: rule.data!.scope,
        rules_json: parseObject(rulesText, 'Rules JSON'),
      },
      comment: 'Draft saved from rule editor',
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['business-rule-set', id] });
      queryClient.invalidateQueries({ queryKey: ['config-versions', 'business_rule', id] });
    },
  });
  const test = useMutation({ mutationFn: () => businessRulesApi.test(id!, { payload: parseObject(sampleText, 'Sample payload'), rules_json: parseObject(rulesText, 'Rules JSON') }) });
  if (rule.isLoading) return <LoadingState label="Loading rule set" />;
  if (rule.error) return <ErrorState error={rule.error} />;
  if (!rule.data) return <ErrorState error={new Error('Rule set not found')} />;
  function run(event: FormEvent, action: 'save' | 'test') {
    event.preventDefault();
    setError(null);
    try { if (action === 'save') save.mutate(); else test.mutate(); } catch (caught) { setError(caught instanceof Error ? caught.message : 'Invalid JSON'); }
  }
  return <div className="page-stack enterprise-runtime-page"><section className="page-header enterprise-hero"><span className="eyebrow">Rule Editor</span><h1>{rule.data.name}</h1><p>{rule.data.description}</p><div className="hero-meta"><StatusBadge status={rule.data.enabled ? 'ok' : 'warning'} label={rule.data.enabled ? 'enabled' : 'disabled'} /><Link className="primary-link" to="/business-rules">Back to rules</Link><Link className="primary-link" to={`/config-history/business_rule/${rule.data.id}`}>Release control</Link></div></section><VersionHistoryPanel objectType="business_rule" objectId={rule.data.id} compact onChanged={() => queryClient.invalidateQueries({ queryKey: ['business-rule-set', id] })} /><section className="runtime-grid"><form className="panel stack-form runtime-control-card"><span className="eyebrow">Advanced JSON</span><h2>Rules</h2><label className="field-label">Rules JSON<CodeEditor value={rulesText} onChange={setRulesText} language="json" minRows={10} /></label><label className="field-label">Sample payload<CodeEditor value={sampleText} onChange={setSampleText} language="json" minRows={7} /></label><div className="action-row wrap-actions"><button className="primary-button" onClick={(event) => run(event, 'test')} disabled={test.isPending}>Test</button><button className="ghost-button" onClick={(event) => run(event, 'save')} disabled={save.isPending}>Save Draft</button></div>{error && <div className="error-state compact">{error}</div>}{(save.error ?? test.error) instanceof Error && <div className="error-state compact">{((save.error ?? test.error) as Error).message}</div>}</form><section className="page-stack"><JsonBlock title="Published rule set" value={rule.data} searchable={false} />{test.data && <JsonBlock title="Evaluation result" value={test.data} searchable={false} />}</section></section></div>;
}
