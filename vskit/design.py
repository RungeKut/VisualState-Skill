# -*- coding: utf-8 -*-
"""Модель Visual State из описания на Python — запись .vsp/.vsr/.vnw.

Пишется формат 11 — тот, что сохраняет Designer 9.1. Ссылки внутри
.vsr — по GUID, вызовы действий — по имени. Координаты, маршруты и
подписи переходов считает vskit.layout (слои, порты, боковые «шины»,
сплайны для параллельных рёбер у выборов, страницы и отдельные листы для
крупных регионов: knowledge/20_ПРИЁМЫ/20-04).

    import vskit as vk
    m = vk.Machine("Lamp")
    m.event("evToggle")
    m.event("evLevel", ("lvl", "VS_UINT8"))
    m.action("LampOn")
    m.action("LampOff")
    m.action("LampSet", ("lvl", "VS_UINT8"))
    m.var("level", "VS_UINT8", 0, lo=0, hi=3)
    m.state("Off", entry="LampOff()")
    m.state("On", entry="LampOn()")
    m.state("On.Dim")
    m.state("On.Bright")
    m.initial("Off")
    m.initial("On.Dim")
    m.trans("Off", "On", "evToggle")
    m.trans("On", "Off", "evToggle")
    m.trans("On.Dim", "On.Bright", "evLevel(lvl)", guard="lvl > 1",
            do=["level = lvl", "LampSet(level)"])
    p = vk.Project("LampProject")
    p.add_system("Lamp_sys", m)
    p.save(r"C:\\work\\lamp")         # Lamp.vsr, LampProject.vsp, .vnw

Состояния задаются путём через точку без имён регионов: 'On.Dim'.
Второй (ортогональный) регион — аргумент region=: m.state("On.Led",
region="Leds"). Ошибки ссылок (нет события, действия, состояния)
ловятся при сохранении, до Coder: Coder молча теряет триггер с неизвестным
именем и ругается уже на «Transition without any trigger»
(knowledge/30_ГРАБЛИ/30-04).

Правка существующей модели — from_project(model.load(vsp)): автоматы
переносятся в описание с сохранением GUID, дальше — те же методы и
save() в НОВУЮ папку. Раскладка на диаграмме при этом строится заново
(vskit.layout).
"""
import os
import re
import uuid
from xml.sax.saxutils import escape, quoteattr

NS = "http://www.iar.com/visualSTATE/2011/Modelfile"
FORMAT = 11
TYPES = ("VS_VOID", "VS_BOOL", "VS_CHAR", "VS_UCHAR", "VS_SCHAR", "VS_INT",
         "VS_UINT", "VS_INT8", "VS_UINT8", "VS_INT16", "VS_UINT16",
         "VS_INT32", "VS_UINT32", "VS_FLOAT", "VS_DOUBLE", "VS_VOIDPTR")
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_CALL = re.compile(r"^\s*([A-Za-z_]\w*)\s*\((.*)\)\s*;?\s*$", re.S)

STATE_W, STATE_H, LABEL_H = 688, 265, 42
PSEUDO = 53
MARGIN = 53
PAGE_W, PAGE_H = 2000, 2850


def new_guid():
    return str(uuid.uuid4()).upper()


def _check_ident(name, what):
    if not _IDENT.match(name or ""):
        raise ValueError("%s %r: нужен идентификатор C" % (what, name))


def _check_type(t, what):
    if t not in TYPES:
        raise ValueError("%s: тип %r не из %s" % (what, t, ", ".join(TYPES)))


def _split_args(s):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
            continue
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


class _El:
    def __init__(self, kind, name, type="", args=(), value=None, expl="",
                 lo=None, hi=None, guid=None):
        self.kind = kind
        self.name = name
        self.type = type
        self.args = list(args)
        self.value = value
        self.expl = expl
        self.lo = lo
        self.hi = hi
        self.guid = guid or new_guid()


class _V:
    def __init__(self, kind, name, guid=None):
        self.kind = kind
        self.name = name
        self.guid = guid or new_guid()
        self.regions = []
        self.entry = []
        self.exit = []
        self.trans = []
        self.expl = ""
        self.w = self.h = 0
        self.x = self.y = 0


class _R:
    def __init__(self, name, guid=None):
        self.name = name
        self.guid = guid or new_guid()
        self.vertices = []
        self.w = self.h = 0


