---
id: 20-02
title: Автомат проектируется текстом — описание на Python (vskit.Machine) -> .vsp/.vsr -> проверки -> код; Designer остаётся для просмотра и ручной раскладки
tags: [проектирование, design, machine, шаблон, модель текстом, рекомендации]
applies_to: Visual State 9.1.1.3863
status: проверено
verified: 2026-10-12 — templates/new_machine и tests/test_design.py: описание -> схема, API, Verificator, HCoder/Coder, gcc, Validator, Designer — без ошибок
source: эксперимент
---

# Автомат текстом

## Цикл

```
model.py (описание)  ->  vs_model\*.vsp/.vsr  ->  full_check  ->  vs_gen\*.c/.h
                                  |                    |
                              Designer             Simulator (сценарий событий)
```

Шаблон — `templates/new_machine`: правится только `model.py`,
`build.py` пересоздаёт модель и код, `--sim` прогоняет сценарий в
Validator, `--designer` открывает модель в Designer.

## Описание

```python
m = vk.Machine("Button")
m.event("evPress"); m.event("evTimeout")
m.event("evData", ("value", "VS_UINT8"))        # аргументы событий
m.action("TimerStart", ("ms", "VS_UINT16"))     # действия пишет человек в C
m.const("LONG_MS", "VS_UINT16", 800)
m.var("count", "VS_UINT8", 0, lo=0, hi=9)       # домен — его проверит Verificator
m.state("Idle")
m.state("Pressed", entry="TimerStart(LONG_MS)", exit="TimerStop()")
m.state("On.Fast")                              # вложенное: путь через точку
m.state("On.LedA", region="Leds")               # второй (ортогональный) регион
m.initial("Idle"); m.initial("On.Fast"); m.initial("On.LedA")
m.trans("Idle", "Pressed", "evPress")
m.trans("A", "B", "evData(v)", guard="v > 3 && v < 9", do=["count = v", "Show(count)"])
m.trans("X", "Y", "evTick", when_in="On.LedA")  # [in State]
m.internal("Idle", "evTick", do="Beep()")       # реакция без выхода
c = m.choice("On"); m.trans(c, "On.Fast", None, guard="count > 5")
m.trans(c, "On.LedA", None, otherwise=True)     # ветка else
vk.Project("ButtonProject").add_system("ButtonSys", m).save(folder)
```

`save()` ловит до записи: несуществующие события, действия, состояния,
неверное число аргументов, регион без начального состояния, переход из
состояния без события; после записи — проверяет файлы схемой.

## Рекомендации, как проектировать автоматы дальше

1. **Источник истины — `model.py` в репозитории проекта**, а не .vsr:
   текст читается в diff и в ревью, ИИ правит его без мыши. `vs_model\`
   и `vs_gen\` — производные; их можно класть под git, но править только
   через `model.py`.
2. **Одно событие — один физический факт**, уже отфильтрованный кодом
   (дребезг, таймауты, приём пакета — в C). Автомат — логика режимов, а
   не опрос железа. Время — событием `evTimeout` от таймера, запущенного
   действием.
3. **Действия — тонкие функции C** с понятными аргументами; данные,
   нужные условиям, — внутренние переменные модели с доменом (`lo`, `hi`),
   тогда Verificator проверит выход за диапазон (он реально ловит
   `level = lvl` без ограничения `lvl` в guard).
4. **После каждой правки — `full_check`**: схема, API, Verificator, код,
   gcc. Предупреждения Verificator о неиспользуемых элементах — сигнал
   недописанной модели; конфликты и выход за домен — ошибки.
5. **Поведение фиксировать сценарием** (`SCENARIO` в шаблоне): событие ->
   ожидаемые действия и присваивания из Validator. Это регрессионный тест
   модели без железа.
6. **Имя системы не совпадает с именем проекта** (`ButtonProject` /
   `ButtonSys`) — [30-02](../30_ГРАБЛИ/30-02_имя_системы_равно_имени_проекта.md).
7. Существующую модель из Designer переводить в текст через
   `vk.from_project(vk.load(vsp))` один раз, дальше вести текстом; GUID
   сохраняются, раскладка на диаграмме строится заново (сеткой).

## Ограничения vskit.design (не проверено или не сделано)

Подмашины, точки входа/выхода, fork/join, группы событий, сигналы в
действиях (`^Signal`), элементы уровня проекта, теги, заметки, несколько
систем с общими событиями — не пишутся или не проверены. Раскладка —
столбец сверху вниз; переходы рисуются прямыми.

## Чем подтверждено

12.10.2026: `templates/new_machine` (`build.py --sim`) — все проверки OK,
сценарий из 4 событий совпал; `tests/test_design.py` — лампа с вложенными
и ортогональными регионами, внутренним переходом, аргументами событий и
`[in State]`.
