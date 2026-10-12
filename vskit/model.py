# -*- coding: utf-8 -*-
"""Чтение модели Visual State: проект .vsp и автоматы .vsr — это XML.

Поддерживаются форматы файлов, которые читает Visual State 9.1:

  * format 11 (так сохраняет Designer 9.1): .vsr плоский — `regionBlocks`,
    `vertexBlocks`, ссылки по GUID (`source`, `target`, `trigger guid=`,
    `positiveState`), вызов действия — по имени (`actionCall
    actionFunction="Имя"`);
  * format 6 и 8 (примеры поставки): .vsr вложенный — `topstate` ->
    `regions/region` -> `vertices` -> `stateVertex` -> `regions` ...,
    ссылки по пути из имён (`Top.Region.State`), триггер по имени;
  * format 1 (самый старый пример): то же, но вершина — `vertex
    kind="normalState|initialState|..."`, файл автомата — `<file
    name="...">`.

Разбор — xml.etree, Visual State не нужен. Пространство имён
`http://www.iar.com/visualSTATE/2011/Modelfile` отбрасывается.

    p = load(r"C:\\копия\\Project.vsp")
    print(p)                       # системы, автоматы, состояния, переходы
    for t in p.transitions():
        print(t)                   # Src: Ev(a) [guard] / act() -> Dst

Подробности формата — knowledge/10_API/10-01.
"""
import os
import xml.etree.ElementTree as ET

ELEMENT_KINDS = {
    "actionFunction": "actions",
    "event": "events",
    "constant": "constants",
    "externVariable": "extvars",
    "internVariable": "intvars",
    "signal": "signals",
    "eventGroup": "event_groups",
}
VERTEX_TAGS = ("stateVertex", "pseudoStateVertex", "finalStateVertex",
               "vertex")
_KIND1 = {"normalState": "state", "finalState": "final"}


def _tag(e):
    t = e.tag
    return t.rsplit("}", 1)[-1] if "}" in t else t


def _kids(e, name=None):
    return [c for c in list(e) if name is None or _tag(c) == name]


def _kid(e, name):
    for c in list(e):
        if _tag(c) == name:
            return c
    return None


def _text(e, name, default=""):
    c = _kid(e, name) if e is not None else None
    return (c.text or "") if c is not None else default


class Element:
    """Элемент модели: действие, событие, константа, переменная, сигнал."""

    def __init__(self, kind, name, guid="", type="", args=None, value=None,
                 expl="", lower=None, upper=None, definition=None):
        self.kind = kind
        self.name = name
        self.guid = guid
        self.type = type
        self.args = args or []
        self.value = value
        self.expl = expl
        self.lower = lower
        self.upper = upper
        self.definition = definition

    def signature(self):
        a = ", ".join("%s %s" % (t, n) for n, t in self.args)
        if self.kind == "actions":
            return "%s %s(%s)" % (self.type or "VS_VOID", self.name, a)
        if self.kind in ("events", "signals"):
            return "%s(%s)" % (self.name, a) if a else self.name
        v = "" if self.value in (None, "") else " = %s" % self.value
        d = ""
        if self.lower not in (None, "") or self.upper not in (None, ""):
            d = " [%s..%s]" % (self.lower or "", self.upper or "")
        return "%s %s%s%s" % (self.type, self.name, v, d)

    def __repr__(self):
        return "<%s %s>" % (self.kind, self.signature())


class Transition:
    """Переход. `kind`: external | internal; `special`: else, triggerless,
    termination или ''."""

    def __init__(self, kind, source, target=None, trigger=None,
                 trigger_args=None, guards=None, actions=None, positive=None,
                 negative=None, special="", guid=""):
        self.kind = kind
        self.source = source
        self.target = target
        self.trigger = trigger
        self.trigger_args = trigger_args or []
        self.guards = guards or []
        self.actions = actions or []
        self.positive = positive or []
        self.negative = negative or []
        self.special = special
        self.guid = guid

    def text(self):
        s = self.source.path if self.source else "?"
        trig = self.trigger or ""
        if trig and self.trigger_args:
            trig += "(%s)" % ", ".join(self.trigger_args)
        if self.special and not trig:
            trig = "<%s>" % self.special
        cond = trig
        if self.positive:
            cond += " " + " ".join("[in %s]" % p for p in self.positive)
        if self.negative:
            cond += " " + " ".join("[not in %s]" % p for p in self.negative)
        if self.guards:
            cond += " [%s]" % " && ".join(self.guards)
        act = (" / " + "; ".join(self.actions)) if self.actions else ""
        if self.kind == "internal":
            return "%s: %s%s (внутренний)" % (s, cond.strip(), act)
        t = self.target.path if self.target else "?"
        return "%s: %s%s -> %s" % (s, cond.strip(), act, t)

    def __repr__(self):
        return "<Transition %s>" % self.text()


