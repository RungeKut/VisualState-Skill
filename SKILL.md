---
name: visualstate
description: "Конечные автоматы в IAR Visual State скриптами — чтение модели (.vsp/.vsr — XML), создание и правка автомата текстом на Python, генерация C/C++ кода Coder и HCoder из командной строки, проверка Verificator, симуляция в Validator и открытие в Designer через Control Center, проверка, что код компилируется arm-none-eabi-gcc. Используй ВСЕГДА, когда речь о Visual State, visualSTATE, IAR Visual State, Designer, Validator, Verificator, Navigator, Coder.exe, HCoder.exe, ControlCenter, StateMachineAPI, файлах .vsp/.vsr/.vnw/.vtg/.vws/.vre/.cre, конечном автомате (state machine, statechart) для прошивки, состояниях, событиях, переходах, guard, entry/exit, VSDeduct, SEM_; а также при ошибках «Transition without any trigger», «is not allowed for content model», «The Verificator didn't complete with success», «No project loaded». Содержит библиотеку vskit и базу проверенного опытом знания."
---

# IAR Visual State: автоматы скриптами

Корень набора — папка, из которой прочитан этот файл (клон
`RungeKut/VisualState-Skill`); соседние скиллы — рядом с ней: hidden-desktop
(снимки Designer), mcu (GCC). Библиотека `vskit`, база `knowledge/` (карта
и поиск по симптому — `INDEX.md`). Общие правила — соседний скилл
skill-skill.

**Первым делом:** `git -C <корень> pull --rebase`; конфликт — разобрать до
работы; владельцу — ещё `gh pr list` (skill-skill, 40-02). База собрана на
Visual State 9.1.1.3863 — сверить `vk.version()` (00).

```python
import sys; sys.path.insert(0, r"<корень>")
import vskit as vk
vk.utf8_console()
print(vk.version(), vk.license_ok()[0])
rep = vk.full_check(vsp, out_dir); print(rep); rep.check()
```

Что чем делать, минимальный цикл, шаблон проекта — 10-07; автомат
текстом — 20-02.

## Железные правила

1. Только над копией: программы Visual State — в `env.job_dir()`, не в
   папке проекта (20-01).
2. Успех — по тексту вывода и файлам, не по коду возврата (30-02, 30-05).
3. Имя системы ≠ имени проекта (30-02).
4. Ссылки проверять до Coder: неизвестное событие теряется молча (30-04).
5. Validator и Designer — только через Control Center, с тайм-аутом;
   после работы `vk.windows()` пуст (30-06). Смотреть диаграмму — только
   на скрытом столе, `vk.designer_shot` (20-05).
6. State Machine API не сохранять «в другую папку»; пути — UTF-8 (30-03).
7. К каждому автомату — русский Markdown об узлах и связях:
   `vk.document(..., strict=True)` (20-06). Раскладку править в
   `vskit.layout`, не руками (20-04, 10-06).
8. Непроверенное не выдавать за проверенное — нигде.

## Правка набора

Нашли грабли — запись по `knowledge/00_ПРАВИЛА.md`, строки в `INDEX.md` и
`CHANGELOG.md`, `git diff`, `python tools/check_docs.py --project "<папка
проекта>"`, коммит, push сразу. В набор — ничего об изделии: ни имён из
его модели, ни снимков его диаграмм (40-02). Коммит — без соавторов.
