# -*- coding: utf-8 -*-
"""Документация автомата из модели (vskit.doc): строгий режим, описания в
<expl> модели, Markdown со всеми сущностями.

    python tests\test_doc.py
"""
import os
import shutil

from _common import OUT, finish, ok, start
from _models import gadget

vk = start("test_doc")
folder = os.path.join(OUT, "doc_model")
if os.path.isdir(folder):
    shutil.rmtree(folder)

m = gadget(vk)
miss = vk.undocumented(m)
ok(len(miss) > 10, "у свежей модели нет описаний: %d сущностей" % len(miss))
try:
    vk.document(m, strict=True)
    ok(False, "строгий режим должен отказать")
except ValueError as e:
    ok("нет описаний" in str(e), "строгий режим отказывает, пока есть "
       "безымянные сущности")

n = 0
for title, parent, region in __import__("vskit.doc", fromlist=["x"])._sections(m):
    if parent:
        m.describe_region(parent, region.name, "Описание региона %s" % region.name)
for path, v, _r in m._walk():
    if v.kind == "initialState":
        continue
    m.describe(path, "Описание вершины %s" % path)
    for t in v.trans:
        t.note = "Смысл перехода из %s" % path
        n += 1
for e in m.els:
    e.note = "Описание %s" % e.name
ok(vk.undocumented(m) == [], "после описания всего: undocumented пуст "
   "(переходов описано: %d)" % n)

path = os.path.join(OUT, "doc_gadget.md")
text = vk.document(m, path=path, title="Устройство", strict=True)
ok(os.path.exists(path) and text == open(path, encoding="utf-8").read(),
   "документ записан в файл без искажений")
for must in ("# Устройство", "## Оглавление", "### Состояния",
             "### Переходы", "### Выборы", "### Внутренние реакции",
             "### События", "### Действия", "## Словарь",
             "Описание вершины Top.Idle", "Смысл перехода из Top.Idle",
             "`evKey`", "**Начальное состояние:**", "иначе"):
    ok(must in text, "в документе есть: %s" % must)
ok(text.count("| `Gather` |") >= 1 and "`Hide()`" in text,
   "действие выхода показано у состояния")

vsp = vk.Project("GadgetProject").add_system("GadgetSys", m).save(folder)
xml = open(os.path.join(folder, "Gadget.vsr"), encoding="utf-8").read()
ok("Описание вершины" not in xml and "Описание региона" not in xml,
   "заметки в модель (.vsr) не попадают")
rep = vk.full_check(vsp, os.path.join(OUT, "doc_gen"))
ok(rep.ok and not any(l == "ОШИБКА" for l, _w, _d in rep.items),
   "модель с описаниями проходит full_check")
finish()