class Vertex:
    """Состояние или псевдосостояние. `kind`: state, final, initialState,
    choiceState, shallowHistoryState, deepHistoryState, forkState..."""

    def __init__(self, kind, name, guid, parent_region=None):
        self.kind = kind
        self.name = name
        self.guid = guid
        self.region = parent_region
        self.regions = []
        self.entry = []
        self.exit = []
        self.transitions = []
        self.expl = ""
        self.excluded = False

    @property
    def parent(self):
        return self.region.owner if self.region else None

    @property
    def path(self):
        """Путь из имён состояний без регионов: 'On.Playing'."""
        names = []
        v = self
        while isinstance(v, Vertex):
            names.append(v.name)
            v = v.parent
        return ".".join(reversed(names))

    @property
    def full_path(self):
        """Путь как в format 6/8: 'Top.Region.On.rSub.Playing'."""
        parts = [self.name]
        r = self.region
        while r is not None:
            parts.append(r.name)
            o = r.owner
            parts.append(o.name)
            r = o.region if isinstance(o, Vertex) else None
        return ".".join(reversed(parts))

    def walk(self):
        yield self
        for r in self.regions:
            for v in r.vertices:
                for x in v.walk():
                    yield x

    def __repr__(self):
        return "<%s %s>" % (self.kind, self.path)


class Region:
    def __init__(self, name, guid, owner):
        self.name = name
        self.guid = guid
        self.owner = owner
        self.vertices = []

    def __repr__(self):
        return "<Region %s: %s>" % (self.name,
                                    ", ".join(v.name for v in self.vertices))


class Machine:
    """Автомат верхнего уровня — один файл .vsr (topstate)."""

    def __init__(self, path, name, guid, fmt):
        self.file = path
        self.name = name
        self.guid = guid
        self.format = fmt
        self.regions = []
        self.elements = {k: [] for k in ELEMENT_KINDS.values()}
        self.expl = ""

    def vertices(self):
        for r in self.regions:
            for v in r.vertices:
                for x in v.walk():
                    yield x

    def states(self):
        return [v for v in self.vertices() if v.kind in ("state", "final")]

    def transitions(self):
        out = []
        for v in self.vertices():
            out += v.transitions
        return out

    def find(self, path):
        """Состояние по пути без регионов ('On.Playing') или по имени."""
        hits = [v for v in self.vertices() if v.path == path]
        if not hits:
            hits = [v for v in self.vertices() if v.name == path]
        if len(hits) != 1:
            raise KeyError("состояние %r: найдено %d" % (path, len(hits)))
        return hits[0]

    def __repr__(self):
        return "<Machine %s (%s): %d состояний, %d переходов>" % (
            self.name, os.path.basename(self.file), len(self.states()),
            len(self.transitions()))


class System:
    def __init__(self, name, guid, files):
        self.name = name
        self.guid = guid
        self.files = files
        self.machines = []

    def __repr__(self):
        return "<System %s: %s>" % (self.name,
                                    ", ".join(m.name for m in self.machines))


