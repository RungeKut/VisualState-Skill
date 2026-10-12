# -*- coding: utf-8 -*-
"""Полная проверка модели одним вызовом: разбор, XML-схема Visual State,
второе чтение через State Machine API, Verificator, генерация кода,
компиляция.

    rep = full_check(r"C:\\модель\\Project.vsp", r"C:\\вывод\\vs_gen")
    print(rep)              # пункты с OK / ОШИБКА / ВНИМАНИЕ
    rep.check()             # RuntimeError, если есть ошибки

Числа сверяются из двух источников: vskit.model (XML) и
StateMachineAPI64.dll (vskit.smapi) должны увидеть одни и те же вершины
и переходы.
"""
import os

from . import build, coder, env, model, schema, smapi, verificator


class Report:
    def __init__(self, title):
        self.title = title
        self.items = []

    def add(self, level, what, detail=""):
        self.items.append((level, what, detail))

    @property
    def ok(self):
        return all(l != "ОШИБКА" for l, _w, _d in self.items)

    def check(self):
        if not self.ok:
            raise RuntimeError(repr(self))
        return self

    def __repr__(self):
        lines = ["== %s" % self.title]
        for level, what, detail in self.items:
            lines.append("%-8s %s" % (level, what))
            for d in str(detail).splitlines():
                if d.strip():
                    lines.append("         " + d)
        lines.append("итог: %s" % ("OK" if self.ok else "ЕСТЬ ОШИБКИ"))
        return "\n".join(lines)


def full_check(vsp, out_dir, coder_name="hcoder", options=None,
               verify=True, compile=True, api=True):
    """Разобрать, сверить с API, проверить Verificator, сгенерировать код
    в out_dir и скомпилировать. Возвращает Report."""
    rep = Report("%s (Visual State %s)" % (vsp, env.version()))
    p = model.load(vsp)
    verts = [v for m in p.machines() for v in m.vertices()]
    trans = p.transitions()
    rep.add("OK", "разбор XML: %d систем, %d автоматов, %d вершин, "
                  "%d переходов" % (len(p.systems), len(p.machines()),
                                    len(verts), len(trans)))
    try:
        bad = {os.path.basename(f): e[:5] for f, e in
               schema.validate_project(vsp).items() if e}
        rep.add("ОШИБКА" if bad else "OK",
                "XML-схема Visual State (format %s)" % p.format,
                "\n".join("%s: %s" % (f, "; ".join(e))
                          for f, e in bad.items()))
    except ImportError:
        rep.add("ВНИМАНИЕ", "XML-схема не проверена: нет lxml "
                            "(pip install lxml)")
    if api:
        try:
            inv = smapi.inventory(vsp)
            ext = sum(1 for t in trans if t.kind == "external")
            itn = sum(1 for t in trans if t.kind == "internal")
            same = (len(inv["vertices"]) == len(verts) and
                    inv["external"] == ext and inv["internal"] == itn)
            rep.add("OK" if same else "ОШИБКА",
                    "State Machine API: %d вершин, %d внешних, %d внутренних"
                    % (len(inv["vertices"]), inv["external"],
                       inv["internal"]),
                    "" if same else "XML: %d вершин, %d внешних, "
                    "%d внутренних" % (len(verts), ext, itn))
        except Exception as e:
            rep.add("ОШИБКА", "State Machine API не прочитал модель", e)
    if verify:
        vr = verificator.verify(vsp)
        level = "OK" if vr.ok and not vr.warnings else (
            "ВНИМАНИЕ" if vr.ok else "ОШИБКА")
        rep.add(level, "Verificator", vr)
    r = coder.generate(vsp, out_dir, coder=coder_name, options=options)
    rep.add("OK" if r.ok else "ОШИБКА", "генерация кода (%s)" % r.coder, r)
    if compile and r.ok:
        c = build.compile_check(out_dir)
        rep.add("OK" if c.ok else "ОШИБКА", "компиляция arm-none-eabi-gcc %s"
                % env.gcc_version(), c)
    return rep
