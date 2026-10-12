---
id: 30-07
title: Validator.exe и Designer.exe — только оконные программы, ключей командной строки для пакетной работы нет; Validator.exe --help открывает окно и висит
tags: [validator, designer, окно, командная строка, тайм-аут]
applies_to: Visual State 9.1.1.3863
status: проверено
verified: 2026-10-12 — Validator.exe --help под subprocess с тайм-аутом 40 с; поиск по руководству пользователя
source: эксперимент; UserGuide.chm (разделы Validator, Designer, Control Center)
---

# Validator и Designer из командной строки

## Что происходит

`Validator.exe --help` не печатает справку: открывается окно Validator,
процесс ждёт человека; снят по тайм-ауту 40 с. В руководстве ключей
командной строки для Validator и Designer нет; есть только у Coder,
HCoder, Documenter и Verificator (`Verificator.exe` без аргументов
печатает синтаксис).

## Как правильно

* Пакетная проверка — `Verificator.exe` ([10-03](../10_API/10-03_verificator_из_командной_строки.md)).
* Симуляция и открытие в Designer — через `ControlCenter.exe`
  ([10-04](../10_API/10-04_control_center_validator_designer.md)):
  `vk.Simulator`, `vk.designer_check`. Окна при этом видны на экране
  несколько секунд.
* Любой запуск программ с окнами — с тайм-аутом и проверкой окон
  (`vk.windows()`: класс `#32770` — диалог).

## Как неправильно

`subprocess.run(["Validator.exe", vsp])` без тайм-аута — вечное ожидание.

## Чем подтверждено

12.10.2026: ручной запуск (`TIMEOUT` через 40 с, процесс снят); Documenter
и Verificator без аргументов печатают справку и выходят с кодом 0.
