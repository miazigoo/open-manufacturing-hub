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
                {"slug": "beginner-path", "title": {"ru": "Начните здесь: первый понятный обмен с 1C", "en": "Start here: first understandable 1C exchange", "zh": "从这里开始：第一个易懂的 1C 交换"}, "description": {"ru": "Endpoint, token, OData profile, Flow, Test Console и Timeline простыми словами.", "en": "Endpoint, token, OData profile, Flow, Test Console and Timeline in plain language.", "zh": "用简单语言解释端点、令牌、OData 配置、Flow、Test Console 和 Timeline。"}},
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
                {"slug": "xml-tools", "title": {"ru": "XML Tools", "en": "XML Tools", "zh": "XML 工具"}, "description": {"ru": "Raw XML, parse, hash, diff и raw-forward.", "en": "Raw XML, parse, hash, diff and raw-forward.", "zh": "原始 XML、解析、哈希、差异和转发。"}},
                {"slug": "cockpit", "title": {"ru": "1C Cockpit", "en": "1C Cockpit", "zh": "1C 驾驶舱"}, "description": {"ru": "Операционная поверхность для 1C-внедренца.", "en": "Operational surface for a 1C implementer.", "zh": "面向 1C 实施人员的操作界面。"}},
                {"slug": "visual-flow-builder", "title": {"ru": "Visual Flow Builder для 1C", "en": "Visual Flow Builder for 1C", "zh": "1C 可视化流程构建器"}, "description": {"ru": "No-code flow с OData lookup, transform и target endpoint.", "en": "No-code flow with OData lookup, transform and target endpoint.", "zh": "包含 OData 查询、转换和目标端点的无代码流程。"}},
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
