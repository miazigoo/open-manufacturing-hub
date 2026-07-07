# Первый OData-запрос после Input Contract

Этот урок относится к `/master` Step 2A: один OData Query Builder после сохранения Input Contract.

Цель шага — взять значение из входящего request, найти одну запись в 1C OData и сохранить результат в переменную для следующих шагов.

## Когда использовать

- Input Contract уже сохранён в `/master`.
- Во входящем JSON есть номер заказа: `request.body.Number`.
- Нужно найти документ 1C и дальше использовать его ссылку `Ref_Key`.

## Настройка в `/master`

1. Откройте `/master`.
2. Выберите сценарий и сохраните Input Contract.
3. В блоке `Step 2A` выберите OData connection.
4. Укажите resource `Document_ЗаказНаПроизводство2_2`.
5. Включите filter builder.
6. Заполните filter:

```text
Field: Number
Operator: eq
Value type: variable
Value: request.body.Number
```

Итоговый template filter:

```text
Number eq '{{request.body.Number}}'
```

На sample `Number=260666/6938` preview должен показать:

```text
Number eq '260666/6938'
```

## Select и save_as

Рекомендуемые поля:

```text
Ref_Key, Number, Date, Posted
```

Сохраните результат как:

```text
save_as=order
```

После успешного test query в следующих шагах будут доступны переменные:

```text
order.Ref_Key
order.Number
order.Date
order.Posted
```

## Empty Result

Если `required=true` и 1C вернула пустой список, test покажет `ODATA_RESULT_EMPTY`.

Что проверить:

- Точный формат номера в 1C: `260666/6938` и `26-0666/6938` могут быть разными значениями.
- Resource выбран из той базы 1C, где лежит документ.
- Пользователь OData имеет права читать документ.
- В filter нет лишних пробелов внутри значения.

## Что не входит в Step 2A

- foreach.
- tabular part helper.
- JSON/XML response builder.
- endpoint send.
- сохранение полной боевой интеграции.
