from __future__ import annotations

from app.docs_portal.schemas import DocsIndexRead, DocsPackageRead, DocsPageRead, DocsPageSummary, DocsSectionRead

UPDATED_AT = "2026-07-04"
SUPPORTED_LANGUAGES = {"ru", "en", "zh"}

DOC_PACKAGES = [
    {
        "id": "core",
        "title": {"ru": "Быстрый старт", "en": "Quick Start", "zh": "快速开始"},
        "description": {"ru": "Основа событий, очереди и timeline.", "en": "Events, queues and timeline basics.", "zh": "事件、队列和时间线基础。"},
        "sections": [
            {"id": "start", "title": {"ru": "Основа продукта", "en": "Product basics", "zh": "产品基础"}, "description": {"ru": "Ключевые понятия OMH.", "en": "Core OMH concepts.", "zh": "OMH 核心概念。"}, "pages": [
                {"slug": "overview", "title": {"ru": "Что такое OMH", "en": "What is OMH", "zh": "什么是 OMH"}, "description": {"ru": "Интеграционный runtime с наблюдаемыми событиями.", "en": "Integration runtime with observable events.", "zh": "带可观测事件的集成运行时。"}},
                {"slug": "concepts", "title": {"ru": "Основные понятия", "en": "Core concepts", "zh": "核心概念"}, "description": {"ru": "Endpoint, route, flow, workflow, mapping, resolver, package.", "en": "Endpoint, route, flow, workflow, mapping, resolver, package.", "zh": "端点、路由、流程、工作流、映射、解析器、软件包。"}},
            ]},
        ],
    },
    {
        "id": "onec",
        "title": {"ru": "1C", "en": "1C", "zh": "1C"},
        "description": {"ru": "OData, XML, HTTP-сервисы, Cockpit, Flow Builder, печать и диагностика.", "en": "OData, XML, HTTP services, Cockpit, Flow Builder, printing and diagnostics.", "zh": "OData、XML、HTTP 服务、驾驶舱、流程构建器、打印和诊断。"},
        "sections": [
            {"id": "start-here", "title": {"ru": "Начните здесь", "en": "Start here", "zh": "从这里开始"}, "description": {"ru": "Первый понятный маршрут для пользователя без опыта интеграций.", "en": "A first clear path for users new to integrations.", "zh": "面向集成新手的第一条清晰路径。"}, "pages": [
                {"slug": "start-in-15-minutes", "title": {"ru": "Start in 15 minutes", "en": "Start in 15 minutes", "zh": "15 分钟开始"}, "description": {"ru": "Короткий маршрут: что открыть, что создать и какой тест увидеть первым.", "en": "A short path: what to open, create and verify first.", "zh": "简短路径：先打开、创建和验证什么。"}},
                {"slug": "what-you-will-build", "title": {"ru": "What you will build", "en": "What you will build", "zh": "你将构建什么"}, "description": {"ru": "Единый Golden Scenario для всей академии.", "en": "The shared Golden Scenario for the academy.", "zh": "学院共享的黄金场景。"}},
                {"slug": "concepts", "title": {"ru": "Basic concepts for 1C users", "en": "Basic concepts for 1C users", "zh": "面向 1C 用户的基础概念"}, "description": {"ru": "Endpoint, OData Connection, Flow, Step, Variable, Timeline, Artifact и DLQ.", "en": "Endpoint, OData Connection, Flow, Step, Variable, Timeline, Artifact and DLQ.", "zh": "端点、OData 连接、流程、步骤、变量、时间线、工件和 DLQ。"}},
                {"slug": "beginner-path", "title": {"ru": "Начните здесь: первый понятный обмен с 1C", "en": "Start here: first understandable 1C exchange", "zh": "从这里开始：第一个易懂的 1C 交换"}, "description": {"ru": "Endpoint, token, OData profile, Flow, Test Console и Timeline простыми словами.", "en": "Endpoint, token, OData profile, Flow, Test Console and Timeline in plain language.", "zh": "用简单语言解释端点、令牌、OData 配置、Flow、Test Console 和 Timeline。"}},
            ]},
            {"id": "academy", "title": {"ru": "1C Integration Academy", "en": "1C Integration Academy", "zh": "1C 集成学院"}, "description": {"ru": "12 уроков вокруг Golden Scenario.", "en": "12 lessons around the Golden Scenario.", "zh": "围绕黄金场景的 12 节课。"}, "pages": [
                {"slug": "create-odata-connection", "title": {"ru": "Create OData Connection", "en": "Create OData Connection", "zh": "创建 OData 连接"}, "description": {"ru": "Создать OData ERP connection, понять поля формы, secrets и healthcheck.", "en": "Create OData ERP connection and understand fields, secrets and healthcheck.", "zh": "创建 OData ERP 连接并理解字段、密钥和健康检查。"}},
                {"slug": "test-odata-explorer", "title": {"ru": "Test OData in OData Explorer", "en": "Test OData in OData Explorer", "zh": "在 OData Explorer 测试 OData"}, "description": {"ru": "Выбрать OData ERP, загрузить resources и выполнить первый query.", "en": "Select OData ERP, load resources and run the first query.", "zh": "选择 OData ERP，加载资源并运行第一次查询。"}},
                {"slug": "find-contractor-by-inn", "title": {"ru": "Find Contractor by INN", "en": "Find Contractor by INN", "zh": "按 INN 查找客户"}, "description": {"ru": "Найти контрагента по ИНН, понять Ref_Key и подготовить lookup.", "en": "Find contractor by INN, understand Ref_Key and prepare lookup.", "zh": "按 INN 查找客户，理解 Ref_Key 并准备查询。"}},
                {"slug": "lesson-01-what-is-omh-for-1c-users", "title": {"ru": "Lesson 01 — What is OMH for 1C users", "en": "Lesson 01 — What is OMH for 1C users", "zh": "第 01 课 — 面向 1C 用户的 OMH"}, "description": {"ru": "Карта продукта для 1C пользователя.", "en": "Product map for a 1C user.", "zh": "面向 1C 用户的产品地图。"}},
                {"slug": "lesson-02-create-odata-connection", "title": {"ru": "Lesson 02 — Create OData connection", "en": "Lesson 02 — Create OData connection", "zh": "第 02 课 — 创建 OData 连接"}, "description": {"ru": "Создание named OData profile.", "en": "Create a named OData profile.", "zh": "创建命名 OData 配置。"}},
                {"slug": "lesson-03-test-odata-in-odata-explorer", "title": {"ru": "Lesson 03 — Test OData in OData Explorer", "en": "Lesson 03 — Test OData in OData Explorer", "zh": "第 03 课 — 在 OData Explorer 测试 OData"}, "description": {"ru": "Проверка resource, filter и select.", "en": "Verify resource, filter and select.", "zh": "验证资源、过滤器和字段选择。"}},
                {"slug": "lesson-04-create-inbound-endpoint-for-1c-post", "title": {"ru": "Lesson 04 — Create inbound endpoint for 1C POST", "en": "Lesson 04 — Create inbound endpoint for 1C POST", "zh": "第 04 课 — 创建 1C POST 入口端点"}, "description": {"ru": "Контракт входного POST из 1C.", "en": "Inbound POST contract from 1C.", "zh": "来自 1C 的入口 POST 合约。"}},
                {"slug": "lesson-05-read-values-from-incoming-request", "title": {"ru": "Lesson 05 — Read values from incoming request", "en": "Lesson 05 — Read values from incoming request", "zh": "第 05 课 — 读取入站请求值"}, "description": {"ru": "Извлечение inn, product_code, pool_id и codes.", "en": "Read inn, product_code, pool_id and codes.", "zh": "读取 inn、product_code、pool_id 和 codes。"}},
                {"slug": "lesson-06-first-odata-lookup-contractor-by-inn", "title": {"ru": "Lesson 06 — First OData lookup: contractor by INN", "en": "Lesson 06 — First OData lookup: contractor by INN", "zh": "第 06 课 — 第一次 OData 查询：按 INN 查客户"}, "description": {"ru": "Поиск контрагента по ИНН.", "en": "Find contractor by INN.", "zh": "按 INN 查找客户。"}},
                {"slug": "lesson-07-second-odata-lookup-product-by-article", "title": {"ru": "Lesson 07 — Second OData lookup: product by article", "en": "Lesson 07 — Second OData lookup: product by article", "zh": "第 07 课 — 第二次 OData 查询：按货号查商品"}, "description": {"ru": "Поиск товара по product_code.", "en": "Find product by product_code.", "zh": "按 product_code 查找商品。"}},
                {"slug": "lesson-08-build-target-json", "title": {"ru": "Lesson 08 — Build target JSON", "en": "Lesson 08 — Build target JSON", "zh": "第 08 课 — 构建目标 JSON"}, "description": {"ru": "Сборка target payload.", "en": "Build target payload.", "zh": "构建目标载荷。"}},
                {"slug": "lesson-09-send-json-to-external-api", "title": {"ru": "Lesson 09 — Send JSON to external API", "en": "Lesson 09 — Send JSON to external API", "zh": "第 09 课 — 向外部 API 发送 JSON"}, "description": {"ru": "Вызов DNP/internal API.", "en": "Call DNP/internal API.", "zh": "调用 DNP/内部 API。"}},
                {"slug": "lesson-10-test-full-flow", "title": {"ru": "Lesson 10 — Test full flow", "en": "Lesson 10 — Test full flow", "zh": "第 10 课 — 测试完整流程"}, "description": {"ru": "End-to-end тест через Test Console.", "en": "End-to-end test through Test Console.", "zh": "通过 Test Console 端到端测试。"}},
                {"slug": "lesson-11-read-timeline-and-artifacts", "title": {"ru": "Lesson 11 — Read Timeline and artifacts", "en": "Lesson 11 — Read Timeline and artifacts", "zh": "第 11 课 — 阅读时间线和工件"}, "description": {"ru": "Диагностика результата по artifacts.", "en": "Diagnose results through artifacts.", "zh": "通过工件诊断结果。"}},
                {"slug": "lesson-12-fix-common-errors", "title": {"ru": "Lesson 12 — Fix common errors", "en": "Lesson 12 — Fix common errors", "zh": "第 12 课 — 修复常见错误"}, "description": {"ru": "401, resource not found, empty lookup, target error и DLQ.", "en": "401, resource not found, empty lookup, target error and DLQ.", "zh": "401、资源未找到、空查询、目标错误和 DLQ。"}},
            ]},
            {"id": "recipes", "title": {"ru": "Practical Recipes", "en": "Practical Recipes", "zh": "实践配方"}, "description": {"ru": "Типовые сценарии 1C с endpoints, payload и диагностикой.", "en": "Common 1C scenarios with endpoints, payloads and diagnostics.", "zh": "包含端点、载荷和诊断的常见 1C 场景。"}, "pages": [
                {"slug": "recipe-01-onec-post-odata-json-endpoint", "title": {"ru": "1C → external API", "en": "1C → external API", "zh": "1C → 外部 API"}, "description": {"ru": "Базовый route через OData lookup и REST target.", "en": "Basic route through OData lookup and REST target.", "zh": "通过 OData 查询和 REST 目标的基础路由。"}},
                {"slug": "recipe-02-onec-post-two-odata-lookups", "title": {"ru": "1C → two OData lookups", "en": "1C → two OData lookups", "zh": "1C → 两次 OData 查询"}, "description": {"ru": "Контрагент и товар из OData.", "en": "Contractor and product from OData.", "zh": "来自 OData 的客户和商品。"}},
                {"slug": "recipe-03-onec-xml-to-odata-json", "title": {"ru": "1C XML → OData → JSON", "en": "1C XML → OData → JSON", "zh": "1C XML → OData → JSON"}, "description": {"ru": "XML input с OData enrichment.", "en": "XML input with OData enrichment.", "zh": "带 OData 补充的 XML 输入。"}},
                {"slug": "recipe-04-website-api-to-onec-http-service", "title": {"ru": "Website/API → 1C OData", "en": "Website/API → 1C OData", "zh": "网站/API → 1C OData"}, "description": {"ru": "Внешний API вызывает 1C через OMH.", "en": "External API calls 1C through OMH.", "zh": "外部 API 通过 OMH 调用 1C。"}},
                {"slug": "recipe-05-onec-to-printer-with-odata-enrichment", "title": {"ru": "1C → printer", "en": "1C → printer", "zh": "1C → 打印机"}, "description": {"ru": "Печать с OData enrichment.", "en": "Printing with OData enrichment.", "zh": "带 OData 补充的打印。"}},
                {"slug": "recipe-07-wms-to-onec-with-resolver", "title": {"ru": "WMS/API → 1C", "en": "WMS/API → 1C", "zh": "WMS/API → 1C"}, "description": {"ru": "WMS событие в 1C через resolver.", "en": "WMS event to 1C through resolver.", "zh": "通过解析器把 WMS 事件发到 1C。"}},
                {"slug": "recipe-08-onec-marking-pool-to-dnp", "title": {"ru": "Route by key phrase/value", "en": "Route by key phrase/value", "zh": "按关键短语/值路由"}, "description": {"ru": "Маркировочный пул и business routing.", "en": "Marking pool and business routing.", "zh": "标识池和业务路由。"}},
            ]},
            {"id": "overview", "title": {"ru": "Обзор 1C", "en": "1C Overview", "zh": "1C 概览"}, "description": {"ru": "Что дает 1C package и где он заканчивается.", "en": "What the 1C package adds and where it ends.", "zh": "1C 软件包提供的能力和边界。"}, "pages": [
                {"slug": "overview", "title": {"ru": "Обзор 1C Package", "en": "1C Package overview", "zh": "1C 软件包概览"}, "description": {"ru": "OData, HTTP-сервисы, XML, печать, Flow Builder и diagnostics.", "en": "OData, HTTP services, XML, printing, Flow Builder and diagnostics.", "zh": "OData、HTTP 服务、XML、打印、流程构建器和诊断。"}},
            ]},
            {"id": "setup", "title": {"ru": "Настройка 1C", "en": "1C Setup", "zh": "1C 设置"}, "description": {"ru": "Connector, secrets, endpoint auth и проверка соединения.", "en": "Connector, secrets, endpoint auth and connection testing.", "zh": "连接器、密钥、端点认证和连接测试。"}, "pages": [
                {"slug": "connector-setup", "title": {"ru": "1C Connector Setup", "en": "1C Connector Setup", "zh": "1C 连接器设置"}, "description": {"ru": "Поля подключения, secret reference, healthcheck и частые ошибки.", "en": "Connection fields, secret references, healthcheck and common mistakes.", "zh": "连接字段、密钥引用、健康检查和常见错误。"}},
                {"slug": "auth-secrets-static-token", "title": {"ru": "Secrets и static token", "en": "Secrets and static token", "zh": "密钥和静态令牌"}, "description": {"ru": "Как закрыть endpoint token-ом и не хранить пароли 1C в JSON.", "en": "Protect endpoints with a token and keep 1C passwords out of JSON.", "zh": "使用令牌保护端点，并避免在 JSON 中保存 1C 密码。"}},
            ]},
            {"id": "tools", "title": {"ru": "Инструменты 1C", "en": "1C Tools", "zh": "1C 工具"}, "description": {"ru": "Connector, OData Explorer, XML Tools, Cockpit, Flow Builder.", "en": "Connector, OData Explorer, XML Tools, Cockpit, Flow Builder.", "zh": "连接器、OData 浏览器、XML 工具、驾驶舱、流程构建器。"}, "pages": [
                {"slug": "connector", "title": {"ru": "1C Connector", "en": "1C Connector", "zh": "1C 连接器"}, "description": {"ru": "Поля подключения и безопасные секреты.", "en": "Connection fields and safe secrets.", "zh": "连接字段和安全密钥。"}},
                {"slug": "odata-explorer", "title": {"ru": "OData Explorer", "en": "OData Explorer", "zh": "OData 浏览器"}, "description": {"ru": "Ресурсы 1C, фильтры и lookup templates.", "en": "1C resources, filters and lookup templates.", "zh": "1C 资源、过滤器和查找模板。"}},
                {"slug": "odata-chaining-fields", "title": {"ru": "OData filters, field selection and chaining", "en": "OData filters, field selection and chaining", "zh": "OData 过滤、字段选择和链式查询"}, "description": {"ru": "Как выбирать поля из OData JSON, строить фильтры и передавать результат в следующий шаг.", "en": "How to select OData JSON fields, build filters and pass results to the next step.", "zh": "如何选择 OData JSON 字段、构建过滤器并将结果传给下一步。"}},
                {"slug": "xml-tools", "title": {"ru": "XML Tools", "en": "XML Tools", "zh": "XML 工具"}, "description": {"ru": "Raw XML, parse, hash, diff и raw-forward.", "en": "Raw XML, parse, hash, diff and raw-forward.", "zh": "原始 XML、解析、哈希、差异和转发。"}},
                {"slug": "cockpit", "title": {"ru": "1C Cockpit", "en": "1C Cockpit", "zh": "1C 驾驶舱"}, "description": {"ru": "Операционная поверхность для 1C-внедренца.", "en": "Operational surface for a 1C implementer.", "zh": "面向 1C 实施人员的操作界面。"}},
                {"slug": "visual-flow-builder", "title": {"ru": "Visual Flow Builder для 1C", "en": "Visual Flow Builder for 1C", "zh": "1C 可视化流程构建器"}, "description": {"ru": "No-code flow с OData lookup, transform и target endpoint.", "en": "No-code flow with OData lookup, transform and target endpoint.", "zh": "包含 OData 查询、转换和目标端点的无代码流程。"}},
            ]},
            {"id": "reference", "title": {"ru": "Reference", "en": "Reference", "zh": "参考"}, "description": {"ru": "Справочник понятий и экранов 1C интеграций.", "en": "Reference for 1C integration concepts and screens.", "zh": "1C 集成概念和页面参考。"}, "pages": [
                {"slug": "odata-connection", "title": {"ru": "Reference — OData Connection", "en": "Reference — OData Connection", "zh": "参考 — OData 连接"}, "description": {"ru": "Что хранит OData connection.", "en": "What an OData connection stores.", "zh": "OData 连接保存什么。"}},
                {"slug": "endpoint", "title": {"ru": "Reference — Endpoint", "en": "Reference — Endpoint", "zh": "参考 — 端点"}, "description": {"ru": "Куда 1C отправляет request.", "en": "Where 1C sends requests.", "zh": "1C 向哪里发送请求。"}},
                {"slug": "integration-flow", "title": {"ru": "Reference — Integration Flow", "en": "Reference — Integration Flow", "zh": "参考 — 集成流程"}, "description": {"ru": "No-code сценарий обработки.", "en": "No-code processing scenario.", "zh": "无代码处理场景。"}},
                {"slug": "visual-flow-builder", "title": {"ru": "Reference — Visual Flow Builder", "en": "Reference — Visual Flow Builder", "zh": "参考 — 可视化流程构建器"}, "description": {"ru": "Где собирать шаги.", "en": "Where to assemble steps.", "zh": "在哪里组装步骤。"}},
                {"slug": "json-builder", "title": {"ru": "Reference — JSON Builder", "en": "Reference — JSON Builder", "zh": "参考 — JSON 构建器"}, "description": {"ru": "Сборка финального JSON.", "en": "Build final JSON.", "zh": "构建最终 JSON。"}},
                {"slug": "timeline", "title": {"ru": "Reference — Timeline", "en": "Reference — Timeline", "zh": "参考 — 时间线"}, "description": {"ru": "Шаги, ошибки и artifacts.", "en": "Steps, errors and artifacts.", "zh": "步骤、错误和工件。"}},
                {"slug": "queue-dlq", "title": {"ru": "Reference — Queue / DLQ", "en": "Reference — Queue / DLQ", "zh": "参考 — 队列 / DLQ"}, "description": {"ru": "Retry и Dead Letter Queue.", "en": "Retry and Dead Letter Queue.", "zh": "重试和死信队列。"}},
                {"slug": "secrets", "title": {"ru": "Reference — Secrets", "en": "Reference — Secrets", "zh": "参考 — 密钥"}, "description": {"ru": "Пароли и токены через secret references.", "en": "Passwords and tokens through secret references.", "zh": "通过密钥引用保存密码和令牌。"}},
            ]},
            {"id": "troubleshooting", "title": {"ru": "Troubleshooting", "en": "Troubleshooting", "zh": "故障排查"}, "description": {"ru": "Типовые ошибки 1C интеграций.", "en": "Common 1C integration errors.", "zh": "常见 1C 集成错误。"}, "pages": [
                {"slug": "onec-returned-401", "title": {"ru": "Troubleshooting — 1C returned 401", "en": "Troubleshooting — 1C returned 401", "zh": "故障排查 — 1C 返回 401"}, "description": {"ru": "Inbound/OData/target 401.", "en": "Inbound/OData/target 401.", "zh": "入口/OData/目标 401。"}},
                {"slug": "odata-resource-not-found", "title": {"ru": "Troubleshooting — OData resource not found", "en": "Troubleshooting — OData resource not found", "zh": "故障排查 — OData 资源未找到"}, "description": {"ru": "Resource отсутствует в OData.", "en": "Resource is missing in OData.", "zh": "OData 中缺少资源。"}},
                {"slug": "contractor-not-found-by-inn", "title": {"ru": "Troubleshooting — Contractor not found by INN", "en": "Troubleshooting — Contractor not found by INN", "zh": "故障排查 — 按 INN 未找到客户"}, "description": {"ru": "Пустой lookup контрагента.", "en": "Empty contractor lookup.", "zh": "客户查询为空。"}},
                {"slug": "product-not-found", "title": {"ru": "Troubleshooting — Product not found", "en": "Troubleshooting — Product not found", "zh": "故障排查 — 商品未找到"}, "description": {"ru": "Пустой lookup товара.", "en": "Empty product lookup.", "zh": "商品查询为空。"}},
                {"slug": "target-api-returned-error", "title": {"ru": "Troubleshooting — Target API returned error", "en": "Troubleshooting — Target API returned error", "zh": "故障排查 — 目标 API 返回错误"}, "description": {"ru": "4xx/5xx от внешнего API.", "en": "4xx/5xx from external API.", "zh": "外部 API 返回 4xx/5xx。"}},
                {"slug": "xml-parse-error", "title": {"ru": "Troubleshooting — XML parse error", "en": "Troubleshooting — XML parse error", "zh": "故障排查 — XML 解析错误"}, "description": {"ru": "XML, namespace, encoding.", "en": "XML, namespace, encoding.", "zh": "XML、命名空间、编码。"}},
                {"slug": "printer-unavailable", "title": {"ru": "Troubleshooting — Printer unavailable", "en": "Troubleshooting — Printer unavailable", "zh": "故障排查 — 打印机不可用"}, "description": {"ru": "Printer connector/job недоступен.", "en": "Printer connector/job unavailable.", "zh": "打印机连接器/任务不可用。"}},
                {"slug": "event-moved-to-dlq", "title": {"ru": "Troubleshooting — Event moved to DLQ", "en": "Troubleshooting — Event moved to DLQ", "zh": "故障排查 — 事件进入 DLQ"}, "description": {"ru": "Как читать DLQ и replay.", "en": "How to inspect DLQ and replay.", "zh": "如何检查 DLQ 和重放。"}},
            ]},
            {"id": "scenarios", "title": {"ru": "Практические сценарии 1C", "en": "Practical 1C scenarios", "zh": "1C 实战场景"}, "description": {"ru": "Payload, endpoints, 1C code, artifacts и troubleshooting.", "en": "Payloads, endpoints, 1C code, artifacts and troubleshooting.", "zh": "载荷、端点、1C 代码、工件和故障排查。"}, "pages": [
                {"slug": "onec-to-external-api", "title": {"ru": "1C -> внешний API / сайт", "en": "1C -> External API / site", "zh": "1C -> 外部 API / 网站"}, "description": {"ru": "1C отправляет маркировочный пул, OMH валидирует и отправляет в DNP/API.", "en": "1C sends a marking pool, OMH validates and sends it to DNP/API.", "zh": "1C 发送标识池，OMH 校验并发送到 DNP/API。"}},
                {"slug": "onec-post-two-odata-json-endpoint", "title": {"ru": "1C POST -> две OData выборки -> JSON -> endpoint", "en": "1C POST -> two OData lookups -> JSON -> endpoint", "zh": "1C POST -> 两次 OData 查询 -> JSON -> 端点"}, "description": {"ru": "INN/product_code из 1C POST обогащаются через OData.", "en": "INN/product_code from a 1C POST are enriched through OData.", "zh": "通过 OData 扩充来自 1C POST 的 INN/product_code。"}},
                {"slug": "xml-raw-forward", "title": {"ru": "1C XML -> OMH -> 1C raw forwarding", "en": "1C XML -> OMH -> 1C raw forwarding", "zh": "1C XML -> OMH -> 1C 原样转发"}, "description": {"ru": "Пересылка XML без изменения тела и hash diagnostics.", "en": "Forward XML without body mutation and keep hash diagnostics.", "zh": "不修改正文转发 XML，并保留哈希诊断。"}},
                {"slug": "xml-inn-lookup", "title": {"ru": "1C XML + INN lookup", "en": "1C XML + INN lookup", "zh": "1C XML + INN 查询"}, "description": {"ru": "XML parse, XPath/path picker, OData lookup и target 1C operation.", "en": "XML parse, XPath/path picker, OData lookup and target 1C operation.", "zh": "XML 解析、XPath/路径选择、OData 查询和目标 1C 操作。"}},
                {"slug": "onec-to-printer", "title": {"ru": "1C -> принтер", "en": "1C -> Printer", "zh": "1C -> 打印机"}, "description": {"ru": "Печать этикеток через Printer Package с print job timeline.", "en": "Print labels through Printer Package with a print job timeline.", "zh": "通过打印软件包打印标签，并记录打印任务时间线。"}},
                {"slug": "website-api-to-1c", "title": {"ru": "Website/API -> 1C", "en": "Website/API -> 1C", "zh": "网站/API -> 1C"}, "description": {"ru": "Внешний сайт вызывает OMH, OMH вызывает 1C HTTP service.", "en": "An external site calls OMH, and OMH calls a 1C HTTP service.", "zh": "外部网站调用 OMH，OMH 调用 1C HTTP 服务。"}},
                {"slug": "odata-polling-to-target", "title": {"ru": "1C OData polling -> target system", "en": "1C OData polling -> target system", "zh": "1C OData 轮询 -> 目标系统"}, "description": {"ru": "Периодическое чтение 1C OData и отправка изменений в целевую систему.", "en": "Periodic 1C OData reads and change delivery to a target system.", "zh": "定期读取 1C OData 并向目标系统发送变更。"}},
                {"slug": "wms-api-to-1c", "title": {"ru": "WMS/API -> OMH -> 1C", "en": "WMS/API -> OMH -> 1C", "zh": "WMS/API -> OMH -> 1C"}, "description": {"ru": "WMS или API отправляет факт/статус, OMH вызывает 1C HTTP service.", "en": "WMS or an API sends a fact/status, OMH calls a 1C HTTP service.", "zh": "WMS 或 API 发送事实/状态，OMH 调用 1C HTTP 服务。"}},
            ]},
            {"id": "support", "title": {"ru": "Ошибки, Timeline и очередь", "en": "Errors, Timeline and queue", "zh": "错误、时间线和队列"}, "description": {"ru": "External error fidelity, artifacts, retry и DLQ.", "en": "External error fidelity, artifacts, retry and DLQ.", "zh": "外部错误保真、工件、重试和 DLQ。"}, "pages": [
                {"slug": "errors-timeline-artifacts", "title": {"ru": "Ошибки 1C, Timeline и Artifacts", "en": "1C errors, Timeline and Artifacts", "zh": "1C 错误、时间线和工件"}, "description": {"ru": "Как читать оригинальные ошибки 1C и внешних систем.", "en": "How to read original 1C and external system errors.", "zh": "如何读取原始 1C 和外部系统错误。"}},
                {"slug": "queue-retry-dlq", "title": {"ru": "Queue, Retry и DLQ для 1C", "en": "Queue, Retry and DLQ for 1C", "zh": "1C 队列、重试和 DLQ"}, "description": {"ru": "Async mode, retry_waiting, DLQ, retry now и edit retry.", "en": "Async mode, retry_waiting, DLQ, retry now and edit retry.", "zh": "异步模式、retry_waiting、DLQ、立即重试和编辑重试。"}},
            ]},
        ],
    },
    {"id": "printer", "title": {"ru": "Печать", "en": "Printing", "zh": "打印"}, "description": {"ru": "ZPL принтеры и troubleshooting.", "en": "ZPL printers and troubleshooting.", "zh": "ZPL 打印机与故障排查。"}, "sections": [{"id": "printing", "title": {"ru": "Печать", "en": "Printing", "zh": "打印"}, "description": {"ru": "Подключение и ошибки.", "en": "Setup and errors.", "zh": "设置和错误。"}, "pages": [{"slug": "overview", "title": {"ru": "Печать ZPL", "en": "ZPL printing", "zh": "ZPL 打印"}, "description": {"ru": "Как отправлять этикетки на принтер.", "en": "How to send labels to a printer.", "zh": "如何向打印机发送标签。"}}]}]},
    {"id": "auth", "title": {"ru": "Авторизация", "en": "Auth", "zh": "认证"}, "description": {"ru": "Опциональный пакет пользователей и сессий.", "en": "Optional users and sessions package.", "zh": "可选用户与会话软件包。"}, "sections": [{"id": "auth", "title": {"ru": "Авторизация", "en": "Auth", "zh": "认证"}, "description": {"ru": "Установка, пользователи, recovery keys.", "en": "Install, users, recovery keys.", "zh": "安装、用户、恢复密钥。"}, "pages": [{"slug": "install", "title": {"ru": "Включение авторизации", "en": "Enable Auth", "zh": "启用认证"}, "description": {"ru": "Как закрыть UI пользователями.", "en": "How to protect UI with users.", "zh": "如何使用用户保护 UI。"}}]}]},
    {"id": "secrets", "title": {"ru": "Secrets", "en": "Secrets", "zh": "密钥"}, "description": {"ru": "Безопасная конфигурация connector и tokens.", "en": "Secure connector and token config.", "zh": "安全连接器与令牌配置。"}, "sections": [{"id": "secrets", "title": {"ru": "Secrets Store", "en": "Secrets Store", "zh": "密钥库"}, "description": {"ru": "Secret references.", "en": "Secret references.", "zh": "密钥引用。"}, "pages": [{"slug": "overview", "title": {"ru": "Что такое Secrets Store", "en": "What is Secrets Store", "zh": "什么是密钥库"}, "description": {"ru": "Хранение паролей вне JSON конфигов.", "en": "Keep passwords out of JSON configs.", "zh": "让密码脱离 JSON 配置。"}}]}]},
    {"id": "packages", "title": {"ru": "Packages", "en": "Packages", "zh": "软件包"}, "description": {"ru": "Plugin Store и lifecycle пакетов.", "en": "Plugin Store and package lifecycle.", "zh": "插件商店和软件包生命周期。"}, "sections": [{"id": "packages", "title": {"ru": "Пакеты", "en": "Packages", "zh": "软件包"}, "description": {"ru": "Установка и статусы.", "en": "Install and statuses.", "zh": "安装和状态。"}, "pages": [{"slug": "plugin-store", "title": {"ru": "Plugin Store", "en": "Plugin Store", "zh": "插件商店"}, "description": {"ru": "Available, installed, disabled, coming soon.", "en": "Available, installed, disabled, coming soon.", "zh": "可用、已安装、已禁用、即将推出。"}}]}]},
]


