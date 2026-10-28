# VisualState-Skill

Инструмент для работы с конечными автоматами IAR Visual State скриптами:
библиотека на Python, база проверенного знания и правила её ведения.
Подключается к агенту как скилл `visualstate`. Общие правила, проверки и
хук — соседний скилл skill-skill; компилятор для проверки кода берётся из
соседнего скилла mcu, а снимки диаграмм Designer делаются на скрытом
рабочем столе через соседний скилл hidden-desktop.

```
visualstate/
├── SKILL.md               точка входа для ИИ
├── vskit/                 библиотека Python (layout — раскладка диаграмм, shot — снимки Designer)
├── knowledge/             база знаний
│   ├── 00_ПРАВИЛА.md      особенности набора; общие правила — skill-skill
│   ├── INDEX.md           карта базы и поиск по симптому
│   ├── 10_API/  20_ПРИЁМЫ/  30_ГРАБЛИ/  40_СРЕДА/
├── templates/new_machine/ автомат текстом: model.py + build.py
├── tests/                 сквозные проверки на примерах поставки
├── tools/check_docs.py    обёртка общей проверки skill-skill
├── tools/kit_local.py     своё в проверке: имена из моделей проекта
└── CHANGELOG.md
```

---

## Главное

Модель Visual State — **открытый XML** (`.vsp` — проект, `.vsr` —
автомат), его схема зашита в программы поставки. Поэтому автомат можно
читать, создавать и править текстом, без мыши, и проверять всеми
штатными средствами:

| Задача | Как | Окна |
|---|---|---|
| Прочитать модель (форматы 1–11) | `vk.load(vsp)` | нет |
| Создать автомат из описания на Python | `vk.Machine`, `vk.Project(...).save()` | нет |
| Править существующую модель | `vk.from_project(vk.load(vsp))` -> `save()` | нет |
| Код C/C++ (HCoder, Coder) | `vk.generate(vsp, out_dir, ...)` | нет |
| Проверить сборку arm-none-eabi-gcc | `vk.compile_check(out_dir)` | нет |
| Формальная проверка (Verificator) | `vk.verify(vsp)` | нет |
| Схема XML и State Machine API — второе мнение | `vk.schema_check`, `vk.smapi.inventory` | нет |
| Всё сразу с отчётом | `vk.full_check(vsp, out_dir)` | нет |
| Симуляция в Validator по событиям | `vk.Simulator(vsp).deduct(...)` | Validator на секунды |
| Открыть и пересохранить в Designer | `vk.designer_check(vsp, save=True)` | Designer на ~8 с |
| Снимок диаграммы | `vk.designer_shot(vsp, png)` | Designer на скрытом столе |

## Установка

```bash
cd "<папка скиллов агента>"
git clone https://github.com/RungeKut/VisualState-Skill.git visualstate
```

Рядом нужны skill-skill (общие правила, проверки, хук), hidden-desktop
(снимки Designer) и по желанию mcu (GCC). Настройка клона — skill-skill,
`knowledge/40_СРЕДА/40-01`; зависимости набора (Visual State, Python
64-bit, lxml) — `knowledge/40_СРЕДА/40-01` здесь.

Нужны: IAR Visual State 9.1 с лицензией (проверено на 9.1.1.3863),
Python 3.11+ 64-bit, lxml (`python -m pip install --user lxml`),
arm-none-eabi-gcc (через соседний скилл mcu, `VSKIT_GCC` или PATH).

## Быстрый старт

```python
import sys
sys.path.insert(0, r"<папка скиллов агента>\visualstate")
import vskit as vk
vk.utf8_console()

p = vk.load(r"D:\проект\Model\Project.vsp")       # оригинал только читается
print(p)                                          # дерево, переходы текстом
rep = vk.full_check(p.file, r"D:\проект\vs_gen")  # схема, API, Verificator, HCoder, gcc
print(rep)
with vk.Simulator(p.file) as s:
    s.deduct("SE_RESET")
    print(s.deduct("evSomething"))                # [('action', 'DoIt', None), ...]
```

Новый автомат: скопировать `templates/new_machine`, вписать корень набора
в `KIT` в `build.py`, описать автомат в `model.py`, запустить
`python build.py --sim`.

## Как это устроено

* **Модель** — XML. `vskit.model` разбирает все форматы, которые читает
  9.1; `vskit.design` пишет format 11 (как Designer 9.1): ссылки по GUID,
  порядок элементов по схеме, раскладка диаграмм (`vskit.layout`).
* **Кодеры и Verificator** — консольные программы; запускаются над копией
  модели в рабочей папке, результат копируется наружу. Их коды возврата
  об успехе не говорят — решает текст вывода и файлы.
* **Validator и Designer** — оконные; управляются через `ControlCenter.exe`
  (JSON-RPC по TCP): запрос — строка JSON с переводом строки, ответ
  `deductEvent` — список вызванных действий и присваиваний.
* **State Machine API** (`StateMachineAPI64.dll`, ctypes) и **схема XML**
  (вырезается из HCoder.exe, проверка lxml) — независимые проверки
  записанного.

## Что проверено, а что нет

Проверено 12.10.2026 на IAR Visual State 9.1.1.3863, Windows 10, Python
3.13, arm-none-eabi-gcc 10.3.1: всё в таблице «Главное». `tests/
test_model.py`, `test_coder.py`, `test_design.py`, `test_sim.py`
проходят целиком; `test_project.py` прошёл на копии рабочего проекта.

**Не проверено:** другие версии Visual State; поведение без лицензии и с
сетевой лицензией; подмашины, fork/join, точки входа/выхода, сигналы,
группы событий и элементы проекта в `vskit.design`; создание модели
через State Machine API; методы Control Center `createProjectAndStateMachine`,
`addStateMachine`, `saveValidator`; Documenter и ProjectConverter;
сборка в прошивку и работа кода на железе.

## Проверка после обновления Visual State

```
python tests\test_model.py      разбор всех примеров против API, схема, format 6 -> 11
python tests\test_coder.py      HCoder и Coder, ключи, gcc, ошибки, Verificator
python tests\test_design.py     автомат текстом -> всё; Validator и Designer (--no-gui без окон)
python tests\test_sim.py        симуляция примеров через Control Center (окна Validator на экране)
python tests\test_layout.py     раскладка диаграмм: пересечения, подписи, листы, страницы, сплайны (без окон)
python tests\test_doc.py        документация автомата: строгий режим, Markdown, заметки не в модели
python tests\test_shot.py       снимки Designer на скрытом столе (нужен скилл hidden-desktop; окон у человека нет)
python tests\test_project.py <проект.vsp>   любой проект целиком (только читается)
python tools\check_docs.py      целостность базы, стоп-слова, git (общая проверка skill-skill)
```

## Работа с репозиторием

По общим правилам skill-skill (`knowledge/40_СРЕДА/40-02`): в начале —
`git pull --rebase`; после каждой правки — `git diff`,
`python tools/check_docs.py --project "<папка проекта>"`, коммит,
`git push`. Без права записи — pull request из своего форка. **В набор не
попадает ничего о проектируемом изделии** — ни в файлы, ни в текст
коммита, включая имена из его модели и снимки его диаграмм; особенности —
`knowledge/40_СРЕДА/40-02`.

---

## Лицензия

MIT — см. [LICENSE](LICENSE).

IAR Systems, IAR Visual State и visualSTATE — торговые марки IAR Systems
AB. Проект с IAR не связан и не одобрен ею: это независимый инструмент,
который управляет легально установленной копией Visual State через её
штатные программы, документированный API и формат файлов. Файлы IAR
(схемы XML, примеры) в набор не входят.
