import { API_BASE_URL } from '../../api/client';
import { CodeBlock } from '../../components/CodeBlock';
import { CopyButton } from '../../components/product/CopyButton';
import { SectionCard } from '../../components/product/SectionCard';

const endpointPath = '/api/marking-code-pools/onec/export-file';

const base64Example = `{
  "source_system": "1C ERP",
  "source_document_id": "AEAE-000137",
  "source_document_name": "Заказ на эмиссию AEAE-000137",
  "order_number": "260703/5442",
  "full_codes_base64": [
    "MDEwNDY0NjE1MTY5NzE4NjIx..."
  ],
  "actions_override": {
    "local_outbox": true,
    "laser_file": false,
    "external_forward": true
  },
  "metadata_json": {
    "product": "power-supply"
  }
}`;

const legacyExample = `{
  "order_number": "260703/5442",
  "codes": [
    "0104646151697186215_<qlk<ZbCWFP>W2)foU{GS}93lzhU"
  ],
  "gs_marker": "{GS}"
}`;

const oneCExample = `Соединение = Новый HTTPСоединение("omh-server", 8710);
Запрос = Новый HTTPЗапрос("/api/marking-code-pools/onec/export-file");
Запрос.Заголовки.Вставить("Content-Type", "application/json");

// Сформируйте JSON с order_number и full_codes_base64
Запрос.УстановитьТелоИзСтроки(СтрокаJSON, КодировкаТекста.UTF8);

Ответ = Соединение.ОтправитьДляОбработки(Запрос);`;

export function EndpointTab() {
  const url = `${API_BASE_URL.replace(/\/$/, '')}${endpointPath}`;
  const curl = `curl -X POST '${url}' \\
  -H 'Content-Type: application/json' \\
  -d '${base64Example.replaceAll("'", "'\\''")}'`;
  return (
    <div className="page-stack">
      <SectionCard title="Endpoint для 1С" description="Используйте этот адрес из 1С. Если backend опубликован за reverse proxy, задайте PUBLIC_BASE_URL/PUBLIC_API_BASE_URL в окружении и используйте внешний URL.">
        <div className="endpoint-url-box">
          <span>POST</span>
          <code>{url}</code>
          <CopyButton value={url} label="Скопировать URL" copiedLabel="URL скопирован" />
        </div>
      </SectionCard>

      <section className="workbench-grid">
        <SectionCard title="JSON example — full_codes_base64" description="full_codes_base64 — полные коды в Base64, включая GS-разделители. actions_override задаёт, делать ли SMB и внешнюю отправку в этом конкретном запросе.">
          <CodeBlock code={base64Example} language="json" copyLabel="Скопировать JSON" copiedLabel="JSON скопирован" />
        </SectionCard>
        <SectionCard title="JSON example — строки с маркером {GS}" description="OMH заменит {GS} на настоящий символ GS.">
          <CodeBlock code={legacyExample} language="json" copyLabel="Скопировать JSON" copiedLabel="JSON скопирован" />
        </SectionCard>
      </section>

      <section className="workbench-grid lower">
        <SectionCard title="curl для разработчика">
          <CodeBlock code={curl} language="bash" copyLabel="Скопировать curl" copiedLabel="curl скопирован" />
        </SectionCard>
        <SectionCard title="Пример 1С-кода">
          <CodeBlock code={oneCExample} language="1c" copyLabel="Скопировать 1С-код" copiedLabel="1С-код скопирован" />
        </SectionCard>
      </section>
    </div>
  );
}
