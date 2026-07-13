import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { trainingApi, type TrainingRunResult } from '../api/training';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { useI18n } from '../i18n/useI18n';

function normalizeTimelineUrl(url: string | null) {
  if (!url) return null;
  if (url.startsWith('/events/')) return url;
  if (/^[a-f0-9-]{20,}$/i.test(url)) return `/events/${url}`;
  return url;
}

export function TrainingPage() {
  const { language, t } = useI18n();
  const queryClient = useQueryClient();
  const [selectedResult, setSelectedResult] = useState<TrainingRunResult | null>(null);
  const status = useQuery({ queryKey: ['training-status'], queryFn: trainingApi.status });
  const install = useMutation({
    mutationFn: trainingApi.install,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['training-status'] });
      queryClient.invalidateQueries({ queryKey: ['odata-connections'] });
      queryClient.invalidateQueries({ queryKey: ['bus-endpoints'] });
    },
  });
  const reset = useMutation({
    mutationFn: trainingApi.reset,
    onSuccess: () => {
      setSelectedResult(null);
      queryClient.invalidateQueries({ queryKey: ['training-status'] });
      queryClient.invalidateQueries({ queryKey: ['odata-connections'] });
      queryClient.invalidateQueries({ queryKey: ['bus-endpoints'] });
    },
  });
  const run = useMutation({
    mutationFn: trainingApi.runExample,
    onSuccess: (result) => {
      setSelectedResult(result);
      queryClient.invalidateQueries({ queryKey: ['training-status'] });
    },
  });

  if (status.isLoading) return <LoadingState label={t('integration.training.loading')} />;
  if (status.error) return <ErrorState error={status.error} />;

  const data = status.data;
  const timelineUrl = normalizeTimelineUrl(selectedResult?.timeline_url ?? null);

  return (
    <div className="page-stack">
      <section className="hero-panel training-hero">
        <div>
          <span className="eyebrow">{t('integration.training.eyebrow')}</span>
          <h1>{t('integration.training.title')}</h1>
          <p>{t('integration.training.subtitle')}</p>
        </div>
        <div className="action-row wrap-actions">
          <button className="primary-button" onClick={() => install.mutate()} disabled={install.isPending}>{data?.sandbox_installed ? t('integration.training.reinstall') : t('integration.training.install')}</button>
          <button className="ghost-button danger" onClick={() => reset.mutate()} disabled={reset.isPending}>{t('integration.training.reset')}</button>
          <Link className="primary-link" to="/docs/onec/academy/training-sandbox-executable-docs">{t('integration.training.openDocs')}</Link>
        </div>
      </section>

      <section className="guidance-strip">
        <div className="guidance-head">
          <div>
            <span className="eyebrow">Учебный маршрут</span>
            <h2>Учебный маршрут: сначала безопасный пример, потом свой сценарий</h2>
            <p>Training Sandbox создаёт mock-подключения, endpoints, flows и test cases. Это самый быстрый способ понять OMH без доступа к реальной 1С, DNP, WMS или принтеру.</p>
          </div>
          <div className="action-row wrap-actions">
            <Link className="ghost-button" to="/integration-start">Подобрать свой сценарий</Link>
            <Link className="ghost-button" to="/docs/onec/start-here/beginner-path">Путь новичка</Link>
          </div>
        </div>
        <div className="guidance-step-grid">
          <article className="guidance-step-card"><span>1</span><strong>Установите sandbox</strong><p>Кнопка создаст учебные OData/REST-подключения, интеграции и примеры. Это не трогает production-системы.</p></article>
          <article className="guidance-step-card"><span>2</span><strong>Запустите пример</strong><p>Нажмите <code>Запустить</code> на карточке урока. OMH выполнит реальный сценарий на mock-данных.</p></article>
          <article className="guidance-step-card"><span>3</span><strong>Откройте Timeline</strong><p>Проверьте шаги, artifacts, request/response и ошибку, если пример специально падает.</p></article>
          <article className="guidance-step-card"><span>4</span><strong>Повторите в Test Console</strong><p>Откройте пример в Test Console и меняйте payload, чтобы увидеть, как меняется результат.</p></article>
        </div>
      </section>

      {(install.error instanceof Error || reset.error instanceof Error || run.error instanceof Error) && <ErrorState error={(install.error || reset.error || run.error) as Error} />}

      <section className="metadata-grid training-metrics">
        <div className="metric-card">
          <span>{t('integration.training.package')}</span>
          <strong>{data?.package.installed ? t('status.installed') : t('status.available')}</strong>
          <StatusBadge status={data?.package.enabled ? 'enabled' : 'disabled'} compact />
        </div>
        <div className="metric-card">
          <span>{t('integration.training.connectors')}</span>
          <strong>{data?.connectors.length ?? 0}</strong>
        </div>
        <div className="metric-card">
          <span>{t('integration.training.flows')}</span>
          <strong>{data?.flows.length ?? 0}</strong>
        </div>
        <div className="metric-card">
          <span>{t('integration.training.examples')}</span>
          <strong>{data?.examples.length ?? 0}</strong>
        </div>
      </section>

      <div className="two-column-page">
        <section className="panel page-stack">
          <div className="panel-toolbar">
            <div>
              <span className="eyebrow">{t('integration.training.examples')}</span>
              <h2>{t('integration.training.executableLessons')}</h2>
              <p className="microcopy">{t('integration.training.examplesHint')}</p>
            </div>
          </div>
          <div className="training-example-list">
            {(data?.examples ?? []).map((example) => {
              const title = example.title[language] ?? example.title.ru ?? example.id;
              const description = example.description[language] ?? example.description.ru ?? '';
              const caseRow = data?.test_cases.find((item) => item.name.endsWith(example.id));
              return (
                <article className="docs-example-card compact-training-card" key={example.id}>
                  <div className="docs-example-head">
                    <div>
                      <span className="eyebrow">{example.id}</span>
                      <h3>{title}</h3>
                      <p>{description}</p>
                    </div>
                    <div className="docs-example-actions">
                      <button className="primary-button" onClick={() => run.mutate(example.id)} disabled={!data?.sandbox_installed || run.isPending}>{t('integration.training.run')}</button>
                      <Link className="ghost-button" to={`/test-console?trainingExampleId=${encodeURIComponent(example.id)}`}>{t('docs.openInTestConsole')}</Link>
                    </div>
                  </div>
                  <div className="metadata-grid compact-grid">
                    <span>{t('docs.endpoint')}<strong>POST /api/bus/in/{example.endpoint_slug}</strong></span>
                    <span>{t('docs.input')}<strong>{example.input_mode}</strong></span>
                    <span>{t('common.status')}<strong>{caseRow?.last_run_status ?? t('status.pending')}</strong></span>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
        <section className="page-stack">
          {timelineUrl && <Link className="primary-link" to={timelineUrl}>{t('integration.training.openLastTimeline')}</Link>}
          <JsonBlock title={t('integration.training.lastRun')} value={selectedResult ?? { hint: t('integration.training.runHint') }} searchable />
          <JsonBlock title={t('integration.training.installedConnectors')} value={data?.connectors ?? []} searchable={false} />
          <JsonBlock title={t('integration.training.installedFlows')} value={data?.flows ?? []} searchable={false} />
        </section>
      </div>
    </div>
  );
}
