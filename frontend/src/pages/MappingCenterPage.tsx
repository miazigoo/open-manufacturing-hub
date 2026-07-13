import { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { dataContractsApi } from '../api/dataContracts';
import { mappingCenterApi, type MappingProfile } from '../api/mappingCenter';
import { operationCatalogApi } from '../api/operationCatalog';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { JsonBlock } from '../components/JsonBlock';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { mappingToTemplate } from '../features/mapping-center/utils';

const tabs = [
  { id: 'all', label: 'Все сопоставления' },
  { id: 'operations', label: 'По операциям' },
  { id: 'patterns', label: 'По паттернам' },
  { id: 'templates', label: 'Шаблоны' },
];

export function MappingCenterPage() {
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const operationFilter = searchParams.get('operation');
  const [activeTab, setActiveTab] = useState('all');
  const [previewResult, setPreviewResult] = useState<unknown>(null);
  const mappingsQuery = useQuery({ queryKey: ['mapping-center-mappings'], queryFn: () => mappingCenterApi.list() });
  const contractsQuery = useQuery({ queryKey: ['data-contracts'], queryFn: () => dataContractsApi.list() });
  const operationsQuery = useQuery({ queryKey: ['operation-catalog-options'], queryFn: operationCatalogApi.options });
  const presetsQuery = useQuery({ queryKey: ['mapping-center-presets'], queryFn: mappingCenterApi.presets });
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['mapping-center-mappings'] });
    queryClient.invalidateQueries({ queryKey: ['data-contracts'] });
    queryClient.invalidateQueries({ queryKey: ['operation-catalog-operations'] });
    queryClient.invalidateQueries({ queryKey: ['operation-catalog-options'] });
  };
  const installPresets = useMutation({ mutationFn: mappingCenterApi.installPresets, onSuccess: (result) => { setPreviewResult(result); refresh(); } });
  const remove = useMutation({ mutationFn: mappingCenterApi.delete, onSuccess: refresh });
  const duplicate = useMutation({ mutationFn: duplicateMapping, onSuccess: refresh });
  const preview = useMutation({ mutationFn: (mapping: MappingProfile) => mappingCenterApi.preview({ mapping_profile_id: mapping.id }), onSuccess: setPreviewResult });
  const mappings = mappingsQuery.data ?? [];
  const contracts = contractsQuery.data ?? [];
  const operations = operationsQuery.data?.operations ?? [];
  const filtered = useMemo(() => mappings.filter((mapping) => filterMapping(mapping, activeTab, operationFilter)), [mappings, activeTab, operationFilter]);
  const mutationError = [installPresets.error, remove.error, duplicate.error, preview.error].find((error): error is Error => error instanceof Error);

  if (mappingsQuery.isLoading || contractsQuery.isLoading || operationsQuery.isLoading) return <LoadingState label="Загружаю Mapping Center" />;
  if (mappingsQuery.error) return <ErrorState error={mappingsQuery.error} />;
  if (contractsQuery.error) return <ErrorState error={contractsQuery.error} />;
  if (operationsQuery.error) return <ErrorState error={operationsQuery.error} />;

  async function duplicateMapping(mapping: MappingProfile) {
    return mappingCenterApi.create({
      name: `${mapping.name} copy`,
      code: `${mapping.code}_copy_${Date.now().toString(36)}`,
      description: mapping.description,
      source_context_json: mapping.source_context_json ?? null,
      target_contract_id: mapping.target_contract_id ?? null,
      operation_profile_id: mapping.operation_profile_id ?? null,
      mapping_json: mapping.mapping_json,
      package_id: mapping.package_id ?? null,
    });
  }

  return (
    <div className="page-stack mapping-center-page">
      <section className="page-header product-page-header connection-center-hero">
        <div>
          <span className="eyebrow">Data Contract & Mapping Center</span>
          <h1>Сопоставления</h1>
          <p>Контракт описывает какие поля операция ожидает, mapping описывает откуда эти поля взять: request, OData, foreach result или context.</p>
        </div>
        <div className="product-header-actions">
          <Link className="primary-button" to="/mapping-center/mappings/new">Создать mapping</Link>
          <button className="ghost-button" onClick={() => installPresets.mutate()} disabled={installPresets.isPending}>Установить presets</button>
          <Link className="ghost-button" to="/operation-catalog">Operation Catalog</Link>
          <Link className="ghost-button" to="/docs/core/data-contracts-and-mappings">Документация</Link>
        </div>
      </section>

      <section className="guidance-strip">
        <div className="guidance-head">
          <div>
            <span className="eyebrow">Когда нужен mapping</span>
            <h2>Mapping связывает результат сценария с контрактом операции</h2>
            <p>Используйте mapping, когда внешний endpoint ждёт другой JSON/XML, чем пришёл в OMH: например, нужно взять <code>codes[]</code> из foreach OData и положить в <code>payload.rows</code>.</p>
          </div>
          <div className="action-row wrap-actions">
            <Link className="ghost-button" to="/operation-catalog">Операции</Link>
            <Link className="ghost-button" to="/docs/core/data-contracts-and-mappings">Урок</Link>
          </div>
        </div>
        <div className="guidance-step-grid">
          <article className="guidance-step-card"><span>1</span><strong>Выберите target contract</strong><p>Контракт задаёт ожидаемые поля, типы и required-проверки. Без контракта mapping работает как raw template.</p></article>
          <article className="guidance-step-card"><span>2</span><strong>Добавьте source context</strong><p>Это пример реальных данных: request body, OData result, foreach array, context/run id. По нему builder покажет доступные переменные.</p></article>
          <article className="guidance-step-card"><span>3</span><strong>Проверьте Preview</strong><p>Preview показывает rendered payload, warnings и errors до того, как mapping попадёт в wizard или operation.</p></article>
        </div>
      </section>

      <section className="panel connection-center-toolbar">
        <div className="component-strip package-capabilities connection-tabs">
          {tabs.map((tab) => <button key={tab.id} type="button" className={activeTab === tab.id ? 'primary-button' : 'ghost-button'} onClick={() => setActiveTab(tab.id)}>{tab.label}</button>)}
        </div>
        {operationFilter && <p className="microcopy">Фильтр по операции: <code>{operationFilter}</code></p>}
        <div className="metadata-grid compact-grid no-margin">
          <span>Contracts<strong>{contracts.length}</strong></span>
          <span>Mappings<strong>{mappings.length}</strong></span>
          <span>Operations with contract<strong>{operations.filter((item) => item.request_contract_id || item.response_contract_id).length}</strong></span>
          <span>Built-in templates<strong>{presetsQuery.data?.mappings.length ?? 0}</strong></span>
        </div>
      </section>

      <section className="panel table-panel connection-profile-table">
        <div className="panel-toolbar"><h2>{tabs.find((tab) => tab.id === activeTab)?.label ?? 'Mappings'}</h2><span className="microcopy">{filtered.length} из {mappings.length}</span></div>
        {filtered.length === 0 ? <EmptyState title="Mappings пока нет" detail="Установите presets или создайте mapping profile для операции с контрактом." actions={<><Link className="primary-button" to="/mapping-center/mappings/new">Создать mapping</Link><button className="ghost-button" onClick={() => installPresets.mutate()} disabled={installPresets.isPending}>Установить presets</button><Link className="ghost-button" to="/operation-catalog">Operation Catalog</Link></>} /> : (
          <div className="table-scroll">
            <table>
              <thead><tr><th>Название</th><th>Операция</th><th>Целевой контракт</th><th>Статус</th><th>Используется где</th><th>Действия</th></tr></thead>
              <tbody>
                {filtered.map((mapping) => (
                  <tr key={mapping.id}>
                    <td><strong>{mapping.name}</strong><small>{mapping.code}</small></td>
                    <td><small>{mapping.operation_profile_name ?? mapping.operation_profile_code ?? '—'}</small></td>
                    <td><small>{mapping.target_contract_name ?? mapping.target_contract_code ?? 'raw template'}</small></td>
                    <td><StatusBadge status={mapping.status} compact /></td>
                    <td><small>{mapping.used_by.join(', ') || '—'}</small></td>
                    <td>
                      <div className="action-row wrap-actions compact-actions">
                        <Link className="ghost-button" to={`/mapping-center/mappings/${mapping.id}`}>Open</Link>
                        <button className="ghost-button" onClick={() => preview.mutate(mapping)} disabled={preview.isPending}>Test</button>
                        <button className="ghost-button" onClick={() => duplicate.mutate(mapping)} disabled={duplicate.isPending}>Duplicate</button>
                        <button className="ghost-button danger" onClick={() => window.confirm(`Удалить mapping ${mapping.name}?`) && remove.mutate(mapping.id)} disabled={remove.isPending}>Delete</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {activeTab === 'templates' && <PresetTemplates presets={presetsQuery.data?.mappings ?? []} />}
      {mutationError && <div className="error-state compact">{mutationError.message}</div>}
      {previewResult != null && <JsonBlock title="Preview / install result" value={previewResult} searchable />}
    </div>
  );
}

function PresetTemplates({ presets }: { presets: Array<Record<string, unknown>> }) {
  return <section className="panel"><div className="panel-toolbar"><h2>Встроенные шаблоны</h2><span className="microcopy">{presets.length}</span></div><div className="metadata-grid compact-grid no-margin">{presets.map((preset) => <article className="builder-help-card" key={String(preset.code)}><strong>{String(preset.name)}</strong><span><code>{String(preset.code)}</code></span><p className="microcopy">{String(preset.description ?? '')}</p><Link className="ghost-button" to={`/mapping-center/mappings/new?preset=${encodeURIComponent(String(preset.code))}`}>Открыть в builder</Link><details><summary>Raw template fallback</summary><pre className="microcopy">{mappingToTemplate(preset.mapping_json as Record<string, unknown>)}</pre></details></article>)}</div></section>;
}

function filterMapping(mapping: MappingProfile, tab: string, operationFilter: string | null) {
  if (operationFilter && mapping.operation_profile_id !== operationFilter) return false;
  if (tab === 'operations') return Boolean(mapping.operation_profile_id);
  if (tab === 'patterns') return !mapping.operation_profile_id && mapping.used_by.length > 0;
  if (tab === 'templates') return mapping.code.startsWith('mapping_');
  return true;
}
