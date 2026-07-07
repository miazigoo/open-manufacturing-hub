# Собираем XML или raw text body в Step 3A

Step 3A умеет собирать не только JSON. Для сценариев, где вызывающей системе нужен компактный XML или строковый ответ, используйте `XML` или `Raw text`.

Этот шаг не возвращает ответ caller и не отправляет HTTP-запрос. Он только сохраняет body как `target_payload`.

## XML

Выберите `XML` и вставьте template:

```xml
<Response>
  <Order>{{order.Number}}</Order>
  <RowsCount>{{codes.length}}</RowsCount>
</Response>
```

Preview выполнит подстановку и проверит, что XML well-formed.

Значения переменных XML-escaped. Если `order.Number` содержит `&`, результат будет `&amp;`.

## Raw Text

Выберите `Raw text` и вставьте template:

```text
OK order={{order.Number}} codes={{codes.length}}
```

Preview вернет строку:

```text
OK order=260666/6938 codes=180
```

## Частые ошибки

`VARIABLE_NOT_FOUND` — переменная отсутствует или путь написан неверно.

`PAYLOAD_XML_INVALID` — после рендера XML стал невалидным. Проверьте один корневой элемент и закрывающие теги.

Пустой `save_as` или имя с пробелами не сохраняется. Используйте `target_payload`, `xml_response` или другое имя из латиницы, цифр и underscore.
