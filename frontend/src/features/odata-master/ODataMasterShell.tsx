import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ODataIntegrationWizard } from './ODataIntegrationWizard';
import { ODataQuickTestMode } from './ODataQuickTestMode';

type MasterMode = 'build' | 'quick';

export function ODataMasterShell() {
  const [mode, setMode] = useState<MasterMode>('build');
  return (
    <div className="page-stack odata-master-shell">
      <section className="hero-panel">
        <div>
          <span className="eyebrow">OData-интеграции</span>
          <h1>Мастер OData-интеграции</h1>
          <p>Проверьте OData-запросы и сразу сохраните их как рабочую интеграцию.</p>
          <div className="hero-meta">
            <span>Просто, удобно и понятно интегрироваться.</span>
            <Link className="primary-link" to="/docs/onec/academy/odata-integration-master">Инструкция</Link>
          </div>
        </div>
        <div className="hero-instrument"><span>O</span><small>DATA MASTER</small></div>
      </section>
      <section className="panel form-panel">
        <div className="segmented-control">
          <button type="button" className={mode === 'build' ? 'active' : ''} onClick={() => setMode('build')}>Собрать интеграцию</button>
          <button type="button" className={mode === 'quick' ? 'active' : ''} onClick={() => setMode('quick')}>Быстро проверить OData</button>
          <button type="button" disabled>Timeline после запуска</button>
        </div>
      </section>
      <section className="panel form-panel odata-master-onboarding">
        <div className="panel-toolbar">
          <div>
            <span className="eyebrow">Safe OData workflow</span>
            <h2>Filter builder, $select и понятный результат</h2>
            <p className="microcopy">Choose the 1C base where OMH will search data. Затем выберите resource из metadata, соберите безопасный $filter и ограничьте ответ через $select.</p>
          </div>
          <Link className="primary-link" to="/odata-connections">Открыть OData Connections</Link>
        </div>
        <div className="metadata-grid compact-grid no-margin">
          <span>1. Connection<strong>Выберите базу 1С</strong></span>
          <span>2. Resource<strong>Скопируйте имя из metadata</strong></span>
          <span>3. Filter builder<strong>Не пишите сложный OData filter вслепую</strong></span>
          <span>4. $select<strong>Верните только поля для следующих шагов</strong></span>
        </div>
        <div className="odata-filter-builder">
          <div className="panel-toolbar compact-toolbar">
            <div>
              <h3>Конструктор фильтра</h3>
              <p className="microcopy">Стартовый пример: поле из 1С + оператор + значение из request. В мастере ниже этот шаблон можно заменить реальными переменными.</p>
            </div>
          </div>
          <div className="success-note">Compiled $filter<span>{"Number eq '{{request.body.Number}}'"}</span></div>
          <div className="hint-chip-row">
            {['Number eq {{request.body.Number}}', 'Ref_Key,Number,Date,Posted', 'Catalog_Контрагенты', 'Document_ЗаказНаПроизводство2_2'].map((hint) => (
              <button key={hint} type="button" className="hint-chip" onClick={() => navigator.clipboard?.writeText(hint)}>{hint}</button>
            ))}
          </div>
        </div>
      </section>
      {mode === 'build' ? <ODataIntegrationWizard /> : <ODataQuickTestMode />}
    </div>
  );
}
