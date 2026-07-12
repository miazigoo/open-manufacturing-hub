import type { XmlODataXmlExtractConfig, XmlODataXmlExtractField } from './types';

interface XmlExtractStepProps {
  extract: XmlODataXmlExtractConfig;
  onChange: (value: XmlODataXmlExtractConfig) => void;
}

export function XmlExtractStep({ extract, onChange }: XmlExtractStepProps) {
  function update(index: number, patch: Partial<XmlODataXmlExtractField>) {
    const fields = extract.fields.map((field, itemIndex) => (itemIndex === index ? { ...field, ...patch } : field));
    onChange({ fields });
  }

  function addField() {
    onChange({ fields: [...extract.fields, { name: 'new_field', path: '/Request/NewField', required: false, mode: 'first', example: '' }] });
  }

  function removeField(index: number) {
    onChange({ fields: extract.fields.filter((_, itemIndex) => itemIndex !== index) });
  }

  const sample = Object.fromEntries(extract.fields.map((field) => [field.name, field.example ?? (field.required ? '<required>' : null)]));

  return (
    <section className="wizard-step integration-master-step xml-odata-extract-step">
      <span className="step-index">02</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">XML extract fields</span>
          <h2>Какие поля достать из XML</h2>
          <p>Эти имена станут переменными для OData filter и response template: <code>order_number</code>, <code>operation</code>, <code>format</code>.</p>
        </div>
        <button type="button" className="secondary-button" onClick={addField}>Добавить поле из XML</button>
      </div>

      <div className="xml-extract-table">
        <div className="xml-path-head"><span>Variable name</span><span>XML path</span><span>Required</span><span>Example</span><span /></div>
        {extract.fields.map((field, index) => (
          <div className="xml-path-row" key={`${field.name}-${index}`}>
            <input value={field.name} onChange={(event) => update(index, { name: event.target.value })} />
            <input value={field.path} onChange={(event) => update(index, { path: event.target.value })} />
            <label className="check-row"><input type="checkbox" checked={field.required} onChange={(event) => update(index, { required: event.target.checked })} /> yes</label>
            <input value={String(field.example ?? '')} onChange={(event) => update(index, { example: event.target.value })} />
            <button type="button" className="ghost-button" onClick={() => removeField(index)}>Удалить</button>
          </div>
        ))}
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <span className="builder-help-card"><strong>Проверить извлечение</strong><span>Preview backend реально применит эти paths к sample XML.</span></span>
        <pre className="json-block">{JSON.stringify(sample, null, 2)}</pre>
      </div>
    </section>
  );
}
