---
id: 10-04
title: Validator и Designer управляются из скрипта через ControlCenter.exe (JSON-RPC по TCP) — пошаговая симуляция с ответом «какие действия вызваны», открытие и сохранение модели в Designer
tags: [control center, json-rpc, validator, designer, симуляция, tcp]
applies_to: Visual State 9.1.1.3863
status: проверено
verified: 2026-10-12 — симуляция CDPlayer и AVSystem (ответы совпали с примером в документации), модели vskit.design; launchDesigner/saveDesigner/quitDesigner на сгенерированной модели
source: эксперимент; UserGuide, раздел «Using IAR Visual State remotely via the Control Center»
---

# Control Center

## Что это

`bin64\ControlCenter.exe [-port<N>] [-verbose]` — консольный сервер
JSON-RPC 2.0 по TCP (порт по умолчанию 8090). По командам запускает
Validator или Designer **с окнами** и пересылает им запросы.

Методы из документации. Проверены: `launchValidator`,
`disableLookAheadGuardCheck`, `deductEvent`, `quitValidator`,
`launchDesigner`, `saveDesigner`, `quitDesigner`, `quit` (с `{"all":
true}` закрывает все Validator/Designer, в том числе оставшиеся от
прошлых сеансов). Не проверены: `saveValidator`, `saveAll`,
`createProjectAndStateMachine`, `addStateMachine`, `launchSceneComposer`.

## Обмен

Каждый запрос — одна JSON-строка **с переводом строки в конце**
(`\r\n`); без него ответа нет никогда
([30-06](../30_ГРАБЛИ/30-06_control_center_перевод_строки_и_диалоги.md)).

```
-> {"jsonrpc":"2.0","id":1,"method":"launchValidator","params":{"projectPath":"C:/w/Lamp.vsp"}}
<- {"id":1,"jsonrpc":"2.0","result":true}
-> {"jsonrpc":"2.0","id":2,"method":"deductEvent","params":{"projectPath":"C:/w/Lamp.vsp","eventName":"evLevel","eventArguments":[3]}}
<- {"id":2,"jsonrpc":"2.0","result":{"actions":[
     {"assignment":{"assignedTo":"level","assignedToIndex":null,"value":3}},
     {"action":{"actionArguments":[3],"actionName":"LampSet"}}]}}
```

Ответ `deductEvent` — действия и присваивания в порядке выполнения
(выход, переход, вход). Если модели нужно значение, возвращаемое
действием, Validator **сам** шлёт клиенту встречный запрос
`getActionFunctionCallResult` с `actionName`/`actionArguments` и ждёт
`{"jsonrpc":"2.0","id":<его id>,"result":<число>}`; потом приходит ответ
на `deductEvent`. Первое событие — `SE_RESET` (входы начальных состояний).

`projectPath` — полный путь, прямые слэши работают. Проект, не
загруженный в Validator, даёт `"result": "No project loaded"` — строку
вместо объекта.

## Как правильно

```python
with vk.Simulator(vsp, answers={"FindLastTrack": 3}) as s:
    s.deduct("SE_RESET")
    print(s.deduct("evPlayKey"))    # [('assign','lastTrack',3), ('action','LocateTrackStart',None), ...]
print(vk.designer_check(vsp, save=True))   # {'ok': True, ...}
```

`Simulator` работает над копией, кладёт рядом `.vws` с
`IncludeExcluded=FALSE`, сверяет имя события с моделью до отправки,
закрывает Validator через `quitValidator` и `quit`. `designer_check`
открывает копию, ищет окна-диалоги (`vk.windows()`), по желанию
сохраняет копию самим Designer, закрывает без вопроса.

## Как неправильно

* `telnet` и ручной ввод — из документации; для скрипта бесполезен.
* Запускать Validator напрямую `Validator.exe проект.vsp` и ждать —
  управлять им дальше нечем.

## Чем подтверждено

12.10.2026, `tests/test_sim.py`: CDPlayer — 6 событий, AVSystem —
`evPlayKey` со встречным запросом `FindLastTrack` (ответы совпали с
примером из документации); `tests/test_design.py`: 6 шагов на модели
vskit.design, Designer открыл и сохранил её, после сохранения разбор
совпал. Окна закрываются: `vk.windows()` пуст после выхода.

## Скрытый рабочий стол
`ControlCenter(desktop=HiddenDesktop())` (набор HiddenDesktop-Kit) запускает
ControlCenter.exe на скрытом столе; Designer и Validator наследуют стол,
окон у человека нет; то же для симуляции: `Simulator(vsp, desktop=...)`.
Подробно — [20-05](../20_ПРИЁМЫ/20-05_снимок_designer_на_скрытом_столе.md).
