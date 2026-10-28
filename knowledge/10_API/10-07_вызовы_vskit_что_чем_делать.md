---
id: 10-07
title: Вызовы vskit — что чем делать, какие открывают окна; минимальный цикл «описание -> проверки -> симуляция»; модули библиотеки
tags: [vskit, вызовы, быстрый старт, модули, шаблон]
applies_to: Visual State 9.1.1.3863, Python 3.13 64-bit
status: проверено
verified: 2026-10-14 — каждая строка таблицы прогнана tests/ (test_model, test_coder, test_design, test_sim, test_layout, test_doc, test_shot); 2026-10-28 перенесено из SKILL.md без изменения сути
source: эксперимент; перенесено из SKILL.md 0.3.0
---

# Вызовы vskit

Подключение — от корня набора (папка `SKILL.md`), переменные окружения не
нужны:

```python
import sys; sys.path.insert(0, r"<корень>")
import vskit as vk
vk.utf8_console()            # иначе print с кириллицей падает
print(vk.version(), vk.license_ok()[0])
```

## Что чем делать

| Задача | Как | Окна |
|---|---|---|
| Прочитать модель любого формата (1–11) | `p = vk.load(vsp)`; `print(p)`; `p.to_dict()` | нет |
| Новый автомат текстом | `vk.Machine(...)`, `vk.Project(...).add_system(...).save(папка)` | нет |
| Правка существующей модели | `d = vk.from_project(vk.load(vsp))` -> методы -> `d.save(новая_папка)` | нет |
| Сгенерировать код | `vk.generate(vsp, out_dir, coder="hcoder"/"classic", options=..., systems=...)` | нет |
| Проверить, что код компилируется | `vk.compile_check(out_dir)` (arm-none-eabi-gcc, `nm`) | нет |
| Формальная проверка | `vk.verify(vsp)` (Verificator) | нет |
| Всё сразу | `vk.full_check(vsp, out_dir)` — схема, API, Verificator, кодер, gcc | нет |
| Симуляция по событиям | `with vk.Simulator(vsp) as s: s.deduct("SE_RESET"); s.deduct("evX", 1)` | Validator на секунды; `desktop=HiddenDesktop()` — на скрытом столе |
| Откроет ли Designer | `vk.designer_check(vsp, save=True)` | Designer на ~8 с |
| Посмотреть диаграмму, не мешая человеку | `vk.designer_shot(vsp, "all.png", zoom=50)`; лист региона — `open_path=[0,0,0,0,0,k]` ([20-05](../20_ПРИЁМЫ/20-05_снимок_designer_на_скрытом_столе.md)) | Designer на СКРЫТОМ столе: окон нет |
| Раскладка диаграммы | считает `vskit.layout` при `save()` ([20-04](../20_ПРИЁМЫ/20-04_раскладка_блок-схем.md), [10-06](10-06_диаграмма_страницы_листы_стиль_линий.md)) | нет |
| Второе мнение о модели | `vk.smapi.inventory(vsp)`, `vk.schema_check(vsp)` | нет |
| Документ автомата | `vk.document(machine, path=..., strict=True)` ([20-06](../20_ПРИЁМЫ/20-06_документация_автомата_по_русски.md)) | нет |
| Новый проект автомата | скопировать `templates/new_machine`, вписать в `KIT` в `build.py` корень набора, править `model.py`, `python build.py --sim` | — |

Сигнатуры — docstring в `vskit/*.py`; ключи кодеров —
`vk.options_help("hcoder")` и [10-02](10-02_coder_и_hcoder_из_командной_строки.md).

## Минимальный цикл

```python
m = vk.Machine("Lamp")
m.event("evToggle"); m.event("evLevel", ("lvl", "VS_UINT8"))
m.action("LampOn"); m.action("LampOff"); m.action("LampSet", ("lvl", "VS_UINT8"))
m.var("level", "VS_UINT8", 0, lo=0, hi=3)
m.state("Off", entry="LampOff()"); m.state("On", entry="LampOn()")
m.state("On.Dim"); m.state("On.Bright")
m.initial("Off"); m.initial("On.Dim")
m.trans("Off", "On", "evToggle"); m.trans("On", "Off", "evToggle")
m.trans("On.Dim", "On.Bright", "evLevel(lvl)", guard="lvl > 1 && lvl <= 3",
        do=["level = lvl", "LampSet(level)"])
vsp = vk.Project("LampProject").add_system("LampSys", m).save(r"D:\проект\vs_model")
rep = vk.full_check(vsp, r"D:\проект\vs_gen"); print(rep); rep.check()
with vk.Simulator(vsp) as s:
    s.deduct("SE_RESET"); print(s.deduct("evToggle"))   # [('action', 'LampOn', None)]
```

## Модули

| Модуль | Что в нём |
|---|---|
| `env` | установка, версия, лицензия, рабочие папки, GCC (через соседний скилл mcu) |
| `model` | `load`, `Project`/`Machine`/`Vertex`/`Transition` — разбор XML |
| `design` | `Machine`, `Project`, `from_project` — запись format 11 |
| `coder` | `generate`, `copy_model`, `options_help` |
| `verificator` | `verify` |
| `sim` | `Simulator`, `ControlCenter`, `designer_check`, `windows` |
| `build` | `compile_check` |
| `smapi` | `inventory`, `normalize` — StateMachineAPI64.dll |
| `schema` | `schemas`, `validate`, `validate_project` — схема из HCoder.exe |
| `report` | `full_check`, `Report` |
| `doc` | `document`, `undocumented` — русский Markdown об узлах и связях из модели и заметок `note=` |
| `layout` | раскладка диаграмм: слои, порты, шины, подписи, листы |
| `shot` | `designer_shot` — снимок Designer на скрытом столе (соседний скилл hidden-desktop) |

## Куда смотреть

Порядок: `INDEX.md` -> файл базы -> docstring -> документация IAR
(`<vs_root>\doc\UserGuide.chm`, `doc\StateMachineAPI\html`) -> эксперимент
на копии ([00](../00_ПРАВИЛА.md)).
