---
name: visualstate
description: "Конечные автоматы в IAR Visual State скриптами — чтение модели (.vsp/.vsr — XML), создание и правка автомата текстом на Python, генерация C/C++ кода Coder и HCoder из командной строки, проверка Verificator, симуляция в Validator и открытие в Designer через Control Center, проверка, что код компилируется arm-none-eabi-gcc. Используй ВСЕГДА, когда речь о Visual State, visualSTATE, IAR Visual State, Designer, Validator, Verificator, Navigator, Coder.exe, HCoder.exe, ControlCenter, StateMachineAPI, файлах .vsp/.vsr/.vnw/.vtg/.vws/.vre/.cre, конечном автомате (state machine, statechart) для прошивки, состояниях, событиях, переходах, guard, entry/exit, VSDeduct, SEM_; а также при ошибках «Transition without any trigger», «is not allowed for content model», «The Verificator didn't complete with success», «No project loaded». Содержит библиотеку vskit и базу проверенного опытом знания."
---

# IAR Visual State: автоматы скриптами

Набор — git-репозиторий. Корень находится так: переменная `VSKIT_HOME`,
иначе junction `~/.claude/skills/visualstate` (Claude Code) или
`~/.kimi-code/skills/visualstate` (Kimi Code) — ведут в `<корень>/skill`.

## Установка на новой машине

```powershell
cd <корень набора>
powershell -ExecutionPolicy Bypass -File tools\setup.ps1
```

Скрипт создаёт junction'ы, ставит `VSKIT_HOME`, включает хук
`commit-msg`, заводит локальный `tools\stoplist.txt`, проверяет Python
64-bit, ставит lxml, находит Visual State, лицензию и arm-none-eabi-gcc.
Прав администратора не требует. Подробности — `knowledge/40_СРЕДА/40-01`.

## ОБЯЗАТЕЛЬНО: синхронизация репозитория

**В начале работы — подтянуть изменения.** Первым действием, до работы с
набором:

```bash
cd "$VSKIT_HOME" && git pull --rebase
```

Конфликт — разобрать сразу: база знаний важнее текущей задачи.

**У владельца — заодно разобрать чужие правки.** Вклад без права записи
приходит pull request'ами, и они висят, пока владелец их не примет. После
`git pull`:

```bash
gh pr list                   # нет gh — REST API, см. 40-02
```

Открытый PR: прочитать diff целиком, прогнать `check_docs.py`, слить
rebase'ом, подтянуть слитое. Порядок и команды —
`knowledge/40_СРЕДА/40-02`. Особое внимание — исполняемым файлам
(`tools/setup.ps1`, `tools/hooks/*`, `*.py`): они окажутся на машине
владельца и будут запускаться.

**Своя правка — сразу в репозиторий.** После каждой правки набора: `git
diff`, `python tools/check_docs.py --project "<папка проекта>"`, коммит,
`git push`. Нет права записи (`403`) — pull request из своего форка, доступ
не подбирать.

## ОБЯЗАТЕЛЬНО: набор не знает об изделии

