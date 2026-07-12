import { useMutation, useQuery } from '@tanstack/react-query';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { integrationPatternsApi, localized } from '../api/integrationPatterns';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { StatusBadge } from '../components/StatusBadge';
import { SectionCard } from '../components/product/SectionCard';

export function IntegrationPatternDetailPage() {
  const { patternId = '' } = useParams();
  const navigate = useNavigate();
  const pattern = useQuery({ queryKey: ['integration-pattern', patternId], queryFn: () => integrationPatternsApi.get(patternId), enabled: Boolean(patternId) });
  const start = useMutation({ mutationFn: integrationPatternsApi.start, onSuccess: (data) => navigate(data.wizard_route) });

  if (pattern.isPending) return <LoadingState label="Загрузка паттерна" />;
  if (pattern.error) return <ErrorState error={pattern.error} />;
  const item = pattern.data;
  if (!item) return <ErrorState error={new Error('Pattern not found')} />;

  return (
    <div className="page-stack integration-pattern-detail-page">
      <section className="page-header integration-start-hero">
        <span className="eyebrow">Integration Pattern</span>
        <h1>{localized(item.title)}</h1>
        <p>{localized(item.description)}</p>
        <div className="hero-meta">
          <StatusBadge status={item.status} label={item.status === 'available' ? 'доступен' : 'скоро'} />
          <span className="microcopy">{item.category} · {item.difficulty}</span>
          <span className="microcopy">{item.input_modes.join(', ')}</span>
        </div>
      </section>

      {start.error instanceof Error && <div className="error-state compact">{start.error.message}</div>}

      <section className="metadata-grid compact-grid no-margin">
        <span>Рекомендуемый мастер<strong>{localized(item.wizard_label, item.recommended_wizard)}</strong><small>{item.wizard_route ?? localized(item.start_disabled_reason, 'wizard пока не реализован')}</small></span>
        <span>Пакеты<strong>{item.package_requirements.length ? item.package_requirements.join(', ') : 'core'}</strong><small>Пакеты проверяются на странице мастера/workbench.</small></span>
        <span>Docs<strong><Link className="primary-link" to={item.docs_link}>Открыть документацию</Link></strong><small>{item.docs_link}</small></span>
      </section>

      <section className="workbench-grid lower">
        <SectionCard title="Когда использовать">
          <ul className="pattern-list">{item.use_cases.map((useCase, index) => <li key={index}>{localized(useCase)}</li>)}</ul>
        </SectionCard>
        <SectionCard title="Что получится">
          <p>{localized(item.expected_result)}</p>
          <p className="microcopy">{localized(item.timeline_hint)}</p>
        </SectionCard>
      </section>

      <SectionCard title="Схема и шаги" description="Это intended step list. Мастер может показывать дополнительные проверки, но порядок задачи сохраняется.">
        <div className="pattern-flow">
          {(item.flow.length ? item.flow : item.initial_steps).map((step, index) => <span key={`${step}:${index}`}>{stepLabel(step)}</span>)}
        </div>
        <ol className="pattern-steps">
          {item.initial_steps.map((step, index) => <li key={`${step}:${index}`}><strong>{stepLabel(step)}</strong><small>{step}</small></li>)}
        </ol>
      </SectionCard>

      <section className="workbench-grid lower">
        <SectionCard title="Какие данные нужны">
          <ul className="pattern-list">{item.required_inputs.map((input, index) => <li key={index}>{localized(input)}</li>)}</ul>
        </SectionCard>
        <SectionCard title="Что можно протестировать">
          <ul className="pattern-list">{item.test_plan.map((test, index) => <li key={index}>{localized(test)}</li>)}</ul>
        </SectionCard>
      </section>

      <SectionCard title="Примеры" description="Эти scenario keys используются мастерами для предзаполнения или как ориентир.">
        {item.examples.length ? <div className="badge-row">{item.examples.map((example) => <span key={example} className="status-badge info compact">{example}</span>)}</div> : <p className="muted">Примеры не заданы.</p>}
      </SectionCard>

      <div className="action-row wrap-actions">
        <Link className="ghost-button" to="/integration-start">Назад к выбору сценария</Link>
        <button className="primary-button" disabled={item.status !== 'available' || start.isPending} onClick={() => start.mutate(item.pattern_id)}>Открыть мастер</button>
      </div>
    </div>
  );
}

function stepLabel(step: string): string {
  const labels: Record<string, string> = {
    input_contract: 'Входящий запрос',
    endpoint_for_1c: 'Endpoint для 1С',
    odata_query: 'OData Query',
    odata_object_query: 'OData Object/Tabular Query',
    foreach_odata: 'Foreach OData',
    payload_builder: 'Payload Builder',
    optional_payload_builder: 'Payload/Response Builder',
    final_action: 'Final Action',
    return_response: 'Вернуть ответ',
    send_endpoint: 'Отправить endpoint',
    caller_response: 'Ответ вызывающей системе',
    input_contract_xml: 'XML input contract',
    xml_extract: 'XML Extract',
    raw_xml_forward: 'Raw XML Forward',
    hash_check: 'Hash Check',
    xml_response_builder: 'XML Response Builder',
    local_outbox: 'Локальный архив',
    optional_laser_smb: 'Копия для лазера / SMB',
    laser_smb_copy: 'Копия для лазера / SMB',
    optional_external_forward: 'Внешняя отправка',
    external_forward: 'Внешняя отправка',
    journal: 'Журнал',
    printer_select: 'Выбор принтера',
    label_builder: 'Label/ZPL Builder',
    zpl_label_builder: 'ZPL Builder',
    print_action: 'Печать',
    odata_connection: 'OData Connection',
    polling_schedule: 'Расписание',
    change_detection: 'Change Detection',
    send_target: 'Send Target',
    odata_enrichment: 'OData Enrichment',
    send_website_api: 'Send Website API',
    extract_response: 'Extract Response',
    call_1c_http_service: 'Call 1C HTTP Service',
    writeback_1c: 'Write Back to 1С',
    test: 'Тест',
    save: 'Сохранить',
  };
  return labels[step] ?? step;
}
