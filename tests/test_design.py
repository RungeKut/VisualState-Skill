# -*- coding: utf-8 -*-
"""Модель текстом: описание на Python -> .vsp/.vsr (format 11) ->
Verificator -> HCoder и Coder -> arm-none-eabi-gcc -> симуляция в
Validator -> Designer открывает и пересохраняет без потерь. Плюс правка
существующей модели через from_project и отказ на битых ссылках.

Модель пишется в папку с пробелом и кириллицей — как у людей.

    python tests\\test_design.py            # с окнами Validator и Designer
    python tests\\test_design.py --no-gui   # без них
"""
import json
import os
import shutil
import sys

from _common import CD, OUT, finish, ok, start

vk = start("test_design")
gui = "--no-gui" not in sys.argv

folder = os.path.join(OUT, "модель с пробелом")
if os.path.isdir(folder):
    shutil.rmtree(folder)

m = vk.Machine("Lamp", expl="лампа с яркостью и миганием")
m.event("evToggle")
m.event("evLevel", ("lvl", "VS_UINT8"))
m.event("evTick")
m.action("LampOn")
m.action("LampOff")
m.action("LampSet", ("lvl", "VS_UINT8"))
m.action("Beep")
m.const("MAX_LEVEL", "VS_UINT8", 3)
m.var("level", "VS_UINT8", 0, lo=0, hi=3)
m.var("ticks", "VS_UINT8", 0, lo=0, hi=5)
m.state("Off", entry="LampOff()")
m.state("On", entry="LampOn()", exit=["LampSet(0)"])
m.state("On.Dim")
m.state("On.Bright", entry="LampSet(MAX_LEVEL)")
m.state("On.Steady", region="Blinker")
m.state("On.Blink", region="Blinker")
m.initial("Off")
m.initial("On.Dim")
m.initial("On.Steady")
m.trans("Off", "On", "evToggle")
m.trans("On", "Off", "evToggle")
m.trans("On.Dim", "On.Bright", "evLevel(lvl)",
        guard="lvl > 1 && lvl <= MAX_LEVEL", do=["level = lvl",
                                                 "LampSet(level)"])
m.trans("On.Bright", "On.Dim", "evLevel(lvl)", guard="lvl <= 1",
        do=["level = lvl", "LampSet(level)"])
m.trans("On.Steady", "On.Blink", "evTick", when_in="On.Bright")
m.trans("On.Blink", "On.Steady", "evTick")
m.internal("Off", "evTick", guard="ticks < 5",
           do=["ticks = ticks + 1", "Beep()"])
vsp = vk.Project("LampProject").add_system("LampSys", m).save(folder)
ok(os.path.exists(vsp), "модель записана: %s" % sorted(os.listdir(folder)))

p = vk.load(vsp)
print(p)
ok(p.format == 11 and len(p.states()) == 6 and len(p.transitions()) == 10,
   "разбор записанного: format 11, 6 состояний, 10 переходов")

for c in ("hcoder", "classic"):
    rep = vk.full_check(vsp, os.path.join(OUT, "design_gen_" + c),
                        coder_name=c)
    print(rep)
    ok(rep.ok and all(l == "OK" for l, _w, _d in rep.items),
       "%s: API = XML, Verificator чистый, код, gcc — всё OK" % c)

if gui:
    with vk.Simulator(vsp) as s:
        steps = [("SE_RESET", (), [("action", "LampOff", None)]),
                 ("evTick", (), [("assign", "ticks", 1),
                                 ("action", "Beep", None)]),
                 ("evToggle", (), [("action", "LampOn", None)]),
                 ("evLevel", (3,), [("assign", "level", 3),
                                    ("action", "LampSet", [3]),
                                    ("action", "LampSet", [3])]),
                 ("evTick", (), []),
                 ("evToggle", (), [("action", "LampSet", [0]),
                                   ("action", "LampOff", None)])]
        for ev, args, want in steps:
            got = s.deduct(ev, *args)
            ok(got == want, "Validator: %s%s -> %s" % (ev, args, got))
        try:
            s.deduct("evNoSuch")
            ok(False, "неизвестное событие должно отклоняться до отправки")
        except vk.SimError:
            ok(True, "неизвестное событие отклонено до отправки (30-06)")
    ok(not vk.windows(), "окна Validator закрыты")

    d = vk.designer_check(vsp, save=True)
    print(d)
    ok(d["ok"], "Designer открыл модель без диалогов и сохранил её")

    def norm(x):
        x = x.to_dict()
        for s in x["systems"]:
            for mm in s["machines"]:
                for k in ("vertices", "transitions"):
                    mm[k] = sorted(json.dumps(v, sort_keys=True)
                                   for v in mm[k])
        return x
    ok(norm(vk.load(d["vsp"])) == norm(p),
       "после сохранения в Designer модель та же")
    ok(not vk.windows(), "окна Designer закрыты")

