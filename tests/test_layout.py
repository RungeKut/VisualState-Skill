# -*- coding: utf-8 -*-
"""Раскладка диаграмм (vskit.layout) без окон: геометрия и страницы.

Отвлечённая модель «устройство»: верхнее состояние с двумя регионами
(лист на каждый регион), в одном — линейка с двумя выборами и
параллельными рёбрами, в другом — кольцо состояний с обратной шиной.
Проверяется: полный full_check (схема, Verificator, HCoder, gcc);
состояния региона не пересекаются; выборы не растянуты; подписи
не накрывают состояния своего региона; регионы с несколькими
соседями вынесены на листы (offPage), число страниц покрывает
содержимое, параллельные рёбра у выбора — сплайны.

    python tests\\test_layout.py
"""
import math
import os
import re
import shutil

from _common import OUT, finish, ok, start
from _models import gadget

vk = start("test_layout")
folder = os.path.join(OUT, "layout_model")
if os.path.isdir(folder):
    shutil.rmtree(folder)


m = gadget(vk)
vsp = vk.Project("GadgetProject").add_system("GadgetSys", m).save(folder)
rep = vk.full_check(vsp, os.path.join(OUT, "layout_gen"))
ok(rep.ok and not any(l == "ОШИБКА" for l, _w, _d in rep.items),
   "full_check: схема, API, Verificator, HCoder, gcc — без ошибок")


def regions(machine):
    out = []

    def walk(reg):
        out.append(reg)
        for v in reg.vertices:
            for sub in v.regions:
                walk(sub)
    walk(machine.top)
    return out


def overlap(a, b):
    return not (a.x + a.w <= b.x or b.x + b.w <= a.x
                or a.y + a.h <= b.y or b.y + b.h <= a.y)


bad_over = bad_pseudo = 0
for reg in regions(m):
    vs = reg.vertices
    for i, a in enumerate(vs):
        if a.kind != "state" and (a.w > 80 or a.h > 80):
            bad_pseudo += 1
        for b in vs[i + 1:]:
            if overlap(a, b):
                bad_over += 1
ok(bad_over == 0, "состояния одного региона не пересекаются")
ok(bad_pseudo == 0, "выборы и начальные вершины не растянуты (<= 80)")

where = {p: (v, r) for p, v, r in m._walk()}
hit = 0
for path, v, reg in m._walk():
    for t in v.trans:
        if t.kind != "external" or not t.target:
            continue
        tg, treg = where[t.target]
        if treg is not reg or not hasattr(t, "_label"):
            continue
        bottom, left, right, top = t._label
        box = (v.x + left, v.y + top, v.x + right, v.y + bottom)
        for u in reg.vertices:
            if u.kind != "state":
                continue
            if not (box[2] <= u.x or u.x + u.w <= box[0]
                    or box[3] <= u.y or u.y + u.h <= box[1]):
                hit += 1
ok(hit == 0, "подписи переходов не накрывают состояния своего региона "
   "(накрытий: %d)" % hit)

top_state = m.top.vertices[-1] if m.top.vertices[-1].regions else \
    next(v for v in m.top.vertices if v.regions)
ok(all(getattr(r, "off_page", False) for r in top_state.regions),
   "регионы верхнего состояния вынесены на листы (offPage)")

text = open(os.path.join(folder, "Gadget.vsr"), encoding="utf-8").read()
flags = re.findall(r'<region [^>]*name="(\w+)" offPage="(\w+)"', text)
ok(("Linear", "true") in flags and ("Ring", "true") in flags,
   "в XML offPage=true у регионов листов: %s" % flags)
spl = len(re.findall(r'<properties value="809894017"/>', text))
ok(spl == 2, "параллельные рёбра выбора — сплайны (value=809894017): %d" % spl)

guid = {r.guid: r for r in regions(m)}
bad_pages = 0
for g, ph, pv in re.findall(
        r'<region [^>]*guid="([^"]+)"[^>]*>.*?<view [^>]*pagesHorz="(\d+)" '
        r'pagesVert="(\d+)"', text, re.S):
    r = guid[g]
    if int(ph) < math.ceil((r.w + 53) / vk.design.PAGE_W) or \
            int(pv) < math.ceil((r.h + 53) / vk.design.PAGE_H):
        bad_pages += 1
ok(bad_pages == 0, "страниц (pagesHorz/pagesVert) хватает на содержимое "
   "каждого региона")

finish()
