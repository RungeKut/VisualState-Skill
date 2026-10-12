# -*- coding: utf-8 -*-
"""Чтение модели: XML-разбор против State Machine API на всех примерах
поставки; format 6 и тот же проект, пересохранённый API в format 11,
дают одинаковую модель; поставка не меняется.

    python tests\\test_model.py
"""
import glob
import json
import os
import shutil

from _common import OUT, CD, fingerprint, finish, ok, start

vk = start("test_model")
ex = vk.examples_dir()
before = fingerprint(ex)

for vsp in sorted(glob.glob(os.path.join(ex, "**", "*.vsp"),
                            recursive=True)):
    try:
        p = vk.load(vsp)
    except PermissionError as e:
        print("пропуск (нет доступа): %s — %s" % (vsp, e))
        continue
    verts = [v for m in p.machines() for v in m.vertices()]
    ext = sum(1 for t in p.transitions() if t.kind == "external")
    itn = sum(1 for t in p.transitions() if t.kind == "internal")
    inv = vk.smapi.inventory(vsp)
    same = (len(inv["vertices"]) == len(verts) and inv["external"] == ext
            and inv["internal"] == itn)
    ok(same, "%s (format %s): XML %d/%d/%d = API %d/%d/%d (вершины/внешн/"
       "внутр)" % (os.path.relpath(vsp, ex), p.format, len(verts), ext, itn,
                   len(inv["vertices"]), inv["external"], inv["internal"]))
    unresolved = [t for t in p.transitions()
                  if t.target is not None and t.target.kind == "unresolved"]
    ok(not unresolved, "  все цели переходов найдены")


def norm(p):
    d = p.to_dict()
    d.pop("format")
    for s in d["systems"]:
        for m in s["machines"]:
            for k in ("vertices", "transitions"):
                m[k] = sorted(json.dumps(x, sort_keys=True) for x in m[k])
    return d


dst = os.path.join(OUT, "format11")
if os.path.isdir(dst):
    shutil.rmtree(dst)
n11 = vk.smapi.normalize(CD, dst)
p6, p11 = vk.load(CD), vk.load(n11)
ok(p6.format == 6 and p11.format == 11 and
   p11.machines()[0].format == 11, "API пересохранил пример в format 11")
ok(norm(p6) == norm(p11), "format 6 и format 11 разбираются в одну модель")
print(p11)
bad = os.path.join(OUT, "schema_bad")
if os.path.isdir(bad):
    shutil.rmtree(bad)
vk.copy_model(n11, bad)
vsr = os.path.join(bad, "CDPlayer.vsr")
t = open(vsr, encoding="utf-8").read()
i = t.index("<exitReactions>")
j = t.index("</exitReactions>") + len("</exitReactions>")
k = t.index("</stateVertex>", j)
moved = t[:i] + t[j:k] + t[i:j] + t[k:]
open(vsr, "w", encoding="utf-8").write(moved)
errs = vk.schema.validate(vsr)
ok("not expected" in " ".join(errs),
   "схема ловит переставленный элемент: %s" % (errs[:1],))
r = vk.generate(os.path.join(bad, "CDPlayer.vsp"),
                os.path.join(OUT, "gen", "schema_bad"))
ok(not r.ok and any("content model" in m for m in r.messages),
   "HCoder отказывает тем же: «not allowed for content model»")
ok(all(not e for e in vk.schema_check(CD).values()),
   "пример format 6 проходит схему format 6")

ok(fingerprint(ex) == before, "файлы поставки не изменились")
finish()
