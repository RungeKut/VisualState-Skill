---
id: 30-03
title: VSMProjectSave(новый_путь) пишет .vsp по новому пути, а .vsr — на их старое место, со ссылкой «..\старая_папка\X.vsr»; пути в API — UTF-8
tags: [state machine api, сохранение, vsr, оригинал, utf-8, кириллица]
applies_to: Visual State 9.1.1.3863, State Machine API 1600
status: проверено
verified: 2026-10-12 — загрузка копии CDPlayer и сохранение в другую папку переписали .vsr копии в format 11; путь с кириллицей в cp1251 — отказ, в UTF-8 — загрузка
source: эксперимент
---

# State Machine API: сохранение и пути

## Что происходит

```python
VSMProjectLoad(b"C:\\w\\cd\\CDPlayer.vsp", &h)
VSMProjectSave(b"C:\\w\\cd_api\\CDPlayer.vsp", h)
```

В `cd_api\` появился только `CDPlayer.vsp` (format 11) с
`<file>..\cd\CDPlayer.vsr</file>`, а `cd\CDPlayer.vsr` переписан на месте
(format 6 -> 11, новое время изменения). «Сохранить как» в API нет:
оригинал автомата меняется.

Путь, переданный в кодировке ANSI (`"…\модель с пробелом\…".encode("mbcs")`),
даёт ошибку «The file '…' is not a project file.»; тот же путь в UTF-8
загружается.

## Как правильно

Сначала скопировать модель, потом загрузить и сохранить копию в неё же:

```python
vk.smapi.normalize(vsp, r"C:\w\copy")   # copy_model + Load + Save по месту копии
```

Строки в API — UTF-8 в обе стороны (`vskit.smapi` кодирует и
декодирует так).

## Как неправильно

`VSMProjectSave` «в другую папку, чтобы не трогать оригинал» — оригинал
.vsr как раз и перепишется.

## Чем подтверждено

12.10.2026: опыт на копии CDPlayer (только копия была изменена);
`tests/test_model.py` — `normalize` даёт format 11, оригинал примера не
изменился (отпечатки совпали).
