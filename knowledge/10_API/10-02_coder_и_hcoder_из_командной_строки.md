---
id: 10-02
title: Coder.exe и HCoder.exe работают из командной строки без окон; значение ключа пишется впритык (-pathout\), успех — код 0 И строка «completed - 0 error(s)»; код компилируется arm-none-eabi-gcc без библиотек Visual State
tags: [coder, hcoder, генерация, ключи, код возврата, cre, gcc]
applies_to: Visual State 9.1.1.3863, arm-none-eabi-gcc 10.3.1
status: проверено
verified: 2026-10-12 — генерация обоими кодерами на CDPlayer, AVSystem, моделях vskit.design и на копии рабочего проекта; ошибки модели; компиляция -Wall -Wextra
source: эксперимент; справка самих программ (запуск без аргументов)
---

# Coder и HCoder

## Что есть

| Программа | Что делает | Окна |
|---|---|---|
| `bin64\HCoder.exe` | иерархический кодер (по умолчанию у новых проектов 9.x) | нет |
| `bin64\Coder.exe` | классический кодер (Adaptive/Uniform API, readable) | нет |

Без аргументов оба печатают полный список ключей и выходят с кодом 0 —
`vk.options_help("hcoder")`, `vk.options_help("classic")`.

## Синтаксис

```
HCoder.exe <проект.vsp> [--l] [--@файл_ключей] -ключ[значение] ... [-VСистема -ключ ...]
```

* значение — **впритык**: `-pathC:\out\`, `-readable1`, `-D2`,
  `-projectheaderPrj.h`; булевы — `0|1`;
* ключи проекта — где угодно; ключи системы — после `-V<имя системы>`;
  до первого `-V` действуют на все системы;
* `--l` — взять ключи из `.vtg` (то, что настроено в Navigator);
* `-path` — папка вывода (по умолчанию `coder\` рядом с .vsp); абсолютный
  путь с кириллицей и пробелами работает;
* `-R` — имя отчёта (`VSCoder.cre`; у Coder — XML со стилем `coder.xsl`,
  у HCoder — текст);
* неизвестный ключ — код 1, «Command line option ... is not recognized».

Полезные ключи (проверены): Coder `-readable1` (читаемый код), HCoder
`-cpp1` (C++: `<Система>.cpp`, отдельного .cpp проекта нет), `-projectheader`
/ `-projectsource`, `-D2` (ширина данных 32 бита — видно в .cre: «Data
width : 32-bit»), системный `-VLampSys -txts1` (имена состояний в коде —
«State name inclusion : Names included»). Применённые ключи надёжнее всего
читать из отчёта `.cre` (`r.report`). Остальные — по справке, не проверены.

## Что получается

| | HCoder | Coder |
|---|---|---|
| проект | `<Проект>.c/.h` — ядро (таблицы, `VSDeduct`, типы) | `<Проект>.c/.h` — типы, сигнатура |
| система | `<Система>.c/.h` — данные модели, объявления действий | `<Система>.c/.h` — `<Система>VSDeduct`, `...SEM_Init` |
| прочее | `.ipcf`, `VSCoder.cre` | `.ipcf`, `vscoder.cre`, `coder.xsl` |

Код самодостаточен: внешние символы — только функции действий
(`extern void Имя (...)` в заголовке системы) и `memcpy`/`__aeabi_*`.
Проверено `vk.compile_check`: `-mcpu=cortex-m4 -mthumb -std=c99 -Wall
-Wextra -O2`, HCoder — 0 предупреждений, Coder — 4–6 предупреждений
`-Wunused-parameter` (`...VSElementName`, `...VSElementExpl` и др.).
C++ от HCoder (`-cpp1`) ссылается ещё на рантайм C++ (`__cxa_pure_virtual`,
`operator delete`, `__aeabi_unwind_cpp_pr0`) — их даёт libstdc++ при
сборке.

## Коды возврата и вывод

| Случай | Код | Вывод |
|---|---|---|
| успех | 0 | `... completed - 0 error(s), 0 warning(s)` |
| синтаксис guard | 1 | `Error in the guard expression '...'. Syntax error at position N` |
| переход без события | 1 | `Transition without any trigger: '...'` ([30-04](../30_ГРАБЛИ/30-04_неизвестное_имя_события_теряет_триггер.md)) |
| нарушение схемы XML | 1 | `... element 'X' is not allowed for content model '(...)'` ([30-08](../30_ГРАБЛИ/30-08_порядок_элементов_по_схеме.md)) |
| нет файла | 1 | `The file '...' is not a project file.` |

HCoder при ошибке печатает **только** строку ошибки, без заголовка и без
«completed». Coder печатает строку «Connecting to IAR Visual State
license...», HCoder — нет (нужна ли HCoder лицензия — не проверено).

## Как правильно

```python
r = vk.generate(vsp, r"D:\проект\vs_gen", coder="hcoder",
                options={"D": 2}, systems={"LampSys": {"txts": 1}})
r.check()                        # CoderError с текстом ошибок
print(vk.compile_check(r.out_dir))
```

`generate()` копирует модель в рабочую папку, запускает кодер там и
переносит результат; при совпадении имени системы с именем проекта сам
переименовывает файлы проекта ([30-02](../30_ГРАБЛИ/30-02_имя_системы_равно_имени_проекта.md)).

## Как неправильно

`-path out\` (с пробелом) — ключ без значения, `out\` — лишний аргумент.
Судить об успехе только по коду 0 — при совпадении имён код 0, а файлы
затёрты.

## Чем подтверждено

`tests/test_coder.py`, `tests/test_design.py`, `tests/test_project.py` —
12.10.2026, все проходят.