s2 = vk.Machine("Sel")
s2.event("evGo")
s2.event("evBack")
s2.event("evStop")
s2.event("evData", ("v", "VS_UINT8"))
s2.action("Fast")
s2.action("Slow")
s2.action("Done")
s2.var("count", "VS_UINT8", 0, lo=0, hi=9)
s2.state("Idle")
s2.state("Run")
s2.state("Run.A")
s2.state("Run.B")
s2.initial("Idle")
s2.initial("Run.A")
hist = s2.history("Run", default="Run.A")
ch = s2.choice()
s2.trans("Idle", ch, "evGo")
s2.trans(ch, "Run", None, guard="count > 5", do="Fast()")
s2.trans(ch, "Run", None, otherwise=True, do="Slow()")
s2.trans("Run.A", "Run.B", "evGo")
s2.trans("Run", "Idle", "evBack")
s2.trans("Idle", hist, "evStop")
s2.internal("Idle", "evData(v)", guard="v <= 9", do="count = v")
fin = s2.final("Run")
s2.trans("Run.B", fin, "evStop", do="Done()")
sel_dir = os.path.join(OUT, "выбор_история")
if os.path.isdir(sel_dir):
    shutil.rmtree(sel_dir)
sel = vk.Project("SelProject").add_system("SelSys", s2).save(sel_dir)
rep = vk.full_check(sel, os.path.join(OUT, "выбор_gen"))
print(rep)
ok(rep.ok and all(l == "OK" for l, _w, _d in rep.items),
   "выбор, история, конечное состояние: все проверки OK")
if gui:
    with vk.Simulator(sel) as s:
        seq = [("SE_RESET", (), []), ("evGo", (), [("action", "Slow", None)]),
               ("evBack", (), []), ("evData", (7,), [("assign", "count", 7)]),
               ("evGo", (), [("action", "Fast", None)]), ("evGo", (), []),
               ("evStop", (), [("action", "Done", None)])]
        for ev, args, want in seq:
            got = s.deduct(ev, *args)
            ok(got == want, "Validator (выбор): %s%s -> %s" % (ev, args, got))

src = vk.load(CD)
dp = vk.from_project(src)
mach = dp.systems[0][2][0]
mach.action("Mute")
mach.internal("CDPlayerOn.Playing", "evStopKey", do="Mute()")
cf_dir = os.path.join(OUT, "правка_с_конфликтом")
if os.path.isdir(cf_dir):
    shutil.rmtree(cf_dir)
v = vk.verify(dp.save(cf_dir))
print(v)
ok(not v.ok and "CONFLICTS" in v.reports[0].findings(),
   "Verificator ловит конфликт: внутренний и внешний переход по evStopKey")

dp = vk.from_project(src)
mach = dp.systems[0][2][0]
mach.event("evMute")
mach.action("Mute")
mach.internal("CDPlayerOn", "evMute", do="Mute()")
rt_dir = os.path.join(OUT, "правка_примера")
if os.path.isdir(rt_dir):
    shutil.rmtree(rt_dir)
rt = dp.save(rt_dir)
q = vk.load(rt)
new = [t for t in q.transitions() if t.kind == "internal"]
ok(len(q.transitions()) == len(src.transitions()) + 1 and
   new and new[0].actions == ["Mute()"],
   "правка примера: добавлен внутренний переход с новым действием")
old_guids = {v.guid for m_ in src.machines() for v in m_.vertices()}
new_guids = {v.guid for m_ in q.machines() for v in m_.vertices()}
ok(old_guids == new_guids, "GUID состояний сохранены при правке")
rep = vk.full_check(rt, os.path.join(OUT, "правка_gen"))
print(rep)
ok(rep.ok, "правленая модель: код генерируется и компилируется")

bad = vk.Machine("Bad")
bad.event("evA")
bad.state("S1")
bad.state("S2")
bad.initial("S1")
bad.trans("S1", "S2", "evB")
bad.trans("S2", "S1", "evA", do="Nope()")
try:
    vk.Project("BadP").add_system("BadS", bad).save(
        os.path.join(OUT, "bad_design"))
    ok(False, "битые ссылки должны ловиться при сохранении")
except ValueError as e:
    ok("evB" in str(e) and "Nope" in str(e),
       "битые ссылки пойманы до записи: %s" % str(e).replace("\n", " "))
try:
    vk.Project("Same").add_system("Same", vk.Machine("X"))
    ok(False, "система с именем проекта должна отклоняться")
except ValueError:
    ok(True, "система с именем проекта отклонена (30-02)")
finish()