Репозиторий готовится к публикации. Ни в файлах, ни в тексте коммита — ни
названия изделия, ни имён его автоматов, состояний, событий, действий,
переменных, ни путей и учётных записей. Примеры — на `examples\` поставки
(CDPlayer, AVSystem) или на отвлечённых моделях («кнопка», «лампа»).
Перед коммитом:

```bash
cd "$VSKIT_HOME"
git diff                                                # глазами
python tools/check_docs.py --project "<папка проекта>"  # стоп-слова, имена из модели
git add -A && git commit -m "кратко что и почему"
```

Автор коммитов задан для клона (`git config user.name/user.email` без
`--global`); не задан — спросить человека. Push — только если владелец
завёл удалённый репозиторий и просит (`knowledge/40_СРЕДА/40-02`).

## Версия: сверить до начала работы

База собрана на **IAR Visual State 9.1.1.3863** (`vk.version()`). На другой
версии запись «проверено» читается как «не проверено», пока не
подтверждена (`knowledge/00_ПРАВИЛА.md`, раздел 11).

## Первое действие

```python
import os, sys
sys.path.insert(0, os.environ["VSKIT_HOME"])
import vskit as vk
vk.utf8_console()            # иначе print с кириллицей упадёт
print(vk.version(), vk.license_ok()[0])
```

## Что есть и чем

| Задача | Как | Окна |
|---|---|---|
| Прочитать модель любого формата (1–11) | `p = vk.load(vsp)`; `print(p)`; `p.to_dict()` | нет |
| Новый автомат текстом | `vk.Machine(...)`, `vk.Project(...).add_system(...).save(папка)` | нет |
| Правка существующей модели | `d = vk.from_project(vk.load(vsp))` -> методы -> `d.save(новая_папка)` | нет |
| Сгенерировать код | `vk.generate(vsp, out_dir, coder="hcoder"/"classic", options=..., systems=...)` | нет |
| Проверить, что код компилируется | `vk.compile_check(out_dir)` (arm-none-eabi-gcc, `nm`) | нет |
| Формальная проверка | `vk.verify(vsp)` (Verificator) | нет |
| Всё сразу | `vk.full_check(vsp, out_dir)` — схема, API, Verificator, кодер, gcc | нет |
| Симуляция по событиям | `with vk.Simulator(vsp) as s: s.deduct("SE_RESET"); s.deduct("evX", 1)` | Validator на секунды |
| Откроет ли Designer | `vk.designer_check(vsp, save=True)` | Designer на ~8 с |
| Посмотреть диаграмму, не мешая человеку | `vk.designer_shot(vsp, "all.png", zoom=50)`; лист региона — `open_path=[0,0,0,0,0,k]`; нужен набор HiddenDesktop-Kit (скилл `hidden-desktop`) | Designer на СКРЫТОМ столе: окон нет |
| Раскладка диаграммы | считает `vskit.layout` при `save()`: правила — `knowledge/20_ПРИЁМЫ/20-04`; страницы и листы — `10-06` | нет |
| Второе мнение о модели | `vk.smapi.inventory(vsp)`, `vk.schema_check(vsp)` | нет |
| Новый проект автомата | скопировать `templates/new_machine`, править `model.py`, `python build.py --sim` | — |

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

## Семь правил, нарушение которых стоит часа

1. **Только над копией.** Оригинал модели читается; Coder, Verificator,
   Validator, API работают над копией в `env.job_dir()` — `vskit` делает
   это сам. Не запускать программы Visual State в папке проекта.
2. **Успех — по тексту вывода и файлам, не по коду возврата.** Verificator
   с неизвестной системой — код 0; кодер при совпадении имён проекта и
   системы — код 0 и битые файлы (30-02, 30-05).
3. **Имя системы ≠ имя проекта** (`LampProject` / `LampSys`).
4. **Ссылки проверять до Coder**: неизвестное событие Visual State молча
   выбрасывает (30-04). `Project.save()` проверяет описание и схему.
5. **Validator и Designer — только через Control Center**, с тайм-аутом;
   в копию кладётся `.vws` с `IncludeExcluded=FALSE`, иначе модальное окно
   (30-06). После работы `vk.windows()` должен быть пуст.
6. **State Machine API не сохранять «в другую папку»** — он перепишет
   оригинал .vsr; пути — UTF-8 (30-03).
7. **Никогда не выдавать непроверенное за проверенное** — ни в коде, ни в
   отчёте, ни в базе знаний.

## ОБЯЗАТЕЛЬНО: документация автомата

К каждому автомату — **читаемый русский Markdown об узлах и связях** (что
делает состояние, за что отвечает переход, зачем выбор и регион). Смысл
пишется в модели параметром `note=` (`describe`, `describe_region`), в
`.vsr` он не попадает; документ строит `vk.document(machine, path=...,
strict=True)` при каждой генерации кода — `strict` отказывает, пока есть
неописанная сущность. Модель без документа не готова. Подробно —
`knowledge/20_ПРИЁМЫ/20-06`. Других форматов (Documenter, HTML) не нужно.

## Диаграммы: раскладка, листы, снимки

* Координаты, маршруты, подписи, страницы и листы (offPage) считает
  `vskit.layout` — **править правила там**, а не руками в Designer. Правила
  и соглашения координат Designer — `knowledge/20_ПРИЁМЫ/20-04` и
  `knowledge/10_API/10-06`.
* **Смотреть диаграмму — только на скрытом столе** (`vk.designer_shot`):
  обычный `launchDesigner` выводит окно на экран человека и перехватывает
  его фокус. Скилл `hidden-desktop` (HiddenDesktop-Kit) объясняет, как
  это устроено и как смотреть снимки (вырезка фрагментов ≤ 2000 px).
* Масштаб Designer не работает, если диаграмма больше сетки страниц
  (`pagesHorz/pagesVert`): `knowledge/30_ГРАБЛИ/30-10`.

## Куда смотреть дальше

| Нужно | Читать |
|---|---|
| Карта базы, поиск по симптому | `knowledge/INDEX.md` |
| Как вести базу | `knowledge/00_ПРАВИЛА.md` |
| Как проектировать автоматы текстом | `knowledge/20_ПРИЁМЫ/20-02` |
| Сигнатура функции | docstring в `vskit/*.py` |
| Ключи кодеров | `vk.options_help("hcoder")`, `knowledge/10_API/10-02` |
| Документация IAR | `<vs_root>\doc\UserGuide.chm`, `doc\StateMachineAPI\html` |

Порядок: **`INDEX.md` -> файл базы -> docstring -> документация IAR ->
эксперимент на копии.** При расхождении базы с документацией — верить
базе.

## Состав библиотеки

| Модуль | Что в нём |
|---|---|
| `env` | установка, версия, лицензия, рабочие папки, GCC (через MCU-Kit) |
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
| `shot` | `designer_shot` — снимок Designer на скрытом столе (HiddenDesktop-Kit) |

## Обновление набора по ходу работы

Нашли поведение, расходящееся с ожиданием, и разобрались — **сразу**
запись в `knowledge/30_ГРАБЛИ` по шаблону `00_ПРАВИЛА.md`, строка в
`INDEX.md`, строка в `CHANGELOG.md`, затем `check_docs.py` и коммит.
Проверка после обновления Visual State — `tests\` (см. README).
