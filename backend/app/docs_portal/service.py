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
        "description": {"ru": "OData, XML, HTTP-сервисы, Cockpit и Flow Builder.", "en": "OData, XML, HTTP services, Cockpit and Flow Builder.", "zh": "OData、XML、HTTP 服务、驾驶舱和流程构建器。"},
        "sections": [
            {"id": "overview", "title": {"ru": "Обзор 1C", "en": "1C Overview", "zh": "1C 概览"}, "description": {"ru": "Что дает 1C package.", "en": "What the 1C package adds.", "zh": "1C 软件包提供的能力。"}, "pages": [
                {"slug": "overview", "title": {"ru": "Обзор 1C Package", "en": "1C Package overview", "zh": "1C 软件包概览"}, "description": {"ru": "OData, HTTP-сервисы, XML, печать, integration bus.", "en": "OData, HTTP services, XML, printing and integration bus.", "zh": "OData、HTTP 服务、XML、打印和集成总线。"}},
            ]},
            {"id": "quick-start", "title": {"ru": "Быстрый старт 1C", "en": "1C Quick Start", "zh": "1C 快速开始"}, "description": {"ru": "От установки до первого события.", "en": "From install to first event.", "zh": "从安装到第一个事件。"}, "pages": [
                {"slug": "quick-start", "title": {"ru": "Быстрый старт 1C", "en": "1C Quick Start", "zh": "1C 快速开始"}, "description": {"ru": "Пошаговая настройка первой интеграции.", "en": "Step-by-step first integration setup.", "zh": "首个集成的分步设置。"}},
            ]},
            {"id": "tools", "title": {"ru": "Инструменты 1C", "en": "1C Tools", "zh": "1C 工具"}, "description": {"ru": "Connector, OData Explorer, XML Tools.", "en": "Connector, OData Explorer, XML Tools.", "zh": "连接器、OData 浏览器、XML 工具。"}, "pages": [
                {"slug": "connector", "title": {"ru": "1C Connector", "en": "1C Connector", "zh": "1C 连接器"}, "description": {"ru": "Поля подключения и секреты.", "en": "Connection fields and secrets.", "zh": "连接字段和密钥。"}},
                {"slug": "odata-explorer", "title": {"ru": "OData Explorer", "en": "OData Explorer", "zh": "OData 浏览器"}, "description": {"ru": "Ресурсы 1C, фильтры и lookup templates.", "en": "1C resources, filters and lookup templates.", "zh": "1C 资源、过滤器和查找模板。"}},
                {"slug": "xml-tools", "title": {"ru": "XML Tools", "en": "XML Tools", "zh": "XML 工具"}, "description": {"ru": "Raw XML, parse, hash, diff и raw-forward.", "en": "Raw XML, parse, hash, diff and raw-forward.", "zh": "原始 XML、解析、哈希、差异和转发。"}},
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
