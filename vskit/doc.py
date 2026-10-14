# -*- coding: utf-8 -*-
"""Документация автомата по-русски: один Markdown-файл из самой модели.

Структура берётся из модели (регионы, состояния, переходы, действия при
входе и выходе, условия, словарь событий, действий и переменных), смысл —
из заметок (`note=`), которые пишутся рядом с описанием в Python и в
модель (.vsr) НЕ попадают: описание региона в <expl> показывалось бы на
самой диаграмме. Описание всего автомата — `Machine(expl=...)`.

    m.state("Idle", note="Ничего не нажато, ждём первую клавишу.")
    m.trans("Idle", "Busy", "evKey", note="Первая клавиша: начинаем сбор.")
    m.describe(choice_path, "Различает комбинацию и обычное нажатие.")
    m.describe_region("Root", "Power", "Питание: включение и выключение.")
    m.event("evKey", note="Нажата клавиша.")

    vk.document(machine, path="docs/automata.md", strict=True)

strict=True — ошибка, если есть регион, вершина, переход, событие, действие
или переменная без заметки (`vk.undocumented(machine)` вернёт список).
Правило набора — каждая сущность описана, документ перегенерируется при
каждой правке модели (knowledge/20_ПРИЁМЫ/20-06).

Состав документа: оглавление регионов; на каждый регион — начальное
состояние, таблица состояний (за что отвечает, действия при входе и
выходе), выборы с ветками, таблица переходов (из, в, когда, что делает,
смысл), внутренние реакции; в конце — словарь событий, действий,
функций-условий, переменных и констант.
"""
import re

_KINDS_EL = {"event": "События", "signal": "Сигналы", "action": "Действия",
             "const": "Константы", "intvar": "Внутренние переменные",
             "extvar": "Внешние переменные"}
_WORD = {"event": "событие", "signal": "сигнал", "action": "действие",
         "const": "константа", "intvar": "переменная",
         "extvar": "внешняя переменная"}
_CALL = re.compile(r"^\s*([A-Za-z_]\w*)\s*\((.*)\)\s*$", re.S)


def _cell(text):
    s = (text or "").strip()
    if not s:
        return "—"
    return s.replace("|", "\\|").replace("\n", "<br>")


def _code(items):
    items = [i for i in (items or []) if i]
    if not items:
        return "—"
    return "<br>".join("`%s`" % _cell(i).replace("`", "'") for i in items)


def _sections(machine):
    """[(заголовок, родитель-путь, регион)] в порядке чтения."""
    out = [("Верхний уровень", "", machine.top)]

    def walk(region, prefix):
        for v in region.vertices:
            path = prefix + v.name
            if not v.regions:
                continue
            for r in v.regions:
                if len(v.regions) > 1:
                    title = "Регион «%s» состояния «%s»" % (r.name, path)
                else:
                    title = "Подсостояния «%s»" % path
                out.append((title, path, r))
                walk(r, path + ".")
    walk(machine.top, "")
    return out


def _paths(region, prefix):
    return [(prefix + v.name, v) for v in region.vertices]


def _when(t):
    if t.special == "triggerless":
        base = "сразу, без события"
    elif t.special == "else":
        base = "иначе (ни одна другая ветка не подошла)"
    elif t.special == "termination":
        base = "при завершении"
    elif t.trigger:
        base = "событие `%s`" % t.trigger
    else:
        base = "сразу, без события"
    extra = []
    if t.guards:
        extra.append("условие `%s`" % " && ".join(t.guards))
    if t.when_in:
        extra.append("пока активно «%s»" % "», «".join(t.when_in))
    if t.not_in:
        extra.append("пока не активно «%s»" % "», «".join(t.not_in))
    return base + ("; " + "; ".join(extra) if extra else "")


def _trans_rows(machine, region, prefix):
    rows = []
    for path, v in _paths(region, prefix):
        for t in v.trans:
            rows.append((path, v, t))
    return rows


def _each_transition(machine):
    for path, v, _r in machine._walk():
        for t in v.trans:
            yield path, v, t


def undocumented(machine):
    """Список сущностей без описания (<expl>) — для строгого режима и
    проверки в тестах."""
    miss = []
    for title, parent, r in _sections(machine):
        if parent and not (r.note or "").strip():
            miss.append("регион «%s»" % title)
    for path, v, _r in machine._walk():
        if v.kind == "initialState" or v.kind in ("final", "finalState"):
            continue
        if not (v.note or "").strip():
            miss.append("%s «%s»" % ("состояние" if v.kind == "state"
                                    else "вершина", path))
    for path, v, t in _each_transition(machine):
        if v.kind == "initialState":
            continue
        if not (t.note or "").strip():
            miss.append("переход «%s» → «%s» (%s)" % (
                path, t.target or "внутренний", _when(t)))
    for e in machine.els:
        if not (e.note or "").strip():
            miss.append("%s «%s»" % (_WORD.get(e.kind, e.kind), e.name))
    return miss


