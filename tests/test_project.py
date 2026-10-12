# -*- coding: utf-8 -*-
"""Сквозная проверка ЛЮБОГО проекта Visual State: разбор, схема, API,
Verificator, HCoder и Coder, компиляция, симуляция каждого события.
Путь к проекту — аргументом или VSKIT_TEST_VSP; в репозиторий пути
проектов не попадают.

    python tests\\test_project.py "D:\\копия\\Model\\Project.vsp"
    python tests\\test_project.py "D:\\копия\\Model\\Project.vsp" --no-gui

Проект только читается: в начале и в конце сравниваются отпечатки всех
файлов его папки. Замечания Verificator (неиспользуемые элементы,
тупики) печатаются, но провалом не считаются — это свойство модели, а не
набора.
"""
import os
import sys

from _common import OUT, fingerprint, finish, ok, start

vk = start("test_project")
args = [a for a in sys.argv[1:] if not a.startswith("--")]
vsp = args[0] if args else os.environ.get("VSKIT_TEST_VSP")
if not vsp or not os.path.exists(vsp):
    print("укажите путь к .vsp аргументом или в VSKIT_TEST_VSP")
    sys.exit(2)
folder = os.path.dirname(os.path.abspath(vsp))
before = fingerprint(folder)

p = vk.load(vsp)
print(p)
for c in ("hcoder", "classic"):
    rep = vk.full_check(vsp, os.path.join(OUT, "project_gen_" + c),
                        coder_name=c)
    print(rep)
    ok(rep.ok, "%s: схема, API = XML, код, компиляция" % c)

if "--no-gui" not in sys.argv:
    with vk.Simulator(vsp) as s:
        s.deduct("SE_RESET")
        for ev in p.all_elements("events"):
            got = s.deduct(ev.name, *([0] * len(ev.args)))
            print("  %s -> %s" % (ev.name, got))
        ok(True, "Validator принял все %d событий модели"
           % len(p.all_elements("events")))
    ok(not vk.windows(), "окна Validator закрыты")
    d = vk.designer_check(vsp)
    ok(d["ok"], "Designer открывает копию без диалогов")

ok(fingerprint(folder) == before, "папка проекта не изменилась")
finish()
