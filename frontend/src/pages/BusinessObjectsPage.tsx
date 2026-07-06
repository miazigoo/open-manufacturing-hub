import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { businessObjectsApi } from '../api/businessObjects';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { useI18n } from '../i18n/useI18n';

export function BusinessObjectsPage() {
  const { t } = useI18n();
  const objects = useQuery({ queryKey: ['business-objects'], queryFn: businessObjectsApi.list });
  const [selected, setSelected] = useState<string>('Customer');
  if (objects.isLoading) return <LoadingState label="Loading business objects" />;
  if (objects.error) return <ErrorState error={objects.error} />;
  const rows = objects.data ?? [];
  const current = rows.find((item) => item.object_type === selected) ?? rows[0];
  if (!current) return <EmptyState title={t('integration.enterprisePolish.businessObjectsTitle')} detail="Business object registry is empty." />;
  return (
    <div className="page-stack enterprise-runtime-page">
      <section className="page-header enterprise-hero">
        <span className="eyebrow">{t('integration.enterprisePolish.canonicalLayer')}</span>
        <h1>{t('integration.enterprisePolish.businessObjectsTitle')}</h1>
        <p>{t('integration.enterprisePolish.businessObjectsDesc')}</p>
        <div className="hero-meta"><Link className="primary-link" to="/resolvers">{t('integration.enterprisePolish.openResolvers')}</Link><span className="microcopy">{t('integration.enterprisePolish.canonicalSchemas', { count: rows.length })}</span></div>
      </section>
      <section className="runtime-grid">
        <aside className="panel builder-rail">
          <div className="panel-toolbar"><h2>Registry</h2><span className="microcopy">identity-first</span></div>
          <div className="builder-step-list">
            {rows.map((item) => <button key={item.object_type} className={`builder-step-card ${current.object_type === item.object_type ? 'active' : ''}`} onClick={() => setSelected(item.object_type)}><strong>{item.display_name}</strong><small>{item.identity_fields.join(' · ')}</small></button>)}
          </div>
        </aside>
        <main className="page-stack">
          <section className="panel runtime-card">
            <span className="eyebrow">{current.object_type}</span>
            <h2>{current.display_name}</h2>
            <p>{current.description}</p>
            <div className="metadata-grid compact-grid no-margin">
              <span className="success-note">Identity fields<span>{current.identity_fields.join(', ')}</span></span>
              <span className="success-note">Fields<span>{current.fields.length}</span></span>
            </div>
          </section>
          <section className="table-panel runtime-table-panel">
            <div className="panel-toolbar"><h2>Fields</h2><span className="microcopy">Canonical contract</span></div>
            <table><thead><tr><th>Name</th><th>Type</th><th>Required</th><th>Description</th></tr></thead><tbody>{current.fields.map((field) => <tr key={field.name}><td><strong>{field.name}</strong></td><td>{field.type}</td><td>{field.required ? 'yes' : 'no'}</td><td>{field.description ?? '—'}</td></tr>)}</tbody></table>
          </section>
          <JsonBlock title="Schema JSON" value={current} searchable={false} />
        </main>
      </section>
    </div>
  );
}