def machine_markdown(machine, title=None):
    L = []
    a = L.append
    a("# %s" % (title or machine.name))
    a("")
    a((machine.expl or "").strip() or "_Описание автомата не задано._")
    a("")
    a("> Документ построен автоматически из модели и заметок `note=` в её "
      "описании на Python; править нужно их и перегенерировать документ, а "
      "не этот файл.")
    a("")
    secs = _sections(machine)
    a("## Оглавление")
    a("")
    for i, (title_, parent, r) in enumerate(secs, 1):
        a("%d. %s" % (i, title_))
    a("")
    a("Словарь событий, действий и переменных — в конце документа.")
    a("")
    for title_, parent, r in secs:
        prefix = parent + "." if parent else ""
        a("## %s" % title_)
        a("")
        if (r.note or "").strip():
            a(r.note.strip())
            a("")
        verts = _paths(r, prefix)
        init = None
        for path, v in verts:
            if v.kind == "initialState":
                for t in v.trans:
                    init = t.target
        if init:
            a("**Начальное состояние:** `%s`." % init)
            a("")
        states = [(p, v) for p, v in verts if v.kind == "state"]
        if states:
            a("### Состояния")
            a("")
            a("| Состояние | За что отвечает | При входе | При выходе |")
            a("|---|---|---|---|")
            for p, v in states:
                name = "`%s`" % v.name
                if v.regions:
                    name += " (составное)"
                a("| %s | %s | %s | %s |" % (name, _cell(v.note),
                                             _code(v.entry), _code(v.exit)))
            a("")
        choices = [(p, v) for p, v in verts
                   if v.kind not in ("state", "initialState")]
        if choices:
            a("### Выборы (ветвление)")
            a("")
            a("| Выбор | Зачем | Ветка | Куда | Что делает |")
            a("|---|---|---|---|---|")
            for p, v in choices:
                first = True
                for t in v.trans:
                    a("| %s | %s | %s | `%s` | %s |" % (
                        "`%s`" % v.name if first else "",
                        _cell(v.note) if first else "", _cell(_when(t)),
                        t.target or "—", _code(t.do)))
                    first = False
            a("")
        ext = [(p, v, t) for p, v, t in _trans_rows(machine, r, prefix)
               if v.kind == "state" and t.kind == "external"]
        if ext:
            a("### Переходы (связи между состояниями)")
            a("")
            a("| Из | В | Когда | Что делает | Смысл |")
            a("|---|---|---|---|---|")
            for p, v, t in ext:
                a("| `%s` | `%s` | %s | %s | %s |" % (
                    v.name, t.target or "—", _cell(_when(t)), _code(t.do),
                    _cell(t.note)))
            a("")
        intr = [(p, v, t) for p, v, t in _trans_rows(machine, r, prefix)
                if t.kind == "internal"]
        if intr:
            a("### Внутренние реакции (без выхода из состояния)")
            a("")
            a("| Состояние | Когда | Что делает | Смысл |")
            a("|---|---|---|---|")
            for p, v, t in intr:
                a("| `%s` | %s | %s | %s |" % (v.name, _cell(_when(t)),
                                              _code(t.do), _cell(t.note)))
            a("")
    a("## Словарь")
    a("")
    for kind, head in _KINDS_EL.items():
        els = [e for e in machine.els if e.kind == kind]
        if kind == "action":
            funcs = [e for e in els if e.type and e.type != "VS_VOID"]
            els = [e for e in els if e not in funcs]
        else:
            funcs = []
        for group, items in ((head, els),
                             ("Функции-условия (возвращают значение)",
                              funcs)):
            if not items:
                continue
            a("### %s" % group)
            a("")
            a("| Имя | Параметры | Значение |")
            a("|---|---|---|")
            for e in sorted(items, key=lambda x: x.name):
                if kind in ("const", "intvar", "extvar"):
                    par = "%s = %s" % (e.type, e.value)
                else:
                    par = ", ".join("%s: %s" % (n, t) for n, t in e.args)
                    if e.type and e.type != "VS_VOID":
                        par += " → %s" % e.type
                a("| `%s` | %s | %s |" % (e.name, _cell(par), _cell(e.note)))
            a("")
    return "\n".join(L) + "\n"


def document(machine, path=None, title=None, strict=False):
    """Построить документ автомата; path — записать в файл (UTF-8, LF).
    strict — отказаться, если есть сущности без описания."""
    if hasattr(machine, "systems"):
        machine = machine.systems[0][2][0]
    miss = undocumented(machine)
    if strict and miss:
        raise ValueError("нет описаний (%d):\n  %s"
                         % (len(miss), "\n  ".join(miss)))
    text = machine_markdown(machine, title)
    if path:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    return text
