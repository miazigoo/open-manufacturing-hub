import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { odataMasterApi } from '../../api/odataMaster';
import { ErrorState } from '../../components/ErrorState';
import { JsonBlock } from '../../components/JsonBlock';
import { LoadingState } from '../../components/LoadingState';
import type { ODataWizardStep } from './types';
import { FinalActionStep } from './components/FinalActionStep';
import { IncomingRequestStep } from './components/IncomingRequestStep';
import { IntegrationPreview } from './components/IntegrationPreview';
import { IntegrationSaveSuccess } from './components/IntegrationSaveSuccess';
import { ODataForeachStepEditor } from './components/ODataForeachStepEditor';
import { ODataStepEditor } from './components/ODataStepEditor';
import { SourceSystemStep } from './components/SourceSystemStep';
import { VariablePicker } from './components/VariablePicker';
import { WizardStepSummary } from './components/WizardStepSummary';
import { useODataConnections } from './hooks/useODataConnections';
import { useODataPreview } from './hooks/useODataPreview';
import { useODataVariables } from './hooks/useODataVariables';
import { useODataWizardDraft } from './hooks/useODataWizardDraft';

const wizardSteps = ['Входящий запрос', 'OData-шаги', 'Итоговое действие', 'Проверка', 'Сохранение'];

export function ODataIntegrationWizard() {
  const { spec, setSpec, resetDraft } = useODataWizardDraft();
  const [activeStep, setActiveStep] = useState(0);
  const [selectedConnectionName, setSelectedConnectionName] = useState('');
  const examples = useQuery({ queryKey: ['odata-master-examples'], queryFn: odataMasterApi.examples });
  const connections = useODataConnections();
  const variables = useODataVariables(spec);
  const { preview, save, runTest } = useODataPreview();

  useEffect(() => {
    if (!selectedConnectionName && connections.enabledConnections[0]) setSelectedConnectionName(connections.enabledConnections[0].name);
  }, [connections.enabledConnections, selectedConnectionName]);

  const selectedConnection = useMemo(() => connections.enabledConnections.find((item) => item.name === selectedConnectionName), [connections.enabledConnections, selectedConnectionName]);

  if (connections.isLoading || examples.isLoading) return <LoadingState label="Загружаем мастер OData" />;
  if (connections.error) return <ErrorState error={connections.error} />;

  function addStep(step: ODataWizardStep) {
    const withConnection = 'connection' in step && !step.connection && selectedConnectionName ? { ...step, connection: selectedConnectionName } as ODataWizardStep : step;
    setSpec({ ...spec, steps: [...spec.steps, withConnection] });
  }

  function removeStep(index: number) {
    setSpec({ ...spec, steps: spec.steps.filter((_, itemIndex) => itemIndex !== index) });
  }

  function loadExample(key: string) {
    const example = examples.data?.find((item) => item.key === key);
    if (!example) return;
    resetDraft(example.spec);
    const connection = example.spec.steps.find((step) => 'connection' in step)?.connection;
    if (connection) setSelectedConnectionName(connection);
    preview.reset();
    save.reset();
    setActiveStep(0);
  }

  return (
    <div className="page-stack odata-wizard-page">
      <section className="panel form-panel">
        <div className="panel-toolbar">
          <div>
            <span className="eyebrow">Мастер OData-интеграции</span>
            <h1>Собрать интеграцию</h1>
            <p className="microcopy">Путь: входящий запрос, OData-запросы, итоговое действие, проверка, сохранение.</p>
          </div>
          <div className="toolbar-actions">
            {examples.data?.map((example) => <button key={example.key} type="button" className="ghost-button" onClick={() => loadExample(example.key)}>{example.title}</button>)}
          </div>
        </div>
        <div className="segmented-control odata-master-stepper">
          {wizardSteps.map((title, index) => <button key={title} type="button" className={activeStep === index ? 'active' : ''} onClick={() => setActiveStep(index)}>{index + 1}. {title}</button>)}
        </div>
      </section>

      {activeStep === 0 && <IncomingRequestStep spec={spec} onChange={setSpec} />}

      {activeStep === 1 && (
        <>
          <SourceSystemStep connections={connections.enabledConnections} selected={selectedConnectionName} onSelect={setSelectedConnectionName} />
          {selectedConnection && <div className="success-note">Активное подключение для новых шагов<span>{selectedConnection.name}</span></div>}
          <VariablePicker groups={variables} />
          <ODataStepEditor connectionName={selectedConnectionName} onAdd={addStep} />
          <ODataForeachStepEditor connectionName={selectedConnectionName} steps={spec.steps} onAdd={addStep} />
          <section className="panel form-panel">
            <div className="panel-toolbar"><h2>Черновик OData-шагов</h2></div>
            <WizardStepSummary steps={spec.steps} onRemove={removeStep} />
          </section>
        </>
      )}

      {activeStep === 2 && <FinalActionStep value={spec.final_action} onChange={(final_action) => setSpec({ ...spec, final_action })} />}

      {activeStep === 3 && (
        <>
          <section className="panel form-panel">
            <div className="panel-toolbar">
              <div>
                <span className="eyebrow">Проверка</span>
                <h2>Проверьте flow до сохранения</h2>
                <p className="microcopy">Preview покажет OData requests, foreach iterations, outgoing endpoint request и response to caller.</p>
              </div>
              <div className="toolbar-actions">
                <button type="button" className="primary-button" onClick={() => preview.mutate({ spec, run_real_queries: false })} disabled={preview.isPending || spec.steps.length === 0}>Проверить интеграцию</button>
                <button type="button" className="ghost-button" onClick={() => runTest.mutate({ spec, run_real_queries: true })} disabled={runTest.isPending || spec.steps.length === 0}>Run test с реальными OData</button>
              </div>
            </div>
            {runTest.error instanceof Error && <div className="error-state compact">{runTest.error.message}</div>}
          </section>
          <IntegrationPreview preview={preview.data} error={preview.error instanceof Error ? preview.error : null} pending={preview.isPending} />
          {runTest.data && <JsonBlock title="Run test result" value={runTest.data.result} searchable />}
        </>
      )}

      {activeStep === 4 && (
        <>
          <section className="panel form-panel">
            <div className="panel-toolbar">
              <div>
                <span className="eyebrow">Сохранение</span>
                <h2>Сохранить как рабочую интеграцию</h2>
                <p className="microcopy">OMH создаст endpoint, route, compiled workflow и saved test case. Низкоуровневые детали остаются в advanced pages.</p>
              </div>
              <button type="button" className="primary-button" onClick={() => save.mutate(spec)} disabled={save.isPending || spec.steps.length === 0}>Сохранить интеграцию</button>
            </div>
            <WizardStepSummary steps={spec.steps} />
            {save.error instanceof Error && <div className="error-state compact">{save.error.message}</div>}
          </section>
          <IntegrationSaveSuccess result={save.data} />
        </>
      )}

      <div className="action-row wrap-actions">
        <button type="button" className="ghost-button" disabled={activeStep === 0} onClick={() => setActiveStep((current) => Math.max(0, current - 1))}>Назад</button>
        <button type="button" className="primary-button" disabled={activeStep === wizardSteps.length - 1} onClick={() => setActiveStep((current) => Math.min(wizardSteps.length - 1, current + 1))}>Следующий шаг</button>
      </div>
    </div>
  );
}
