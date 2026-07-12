import { CodeEditor } from '../../../components/CodeEditor';
import type { PayloadBodyType } from '../../integration-master/types';
import type { RequestMultipleODataResponseResponseConfig } from './types';

interface ResponseBuilderStepProps {
  response: RequestMultipleODataResponseResponseConfig;
  orderSaveAs: string;
  itemsSaveAs: string;
  onChange: (value: RequestMultipleODataResponseResponseConfig) => void;
}

const RESPONSE_TYPES: Array<{ type: PayloadBodyType; title: string; description: string }> = [
  { type: 'xml', title: 'XML', description: 'Default для legacy caller: шапка заказа и loop по items.' },
  { type: 'json', title: 'JSON', description: 'Вернуть объект и сохранить массив строк как массив.' },
  { type: 'raw_text', title: 'Raw text', description: 'Вернуть одну строку или legacy text protocol.' },
];

export function ResponseBuilderStep({ response, orderSaveAs, itemsSaveAs, onChange }: ResponseBuilderStepProps) {
  const templateText = typeof response.template === 'string' ? response.template : JSON.stringify(response.template ?? {}, null, 2);
  const language = response.type === 'json' ? 'json' : response.type === 'xml' ? 'xml' : 'text';
  const variables = [`${orderSaveAs}.Ref_Key`, `${orderSaveAs}.Number`, `${orderSaveAs}.Date`, `${orderSaveAs}.Posted`, `${itemsSaveAs}`, `${itemsSaveAs}[0].Номенклатура_Key`, `${itemsSaveAs}[0].Количество`, `${itemsSaveAs}[0].Цена`, `${itemsSaveAs}[0].Сумма`];

  function changeType(type: PayloadBodyType) {
    onChange({ ...response, type, template: defaultTemplate(type, orderSaveAs || 'order', itemsSaveAs || 'items'), headers: defaultHeaders(type) });
  }

  function insert(path: string) {
    onChange({ ...response, template: `${templateText}${templateText.endsWith('\n') || !templateText ? '' : '\n'}{{${path}}}` });
  }

  return (
    <section className="wizard-step integration-master-step request-multiple-response-step">
      <span className="step-index">04</span>
      <div className="odata-step-heading">
        <div>
          <span className="eyebrow">Response builder</span>
          <h2>Что вернуть вызывающему сервису</h2>
          <p>Default XML поддерживает controlled loop: <code>{'{{#items}}...{{/items}}'}</code>. Внутри loop поля читаются относительно текущей строки.</p>
        </div>
        <span className="status-card success"><small>Response mode</small><strong>sync_response</strong></span>
      </div>

      <div className="metadata-grid compact-grid no-margin request-action-cards">
        {RESPONSE_TYPES.map((option) => (
          <button key={option.type} type="button" className={`builder-help-card action-card ${response.type === option.type ? 'active' : ''}`} onClick={() => changeType(option.type)}>
            <strong>{option.title}</strong>
            <span>{option.description}</span>
          </button>
        ))}
      </div>

      <div className="metadata-grid compact-grid no-margin">
        <label className="field-label">HTTP status<input type="number" min={100} max={599} value={response.status_code} onChange={(event) => onChange({ ...response, status_code: Number(event.target.value) || 200 })} /></label>
        <span className="builder-help-card"><strong>XML loop</strong><span><code>{'{{#items}}'}</code> открывает loop, <code>{'{{/items}}'}</code> закрывает. Поля внутри берутся из строки.</span></span>
        <span className="builder-help-card"><strong>JSON array</strong><span>В JSON используйте <code>{'"items": "{{items}}"'}</code>, чтобы сохранить массив.</span></span>
      </div>

      <details className="variable-card odata-variable-picker" open>
        <summary><span>Переменные ответа</span><strong>{variables.length}</strong></summary>
        <div className="odata-variable-grid">
          {variables.map((path) => <button key={path} type="button" className="builder-help-card" onClick={() => insert(path)}><strong>{path}</strong><span>Вставить <code>{`{{${path}}}`}</code></span></button>)}
        </div>
      </details>

      <label className="field-label">Response template<CodeEditor value={templateText} onChange={(template) => onChange({ ...response, template })} language={language} minRows={response.type === 'raw_text' ? 4 : 18} /></label>
    </section>
  );
}

export function defaultTemplate(type: PayloadBodyType, order = 'order', items = 'items') {
  if (type === 'json') {
    return `{
  "success": true,
  "order": {
    "uuid": "{{${order}.Ref_Key}}",
    "number": "{{${order}.Number}}",
    "date": "{{${order}.Date}}",
    "posted": "{{${order}.Posted}}"
  },
  "items": "{{${items}}}"
}`;
  }
  if (type === 'raw_text') return `OK order={{${order}.Number}} items={{${items}.length}}`;
  return `<Response>
  <Success>true</Success>
  <Order>
    <UUID>{{${order}.Ref_Key}}</UUID>
    <Number>{{${order}.Number}}</Number>
    <Date>{{${order}.Date}}</Date>
    <Posted>{{${order}.Posted}}</Posted>
  </Order>
  <Items>
    {{#${items}}}
    <Item>
      <ProductUUID>{{Номенклатура_Key}}</ProductUUID>
      <Quantity>{{Количество}}</Quantity>
      <Price>{{Цена}}</Price>
      <Amount>{{Сумма}}</Amount>
    </Item>
    {{/${items}}}
  </Items>
</Response>`;
}

export function defaultHeaders(type: PayloadBodyType) {
  if (type === 'xml') return { 'Content-Type': 'application/xml; charset=utf-8' };
  if (type === 'raw_text') return { 'Content-Type': 'text/plain; charset=utf-8' };
  return { 'Content-Type': 'application/json' };
}