def normalize_language(language: str) -> tuple[str, str | None]:
    if language in SUPPORTED_LANGUAGES:
        return language, None
    return "ru", "ru"


def docs_index(language: str) -> DocsIndexRead:
    lang, fallback = normalize_language(language)
    return DocsIndexRead(language=lang, fallback_language=fallback, packages=[_package(pkg, lang) for pkg in DOC_PACKAGES])


def docs_packages(language: str) -> list[DocsPackageRead]:
    return docs_index(language).packages


def docs_page(page_id: str, language: str) -> DocsPageRead | None:
    lang, _ = normalize_language(language)
    for pkg in DOC_PACKAGES:
        for section in pkg["sections"]:
            for page in section["pages"]:
                candidate_id = f"{pkg['id']}.{section['id']}.{page['slug']}"
                if candidate_id == page_id:
                    summary = _page_summary(pkg, section, page, lang)
                    return DocsPageRead(**summary.model_dump(), markdown=_placeholder_markdown(pkg, section, page, lang), translation_status="complete" if lang == "ru" else "in_progress")
    return None


def _package(pkg: dict, lang: str) -> DocsPackageRead:
    return DocsPackageRead(
        id=pkg["id"],
        title=_localized(pkg["title"], lang),
        description=_localized(pkg["description"], lang),
        route=f"/docs/{pkg['id']}",
        sections=[_section(pkg, section, lang) for section in pkg["sections"]],
    )


