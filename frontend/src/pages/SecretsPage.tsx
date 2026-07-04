import { FormEvent, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { secretTypes, secretsApi, type SecretPayload, type SecretRead, type SecretType } from '../api/secrets';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { useT } from '../i18n/useI18n';
import { formatDateTime } from '../utils';

const initialForm = { name: '', description: '', secret_type: 'generic' as SecretType, value: '' };

export function SecretsPage() {
  const t = useT();
  const queryClient = useQueryClient();
  const secrets = useQuery({ queryKey: ['secrets'], queryFn: secretsApi.list });
  const [form, setForm] = useState(initialForm);
  const [rotateId, setRotateId] = useState<string | null>(null);
  const [rotateValue, setRotateValue] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['secrets'] });
  const create = useMutation({ mutationFn: secretsApi.create, onSuccess: () => { refresh(); setForm(initialForm); setMessage(t('secrets.created')); } });
  const rotate = useMutation({ mutationFn: ({ id, value }: { id: string; value: string }) => secretsApi.rotate(id, value), onSuccess: () => { refresh(); setRotateId(null); setRotateValue(''); setMessage(t('secrets.rotated')); } });
  const enable = useMutation({ mutationFn: secretsApi.enable, onSuccess: refresh });
  const disable = useMutation({ mutationFn: secretsApi.disable, onSuccess: refresh });
  const remove = useMutation({ mutationFn: secretsApi.delete, onSuccess: refresh });
  const rows = useMemo(() => secrets.data ?? [], [secrets.data]);

  function submit(event: FormEvent) {
    event.preventDefault();
    setMessage(null);
    const payload: SecretPayload = { name: form.name.trim(), description: form.description.trim() || null, secret_type: form.secret_type, value: form.value };
    create.mutate(payload);
  }

  function submitRotate(event: FormEvent) {
    event.preventDefault();
    if (!rotateId) return;
    rotate.mutate({ id: rotateId, value: rotateValue });
  }

  async function copyReference(secret: SecretRead) {
    const reference = JSON.stringify(secret.reference);
    try {
      await navigator.clipboard?.writeText(reference);
      setMessage(t('secrets.referenceCopied'));
    } catch {
      setMessage(`${t('secrets.referenceCopied')}: ${reference}`);
    }
  }

  const error = secrets.error;
  if (secrets.isLoading) return <LoadingState label={t('secrets.loading')} />;
  if (error) return <ErrorState error={error} />;

  return (
    <div className="page-stack two-column-page secrets-page">
      <section className="panel form-panel">
        <span className="eyebrow">{t('secrets.eyebrow')}</span>
        <h1>{t('secrets.title')}</h1>
        <p>{t('secrets.subtitle')}</p>
        <form className="stack-form" onSubmit={submit}>
          <label className="field-label">{t('common.name')}<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="onec.erp.password" required /></label>
          <label className="field-label">{t('secrets.description')}<input value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
          <label className="field-label">{t('secrets.type')}<select value={form.secret_type} onChange={(event) => setForm({ ...form, secret_type: event.target.value as SecretType })}>{secretTypes.map((type) => <option key={type} value={type}>{type}</option>)}</select></label>
          <label className="field-label">{t('secrets.value')}<textarea value={form.value} onChange={(event) => setForm({ ...form, value: event.target.value })} required spellCheck={false} /></label>
          {create.error instanceof Error && <div className="error-state compact">{create.error.message}</div>}
          {message && <div className="success-note">{message}</div>}
          <button className="primary-button" disabled={create.isPending}>{t('secrets.create')}</button>
        </form>
        <div className="success-note"><strong>{t('secrets.referenceFormat')}</strong><span>{'{ "$secret": "onec.erp.password" }'}</span></div>
      </section>

      <section className="panel">
        <div className="panel-toolbar"><div><h2>{t('secrets.items')}</h2><span className="microcopy">{rows.length}</span></div><Link className="primary-link" to="/connectors">{t('secrets.openConnectors')}</Link></div>
        {rows.length ? rows.map((secret) => (
          <article className="connector-card secret-card" key={secret.id}>
            <div className="connector-card-top">
              <div><h3>{secret.name}</h3><p>{secret.description || secret.secret_type}</p></div>
              <StatusBadge status={secret.enabled ? 'ok' : 'unknown'} label={secret.enabled ? t('connectors.enabled') : t('connectors.disabled')} />
            </div>
            <div className="metadata-grid compact-grid">
              <span>{t('secrets.preview')}<strong>{secret.value_preview ?? 'none'}</strong></span>
              <span>{t('secrets.lastUsed')}<strong>{formatDateTime(secret.last_used_at)}</strong></span>
              <span>{t('secrets.rotatedAt')}<strong>{formatDateTime(secret.rotated_at)}</strong></span>
            </div>
            <code className="secret-reference">{JSON.stringify(secret.reference)}</code>
            {rotateId === secret.id && <form className="stack-form compact-rotate-form" onSubmit={submitRotate}><label className="field-label">{t('secrets.newValue')}<textarea value={rotateValue} onChange={(event) => setRotateValue(event.target.value)} required /></label><div className="action-row"><button className="primary-button" disabled={rotate.isPending}>{t('secrets.rotate')}</button><button type="button" className="ghost-button" onClick={() => setRotateId(null)}>{t('common.cancel')}</button></div></form>}
            <div className="action-row wrap-actions">
              <button className="ghost-button" onClick={() => copyReference(secret)}>{t('secrets.copyReference')}</button>
              <button className="ghost-button" onClick={() => setRotateId(secret.id)}>{t('secrets.rotate')}</button>
              <button className="ghost-button" onClick={() => secret.enabled ? disable.mutate(secret.id) : enable.mutate(secret.id)}>{secret.enabled ? t('connectors.disable') : t('connectors.enable')}</button>
              <button className="ghost-button danger" onClick={() => remove.mutate(secret.id)}>{t('connectors.delete')}</button>
            </div>
          </article>
        )) : <EmptyState title={t('secrets.empty')} detail={t('secrets.emptyDetail')} />}
      </section>
    </div>
  );
}
