---
id: 30-06
title: Control Center молчит без перевода строки и на неизвестное событие; Validator без IncludeExcluded в .vws или на битой модели открывает модальное окно и отвечает «No project loaded»
tags: [control center, validator, json-rpc, диалог, vws, тайм-аут]
applies_to: Visual State 9.1.1.3863
status: проверено
verified: 2026-10-12 — сеансы с CDPlayer, AVSystem, моделями vskit.design; окна прочитаны EnumWindows
source: эксперимент
---

# Control Center: тишина и окна

## Что происходит

1. **Нет перевода строки** — запрос `{"jsonrpc":"2.0",...}` без `\r\n`
   Control Center принимает (в `-verbose` видно «Connected»), но ответа не
   шлёт никогда (ждали 30 с). С `\r\n` — ответ за 0.0–1.1 с.
2. **Неизвестное событие** в `deductEvent` — ответа нет совсем: ни
   ошибки, ни окна (у Validator видимых диалогов нет).
3. **Нет `.vws` или в нём нет `IncludeExcluded=`** (так у примера
   AVSystem): Validator при `launchValidator` открывает модальное окно
   «Include excluded items» (*The project may contain items marked as
   excluded…*), `launchValidator` всё равно отвечает `true`, а каждый
   `deductEvent` — строкой `"No project loaded"`.
4. **Модель с ошибкой**: окно «IAR Visual State Validator» — *Unable to
   create workspace*, дальше то же «No project loaded».
5. После такой неудачной загрузки следующие запросы запускают новые
   процессы Validator (видели 2–3 с одинаковым окном). `quit {"all":
   true}` закрывает все, даже с открытыми диалогами.

## Как правильно

`vk.Simulator` (vskit/sim.py):

* шлёт `json + "\r\n"`;
* сверяет имя события с моделью до отправки (`SimError`);
* в копии модели создаёт `.vws` или дописывает `IncludeExcluded=FALSE` в
  `[ProjectSetup]`;
* строку вместо объекта в ответе превращает в `SimError` со списком
  окон-диалогов (`vk.windows()`);
* в конце `quitValidator` и `quit {"all": true}`.

Модель сначала прогнать через `full_check` — битая модель в Validator
даёт только окно.

## Как неправильно

Ждать ответа без тайм-аута; слать события по памяти; запускать Validator
на модели прямо из Designer-папки (там нет `.vws`, а писать туда нельзя —
[20-01](../20_ПРИЁМЫ/20-01_работать_на_копии.md)).

## Чем подтверждено

12.10.2026: отладочные сеансы (без `\r\n` — тайм-аут; `evNoSuch` —
тайм-аут; модель без `.vws` — окно «Include excluded items» у трёх
процессов Validator); `tests/test_sim.py`, `tests/test_design.py` — OK с
обходами.
