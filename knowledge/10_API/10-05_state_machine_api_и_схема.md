---
id: 10-05
title: Два независимых способа проверить модель без Coder — State Machine API (StateMachineAPI64.dll через ctypes) и XML-схема, зашитая в программы поставки (lxml)
tags: [state machine api, ctypes, dll, xsd, схема, lxml, проверка]
applies_to: Visual State 9.1.1.3863, API версии 1600, lxml 6.1.3
status: проверено
verified: 2026-10-12 — inventory() совпал с XML-разбором на всех примерах; схемы format 1, 6, 8, 11 приняли примеры и модели vskit.design, отвергли переставленный элемент
source: эксперимент; doc\StateMachineAPI (заголовок и HTML)
---

# State Machine API и схема

## State Machine API

`bin64\StateMachineAPI64.dll` — C-библиотека: загрузка, обход, создание,
правка, сохранение модели. Описание — `doc\StateMachineAPI\
StateMachineAPI.h` и `html\index.html`. Функции возвращают 1 (успех) или
0; текст ошибки — `VSMGetErrorStringPtr`. Хэндл — `size_t`. Экспорт —
простые имена (`VSMProjectLoad`), прослойка `StateMachineAPI.hc` для
ctypes не нужна. По документации лицензии не требует (без лицензии не
проверялось).

```python
inv = vk.smapi.inventory(vsp)   # {'systems': {...}, 'vertices': [...], 'external': n, 'internal': n}
vk.smapi.normalize(vsp, r"C:\w\copy")   # копия, пересохранённая в format 11
```

Обход, проверенный в `vskit.smapi`: `VSMSystemGetHandle(hProj, i)` →
`VSMTopstateGetHandle(hSys, i)` → `VSMRegionGetHandle(hVertex, i)` →
`VSMVertexGetHandle(hRegion, i)` → `VSMExternalTransitionGetHandle` /
`VSMInternalTransitionGetHandle`; перебор индекса до возврата 0.

Строки API — **UTF-8, пути тоже**; путь в ANSI с кириллицей даёт «is not a
project file». `VSMProjectSave(путь, h)` пишет .vsr на старое место
([30-03](../30_ГРАБЛИ/30-03_state_machine_api_пишет_vsr_на_месте.md)).

Создание и правка модели через API (`VSMVertexAdd`, `VSMEventAdd`...) не
проверены: модель проще и прозрачнее писать XML-ом
([20-02](../20_ПРИЁМЫ/20-02_автомат_текстом_на_python.md)), а API
использовать как второе мнение.

## XML-схема

Схемы форматов 1..11 лежат внутри `Coder.exe`, `HCoder.exe`,
`Designer.exe` и др. (блоки `<xs:schema>`; 11 штук по порядку = номер
формата: первая без пространства имён, как файлы format 1).
`vskit.schema.schemas()` вырезает их из HCoder.exe в
`<рабочая папка>\xsd\<версия>\formatNN.xsd`; в набор они не кладутся — это
файлы IAR.

lxml (libxml2) строже Xerces внутри Visual State: `memberTypes="vsScalarType
..."` без префикса он не принимает — `schemas()` дописывает `vs:`.

```python
vk.schema.validate(r"C:\w\Lamp.vsr")    # [] или ['строка N: ...']
vk.schema_check(vsp)                    # {файл: [ошибки]} по всему проекту
```

`Project.save()` проверяет записанное схемой сам (если есть lxml).

## Чем подтверждено

12.10.2026: `tests/test_model.py` — API и XML-разбор совпали на 6
примерах (форматы 1, 6, 8); схема приняла все примеры, копии рабочего
проекта (format 11) и модели vskit.design; переставленный `exitReactions`
отвергнут схемой («This element is not expected») и HCoder («not allowed
for content model»).
