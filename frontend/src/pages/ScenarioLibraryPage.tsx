import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { scenarioLibraryApi } from '../api/scenarioLibrary';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';

export function ScenarioLibraryPage() {
  const queryClient = useQueryClient();
  const scenarios = useQuery({ queryKey: ['scenario-library'], queryFn: scenarioLibraryApi.list });
  const preview = useMutation({ mutationFn: scenarioLibraryApi.preview });
  const install = useMutation({
    mutationFn: (code: string) => scenarioLibraryApi.install(code),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['test-cases'] });
      queryClient.invalidateQueries({ queryKey: ['integration-flows'] });
      queryClient.invalidateQueries({ queryKey: ['bus-endpoints'] });
    },
  });

  if (scenarios.isLoading) return <LoadingState label="Loading scenario library" />;
  if (scenarios.error) return <ErrorState error={scenarios.error} />;

  return (
    <div className="page-stack">
      <section className="page-header designer-hero">
        <span className="eyebrow">1C Tools</span>
        <h1>Scenario Library</h1>
        <p>Install practical 1C/API/XML/printer integration presets without editing backend code.</p>
      </section>

      <section className="guidance-strip">
        <div className="guidance-head">
          <div>
            <span className="eyebrow">Как использовать библиотеку</span>
            <h2>Сначала посмотрите Preview, потом устанавливайте сценарий</h2>
            <p>Scenario Library ставит готовые endpoint, flow, operation и тестовые примеры. Preview показывает, что именно будет создано, Install добавляет сценарий в рабочую среду, а дальше его нужно открыть в интеграциях или Test Console и проверить на реальном payload.</p>
          </div>
          <div className="action-row wrap-actions">
            <Link className="primary-link" to="/integration-start">Подобрать сценарий</Link>
            <Link className="ghost-button" to="/training">Учебный пример</Link>
            <Link className="ghost-button" to="/docs/core/start/integration-scenarios">Документация</Link>
          </div>
        </div>
        <div className="guidance-step-grid">
          <div className="guidance-step-card"><span>01</span><strong>Preview</strong><small>Проверьте slug, источник, цель, operation и тестовые данные до установки.</small></div>
          <div className="guidance-step-card"><span>02</span><strong>Install</strong><small>Создайте готовую заготовку без ручной сборки backend-конфигурации.</small></div>
          <div className="guidance-step-card"><span>03</span><strong>Open and test</strong><small>Откройте flow, отправьте тестовый запрос и проверьте Timeline.</small></div>
        </div>
      </section>

      {(preview.error instanceof Error || install.error instanceof Error) && <div className="error-state compact">{(preview.error as Error | null)?.message ?? (install.error as Error | null)?.message}</div>}
      <section className="scenario-library-grid">
        {scenarios.data?.length ? scenarios.data.map((scenario) => (
          <article className="panel scenario-install-card" key={scenario.code}>
            <div className="panel-toolbar">
              <div><span className="eyebrow">{scenario.code}</span><h2>{scenario.title}</h2></div>
              <StatusBadge status="ok" />
            </div>
            <p>{scenario.description}</p>
            <div className="metadata-grid compact-grid">
              <span>Source<strong>{scenario.source}</strong></span>
              <span>Target<strong>{scenario.target}</strong></span>
              <span>Input<strong>{scenario.input_modes.join(', ')}</strong></span>
            </div>
            <div className="badge-row"><span className="status-badge info compact">{scenario.operation_code}</span><span className="status-badge muted compact">/{scenario.default_slug}</span></div>
            <div className="action-row">
              <button className="ghost-button" onClick={() => preview.mutate(scenario.code)} disabled={preview.isPending}>Preview</button>
              <button className="primary-button" onClick={() => install.mutate(scenario.code)} disabled={install.isPending}>Install</button>
              <Link className="primary-link" to="/integration-designer">Open designer</Link>
            </div>
          </article>
        )) : (
          <EmptyState
            title="No scenarios"
            detail="Пока нет готовых preset-сценариев. Можно начать через Scenario Router или учебный пример."
            actions={<><Link className="primary-link" to="/integration-start">Подобрать сценарий</Link><Link className="ghost-button" to="/training">Учебный пример</Link></>}
          />
        )}
      </section>
      {preview.data && <JsonBlock title="Preview" value={preview.data} searchable={false} />}
      {install.data && (
        <section className="panel page-stack">
          <div className="panel-toolbar">
            <div><span className="eyebrow">Сценарий установлен</span><h2>Следующий шаг: проверить выполнение</h2></div>
            <div className="action-row wrap-actions">
              <Link className="primary-link" to="/integration-flows">Открыть интеграции</Link>
              <Link className="ghost-button" to="/test-console">Отправить тест</Link>
              <Link className="ghost-button" to="/events">Проверить Timeline</Link>
            </div>
          </div>
          <JsonBlock title="Installed scenario" value={install.data} searchable={false} />
        </section>
      )}
    </div>
  );
}
