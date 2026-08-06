import { FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { asJson } from '../api/client';
import { businessRulesApi } from '../api/businessRules';
import { CodeEditor } from '../components/CodeEditor';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { RuleSetEditor } from '../components/integration/RuleSetEditor';
import { useI18n } from '../i18n/useI18n';

const defaultRules: Record<string, unknown> = { mode: 'first_match', rules: [{ name: 'DNP pool', if: { path: 'request.body.pool_type', operator: 'eq', value: 'DNP' }, then: [{ action: 'set_target_system', value: 'DNP Service' }] }] };

function parseObject(value: string, label: string): Record<string, unknown> {
  const parsed = JSON.parse(value || '{}') as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error(`${label} must be a JSON object`);
  return parsed as Record<string, unknown>;
}

export function BusinessRulesPage() {
  const queryClient = useQueryClient();
  const { t } = useI18n();
  const rules = useQuery({ queryKey: ['business-rule-sets'], queryFn: businessRulesApi.list });
  const [form, setForm] = useState({ name: 'Pool routing rules', description: 'Route by pool type' });
  const [rulesJson, setRulesJson] = useState<Record<string, unknown>>(defaultRules);
  const [formError, setFormError] = useState<string | null>(null);
  const create = useMutation({
    mutationFn: () => businessRulesApi.create({ name: form.name, description: form.description, scope: 'global', enabled: true, rules_json: rulesJson }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['business-rule-sets'] }),
  });
  const install = useMutation({ mutationFn: businessRulesApi.installPresets, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['business-rule-sets'] }) });
  if (rules.isLoading) return <LoadingState label="Loading business rules" />;
  if (rules.error) return <ErrorState error={rules.error} />;
  function submit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    try { create.mutate(); } catch (caught) { setFormError(caught instanceof Error ? caught.message : 'Invalid input'); }
  }
  const rows = rules.data ?? [];
  return (
    <div className="page-stack enterprise-runtime-page">
      <section className="page-header enterprise-hero">
        <span className="eyebrow">{t('integration.enterprisePolish.rulesTitle')}</span>
        <h1>{t('integration.enterprisePolish.ruleSetsTitle')}</h1>
        <p>{t('integration.enterprisePolish.ruleSetsDesc')}</p>
        <div className="hero-meta">
          <button className="primary-button" onClick={() => install.mutate()} disabled={install.isPending}>{t('integration.enterprisePolish.installPresets')}</button>
          <span className="microcopy">{t('integration.enterprisePolish.ruleSetsCount', { count: rows.length })}</span>
        </div>
      </section>
      <section className="runtime-grid">
        <form className="panel stack-form runtime-control-card" onSubmit={submit}>
          <span className="eyebrow">Новый набор правил</span>
          <h2>Собрать без кода</h2>
          <p className="microcopy">Правило = условие (поле — оператор — значение) и действия, которые выполняются при совпадении. Откройте набор после создания и проверьте его на примере через кнопку Test.</p>
          <label className="field-label">Название<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
          <label className="field-label">Описание<input value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
          <RuleSetEditor value={rulesJson} onChange={setRulesJson} />
          <details className="technical-details">
            <summary>JSON для продвинутых</summary>
            <CodeEditor value={asJson(rulesJson)} onChange={(value) => { try { setRulesJson(parseObject(value, 'Rules JSON')); setFormError(null); } catch (caught) { setFormError(caught instanceof Error ? caught.message : 'Invalid JSON'); } }} language="json" minRows={8} />
          </details>
          <button className="primary-button" disabled={create.isPending}>Сохранить набор</button>
          {formError && <div className="error-state compact">{formError}</div>}
          {create.error instanceof Error && <div className="error-state compact">{create.error.message}</div>}
        </form>
        {rows.length === 0 ? <EmptyState title="No business rules" detail="Install presets or create a rule set." /> : (
          <section className="card-grid runtime-card-grid">
            {rows.map((item) => (
              <article className="panel runtime-card" key={item.id}>
                <div className="panel-toolbar"><span className="eyebrow">{item.scope}</span><StatusBadge status={item.enabled ? 'ok' : 'warning'} label={item.enabled ? 'enabled' : 'disabled'} /></div>
                <h2>{item.name}</h2>
                <p>{item.description}</p>
                <Link className="primary-link" to={`/business-rules/${item.id}`}>Открыть редактор</Link>
                <JsonBlock title="Rules" value={item.rules_json} searchable={false} />
              </article>
            ))}
          </section>
        )}
      </section>
    </div>
  );
}
