import { FormEvent, useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { transformsApi } from '../api/transforms';
import { CodeEditor } from '../components/CodeEditor';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { useI18n } from '../i18n/useI18n';

function parseChain(value: string): Array<Record<string, unknown>> {
  const parsed = JSON.parse(value || '[]') as unknown;
  if (!Array.isArray(parsed)) throw new Error('Transform chain must be a JSON array');
  return parsed as Array<Record<string, unknown>>;
}

export function TransformsPage() {
  const { t } = useI18n();
  const transforms = useQuery({ queryKey: ['transforms'], queryFn: transformsApi.list });
  const [value, setValue] = useState('  abc 123  ');
  const [chain, setChain] = useState(asJson([{ name: 'trim' }, { name: 'uppercase' }]));
  const [error, setError] = useState<string | null>(null);
  const test = useMutation({ mutationFn: () => transformsApi.test({ value, chain: parseChain(chain) }) });
  const grouped = useMemo(() => {
    const map = new Map<string, typeof transforms.data>();
    (transforms.data ?? []).forEach((item) => map.set(item.category, [...(map.get(item.category) ?? []), item]));
    return Array.from(map.entries());
  }, [transforms.data]);
  if (transforms.isLoading) return <LoadingState label="Loading transforms" />;
  if (transforms.error) return <ErrorState error={transforms.error} />;
  function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try { test.mutate(); } catch (caught) { setError(caught instanceof Error ? caught.message : 'Invalid transform chain'); }
  }
  return <div className="page-stack enterprise-runtime-page"><section className="page-header enterprise-hero"><span className="eyebrow">{t('integration.enterprisePolish.transformsTitle')}</span><h1>{t('integration.enterprisePolish.safeTransformsTitle')}</h1><p>{t('integration.enterprisePolish.safeTransformsDesc')}</p><div className="hero-meta"><span className="microcopy">{t('integration.enterprisePolish.builtInTransforms', { count: transforms.data?.length ?? 0 })}</span></div></section><section className="runtime-grid"><form className="panel stack-form runtime-control-card" onSubmit={submit}><span className="eyebrow">Test bench</span><h2>Try a chain</h2><label className="field-label">Value<input value={value} onChange={(event) => setValue(event.target.value)} /></label><label className="field-label">Chain JSON<CodeEditor value={chain} onChange={setChain} language="json" minRows={7} /></label><button className="primary-button" disabled={test.isPending}>Run transform</button>{error && <div className="error-state compact">{error}</div>}{test.error instanceof Error && <div className="error-state compact">{test.error.message}</div>}</form><section className="page-stack">{test.data && <JsonBlock title="Transform result" value={test.data} searchable={false} />}{grouped.length === 0 ? <EmptyState title="No transforms" detail="Transform registry is empty." /> : grouped.map(([category, items]) => <section className="table-panel runtime-table-panel" key={category}><div className="panel-toolbar"><h2>{category}</h2><span className="microcopy">{items?.length ?? 0}</span></div><table><thead><tr><th>Name</th><th>Description</th><th>Args</th></tr></thead><tbody>{(items ?? []).map((item) => <tr key={item.name}><td><strong>{item.name}</strong></td><td>{item.description}</td><td><code>{Object.keys(item.args_schema).join(', ') || 'none'}</code></td></tr>)}</tbody></table></section>)}</section></section></div>;
}
