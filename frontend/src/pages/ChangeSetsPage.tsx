import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { changeSetsApi } from '../api/changeSets';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { formatDateTime } from '../utils';

export function ChangeSetsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const changeSets = useQuery({ queryKey: ['change-sets'], queryFn: changeSetsApi.list });
  const [form, setForm] = useState({ name: 'Production promotion', description: 'Promote tested draft configuration', object_type: 'integration_flow', object_id: '' });
  const create = useMutation({
    mutationFn: () => changeSetsApi.createFromDrafts({ name: form.name, description: form.description, object_refs: [{ object_type: form.object_type, object_id: form.object_id }], include_dependencies: true }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['change-sets'] });
      navigate(`/change-sets/${data.id}`);
    },
  });

  if (changeSets.isLoading) return <LoadingState label="Loading change sets" />;
  if (changeSets.error) return <ErrorState error={changeSets.error} />;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (form.object_id.trim()) create.mutate();
  }

  return (
    <div className="page-stack promotion-page">
      <section className="page-header promotion-hero change-set-hero">
        <div>
          <span className="eyebrow">Promotion Pipeline</span>
          <h1>Package drafts into audited release change sets.</h1>
          <p>Create from tested drafts, export a reference-only package, preview imports, map secrets/environment variables and apply without silent overwrite.</p>
        </div>
        <div className="hero-meta"><Link className="primary-button" to="/change-sets/import">Import change set</Link><Link className="ghost-button" to="/environments">Environment profiles</Link></div>
      </section>

      <section className="promotion-grid">
        <section className="panel">
          <div className="panel-toolbar"><h2>Change sets</h2><span className="microcopy">{changeSets.data?.length ?? 0}</span></div>
          {(changeSets.data ?? []).length === 0 ? <EmptyState title="No change sets" detail="Create one from a draft config version or import a production package." /> : (
            <div className="promotion-list">
              {(changeSets.data ?? []).map((item) => (
                <Link className="promotion-card link-card" key={item.id} to={`/change-sets/${item.id}`}>
                  <span><strong>{item.name}</strong><small>{item.source_environment ?? 'local'} → {item.target_environment ?? 'not applied'} · {formatDateTime(item.created_at)}</small></span>
                  <StatusBadge status={item.status === 'applied' ? 'ok' : item.status === 'failed' ? 'failed' : 'warning'} label={item.status} compact />
                </Link>
              ))}
            </div>
          )}
        </section>

        <form className="panel stack-form" onSubmit={submit}>
          <div className="panel-toolbar"><div><span className="eyebrow">Create Manually</span><h2>From draft object</h2></div></div>
          <label className="field-label">Name<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
          <label className="field-label">Description<textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
          <div className="metadata-grid compact-grid no-margin">
            <label className="field-label">Object type<select value={form.object_type} onChange={(event) => setForm({ ...form, object_type: event.target.value })}><option value="integration_flow">integration_flow</option><option value="business_rule">business_rule</option><option value="mapping">mapping</option><option value="resolver">resolver</option><option value="workflow">workflow</option><option value="endpoint">endpoint</option><option value="route">route</option><option value="operation_template">operation_template</option><option value="odata_lookup_template">odata_lookup_template</option></select></label>
            <label className="field-label">Object ID<input value={form.object_id} onChange={(event) => setForm({ ...form, object_id: event.target.value })} placeholder="UUID" /></label>
          </div>
          <button className="primary-button" disabled={create.isPending || !form.object_id.trim()}>Create change set</button>
          {create.error instanceof Error && <div className="error-state compact">{create.error.message}</div>}
        </form>
      </section>
    </div>
  );
}