class _T:
    def __init__(self, kind, source, target, trigger, guards, do, when_in,
                 not_in, special, expl, guid=None):
        self.kind = kind
        self.source = source
        self.target = target
        self.trigger = trigger
        self.guards = guards
        self.do = do
        self.when_in = when_in
        self.not_in = not_in
        self.special = special
        self.expl = expl
        self.guid = guid or new_guid()


def _list(x):
    if x is None:
        return []
    if isinstance(x, str):
        return [x]
    return list(x)


class Machine:
    """Автомат верхнего уровня (один файл .vsr)."""

    def __init__(self, name, file=None, expl="", guid=None):
        _check_ident(name, "автомат")
        self.name = name
        self.file = file or name + ".vsr"
        self.expl = expl
        self.guid = guid or new_guid()
        self.top = _R("Region1")
        self.els = []
        self._n = {"initialState": 0, "final": 0, "shallowHistoryState": 0,
                   "deepHistoryState": 0, "choiceState": 0}

    def _add_el(self, kind, name, **kw):
        _check_ident(name, kind)
        if any(e.name == name for e in self.els):
            raise ValueError("имя %r уже занято в %s" % (name, self.name))
        e = _El(kind, name, **kw)
        self.els.append(e)
        return e

    def event(self, name, *args, expl="", guid=None):
        """Событие. args — пары (имя, тип): ("lvl", "VS_UINT8")."""
        for a in args:
            _check_type(a[1], "аргумент события %s" % name)
        return self._add_el("event", name, args=args, expl=expl, guid=guid)

    def signal(self, name, *args, expl="", guid=None):
        """Сигнал (внутреннее событие системы)."""
        return self._add_el("signal", name, args=args, expl=expl, guid=guid)

    def action(self, name, *args, returns="VS_VOID", expl="", guid=None):
        """Функция действия (её пишет человек в C)."""
        _check_type(returns, "действие %s" % name)
        for a in args:
            _check_type(a[1], "аргумент действия %s" % name)
        return self._add_el("action", name, type=returns, args=args,
                            expl=expl, guid=guid)

    def const(self, name, type, value, expl="", guid=None):
        _check_type(type, "константа %s" % name)
        return self._add_el("const", name, type=type, value=value,
                            expl=expl, guid=guid)

    def var(self, name, type, init=0, lo=None, hi=None, expl="", guid=None):
        """Внутренняя переменная модели."""
        _check_type(type, "переменная %s" % name)
        return self._add_el("intvar", name, type=type, value=init, lo=lo,
                            hi=hi, expl=expl, guid=guid)

    def extvar(self, name, type, init=0, lo=None, hi=None, expl="",
               guid=None):
        """Внешняя переменная (живёт в коде пользователя)."""
        _check_type(type, "переменная %s" % name)
        return self._add_el("extvar", name, type=type, value=init, lo=lo,
                            hi=hi, expl=expl, guid=guid)

    def _region_of(self, parent_path, region):
        if not parent_path:
            if region and region != self.top.name:
                raise ValueError("у автомата верхнего уровня один регион "
                                 "%r" % self.top.name)
            return self.top
        p = self._vertex(parent_path)
        if p.kind != "state":
            raise ValueError("%s — не состояние" % parent_path)
        name = region or (p.regions[0].name if p.regions else "Region1")
        for r in p.regions:
            if r.name == name:
                return r
        r = _R(name)
        p.regions.append(r)
        return r

    def _walk(self, region=None, prefix=""):
        region = region or self.top
        for v in region.vertices:
            path = prefix + v.name
            yield path, v, region
            for r in v.regions:
                for x in self._walk(r, path + "."):
                    yield x

    def _vertex(self, path):
        for p, v, _r in self._walk():
            if p == path:
                return v
        raise KeyError("нет состояния %r в автомате %s" % (path, self.name))

    def _add_vertex(self, kind, path, region=None, guid=None):
        parent, _, name = path.rpartition(".")
        _check_ident(name, "состояние")
        r = self._region_of(parent, region)
        if any(v.name == name for v in r.vertices):
            raise ValueError("состояние %r уже есть" % path)
        v = _V(kind, name, guid)
        r.vertices.append(v)
        return v

    def state(self, path, entry=None, exit=None, region=None, expl="",
              guid=None):
        """Состояние. path — 'A' или 'A.B' (B внутри A). entry/exit —
        строка или список: 'Act(1)', 'x = x + 1'."""
        v = self._add_vertex("state", path, region, guid)
        v.entry = _list(entry)
        v.exit = _list(exit)
        v.expl = expl
        return path

    def _pseudo(self, kind, prefix, parent, region, guid):
        self._n[kind] += 1
        name = "%s%d" % (prefix, self._n[kind])
        path = (parent + "." if parent else "") + name
        self._add_vertex(kind, path, region, guid)
        return path

    def initial(self, target, region=None, do=None, guid=None):
        """Начальное состояние региона, в котором лежит target."""
        parent = target.rpartition(".")[0]
        if region is None and parent:
            for r in self._vertex(parent).regions:
                if any(v.name == target.rpartition(".")[2]
                       for v in r.vertices):
                    region = r.name
        p = self._pseudo("initialState", "initial", parent, region, guid)
        self.trans(p, target, None, do=do)
        return p

    def final(self, parent="", region=None, guid=None):
        """Конечное состояние в регионе состояния parent."""
        self._n["final"] += 1
        path = (parent + "." if parent else "") + "final%d" % self._n["final"]
        self._add_vertex("final", path, region, guid)
        return path

    def history(self, parent, deep=False, region=None, default=None,
                guid=None):
        """Историческое псевдосостояние в регионе состояния parent."""
        kind = "deepHistoryState" if deep else "shallowHistoryState"
        p = self._pseudo(kind, "deepHistory" if deep else "history", parent,
                         region, guid)
        if default:
            self.trans(p, default, None)
        return p

    def choice(self, parent="", region=None, guid=None):
        """Псевдосостояние выбора; выходы — trans(..., guard=...) и
        trans(..., otherwise=True)."""
        return self._pseudo("choiceState", "choice", parent, region, guid)

    def trans(self, source, target, trigger, guard=None, do=None,
              when_in=None, not_in=None, otherwise=False, triggerless=False,
              expl="", guid=None):
        """Внешний переход. trigger — 'evX' или 'evX(a, b)' (имена
        аргументов события); None — без события (из начального,
        исторического, выбора; из состояния — только triggerless=True).
        guard — строка или список (И). otherwise=True — ветка else из
        выбора."""
        src = self._vertex(source)
        if src.kind == "choiceState" and not otherwise and not trigger:
            triggerless = True
        special = "else" if otherwise else (
            "triggerless" if triggerless else "")
        t = _T("external", source, target, trigger, _list(guard), _list(do),
               _list(when_in), _list(not_in), special, expl, guid)
        src.trans.append(t)
        return t

    def internal(self, state, trigger, guard=None, do=None, when_in=None,
                 not_in=None, expl="", guid=None):
        """Внутренний переход: реакция без выхода из состояния."""
        t = _T("internal", state, None, trigger, _list(guard), _list(do),
               _list(when_in), _list(not_in), "", expl, guid)
        self._vertex(state).trans.append(t)
        return t

    def check(self):
        """Ссылки на события, действия и состояния — до записи.
        Возвращает список ошибок (пустой — всё сходится)."""
        errs = []
        names = {e.name: e for e in self.els}
        paths = {p for p, _v, _r in self._walk()}
        for path, v, r in self._walk():
            if v.kind == "state" and v.regions:
                for reg in v.regions:
                    has_init = any(x.kind in ("initialState",
                                              "shallowHistoryState",
                                              "deepHistoryState")
                                   for x in reg.vertices)
                    if not has_init and any(x.kind == "state"
                                            for x in reg.vertices):
                        errs.append("%s/%s: нет начального состояния"
                                    % (path, reg.name))
            for a in v.entry + v.exit:
                errs += self._check_action(a, names, path)
            for t in v.trans:
                where = "%s -> %s" % (t.source, t.target or "(внутр.)")
                if t.target is not None and t.target not in paths:
                    errs.append("%s: нет состояния %r" % (where, t.target))
                if t.trigger:
                    m = _CALL.match(t.trigger)
                    ev = m.group(1) if m else t.trigger.strip()
                    e = names.get(ev)
                    if e is None or e.kind not in ("event", "signal"):
                        errs.append("%s: нет события %r" % (where, ev))
                    elif m and len(_split_args(m.group(2))) != len(e.args):
                        errs.append("%s: у события %s %d аргумент(ов)"
                                    % (where, ev, len(e.args)))
                elif v.kind == "state" and not t.special:
                    errs.append("%s: переход из состояния без события"
                                % where)
                for s in t.when_in + t.not_in:
                    if s not in paths:
                        errs.append("%s: нет состояния %r в условии"
                                    % (where, s))
                for a in t.do:
                    errs += self._check_action(a, names, where)
        return errs

    def _check_action(self, a, names, where):
        m = _CALL.match(a)
        if m:
            e = names.get(m.group(1))
            if e is None or e.kind != "action":
                return ["%s: нет действия %r" % (where, m.group(1))]
            n = len(_split_args(m.group(2)))
            if n != len(e.args):
                return ["%s: %s ждёт %d аргумент(ов), дано %d"
                        % (where, e.name, len(e.args), n)]
            return []
        if "=" in a or "++" in a or "--" in a:
            return []
        return ["%s: %r — не вызов действия и не присваивание" % (where, a)]

    def xml(self):
        """Текст .vsr (format 11)."""
        errs = self.check()
        if errs:
            raise ValueError("автомат %s:\n  " % self.name + "\n  ".join(errs))
        from . import layout as _layout
        _layout.layout(self)
        guids = {p: v.guid for p, v, _r in self._walk()}
        geo = {p: v for p, v, _r in self._walk()}
        names = {e.name: e for e in self.els}
        o = []
        a = o.append
        a('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>')
        a('<modelFile excluded="false" format="%d" guid="%s" name="%s" '
          'xmlns="%s">' % (FORMAT, self.guid, self.name, NS))
        a("")
        a("  <expl>%s</expl>" % escape(self.expl))
        a("")
        a("  <alias></alias>")
        a("")
        a('  <position bottom="635" left="0" right="741" top="0"/>')
        a("")
        a('  <stateProperties labelHeight="42" wrapText="true">')
        a('    <properties value="65537"/>')
        a("  </stateProperties>")
        a("")
        a("  <elements>")
        self._folders(a, names)
        a("  </elements>")
        a("")
        a("  <regions>")
        a('    <regionBlock guid="%s"/>' % self.top.guid)
        a("  </regions>")
        a("")
        a("  <regionBlocks>")
        self._region_blocks(a, self.top, True)
        a("  </regionBlocks>")
        a("")
        a("  <vertexBlocks>")
        for p, v, _r in self._walk():
            self._vertex_xml(a, p, v, guids, geo, names)
        a("  </vertexBlocks>")
        a("")
        a("</modelFile>")
        a("")
        return "\n".join(o)

    def _folders(self, a, names):
        spec = (("actionsFolder", "action"), ("constantsFolder", "const"),
                ("eventsFolder", "event"), ("eventGroupsFolder", None),
                ("externVariablesFolder", "extvar"),
                ("internVariablesFolder", "intvar"),
                ("signalsFolder", "signal"))
        tags = {"action": "actionFunction", "const": "constant",
                "event": "event", "extvar": "externVariable",
                "intvar": "internVariable", "signal": "signal"}
        for folder, kind in spec:
            items = sorted((e for e in self.els if e.kind == kind),
                           key=lambda e: e.name)
            fg = new_guid()
            if not items:
                a('    <%s guid="%s" name="root"/>' % (folder, fg))
                continue
            a('    <%s guid="%s" name="root">' % (folder, fg))
            for e in items:
                tag = tags[kind]
                attrs = 'definition="%s" guid="%s" name="%s"' % (
                    "false" if kind == "action" else "true", e.guid, e.name)
                if kind == "action":
                    attrs += ' returnType="%s"' % e.type
                elif e.type:
                    attrs += ' type="%s"' % e.type
                a("      <%s %s>" % (tag, attrs))
                a("        <expl>%s</expl>" % escape(e.expl or ""))
                if e.args:
                    a("        <arguments>")
                    for n, t in e.args:
                        a('          <argument name="%s" type="%s"/>' % (n, t))
                    a("        </arguments>")
                if kind in ("const", "intvar", "extvar"):
                    a("        <value>%s</value>" % escape(str(e.value)))
                if kind in ("intvar", "extvar"):
                    if e.lo is not None:
                        a("        <lowerDomain>%s</lowerDomain>" % e.lo)
                    if e.hi is not None:
                        a("        <upperDomain>%s</upperDomain>" % e.hi)
                a("      </%s>" % tag)
            a("    </%s>" % folder)

    def _region_blocks(self, a, r, top, column=0):
        off = not top and getattr(r, "off_page", False)
        a('    <region excluded="false" guid="%s" name="%s" offPage="%s">'
          % (r.guid, r.name, "true" if (top or off) else "false"))
        a("      <expl></expl>")
        a('      <placement column="%d" row="0"/>' % column)
        if off:
            from .layout import PH_W, PH_H
            a('      <size height="%d" width="%d"/>' % (PH_H, PH_W))
        else:
            a('      <size height="%d" width="%d"/>' % (r.h, r.w))
        a('      <view colorNumber="7" pagesHorz="%d" pagesVert="%d"/>'
          % (max(2, -(-(r.w + MARGIN) // PAGE_W)),
             max(2, -(-(r.h + MARGIN) // PAGE_H))))
        a('      <diagramInformation textDisplayNote="preserve" '
          'textDisplayState="preserve" textDisplayTransition="preserve"/>')
        if r.vertices:
            a("      <vertices>")
            for v in r.vertices:
                a('        <vertexBlock guid="%s"/>' % v.guid)
            a("      </vertices>")
        a("    </region>")
        for v in r.vertices:
            for i, sub in enumerate(v.regions):
                self._region_blocks(a, sub, False, i)

    def _pos(self, v):
        return 'bottom="%d" left="%d" right="%d" top="%d"' % (
            v.y + v.h, v.x, v.x + v.w, v.y)

    def _actions(self, a, items, names, ind):
        if not items:
            return
        a(ind + "<actionSide>")
        for s in items:
            m = _CALL.match(s)
            if m and names.get(m.group(1)) is not None and \
                    names[m.group(1)].kind == "action":
                args = _split_args(m.group(2))
                if not args:
                    a(ind + '  <actionCall actionFunction="%s"/>' % m.group(1))
                else:
                    a(ind + '  <actionCall actionFunction="%s">' % m.group(1))
                    a(ind + "    <actionCallArguments>")
                    for x in args:
                        a(ind + "      <actionCallArgument token=%s/>"
                          % quoteattr(x))
                    a(ind + "    </actionCallArguments>")
                    a(ind + "  </actionCall>")
            else:
                a(ind + "  <assignment>%s</assignment>" % escape(s.strip()))
        a(ind + "</actionSide>")

    def _condition(self, a, t, guids, names, ind):
        parts = []
        if t.trigger:
            m = _CALL.match(t.trigger)
            ev = m.group(1) if m else t.trigger.strip()
            args = _split_args(m.group(2)) if m else []
            if args:
                parts.append(ind + '  <trigger guid="%s">' % names[ev].guid)
                for x in args:
                    parts.append(ind + "    <argument>%s</argument>"
                                 % escape(x))
                parts.append(ind + "  </trigger>")
            else:
                parts.append(ind + '  <trigger guid="%s"/>' % names[ev].guid)
        elif t.special == "triggerless":
            parts.append(ind + "  <trigger/>")
        if t.guards:
            parts.append(ind + "  <guards>")
            for g in t.guards:
                parts.append(ind + "    <guard>%s</guard>" % escape(g))
            parts.append(ind + "  </guards>")
        for tag, inner, items in (
                ("positiveSynchronizations", "positiveState", t.when_in),
                ("negativeSynchronizations", "negativeState", t.not_in)):
            if items:
                parts.append(ind + "  <%s>" % tag)
                for s in items:
                    parts.append(ind + "    <%s>%s</%s>"
                                 % (inner, guids[s], inner))
                parts.append(ind + "  </%s>" % tag)
        if parts:
            a(ind + "<conditionSide>")
            for p in parts:
                a(p)
            a(ind + "</conditionSide>")

    def _reaction(self, a, tag, items, names):
        if not items:
            return
        a("      <%ss>" % tag)
        a('        <%s guid="%s">' % (tag, new_guid()))
        a("          <expl></expl>")
        a("          <alias></alias>")
        self._actions(a, items, names, "          ")
        a("        </%s>" % tag)
        a("      </%ss>" % tag)

    def _vertex_xml(self, a, path, v, guids, geo, names):
        """Порядок дочерних элементов — как в схеме format 11:
        expl, alias, position, stateProperties, entryReactions,
        internalTransitions, exitReactions, externalTransitions, regions
        (иначе Coder: «element ... is not allowed for content model»)."""
        if v.kind == "state":
            a('    <stateVertex excluded="false" guid="%s" name="%s">'
              % (v.guid, v.name))
        elif v.kind == "final":
            a('    <finalStateVertex excluded="false" guid="%s" name="%s">'
              % (v.guid, v.name))
        else:
            a('    <pseudoStateVertex excluded="false" guid="%s" kind="%s" '
              'name="%s">' % (v.guid, v.kind, v.name))
        a("      <expl>%s</expl>" % escape(v.expl or ""))
        a("      <alias></alias>")
        a("      <position %s/>" % self._pos(v))
        if v.kind == "state":
            a('      <stateProperties labelHeight="%d" wrapText="true">'
              % LABEL_H)
            a('        <properties value="%d"/>'
              % (114689 if v.regions else 1638401))
            a("      </stateProperties>")
        elif v.kind == "final":
            a('      <properties value="16385"/>')
        else:
            a('      <properties value="114689"/>')
        self._reaction(a, "entryReaction", v.entry, names)
        internal = [t for t in v.trans if t.kind == "internal"]
        external = [t for t in v.trans if t.kind == "external"]
        if internal:
            a("      <internalTransitions>")
            for t in internal:
                a('        <internalTransition guid="%s">' % t.guid)
                a("          <expl>%s</expl>" % escape(t.expl or ""))
                a("          <alias></alias>")
                self._condition(a, t, guids, names, "          ")
                self._actions(a, t.do, names, "          ")
                a("        </internalTransition>")
            a("      </internalTransitions>")
        self._reaction(a, "exitReaction", v.exit, names)
        if external:
            a("      <externalTransitions>")
            for t in external:
                tg = geo[t.target]
                a('        <externalTransition guid="%s" source="%s" '
                  'target="%s">' % (t.guid, v.guid, guids[t.target]))
                a("          <expl>%s</expl>" % escape(t.expl or ""))
                a("          <alias></alias>")
                a("          <transitionProperties>")
                label = getattr(t, "_label", None)
                if label is None:
                    label = (v.h + 79, v.w // 2, v.w // 2 + 476, v.h)
                a('            <position bottom="%d" left="%d" right="%d" '
                  'top="%d"/>' % label)
                a('            <properties value="%d"/>'
                  % getattr(t, "_props", 809894016))
                a("            <routePoints>")
                route = getattr(t, "_route", None)
                if route is None:
                    if t.target == path:
                        route = [(v.w, v.h // 3), (v.w, 2 * v.h // 3)]
                    else:
                        route = [(v.w // 2, v.h), (tg.w // 2, 0)]
                for x, y in route:
                    a('              <routePoint x="%d" y="%d"/>' % (x, y))
                a("            </routePoints>")
                a("          </transitionProperties>")
                if t.special:
                    a("          <%sTransition/>" % {
                        "else": "else", "triggerless": "triggerLess",
                        "termination": "termination"}[t.special])
                self._condition(a, t, guids, names, "          ")
                self._actions(a, t.do, names, "          ")
                a("        </externalTransition>")
            a("      </externalTransitions>")
        if v.regions:
            a("      <regions>")
            for r in v.regions:
                a('        <regionBlock guid="%s"/>' % r.guid)
            a("      </regions>")
        tag = {"state": "stateVertex", "final": "finalStateVertex"}.get(
            v.kind, "pseudoStateVertex")
        a("    </%s>" % tag)


_SETTINGS = """  <settings>
    <colors>
      <color rgb="0X000000"/>
      <color rgb="0X637AFF"/>
      <color rgb="0XB1D991"/>
      <color rgb="0XFF0000"/>
      <color rgb="0XF0DCDC"/>
      <color rgb="0XD2FAFA"/>
      <color rgb="0XFFFFFF"/>
      <color rgb="0XFEFAF3"/>
      <color rgb="0X00BBFA"/>
      <color rgb="0X00E0FF"/>
      <color rgb="0XEAC771"/>
      <color rgb="0X835A00"/>
      <color rgb="0X37C2AE"/>
      <color rgb="0X808000"/>
      <color rgb="0XC0C0C0"/>
      <color rgb="0X808080"/>
    </colors>
    <fonts>
      <font>-13 400 0 255 "Arial"</font>
      <font>-13 700 0 255 "Arial"</font>
      <font>-11 400 0 255 "Arial"</font>
      <font>-11 700 0 255 "Arial"</font>
      <font>-13 400 0 255 "Times New Roman"</font>
      <font>-13 700 0 255 "Times New Roman"</font>
      <font>-11 400 0 255 "Times New Roman"</font>
      <font>-11 700 0 255 "Times New Roman"</font>
    </fonts>
    <pageSetup>
      <footer center="" height="12" left="&amp;FN" right="&amp;PN">
        <font>-13 400 0 255 "Times New Roman"</font>
      </footer>
      <header center="&amp;NF" height="12" left="" right="">
        <font>-13 400 0 255 "Times New Roman"</font>
      </header>
      <pageLayout height="296" marginBottom="5" marginLeft="4" marginRight="4" marginTop="4" paperType="9" portrait="true" width="209"/>
      <elementPrintSetup print="true">
        <font>-13 400 0 255 "Times New Roman"</font>
      </elementPrintSetup>
    </pageSetup>
  </settings>"""


class Project:
    """Проект .vsp: системы и их автоматы."""

    def __init__(self, name, expl="", guid=None):
        _check_ident(name, "проект")
        self.name = name
        self.expl = expl
        self.guid = guid or new_guid()
        self.systems = []

    def add_system(self, name, *machines, guid=None):
        """Система из одного или нескольких автоматов верхнего уровня.

        Имя системы не должно совпадать с именем проекта: Coder по
        умолчанию пишет файлы проекта $(PRJNAME).c/.h и файлы системы
        $(SYSNAME).c/.h в одну папку (knowledge/30_ГРАБЛИ/30-02)."""
        _check_ident(name, "система")
        if name == self.name:
            raise ValueError("система %r называется как проект: Coder "
                             "затрёт один .c/.h другим (30-02)" % name)
        self.systems.append((name, guid or new_guid(), list(machines)))
        return self

    def vsp_xml(self):
        o = []
        a = o.append
        a('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>')
        a('<projectFile dropSignalIfQueueFull="false" format="%d" guid="%s" '
          'name="%s" xmlns="%s">' % (FORMAT, self.guid, self.name, NS))
        a("")
        a("  <expl>%s</expl>" % escape(self.expl))
        a("")
        a('  <SCCInfo auxPath="" localPath="." project="" provider=""/>')
        a("")
        a('  <view colorNumber="7" pagesHorz="2" pagesVert="2"/>')
        a("")
        a('  <diagramInformation textDisplayNote="preserve" '
          'textDisplayState="preserve" textDisplayTransition="preserve"/>')
        a("")
        a(_SETTINGS)
        a("")
        a("  <elements>")
        for f in ("actionsFolder", "constantsFolder", "eventsFolder",
                  "eventGroupsFolder", "externVariablesFolder",
                  "internVariablesFolder", "signalsFolder"):
            a('    <%s guid="%s" name="root"/>' % (f, new_guid()))
        a("  </elements>")
        a("")
        a("  <systems>")
        for i, (name, guid, machines) in enumerate(self.systems):
            a('    <system guid="%s" name="%s" numberOfInstances="1" '
              'signalQueueSize="0">' % (guid, name))
            a("      <expl></expl>")
            a("      <alias></alias>")
            a('      <view colorNumber="7" pagesHorz="2" pagesVert="2"/>')
            a('      <diagramInformation textDisplayNote="preserve" '
              'textDisplayState="preserve" textDisplayTransition="preserve"/>')
            a('      <position bottom="%d" left="0" right="688" top="%d"/>'
              % (635 + 700 * i, 700 * i))
            a('      <properties value="1048578"/>')
            a("      <files>")
            for m in machines:
                a("        <file>%s</file>" % escape(m.file))
            a("      </files>")
            a("    </system>")
        a("  </systems>")
        a("")
        a("</projectFile>")
        a("")
        return "\n".join(o)

    def vnw_xml(self):
        active = self.systems[0][0] if self.systems else ""
        return ('<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'
                '<NavigatorWorkspace Date="" Explanation="" Time="">\n\n'
                '  <SourceControl SccAuxPath="" SccName="" SccPath="." '
                'SccProvider=""/>\n\n'
                '  <Project Active="true" ActiveSystem="%s" File=".\\%s.vsp">\n'
                '    <Signature CheckSum="" Version=""/>\n'
                '    <Validator File=".\\%s.vws"/>\n'
                '  </Project>\n\n'
                '</NavigatorWorkspace>\n' % (active, self.name, self.name))

    def vws_text(self):
        """Рабочая область Validator: без неё Validator спрашивает про
        исключённые элементы модальным окном (30-06)."""
        from .sim import VWS
        return VWS % (self.name + ".vsp")

    def check(self):
        errs = []
        files = set()
        for name, _g, machines in self.systems:
            if not machines:
                errs.append("система %s без автоматов" % name)
            for m in machines:
                if m.file.lower() in files:
                    errs.append("файл %s повторяется" % m.file)
                files.add(m.file.lower())
                errs += ["%s: %s" % (m.name, e) for e in m.check()]
        if not self.systems:
            errs.append("в проекте нет систем")
        return errs

    def save(self, folder, overwrite=False, validate=True):
        """Записать .vsp, .vsr, .vnw и .vws в folder. Возвращает путь к
        .vsp. Существующие файлы не перезаписываются без overwrite=True.
        validate=True — проверить записанное схемой Visual State
        (vskit.schema; без lxml проверка пропускается)."""
        errs = self.check()
        if errs:
            raise ValueError("модель не сходится:\n  " + "\n  ".join(errs))
        os.makedirs(folder, exist_ok=True)
        out = {os.path.join(folder, self.name + ".vsp"): self.vsp_xml(),
               os.path.join(folder, "Workspace.vnw"): self.vnw_xml(),
               os.path.join(folder, self.name + ".vws"): self.vws_text()}
        for _n, _g, machines in self.systems:
            for m in machines:
                out[os.path.join(folder, m.file)] = m.xml()
        if not overwrite:
            busy = [p for p in out if os.path.exists(p)]
            if busy:
                raise FileExistsError("уже есть: %s (overwrite=True — "
                                      "только осознанно)" % ", ".join(busy))
        for p, text in out.items():
            with open(p, "w", encoding="utf-8", newline="\r\n") as f:
                f.write(text)
        vsp = os.path.join(folder, self.name + ".vsp")
        if validate:
            try:
                from . import schema
                bad = {f: e for f, e in schema.validate_project(vsp).items()
                       if e}
            except ImportError:
                bad = {}
            if bad:
                raise ValueError("записанное не проходит схему Visual "
                                 "State: %s" % bad)
        return vsp


def from_project(p):
    """Описание (Project с Machine) из разобранной модели model.Project.

    Сохраняются имена, типы, GUID элементов, состояний и переходов,
    реакции, условия и действия. Не переносятся: координаты (раскладка
    строится заново), элементы уровня проекта, группы событий, заметки.
    """
    dp = Project(p.name, guid=p.guid or None)
    for s in p.systems:
        ms = []
        for m in s.machines:
            dm = Machine(m.name, file=os.path.basename(m.file), expl=m.expl,
                         guid=m.guid or None)
            kinds = {"actions": "action", "events": "event",
                     "constants": "const", "intvars": "intvar",
                     "extvars": "extvar", "signals": "signal"}
            for k, kind in kinds.items():
                for e in m.elements[k]:
                    el = _El(kind, e.name, type=e.type, args=e.args,
                             value=e.value, expl=e.expl, lo=e.lower,
                             hi=e.upper, guid=e.guid or None)
                    dm.els.append(el)
            if m.regions:
                dm.top.name = m.regions[0].name
                dm.top.guid = m.regions[0].guid or dm.top.guid

            def copy(region, prefix, rname):
                for v in region.vertices:
                    path = prefix + v.name
                    kind = v.kind
                    dv = dm._add_vertex(kind, path, rname, v.guid or None)
                    dv.entry = list(v.entry)
                    dv.exit = list(v.exit)
                    dv.expl = v.expl
                    for kk in dm._n:
                        if kind == kk:
                            dm._n[kk] += 1
                    for r in v.regions:
                        copy(r, path + ".", r.name)
                        for x in dv.regions:
                            if x.name == r.name:
                                x.guid = r.guid or x.guid

            for r in m.regions[:1]:
                copy(r, "", None)
            for v in m.vertices():
                for t in v.transitions:
                    trig = t.trigger
                    if trig and t.trigger_args:
                        trig = "%s(%s)" % (trig, ", ".join(t.trigger_args))
                    tt = _T(t.kind, v.path,
                            t.target.path if t.target else None, trig,
                            list(t.guards), list(t.actions), list(t.positive),
                            list(t.negative), t.special, "", t.guid or None)
                    dm._vertex(v.path).trans.append(tt)
            ms.append(dm)
        dp.systems.append((s.name, s.guid or new_guid(), ms))
    return dp
