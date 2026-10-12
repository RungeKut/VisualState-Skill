# VisualState-Kit

Инструмент для работы с конечными автоматами IAR Visual State скриптами:
библиотека на Python, база проверенного знания и правила её ведения.
Подключается к Claude Code как скилл `/visualstate` и к Kimi Code как
`/skill:visualstate`. Устроен так же, как соседние наборы Allegro-Kit и
MCU-Kit; компилятор для проверки кода берёт из MCU-Kit.

```
VisualState-Kit/
├── skill/SKILL.md         точка входа для ИИ (подключён как скилл)
├── vskit/                 библиотека Python
├── knowledge/             база знаний
│   ├── 00_ПРАВИЛА.md      правила ведения базы
│   ├── INDEX.md           карта базы и поиск по симптому
│   ├── 10_API/  20_ПРИЁМЫ/  30_ГРАБЛИ/  40_СРЕДА/
├── templates/new_machine/ автомат текстом: model.py + build.py
├── tests/                 сквозные проверки на примерах поставки
├── tools/setup.ps1        установка на машине
├── tools/check_docs.py    проверка целостности базы и стоп-слов
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

## Установка

```powershell
cd VisualState-Kit
powershell -ExecutionPolicy Bypass -File tools\setup.ps1
```

Либо двойной щелчок по `Install-skill.bat`. Создаются junction'ы
`~\.claude\skills\visualstate` и `~\.kimi-code\skills\visualstate` ->
`<репозиторий>\skill`, переменная `VSKIT_HOME`, хук на текст коммита,
локальный стоп-лист; ставится lxml; ищутся Visual State и GCC. Прав
администратора не требует. После установки — перезапустить агента.

Нужны: IAR Visual State 9.1 с лицензией (проверено на 9.1.1.3863),
Python 3.11+ 64-bit, lxml, arm-none-eabi-gcc (через MCU-Kit, `VSKIT_GCC`
или PATH).

## Быстрый старт

```python
import os, sys
sys.path.insert(0, os.environ["VSKIT_HOME"])
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

Новый автомат: скопировать `templates/new_machine`, описать автомат в
`model.py`, запустить `python build.py --sim`.

## Как это устроено

* **Модель** — XML. `vskit.model` разбирает все форматы, которые читает
  9.1; `vskit.design` пишет format 11 (как Designer 9.1): ссылки по GUID,
  порядок элементов по схеме, грубая раскладка сеткой.
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
python tests\test_sim.py        симуляция примеров через Control Center
python tests\test_project.py <проект.vsp>   любой проект целиком (только читается)
python tools\check_docs.py      целостность базы знаний
```

## Работа с репозиторием

Репозиторий пока локальный. **В набор не попадает ничего о проектируемом
изделии** — ни в файлы, ни в текст коммита, включая имена из его модели.
Приметы изделия — в `tools/stoplist.txt` (локальный, в `.gitignore`),
`check_docs.py --project "<папка>"` добавляет к ним имена из моделей
проекта. Подробности — `knowledge/40_СРЕДА/40-02`.

---

## Лицензия

MIT — см. [LICENSE](LICENSE).

IAR Systems, IAR Visual State и visualSTATE — торговые марки IAR Systems
AB. Проект с IAR не связан и не одобрен ею: это независимый инструмент,
который управляет легально установленной копией Visual State через её
штатные программы, документированный API и формат файлов. Файлы IAR
(схемы XML, примеры) в набор не входят.
