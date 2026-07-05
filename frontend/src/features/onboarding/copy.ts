import type { Language } from '../../i18n/dictionary';

export const onboardingCopy = {
  ru: {
    welcome: 'Добро пожаловать в OMH.',
    subtitle: 'Платформа помогает связывать 1C, сайты, WMS, принтеры и другие системы через наблюдаемые события, timeline и повторяемые интеграции.',
    recommended: 'Рекомендуемая настройка',
    openWizard: 'Создать первую интеграцию',
    reset: 'Сбросить прогресс',
    complete: 'Готово',
    skip: 'Пропустить',
    done: 'Выполнено',
    skipped: 'Пропущено',
    open: 'Открыть',
    docs: 'Документация',
    runExample: 'Запустить пример',
    onboarding: 'Онбординг',
    cardTitle: 'Настроить OMH без догадок',
    cardText: 'Пройдите короткий чеклист: пакет 1C, connector, OData, flow, тестовый запрос и timeline.',
    progress: 'прогресс',
  },
  en: {
    welcome: 'Welcome to OMH.', subtitle: 'Connect 1C, websites, WMS, printers and other systems through observable events and timelines.', recommended: 'Recommended setup', openWizard: 'Create first integration', reset: 'Reset progress', complete: 'Complete', skip: 'Skip', done: 'Done', skipped: 'Skipped', open: 'Open', docs: 'Docs', runExample: 'Run example', onboarding: 'Onboarding', cardTitle: 'Set up OMH without guesswork', cardText: 'Follow the checklist: 1C package, connector, OData, flow, test request and timeline.', progress: 'progress',
  },
  zh: {
    welcome: '欢迎使用 OMH。', subtitle: '通过可观测事件和时间线连接 1C、网站、WMS、打印机和其他系统。', recommended: '推荐设置', openWizard: '创建第一个集成', reset: '重置进度', complete: '完成', skip: '跳过', done: '已完成', skipped: '已跳过', open: '打开', docs: '文档', runExample: '运行示例', onboarding: '引导', cardTitle: '无需猜测即可设置 OMH', cardText: '按清单完成：1C 包、连接器、OData、流程、测试请求和时间线。', progress: '进度',
  },
} satisfies Record<Language, Record<string, string>>;

export const itemCopy: Record<string, Record<Language, { title: string; description: string }>> = {
  install_onec_package: { ru: { title: 'Установить нужные пакеты', description: 'Установите и включите 1C package перед настройкой 1C маршрутов.' }, en: { title: 'Install required packages', description: 'Install and enable the 1C package before building 1C routes.' }, zh: { title: '安装所需软件包', description: '在构建 1C 路由前安装并启用 1C 软件包。' } },
  create_first_onec_connector: { ru: { title: 'Создать 1C connector', description: 'Добавьте OData и HTTP-service URL первой базы 1C.' }, en: { title: 'Create 1C connector', description: 'Register OData and HTTP-service URLs for your first 1C database.' }, zh: { title: '创建 1C 连接器', description: '为第一个 1C 数据库配置 OData 和 HTTP 服务 URL。' } },
  test_onec_connection: { ru: { title: 'Проверить OData', description: 'Откройте OData Explorer, загрузите ресурсы и выполните безопасный запрос.' }, en: { title: 'Test OData connection', description: 'Open OData Explorer, load resources and run a safe query.' }, zh: { title: '测试 OData 连接', description: '打开 OData 浏览器，加载资源并运行安全查询。' } },
  create_first_integration_flow: { ru: { title: 'Создать первый integration flow', description: 'Соберите маршрут 1C POST -> OData lookup -> JSON -> endpoint.' }, en: { title: 'Create first integration flow', description: 'Build 1C POST -> OData lookup -> JSON -> endpoint.' }, zh: { title: '创建第一个集成流', description: '构建 1C POST -> OData 查找 -> JSON -> 端点。' } },
  run_first_test_case: { ru: { title: 'Запустить тестовый запрос', description: 'Отправьте известный payload и проверьте ответ.' }, en: { title: 'Run test request', description: 'Send a known payload and inspect the response.' }, zh: { title: '运行测试请求', description: '发送已知 payload 并检查响应。' } },
  open_first_timeline: { ru: { title: 'Открыть timeline', description: 'Проверьте шаги, артефакты и ошибки тестового события.' }, en: { title: 'Open timeline', description: 'Check steps, artifacts and errors for the test event.' }, zh: { title: '打开时间线', description: '检查测试事件的步骤、产物和错误。' } },
  configure_backup: { ru: { title: 'Настроить backup', description: 'Сделайте export config перед реальными интеграциями.' }, en: { title: 'Configure backup', description: 'Export config before real integrations go live.' }, zh: { title: '配置备份', description: '上线真实集成前导出配置。' } },
  enable_auth_or_skip: { ru: { title: 'Настроить авторизацию при необходимости', description: 'Включите Auth package, если UI должен быть закрыт пользователями.' }, en: { title: 'Configure auth if needed', description: 'Install Auth package when UI access must be restricted.' }, zh: { title: '按需配置认证', description: '当 UI 需要限制访问时安装 Auth 包。' } },
  create_first_secret: { ru: { title: 'Создать первый secret', description: 'Уберите пароли и токены из JSON connector.' }, en: { title: 'Create first secret', description: 'Move passwords and tokens out of connector JSON.' }, zh: { title: '创建第一个密钥', description: '将密码和令牌移出连接器 JSON。' } },
};
