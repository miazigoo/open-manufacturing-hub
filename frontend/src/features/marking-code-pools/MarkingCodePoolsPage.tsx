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

const tabs = [
  ['overview', 'Обзор'],
  ['settings', 'Настройки'],
  ['endpoint', 'Endpoint для 1С'],
  ['test', 'Тест'],
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
        <h1>Пулы кодов Честного знака</h1>
        <p>Конкретный production-инструмент: 1С отправила пул кодов, OMH сохранил файл, при необходимости сделал SMB-копию и отправил данные дальше.</p>
        <div className="hero-meta">
          <StatusBadge status={settings.data?.local_outbox.required ? 'enabled' : 'disabled'} label="локальный архив" />
          <StatusBadge status={settings.data?.laser.enabled ? 'enabled' : 'disabled'} label="лазер / SMB" />
          <StatusBadge status={settings.data?.forward.enabled ? 'enabled' : 'disabled'} label={settings.data?.forward.service_name ?? 'внешняя отправка'} />
          <Link className="primary-link" to="/docs/onec/recipes/onec-sends-chz-code-pool-file">Инструкция</Link>
          <span className="microcopy">{exports.length} экспортов</span>
        </div>
      </section>

      <div className="segmented-control chz-tabs" role="tablist" aria-label="Пулы кодов ЧЗ">
        {tabs.map(([id, label]) => <button key={id} type="button" className={activeTab === id ? 'active' : ''} onClick={() => setActiveTab(id)}>{label}</button>)}
      </div>

      {activeTab === 'overview' && <OverviewTab settings={settings.data} exports={exports} />}
      {activeTab === 'settings' && <SettingsTab settings={settings.data} />}
      {activeTab === 'endpoint' && <EndpointTab />}
      {activeTab === 'test' && <TestTab />}
      {activeTab === 'journal' && <ExportsJournalTab exports={exports} settings={settings.data} />}
    </div>
  );
}
