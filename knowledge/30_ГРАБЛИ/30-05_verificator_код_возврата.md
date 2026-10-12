---
id: 30-05
title: Код возврата Verificator об успехе не говорит — неизвестная система даёт код 0, ошибки модели в отчёте — код 0, синтаксическая ошибка — код 1 без причины
tags: [verificator, код возврата, vre, система]
applies_to: Visual State 9.1.1.3863
status: проверено
verified: 2026-10-12 — CDPlayer с неизвестной системой; модели с конфликтом и выходом за домен; копия CDPlayer с ошибкой в guard
source: эксперимент
---

# Verificator: код возврата

## Что происходит

| Случай | Код | Вывод |
|---|---|---|
| система `NoSuchSystem` | **0** | `The Verificator didn't complete with success.` / `Could not load the system 'NoSuchSystem'.` |
| конфликт переходов, выход за домен | 0 | `Verificator completed - 1 error(s), 0 warning(s).` |
| ошибка в тексте guard | 1 | `The Verificator didn't complete with success.` — причина не печатается |
| в регионе нет начального, а вход в состояние прямой | 1 | `No initial reaction or state specified for state '…Run.Region1'.` |

Ключ `-vver.txt` пишет `ver.txt.vre`: суффикс добавляется всегда.

## Как правильно

Успех — только строка `completed - 0 error(s)`; без неё — провал, и
причину смотреть в выводе Coder/HCoder на той же модели. `vk.verify()`
так и считает (`errors is None` -> не ok), а неизвестную систему
отвергает до запуска.

## Как неправильно

`returncode == 0` -> «модель проверена».

## Чем подтверждено

`tests/test_coder.py` — 12.10.2026: прямой запуск Verificator.exe с
неизвестной системой (код 0) и `vk.verify` на сломанной копии (код 1,
`errors is None`); `tests/test_design.py` — конфликт найден при коде 0.
