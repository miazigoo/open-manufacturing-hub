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
      {mode === 'build' ? <ODataIntegrationWizard /> : <ODataQuickTestMode />}
    </div>
  );
}
