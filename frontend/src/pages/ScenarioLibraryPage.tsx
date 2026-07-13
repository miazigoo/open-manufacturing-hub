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

  if (scenarios.isLoading) return <LoadingState label="Загрузка библиотеки сценариев" />;
  if (scenarios.error) return <ErrorState error={scenarios.error} />;

  return (
    <div className="page-stack">
      <section className="page-header designer-hero">
        <span className="eyebrow">Готовые presets</span>
        <h1>Библиотека сценариев</h1>
        <p>Установите практический сценарий 1C/API/XML/печати без ручного редактирования backend-конфигурации. Сначала смотрите Preview, затем устанавливайте и проверяйте через Test Console и Timeline.</p>
      </section>

      <section className="guidance-strip">
        <div className="guidance-head">
          <div>
            <span className="eyebrow">Как использовать библиотеку</span>
            <h2>Сначала Preview, потом установка и тест</h2>
            <p>Библиотека создаёт готовые endpoint, flow, operation и тестовые примеры. Preview показывает состав изменений до записи, установка добавляет сценарий в рабочую среду, а затем его нужно открыть в интеграциях или Test Console и проверить на реальном payload.</p>
          </div>
          <div className="action-row wrap-actions">
            <Link className="primary-link" to="/integration-start">Подобрать сценарий</Link>
            <Link className="ghost-button" to="/training">Учебный пример</Link>
            <Link className="ghost-button" to="/docs/core/start/integration-scenarios">Документация</Link>
          </div>
        </div>
        <div className="guidance-step-grid">
          <div className="guidance-step-card"><span>01</span><strong>Preview</strong><small>Проверьте slug, источник, цель, operation и тестовые данные до установки.</small></div>
          <div className="guidance-step-card"><span>02</span><strong>Установить</strong><small>Создайте готовую заготовку без ручной сборки backend-конфигурации.</small></div>
          <div className="guidance-step-card"><span>03</span><strong>Открыть и проверить</strong><small>Откройте flow, отправьте тестовый запрос и проверьте Timeline.</small></div>
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
              <span>Источник<strong>{sourceLabel(scenario.source)}</strong></span>
              <span>Цель<strong>{targetLabel(scenario.target)}</strong></span>
              <span>Формат входа<strong>{inputModesLabel(scenario.input_modes)}</strong></span>
            </div>
            <div className="badge-row">
              <span className="status-badge info compact">operation: {scenario.operation_code}</span>
              <span className="status-badge muted compact">endpoint: /{scenario.default_slug}</span>
            </div>
            <p className="microcopy">После установки проверьте сценарий тестовым payload и откройте Timeline. Не переносите в production без проверки ответа и artifacts.</p>
            <div className="action-row wrap-actions">
              <button className="ghost-button" onClick={() => preview.mutate(scenario.code)} disabled={preview.isPending}>Preview: посмотреть состав</button>
              <button className="primary-button" onClick={() => install.mutate(scenario.code)} disabled={install.isPending}>Установить сценарий</button>
              <Link className="primary-link" to="/integration-designer">Открыть дизайнер</Link>
            </div>
          </article>
        )) : (
          <EmptyState
            title="Сценариев пока нет"
            detail="Пока нет готовых preset-сценариев. Можно начать через Scenario Router или учебный пример."
            actions={<><Link className="primary-link" to="/integration-start">Подобрать сценарий</Link><Link className="ghost-button" to="/training">Учебный пример</Link></>}
          />
        )}
      </section>
      {preview.data && <JsonBlock title="Preview: что будет создано" value={preview.data} searchable={false} />}
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
          <div className="success-note">
            <strong>Endpoint готов для теста</strong>
            <span>{install.data.endpoint_url}</span>
          </div>
          {install.data.next_steps.length > 0 && (
            <div className="builder-help-card">
              <strong>Что сделать дальше</strong>
              {install.data.next_steps.map((step) => <span key={step}>{step}</span>)}
            </div>
          )}
          <JsonBlock title="Технические детали установки" value={install.data} searchable={false} />
        </section>
      )}
    </div>
  );
}

function sourceLabel(value: string) {
  const labels: Record<string, string> = {
    onec: '1C',
    external_api: 'Внешний API',
    website: 'Сайт',
    wms: 'WMS',
    omh_scheduler: 'OMH по расписанию',
  };
  return labels[value] ?? value;
}

function targetLabel(value: string) {
  const labels: Record<string, string> = {
    onec: '1C',
    external_api: 'Внешний API',
    printer: 'Принтер',
    odata_lookup: 'OData lookup',
    dnp: 'DNP / ЧЗ',
  };
  return labels[value] ?? value;
}

function inputModesLabel(modes: string[]) {
  const labels: Record<string, string> = {
    json: 'JSON',
    xml: 'XML',
    raw_text: 'Raw text',
    file: 'Файл',
  };
  return modes.map((mode) => labels[mode] ?? mode).join(', ');
}
