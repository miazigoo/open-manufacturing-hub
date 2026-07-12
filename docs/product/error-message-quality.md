# Error Message Quality

Pattern wizard errors must tell the user what failed, where to look and what to change.

## Rules

- Name the business field, not only the internal step.
- Keep the failing value visible when it is safe.
- Link to troubleshooting when the symptom has a playbook.
- Do not expose raw internals in Simple Mode unless they are inside collapsed advanced details.
- For target HTTP errors, preserve status code, body and connector name.
- For OData empty result, show the rendered filter and selected resource.

## Bad vs good

| Bad | Good |
| --- | --- |
| `builder_json invalid` | `Поле inn не найдено во входящем JSON. Выберите поле бизнес-ключа или исправьте sample.` |
| `workflow failed` | `1C OData вернул пустой результат для фильтра ИНН eq '7707083893'. Проверьте фильтр или данные training стенда.` |
| `target error` | `Внешний API вернул 422: order_number is required. Исправьте payload template или тестовый sample.` |

## Gate

Certification should mark the pattern partial when common errors do not have user-facing messages or troubleshooting links.
