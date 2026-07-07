import { useState } from 'react';
import { buildOneCObjectResource } from '../utils/odataResource';

interface ODataResourceBuilderProps { onUse: (resource: string) => void }

export function ODataResourceBuilder({ onUse }: ODataResourceBuilderProps) {
  const [baseResource, setBaseResource] = useState('Document_ЗаказНаПроизводство2_2');
  const [keyVariable, setKeyVariable] = useState('order.Ref_Key');
  const [tabularPart, setTabularPart] = useState('Продукция');
  const preview = buildOneCObjectResource(baseResource, keyVariable, tabularPart);

  return (
    <div className="builder-help-card">
      <strong>Build 1C object resource</strong>
      <span>Для табличных частей 1C используйте object resource вместо ручной сборки строки.</span>
      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">Base resource<input value={baseResource} onChange={(event) => setBaseResource(event.target.value)} /></label>
        <label className="field-label">Key variable<input value={keyVariable} onChange={(event) => setKeyVariable(event.target.value)} /></label>
        <label className="field-label">Tabular part<input value={tabularPart} onChange={(event) => setTabularPart(event.target.value)} /></label>
      </div>
      <div className="success-note">Preview<span>{preview}</span></div>
      <button type="button" className="ghost-button" onClick={() => onUse(preview)}>Use this resource</button>
    </div>
  );
}