class Project:
    """Проект .vsp: системы, их автоматы и элементы проекта."""

    def __init__(self, path, name, guid, fmt):
        self.file = path
        self.name = name
        self.guid = guid
        self.format = fmt
        self.systems = []
        self.elements = {k: [] for k in ELEMENT_KINDS.values()}

    def machines(self):
        return [m for s in self.systems for m in s.machines]

    def system(self, name):
        for s in self.systems:
            if s.name == name:
                return s
        raise KeyError("нет системы %r в %s" % (name, self.file))

    def all_elements(self, kind):
        """Элементы вида kind ('events', 'actions'...) проекта и всех
        автоматов."""
        out = list(self.elements[kind])
        for m in self.machines():
            out += m.elements[kind]
        return out

    def names(self, kind):
        return sorted({e.name for e in self.all_elements(kind)})

    def states(self):
        return [v for m in self.machines() for v in m.states()]

    def transitions(self):
        return [t for m in self.machines() for t in m.transitions()]

    def summary(self):
        lines = ["Проект %s (format %s), %s" % (self.name, self.format,
                                               self.file)]
        for kind in ELEMENT_KINDS.values():
            if self.elements[kind]:
                lines.append("  %s проекта: %s" % (kind, ", ".join(
                    e.signature() for e in self.elements[kind])))
        for s in self.systems:
            lines.append("  система %s" % s.name)
            for m in s.machines:
                lines.append("    автомат %s (%s, format %s)" % (
                    m.name, os.path.basename(m.file), m.format))
                for kind in ELEMENT_KINDS.values():
                    if m.elements[kind]:
                        lines.append("      %s: %s" % (kind, ", ".join(
                            e.signature() for e in m.elements[kind])))
                for v in m.vertices():
                    depth = v.path.count(".")
                    extra = []
                    if v.entry:
                        extra.append("entry: " + "; ".join(v.entry))
                    if v.exit:
                        extra.append("exit: " + "; ".join(v.exit))
                    lines.append("      %s%s [%s]%s" % (
                        "  " * depth, v.name, v.kind,
                        ("  " + " | ".join(extra)) if extra else ""))
                for t in m.transitions():
                    lines.append("      > " + t.text())
        return "\n".join(lines)

    def to_dict(self):
        """Модель словарём — для JSON и сравнения."""
        def el(e):
            return {"name": e.name, "type": e.type, "args": e.args,
                    "value": e.value, "expl": e.expl}

        def tr(t):
            return {"kind": t.kind, "source": t.source.path,
                    "target": t.target.path if t.target else None,
                    "trigger": t.trigger, "args": t.trigger_args,
                    "guards": t.guards, "actions": t.actions,
                    "positive": t.positive, "negative": t.negative,
                    "special": t.special}

        def mach(m):
            return {"name": m.name, "file": os.path.basename(m.file),
                    "elements": {k: [el(e) for e in v]
                                 for k, v in m.elements.items() if v},
                    "vertices": [{"path": v.path, "kind": v.kind,
                                  "entry": v.entry, "exit": v.exit}
                                 for v in m.vertices()],
                    "transitions": [tr(t) for t in m.transitions()]}

        return {"name": self.name, "format": self.format,
                "elements": {k: [el(e) for e in v]
                             for k, v in self.elements.items() if v},
                "systems": [{"name": s.name,
                             "machines": [mach(m) for m in s.machines]}
                            for s in self.systems]}

    def __str__(self):
        return self.summary()

    def __repr__(self):
        return "<Project %s: %d систем, %d автоматов, %d состояний, " \
               "%d переходов>" % (self.name, len(self.systems),
                                  len(self.machines()), len(self.states()),
                                  len(self.transitions()))


def _args(e):
    a = _kid(e, "arguments")
    return [(x.get("name"), x.get("type")) for x in _kids(a, "argument")] \
        if a is not None else []


def _elements(root, into):
    if root is None:
        return
    for e in root.iter():
        kind = ELEMENT_KINDS.get(_tag(e))
        if not kind:
            continue
        typ = e.get("type") or e.get("returnType") or ""
        into[kind].append(Element(
            kind, e.get("name"), e.get("guid", ""), typ, _args(e),
            _text(e, "value", None), _text(e, "expl"),
            _text(e, "lowerDomain", None), _text(e, "upperDomain", None),
            e.get("definition")))


def _action_side(e):
    out = []
    if e is None:
        return out
    for c in list(e):
        t = _tag(c)
        if t == "actionCall":
            args = [a.get("token", a.text or "") for a in c.iter()
                    if _tag(a) == "actionCallArgument"]
            out.append("%s(%s)" % (c.get("actionFunction"), ", ".join(args)))
        elif t == "assignment":
            out.append((c.text or "").strip())
        elif t in ("signal", "signalEmit", "sendSignal"):
            out.append("^" + (c.get("name") or c.get("signal") or
                              c.text or "").strip())
        else:
            out.append("<%s %s>" % (t, (c.text or "").strip()))
    return out


def _reactions(v, tag):
    out = []
    holder = _kid(v, tag + "s")
    for r in _kids(holder, tag) if holder is not None else []:
        out += _action_side(_kid(r, "actionSide"))
    return out


class _Ctx:
    def __init__(self, machine, fmt, events_by_guid):
        self.m = machine
        self.fmt = fmt
        self.events = events_by_guid
        self.by_guid = {}
        self.by_full = {}
        self.pending = []


def _vertex(ctx, e, region, blocks):
    t = _tag(e)
    if t == "stateVertex":
        kind = "state"
    elif t == "finalStateVertex":
        kind = "final"
    else:
        kind = e.get("kind") or "pseudo"
        kind = _KIND1.get(kind, kind)
    v = Vertex(kind, e.get("name"), e.get("guid", ""), region)
    v.expl = _text(e, "expl")
    v.excluded = e.get("excluded") == "true"
    v.entry = _reactions(e, "entryReaction")
    v.exit = _reactions(e, "exitReaction")
    ctx.by_guid[v.guid] = v
    ctx.by_full[v.full_path] = v
    for holder, kindt in (("externalTransitions", "external"),
                          ("internalTransitions", "internal")):
        h = _kid(e, holder)
        for tr in list(h) if h is not None else []:
            ctx.pending.append((v, kindt, tr))
    rs = _kid(e, "regions")
    for r in list(rs) if rs is not None else []:
        v.regions.append(_region(ctx, r, v, blocks))
    return v


