# Найти заказ на производство по номеру

Практический сценарий для `/master`: внешний сервис передаёт номер заказа, OMH делает один OData-запрос в 1C и сохраняет найденный документ как `order`.

## Входящий sample

```json
{
  "operation": "dnp_sinc_pull_codes",
  "sinc": "dnp_sinc_pull_codes",
  "order_name": "26-0666/6938",
  "Number": "260666/6938"
}
```

Input Contract должен содержать поле:

```text
request.body.Number
```

## OData Query Builder

```text
OData connection: 1C ERP OData
Resource: Document_ЗаказНаПроизводство2_2
Filter: Number eq '{{request.body.Number}}'
$select: Ref_Key, Number, Date, Posted
$top: 1
$orderby: Date desc
save_as: order
required: true
```

## Что должен показать Preview

```text
Document_ЗаказНаПроизводство2_2?$filter=Number eq '260666/6938'&$select=Ref_Key,Number,Date,Posted&$top=1&$orderby=Date desc
```

Переменные после шага:

```text
order.Ref_Key
order.Number
order.Date
order.Posted
```

## Что должен показать Test

Успешный ответ содержит первую найденную запись:

```json
{
  "Ref_Key": "order-guid",
  "Number": "260666/6938",
  "Date": "2026-04-29T16:38:53",
  "Posted": true
}
```

`Ref_Key` — это ссылка 1C на документ. Следующие шаги должны передавать именно `order.Ref_Key`, если внешней системе нужна стабильная ссылка на документ, а не человекочитаемый номер.

## Если результат пустой

`ODATA_RESULT_EMPTY` означает, что запрос выполнился, но 1C вернула `value=[]`.

Порядок диагностики:

1. Скопируйте rendered filter из Preview.
2. Проверьте этот filter в OData Explorer на том же connection.
3. Сравните номер из request с номером в 1C.
4. Проверьте, что resource `Document_ЗаказНаПроизводство2_2` относится к нужной конфигурации и версии документа.
5. Если документ есть, проверьте права пользователя OData.

Не отключайте `required`, если без найденного заказа следующий шаг не имеет смысла.

## Следующий шаг

После успешного поиска заказа прочитайте его табличную часть:

[Читаем табличную часть документа 1С через OData](./read-tabular-part.md)
