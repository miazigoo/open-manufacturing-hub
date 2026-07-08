import type { IntegrationScenario } from './types';

interface ScenarioChooserProps {
  scenarios: IntegrationScenario[];
  selectedKey?: string;
  onSelect: (scenario: IntegrationScenario) => void;
}

export function ScenarioChooser({ scenarios, selectedKey, onSelect }: ScenarioChooserProps) {
  return (
    <div className="scenario-card-grid integration-scenario-grid">
      {scenarios.map((scenario) => (
        <button key={scenario.key} type="button" className={`scenario-card scenario-choice-card ${selectedKey === scenario.key ? 'primary selected' : ''}`} onClick={() => onSelect(scenario)} aria-pressed={selectedKey === scenario.key}>
          <div className="scenario-card-head">
            <span className="eyebrow">Сценарий</span>
            <strong>{selectedKey === scenario.key ? 'Выбрано' : 'Выбрать'}</strong>
          </div>
          <h3>{scenario.title}</h3>
          <p>{scenario.description}</p>
          <dl className="scenario-card-meta">
            <div><dt>Кто вызывает OMH</dt><dd>{scenario.caller}</dd></div>
            <div><dt>Что приходит</dt><dd>{scenario.incoming}</dd></div>
            <div className="wide"><dt>Что делает OMH дальше</dt><dd>{scenario.next_action}</dd></div>
          </dl>
        </button>
      ))}
    </div>
  );
}
