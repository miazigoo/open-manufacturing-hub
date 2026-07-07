# Product UX Doctrine: Simple Integration Mode

OMH is not a set of technical tools. OMH is an integration platform that leads a user from a business task to a working integration.

## Product Formula

**OMH ведёт пользователя от задачи до рабочей интеграции.**

The first product question is not "Which workflow do you want to create?".

The first product questions are:

1. Кто к вам обращается?
2. Что приходит?
3. Что нужно найти, изменить или отправить?
4. Что нужно вернуть?
5. Как проверить, что всё работает?

Routes, flows, workflows, steps, artifacts, packages, connectors and resolvers are internal mechanics. They remain available, but they must not be the first thing a normal user sees.

## UI Modes

### Simple

Default mode. Shows scenario-first pages only:

- Start page: "Что вы хотите интегрировать?"
- Documentation and Training
- 1C Cockpit
- Request/Response Workbench
- OData Connections and OData Master
- Integration Flows as the list of created integrations
- Event Journal, Transaction Monitor, Incidents and Health
- Packages and Production

Simple mode hides low-level pages from navigation. Direct links still work for support and power users.

### Advanced

Shows configuration and production ownership:

- Connectors, Secrets, Users and Auth
- Change Sets, Environments, Audit, Retention and Notifications
- Business objects, resolvers, transformations, business rules and mapping
- XML Tools, test cases, plugin store, queues and DLQ

Advanced mode is for an integrator who already understands OMH concepts.

### Developer

Shows internal implementation details:

- Integration Bus
- Workflows
- Execution Steps
- i18n debug and internal diagnostics

Developer mode is not a product entry point.

## Scenario-First Rule

A feature is good when it helps a user complete a real scenario with fewer jumps between pages.

A feature is bad when it adds another unexplained tab, another raw JSON form, or another technical noun without answering why the user needs it.

Before adding a page, ask:

1. What user task starts here?
2. What input does the user already have?
3. What result does the user expect?
4. What does OMH do under the hood?
5. Where will the user test and replay the integration?

If those answers are unclear, the feature should be a section inside an existing scenario page, not a new navigation item.

## Canonical Flow

External service calls OMH

OMH helps understand the incoming request

OMH suggests actions: OData, API, XML, printing, 1C HTTP service

OMH helps assemble the response: JSON, XML, raw text, event_id, proxy response

OMH gives test, timeline, replay and error diagnosis

User understands what happens in production

## Navigation Rules

- Simple mode must not start from routes, workflows, execution steps or raw bus concepts.
- "Create integration" opens a scenario chooser, not a blank technical builder.
- Integration Flows is a management page for already created flows.
- OData Master is both a test tool and an integration-building step.
- XML Tools is a reusable toolbox, not the first XML integration page.
- Developer pages can be reachable by URL, but hidden in Simple and Advanced navigation unless explicitly needed.

## Done Criteria For New UX

- The page title explains the real user goal.
- The first screen answers when to use this page.
- Primary action uses user language, not implementation language.
- Raw JSON is behind preview, details, or an advanced section unless JSON is the user input.
- Every created integration has a test path, event/timeline path and recovery path.
- Russian UI copy does not use unexplained English unless it is a standard term like OData, JSON, XML, HTTP, API or URL.
