---
id: 10-03
title: Пакетная проверка модели — Verificator.exe (тупики, конфликты, домены, недостижимое); Validator.exe пакетного режима не имеет
tags: [verificator, validator, проверка, vre, тупики, конфликты]
applies_to: Visual State 9.1.1.3863
status: проверено
verified: 2026-10-12 — CDPlayer (чисто), AVSystem (тупик состояния), модель с конфликтом и с выходом за домен, сломанная модель, неизвестная система
source: эксперимент; справка Verificator.exe без аргументов
---

# Verificator

## Синтаксис

```
Verificator.exe <проект.vsp> <система> [-v<отчёт>] [-x<проверка>] [-h<сек>] ...
```

* `-v<файл>` — отчёт в `<файл>.vre` (суффикс `.vre` добавляется всегда:
  `-vver.txt` даёт `ver.txt.vre`);
* `-x<проверка>` — исключить: `use`, `activation`, `conflicts`,
  `state_dead_ends`, `local_dead_ends`, `system_dead_ends`,
  `domain_errors`; `-h<n>` — тайм-аут; остальные — справка без аргументов;
* окон не открывает, 0.1 с на примерах поставки; лицензию запрашивает
  («Connecting to IAR Visual State license...»).

## Разделы отчёта .vre

USE OF ALL ELEMENTS, ACTIVATION OF ALL ELEMENTS, CONFLICTS, STATE DEAD
ENDS, LOCAL DEAD ENDS, SYSTEM DEAD ENDS, DOMAIN ERRORS, AMBIGUOUS
ASSIGNMENTS (static/dynamic), SIGNAL QUEUE. Чистый раздел — одна строка
`None.` / `All elements are used.` / ...

Что он находит на деле:

* неиспользуемые события, действия, переменные — **предупреждения**, код 0;
* тупик состояния (AVSystem: `...Playing.Region1.PlayTrack`) —
  предупреждение, код 0;
* конфликт: внутренний и внешний переход одного состояния по одному
  событию — **ошибка** (`Conflict(s) for the trigger evStopKey`), код 0;
* выход за домен: `level = lvl` при `level` в [0..3], а `lvl` —
  VS_UINT8 без ограничения в guard — ошибка в DOMAIN ERRORS с правилом и
  состоянием.

## Коды возврата

| Случай | Код | Вывод |
|---|---|---|
| проверено, есть ошибки или предупреждения | 0 | `Verificator completed - N error(s), M warning(s).` |
| синтаксическая ошибка модели | 1 | `The Verificator didn't complete with success.` — без причины |
| неизвестная система | **0** | та же строка и `Could not load the system 'X'.` |

Успех — только по строке «completed - 0 error(s)»
([30-05](../30_ГРАБЛИ/30-05_verificator_код_возврата.md)). Причину
синтаксической ошибки показывает Coder/HCoder.

## Validator

`Validator.exe` — только оконная программа: `Validator.exe --help`
открывает окно и висит (снят по тайм-ауту 40 с). Пакетного анализа нет;
пошаговая симуляция из скрипта — через Control Center
([10-04](10-04_control_center_validator_designer.md)).

## Как правильно

```python
v = vk.verify(vsp)                 # все системы проекта, над копией
print(v)                           # только разделы с замечаниями
v.check(allow_warnings=False)      # VerifyError, если есть что-то
v.reports[0].findings()            # {раздел: [строки]}
```

## Чем подтверждено

`tests/test_coder.py`, `tests/test_design.py` — 12.10.2026.
