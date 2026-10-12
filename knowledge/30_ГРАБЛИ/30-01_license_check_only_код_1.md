---
id: 30-01
title: Coder.exe --license_check_only возвращает код 1 и тогда, когда лицензия найдена — решает строка «Found a IAR Visual State license»
tags: [лицензия, coder, код возврата, lms]
applies_to: Visual State 9.1.1.3863, лицензия LMS2 на этой машине
status: проверено
verified: 2026-10-12 — несколько запусков, всегда код 1 при строке «Found a ... license»; генерация тут же проходит
source: эксперимент
---

# Проверка лицензии

## Что происходит

```
> Coder.exe --license_check_only
Connecting to IAR Visual State license...
Found a IAR Visual State license.
код 1
```

Сразу после этого `Coder.exe проект.vsp` генерирует код с кодом 0.

## Почему

Неизвестно. Похоже, ключ проверяет лицензию и выходит «без работы»,
что Coder считает неуспехом.

## Как правильно

```python
ok, text = vk.license_ok()     # True, если в выводе «Found a IAR Visual State license»
```

Coder и Verificator при старте пишут «Connecting to IAR Visual State
license...»; HCoder такой строки не печатает (нужна ли ему лицензия — не
проверено). Поведение без лицензии и при занятой сетевой лицензии — не
проверено: отказа на этой машине не было ни разу.

## Как неправильно

`if subprocess.run([...,"--license_check_only"]).returncode != 0:
raise "нет лицензии"` — ложная тревога при рабочей лицензии.

## Чем подтверждено

12.10.2026: ручной запуск и `tests/test_coder.py` (первая проверка).
