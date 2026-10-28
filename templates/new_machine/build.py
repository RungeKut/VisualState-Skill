# -*- coding: utf-8 -*-
"""Сборка автомата из model.py: модель Visual State -> проверки -> код.

    python build.py              # модель, схема, API, Verificator, код, gcc
    python build.py --sim        # плюс сценарий SCENARIO в Validator
    python build.py --designer   # плюс открыть модель в Designer и закрыть

Результат рядом с этим файлом:
    vs_model/   .vsp, .vsr, .vnw, .vws — открываются в Designer
    vs_gen/     сгенерированный C-код для прошивки
Обе папки пересоздаются при каждом запуске: правка — только в model.py.

Скопировав шаблон в проект, впишите в KIT корень набора VisualState-Skill
(папку его SKILL.md); шаблон на своём месте в наборе находит корень сам.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = r""


def kit_root():
    """Корень набора: KIT, иначе <корень>/templates/new_machine -> <корень>."""
    for c in (KIT, os.path.dirname(os.path.dirname(HERE))):
        if c and os.path.isdir(os.path.join(c, "vskit")):
            return c
    sys.exit("не найден набор VisualState-Skill: впишите его корень (папку "
             "SKILL.md) в KIT в начале build.py")


sys.path.insert(0, kit_root())
sys.path.insert(0, HERE)
import vskit as vk   # noqa: E402
import model         # noqa: E402

vk.utf8_console()
mdir = os.path.join(HERE, "vs_model")
gdir = os.path.join(HERE, "vs_gen")
if os.path.isdir(mdir):
    shutil.rmtree(mdir)
vsp = model.build(vk).save(mdir)
print(vk.load(vsp))
rep = vk.full_check(vsp, gdir)
print(rep)
if not rep.ok:
    sys.exit(1)

if "--sim" in sys.argv:
    bad = 0
    with vk.Simulator(vsp) as s:
        for ev, args, want in model.SCENARIO:
            got = s.deduct(ev, *args)
            same = want is None or got == want
            bad += not same
            print("%s  %s%s -> %s" % ("OK    " if same else "ОШИБКА", ev,
                                      args, got))
    if bad:
        sys.exit(1)

if "--designer" in sys.argv:
    print(vk.designer_check(vsp))