def _region(ctx, e, owner, blocks):
    if _tag(e) == "regionBlock":
        e = blocks["region"][e.get("guid")]
    r = Region(e.get("name"), e.get("guid", ""), owner)
    vs = _kid(e, "vertices")
    for x in list(vs) if vs is not None else []:
        if _tag(x) == "vertexBlock":
            x = blocks["vertex"][x.get("guid")]
        if _tag(x) in VERTEX_TAGS:
            r.vertices.append(_vertex(ctx, x, r, blocks))
    return r


def _ref(ctx, s):
    if s is None:
        return None
    s = s.strip()
    if s in ctx.by_guid:
        return ctx.by_guid[s]
    if s in ctx.by_full:
        return ctx.by_full[s]
    return None


def _ref_name(ctx, s):
    v = _ref(ctx, s)
    return v.path if v else s


def _transition(ctx, src, kindt, e):
    cs = _kid(e, "conditionSide")
    trig = None
    targs = []
    guards = []
    pos = []
    neg = []
    if cs is not None:
        te = _kid(cs, "trigger")
        if te is not None:
            if te.get("guid"):
                trig = ctx.events.get(te.get("guid"), te.get("guid"))
            else:
                trig = te.get("name")
            targs = [(a.text or "").strip() for a in _kids(te, "argument")]
        g = _kid(cs, "guards")
        guards = [(x.text or "").strip() for x in _kids(g, "guard")] \
            if g is not None else []
        p = _kid(cs, "positiveSynchronizations")
        pos = [_ref_name(ctx, x.text) for x in _kids(p, "positiveState")] \
            if p is not None else []
        n = _kid(cs, "negativeSynchronizations")
        neg = [_ref_name(ctx, x.text) for x in _kids(n, "negativeState")] \
            if n is not None else []
    special = ""
    for sp, name in (("elseTransition", "else"),
                     ("triggerLessTransition", "triggerless"),
                     ("terminationTransition", "termination")):
        if _kid(e, sp) is not None:
            special = name
    tgt = _ref(ctx, e.get("target")) if kindt == "external" else None
    if kindt == "external" and tgt is None and e.get("target"):
        tgt = Vertex("unresolved", e.get("target"), "")
    return Transition(kindt, src, tgt, trig, targs, guards,
                      _action_side(_kid(e, "actionSide")), pos, neg, special,
                      e.get("guid", ""))


def load_machine(path, events_by_guid=None):
    """Разобрать один файл .vsr. events_by_guid — {guid: имя} событий
    проекта (в format 11 триггер ссылается на событие по GUID)."""
    root = ET.parse(path).getroot()
    fmt = int(root.get("format", "0") or 0)
    top = _kid(root, "topstate")
    if top is None:
        top = root
    m = Machine(path, top.get("name"), top.get("guid", ""), fmt)
    m.expl = _text(top, "expl")
    _elements(_kid(top, "elements"), m.elements)
    events = dict(events_by_guid or {})
    for e in m.elements["events"] + m.elements["signals"]:
        events[e.guid] = e.name
    blocks = {"region": {}, "vertex": {}}
    rb = _kid(root, "regionBlocks")
    for r in list(rb) if rb is not None else []:
        blocks["region"][r.get("guid")] = r
    vb = _kid(root, "vertexBlocks")
    for v in list(vb) if vb is not None else []:
        blocks["vertex"][v.get("guid")] = v
    ctx = _Ctx(m, fmt, events)
    rs = _kid(top, "regions")
    for r in list(rs) if rs is not None else []:
        m.regions.append(_region(ctx, r, m, blocks))
    for src, kindt, e in ctx.pending:
        src.transitions.append(_transition(ctx, src, kindt, e))
    return m


def load(vsp):
    """Разобрать проект .vsp вместе со всеми его .vsr."""
    vsp = os.path.abspath(vsp)
    root = ET.parse(vsp).getroot()
    fmt = int(root.get("format", "0") or 0)
    pe = _kid(root, "project")
    holder = pe if pe is not None else root
    name = root.get("name") or holder.get("name") or \
        os.path.splitext(os.path.basename(vsp))[0]
    p = Project(vsp, name, root.get("guid") or holder.get("guid", ""), fmt)
    _elements(_kid(holder, "elements"), p.elements)
    events = {e.guid: e.name for e in p.elements["events"] +
              p.elements["signals"]}
    base = os.path.dirname(vsp)
    for se in holder.iter():
        if _tag(se) != "system":
            continue
        files = [(f.get("name") or f.text or "").strip() for f in se.iter()
                 if _tag(f) == "file"]
        s = System(se.get("name"), se.get("guid", ""), files)
        for f in files:
            fp = os.path.normpath(os.path.join(base, f))
            s.machines.append(load_machine(fp, events))
        p.systems.append(s)
    return p
