# Ozon Seller API — карта для интеграции OMH ↔ 1C

Дата составления: 2026-08-06. Источники: [docs.ozon.ru/api/seller](https://docs.ozon.ru/api/seller/en/) (редиректит из РФ-сети, содержимое сверено с [ozon-api-client (PyPI)](https://pypi.org/project/ozon-api-client/), [diphantxm/ozon-api-client (Go)](https://pkg.go.dev/github.com/diphantxm/ozon-api-client/ozon), [irenicaa/ozon-seller](https://github.com/irenicaa/ozon-seller)).

## База

- Base URL: `https://api-seller.ozon.ru`
- Все методы: `POST` с JSON body, `Content-Type: application/json`.
- Аутентификация: заголовки `Client-Id` и `Api-Key` (создаются в личном кабинете продавца, нужна роль с доступами Products/Stocks/Prices/FBS).
- Пагинация: `last_id` (product list), `cursor` (info/stocks, prices), `offset+limit` (postings).
- Лимиты: ≤100 запросов/сек по большинству методов; batch до 1000 элементов в list-методах.

## Что нужно интеграции «Ozon → 1C и обратно»

### 1. Каталог товаров (мастер-данные)

| Метод | Назначение | Тело / ответ |
| --- | --- | --- |
| `POST /v3/product/list` | Список товаров продавца | body: `{filter: {visibility: "ALL"\|"ARCHIVED"\|"VISIBLE"\|...}, last_id, limit ≤1000}` → `{result: {items: [{product_id, offer_id, has_fbo_stocks, has_fbs_stocks, archived, is_discounted}], last_id, total}}` |
| `POST /v3/product/info/list` | Карточки по id/offer_id | body: `{product_id?: [], offer_id?: [], sku?: []}` → `{result: {items: [{id, name, offer_id, barcode, sku, ...}]}}` |

Ключ связи с 1С: `offer_id` (артикул продавца) ↔ код/артикул номенклатуры 1С; `product_id` внутренний id Ozon; `sku` числовой SKU.

### 2. Остатки (stocks)

| Метод | Назначение | Тело / ответ |
| --- | --- | --- |
| `POST /v4/product/info/stocks` | Чтение остатков | body: `{filter: {offer_id?: [], product_id?: [], visibility?: "ALL"}, cursor, limit ≤1000}` → `{cursor, total, items: [{offer_id, product_id, stocks: [{present, reserved, sku, type?}]}]}` |
| `POST /v2/products/stocks` | Обновление остатков | body: `{stocks: [{offer_id, product_id, stock}]}` (до 100 элементов) → `{result: [{offer_id, product_id, updated, errors: []}]}` |
| `POST /v1/product/info/stocks-by-warehouse/fbs` | Остатки по складам FBS | body: `{filter: [], cursor, limit}` → `{result: [{product_id, offer_id, stocks: [{present, reserved, sku, warehouse_id, warehouse_name}]}], cursor, total}` |

Важно: `reserved` — зарезервировано Ozon; доступно к продаже = `present` (уже включает зарезерв, по доке «present includes reserved»). Для синхронизации «продаж в минус не должно быть» выгружаем `present`.

### 3. Цены (prices)

| Метод | Назначение | Тело / ответ |
| --- | --- | --- |
| `POST /v1/product/import/prices` | Обновление цен | body: `{prices: [{offer_id \| product_id, price: "100.00", old_price: "120.00", premium_price: "90.00", min_price: "80.00", currency: "RUB", price_index: "DEFAULT", auto_action_enabled?: bool, min_auto_price?: "80.00"}]}` (до 1000) → `{result: [{product_id, offer_id, updated, errors: [{code, field, attribute_id, description}]}]}` |
| `POST /v5/product/info/prices` | Чтение цен | body: `{filter: {offer_id?: [], product_id?: [], visibility?: "ALL"}, cursor, limit ≤1000}` → `{items: [{id, price: {price, old_price, premium_price, min_price, currency, retail_price?, vat?}}], cursor, total}` |

`min_price` — минимальная цена (защита от автоакций). `auto_action_enabled` — применять ли автоакции.

### 4. Заказы / отправления

FBS (со склада продавца) — основной поток для «заказы → 1C»:

| Метод | Назначение | Тело / ответ |
| --- | --- | --- |
| `POST /v3/posting/fbs/list` | Список FBS-отправлений | body: `{dir: "ASC"\|"DESC", filter: {since: ISO8601, to: ISO8601, status?: "awaiting_registration\|awaiting_packaging\|awaiting_deliver\|delivering\|delivered\|cancelled", delivery_schema?, order_id?, warehouse_id?}, with: {barcodes?, analytics_data?, financial_data?}, limit ≤100, offset}` → `{result: {postings: [...], count}}` |
| `POST /v3/posting/fbs/get` | Отправление по номеру | body: `{posting_number, with: {barcodes?, analytics_data?, financial_data?}}` → `{result: {...}}` |
| `POST /v2/posting/fbo/list` | FBO-отправления (со склада Ozon) | body: `{dir, filter: {since, to, status?}, limit ≤1000, offset, translit?}` |

Состав posting: `posting_number`, `order_id`, `order_number`, `status`, `created_at`, `in_process_at`, `products: [{sku, offer_id, name, quantity, price, currency_code?}]`, `analytics_data` (город/регион доставки, premium), `financial_data` (цена для отчета), `barcodes` (при with.barcodes).

### 5. Склады и справочники

| Метод | Назначение |
| --- | --- |
| `POST /v1/warehouse/list` | Склады продавца (id, name) для stocks-by-warehouse |
| `POST /v1/analytics/stock_on_warehouses` | Аналитика остатков по складам |

## Потоки, которые закрывает наш кейс

1. **Заказы Ozon → 1C** (polling с watermark по `filter.since`, dir=ASC): `fbs/list` → canonical `MarketplaceOrder {marketplace: "ozon", number: posting_number, status, created_at, customer_region, items: [{offer_id/sku, name, qty, price}], financial}` → 1C HTTP-сервис.
2. **Остатки 1C → Ozon** (push по расписанию/событию): 1C отдает `{offer_id, qty}` → `v2/products/stocks` (batch 100). Показать updated/errors.
3. **Остатки Ozon → 1C** (проверка «продаж в минус»): `v4/product/info/stocks` → canonical rows → 1C.
4. **Цены 1C → Ozon**: 1C отдает `{offer_id, price, old_price?, min_price?}` → `v1/product/import/prices` (batch 1000). Показать updated/errors.
5. **Каталог Ozon → 1C**: `v3/product/list` + `info/list` → синхронизация offer_id ↔ номенклатура.

## Роли API-ключа

Нужны доступы: Products (list/info), Prices & Stocks (read+write), FBS postings (read). Без FBO/Finance/Reports для базового кейса.

## Замечания по надежности

- Rate limit: держать ≤1 batch/сек на sync-задачу, retry с backoff при 429/5xx.
- Ошибки обновления: `result[].errors[]` у stocks/prices — выносить в incident, не молчать.
- `cursor`/`last_id` сохранять в state задачи (watermark), не гонять полную выгрузку каждый раз.