def _section(pkg: dict, section: dict, lang: str) -> DocsSectionRead:
    return DocsSectionRead(
        id=section["id"],
        package_id=pkg["id"],
        title=_localized(section["title"], lang),
        description=_localized(section["description"], lang),
        pages=[_page_summary(pkg, section, page, lang) for page in section["pages"]],
    )


def _page_summary(pkg: dict, section: dict, page: dict, lang: str) -> DocsPageSummary:
    page_id = f"{pkg['id']}.{section['id']}.{page['slug']}"
    return DocsPageSummary(
        id=page_id,
        package_id=pkg["id"],
        section_id=section["id"],
        slug=page["slug"],
        title=_localized(page["title"], lang),
        description=_localized(page["description"], lang),
        route=f"/docs/{pkg['id']}/{section['id']}/{page['slug']}",
        updated_at=UPDATED_AT,
    )


def _placeholder_markdown(pkg: dict, section: dict, page: dict, lang: str) -> str:
    title = _localized(page["title"], lang)
    description = _localized(page["description"], lang)
    note = {
        "ru": "Полная версия этой страницы рендерится во фронтенд-портале /docs.",
        "en": "The complete page is rendered in the frontend /docs portal.",
        "zh": "完整页面在前端 /docs 门户中渲染。",
    }[lang]
    return f"# {title}\n\n{description}\n\n{note}"


def _localized(values: dict[str, str], lang: str) -> str:
    return values.get(lang) or values.get("ru") or next(iter(values.values()))
