import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { StatusBadge } from '../../components/StatusBadge';
import { markingCodePoolsApi } from './api';
import { EndpointTab } from './EndpointTab';
import { ExportsJournalTab } from './ExportsJournalTab';
import { OverviewTab } from './OverviewTab';
import { SettingsTab } from './SettingsTab';
import { TestTab } from './TestTab';
import { AggregationsTab } from './AggregationsTab';
import { PullFromDnpTab } from './PullFromDnpTab';
import { RoutingRulesTab } from './RoutingRulesTab';

const tabs = [
  ['overview', 'Обзор'],
  ['settings', 'Настройки'],
  ['endpoint', 'Endpoint для 1С'],
  ['test', 'Тест'],
  ['routing', 'Маршрутизация'],
  ['aggregations', 'Агрегация -> 1С'],
  ['pull-from-dnp', 'Получение кодов из DnP'],
  ['journal', 'Журнал экспортов'],
] as const;

type TabId = typeof tabs[number][0];

export function MarkingCodePoolsPage() {
  const initialTab = useMemo<TabId>(() => {
    const value = new URLSearchParams(window.location.search).get('tab');
    return tabs.some(([id]) => id === value) ? value as TabId : 'overview';
  }, []);
  const [activeTab, setActiveTab] = useState<TabId>(initialTab);
  const settings = useQuery({ queryKey: ['marking-code-pools-settings'], queryFn: markingCodePoolsApi.settings });
  const exportsQuery = useQuery({ queryKey: ['marking-code-pools-exports'], queryFn: markingCodePoolsApi.exports });

  if (settings.isLoading || exportsQuery.isLoading) return <LoadingState label="Загрузка пулов кодов ЧЗ" />;
  const error = settings.error ?? exportsQuery.error;
  if (error) return <ErrorState error={error} />;

  const exports = exportsQuery.data ?? [];
  return (
    <div className="page-stack marking-code-pools-page">
      <section className="page-header onec-hero chz-hero">
        <span className="eyebrow">1С / Честный знак</span>
        <h1>Пулы кодов маркировки Честного знака</h1>
        <p>Конкретный production-инструмент: 1С отправила пул кодов, OMH сохранил файл, при необходимости сделал SMB-копию и отправил данные дальше.</p>
        <div className="hero-meta">
          <StatusBadge status={settings.data?.local_outbox.required ? 'enabled' : 'disabled'} label="локальный архив" />
          <StatusBadge status={settings.data?.laser.enabled ? 'enabled' : 'disabled'} label="лазер / SMB" />
          <StatusBadge status={settings.data?.forward.enabled ? 'enabled' : 'disabled'} label={settings.data?.forward.service_name ?? 'внешняя отправка'} />
          <Link className="primary-link" to="/docs/onec/recipes/onec-sends-chz-code-pool-file">Инструкция</Link>
          <span className="microcopy">{exports.length} экспортов</span>
        </div>
      </section>

      <section className="guidance-strip">
        <div className="guidance-head">
          <div>
            <span className="eyebrow">Как не потерять пул кодов</span>
            <h2>Сначала archive, затем optional copy/send</h2>
            <p>Workbench сохраняет исходный запрос и файл локально, а SMB-копия и отправка во внешний endpoint идут как отдельные retryable действия. Поэтому сбой лазера или DNP не теряет исходный пул.</p>
          </div>
          <div className="action-row wrap-actions">
            <Link className="ghost-button" to="/connection-center">Профили подключений</Link>
            <Link className="ghost-button" to="/operation-catalog">Операции отправки</Link>
          </div>
        </div>
        <div className="guidance-step-grid">
          <article className="guidance-step-card"><span>1</span><strong>Проверьте настройки</strong><p>На вкладке <code>Настройки</code> выберите local outbox, SMB/local target и REST Operation Profile для внешней отправки.</p></article>
          <article className="guidance-step-card"><span>2</span><strong>Сделайте preview</strong><p>Вкладка <code>Тест</code> показывает имя файла, payload и предупреждения до реального экспорта из 1С.</p></article>
          <article className="guidance-step-card"><span>3</span><strong>Смотрите журнал</strong><p>В <code>Журнале экспортов</code> видны archive/copy/forward статусы и retry для каждого неуспешного действия.</p></article>
          <article className="guidance-step-card"><span>4</span><strong>Коды для 1С</strong><p>Вкладка <code>Получение кодов из DnP</code> забирает упакованные коды из DnP для документа «Нанесение и ввод в оборот».</p></article>
          <article className="guidance-step-card"><span>5</span><strong>Правила</strong><p>Вкладка <code>Маршрутизация</code> делит пул по GTIN, серийнику или заказу и отправляет части в разные места — без программирования.</p></article>
        </div>
      </section>

      <div className="segmented-control chz-tabs" role="tablist" aria-label="Пулы кодов ЧЗ">
        {tabs.map(([id, label]) => <button key={id} type="button" className={activeTab === id ? 'active' : ''} onClick={() => setActiveTab(id)}>{label}</button>)}
      </div>

      {activeTab === 'overview' && <OverviewTab settings={settings.data} exports={exports} />}
      {activeTab === 'settings' && <SettingsTab settings={settings.data} />}
      {activeTab === 'endpoint' && <EndpointTab />}
      {activeTab === 'test' && <TestTab />}
      {activeTab === 'routing' && <RoutingRulesTab />}
      {activeTab === 'aggregations' && <AggregationsTab />}
      {activeTab === 'pull-from-dnp' && <PullFromDnpTab />}
      {activeTab === 'journal' && <ExportsJournalTab exports={exports} settings={settings.data} />}
    </div>
  );
}
