# -*- coding: utf-8 -*-
"""Снимок Designer на скрытом столе: обзор и лист региона. Требует набор
HiddenDesktop-Kit (HDKIT_HOME). Окон у человека не появляется.

    python tests\test_shot.py
"""
import os
import shutil

from _common import OUT, finish, ok, start
from _models import gadget

vk = start("test_shot")
folder = os.path.join(OUT, "shot_model")
if os.path.isdir(folder):
    shutil.rmtree(folder)
vsp = vk.Project("GadgetProject").add_system("GadgetSys", gadget(vk)).save(
    folder)
before = vk.windows()

r = vk.designer_shot(vsp, os.path.join(OUT, "shot_all.png"), zoom=50)
ok(r["size"][0] > 1000 and not r["blank"],
   "обзор: %dx%d, не пустой, заголовок %r" % (r["size"] + (r["title"],)))
r = vk.designer_shot(vsp, os.path.join(OUT, "shot_sheet.png"), zoom=75,
                     open_path=[0, 0, 0, 0, 0, 1])
ok(not r["blank"], "лист второго региона открыт и снят: %dx%d" % r["size"])
ok(vk.windows() == before and not vk.windows(),
   "на столе человека окон Designer нет")
finish()
