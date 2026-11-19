# Рецепт: Ozon ↔ 1С — заказы, остатки и цены

## Когда использовать

Нужно связать 1С с маркетплейсом Ozon без API-разработчика: забирать заказы
FBS в 1С, обновлять остатки и цены из 1С в Ozon, держать синхронизацию
под контролем из UI. Разные API Ozon приводятся к каноническому формату —
в 1С данные уходят единообразно.

## Подключение (один раз)

1. В личном кабинете Ozon Seller создайте API-ключ (`Client-Id` + `Api-Key`)
   с доступами Products, Prices & Stocks (read+write), FBS postings (read).
2. В `Connection Center` создайте коннектор `Ozon Seller`: тип REST,
   url `https://api-seller.ozon.ru`, в config — `client_id` и `api_key`
   (поддерживается secret reference).
3. Проверка: в Visual Flow Builder добавьте шаг `Ozon`, действие
   `Склады (list_warehouses)`, нажмите Preview — в предпросмотре работает
   встроенный мок, реальный ключ не нужен.

Карта используемых методов API: `docs/integrations/ozon-api-map.md`.

## Сценарий 1. Заказы FBS из Ozon в 1С

Установите из библиотеки сценариев `Ozon orders to 1C (FBS)`:

```text
Ozon fbs/list -> канонический MarketplaceOrder -> 1C HTTP-сервис
```

Запуск вручную или из планировщика:

```http
POST /api/bus/in/ozon-orders-to-onec
{"ozon_since": "2026-08-01T00:00:00Z"}
```

- `ozon_since` — с какой даты забрать заказы (ISO 8601).
- Ответ: `{"ok": true, "orders": <количество>, "onec": <ответ 1С>}`.
- Каждый запуск виден в Timeline: запрос к Ozon, канонические заказы,
  ответ 1С.

## Сценарий 2. Остатки и цены из 1С в Ozon

Установите сценарий `1C stocks and prices to Ozon`. 1С отправляет:

```http
POST /api/bus/in/ozon-stocks-prices-from-onec
{
  "stocks": [{"offer_id": "ABC-123", "qty": 15}],
  "prices": [{"offer_id": "ABC-123", "price": "100.00", "old_price": "120.00", "min_price": "80.00"}]
}
```

- Можно слать только `stocks` или только `prices` — второй шаг пропустится
  условием запуска.
- Остатки уходят пачками до 100 позиций, цены — до 1000.
- Ответ содержит по каждой позиции `updated`/`errors`. Если Ozon отклонил
  часть позиций, шаг завершается ошибкой `OZON_ITEMS_FAILED`, а в артефакте
  `ozon_response.json` видно, какие `offer_id` и почему не приняты —
  сбой не проходит молча.

## Своя связка: шаг Ozon в Visual Flow Builder

Действия шага `Ozon`:

| Действие | Что делает |
| --- | --- |
| `list_orders` | Заказы FBS с даты `since`, фильтр по статусу |
| `list_products` | Список товаров продавца |
| `product_info` | Карточки по offer_id/product_id |
| `get_stocks` | Остатки из Ozon (проверка «продаж в минус») |
| `update_stocks` | Обновить остатки из массива `[{offer_id, qty}]` |
| `get_prices` | Цены из Ozon |
| `update_prices` | Обновить цены из массива `[{offer_id, price, ...}]` |
| `list_warehouses` | Склады продавца |

Параметры задаются путями к переменным (`request.body.stocks`,
`variables.price_rows`) — шаг комбинируется с Extract, Filter, Condition и
Build JSON в любую логическую цепочку.

## Ошибки и что с ними делать

- `OZON_CONFIG_INVALID` — нет коннектора или пустые `client_id`/`api_key`.
  Откройте Connection Center и заполните ключи.
- `401/403` — ключ отклонен Ozon: проверьте Client-Id/Api-Key и роль ключа.
- `429` — превышен лимит запросов: увеличьте интервал синхронизации.
- `OZON_ITEMS_FAILED` — часть позиций отклонена: offer_id и причина в
  артефакте `ozon_response.json`.
- `OZON_SINCE_REQUIRED` — для заказов не указана дата: передайте
  `ozon_since` в теле запуска.
