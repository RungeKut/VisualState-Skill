# -*- coding: utf-8 -*-
"""Общее для сквозных проверок: пути к примерам поставки и к выводу.

Проверки идут на примерах из поставки Visual State (examples/CDPlayer,
examples/AVSystem) — файлы поставки только читаются: vskit работает с
копиями, а проверки сравнивают отпечатки файлов до и после.
"""
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import vskit as vk   # noqa: E402

OUT = os.path.join(ROOT, "tests", "vyvod")
CD = os.path.join(vk.examples_dir(), "CDPlayer", "CDPlayer.vsp")
AV = os.path.join(vk.examples_dir(), "AVSystem", "AVSystem.vsp")
FAILS = []


def start(name):
    vk.utf8_console()
    os.makedirs(OUT, exist_ok=True)
    for p in (CD, AV):
        if not os.path.exists(p):
            print("нет примера поставки: %s" % p)
            sys.exit(2)
    print("== %s   Visual State %s" % (name, vk.version()))
    return vk


def ok(cond, what):
    print(("OK    " if cond else "ОШИБКА") + "  " + what)
    if not cond:
        FAILS.append(what)
    return bool(cond)


def fingerprint(folder):
    """Отпечаток папки: {файл: sha1} — чтобы доказать, что её не трогали."""
    out = {}
    for dp, _dn, fn in os.walk(folder):
        for f in fn:
            p = os.path.join(dp, f)
            try:
                with open(p, "rb") as fh:
                    out[os.path.relpath(p, folder)] = hashlib.sha1(
                        fh.read()).hexdigest()
            except PermissionError:
                out[os.path.relpath(p, folder)] = "нет доступа"
    return out


def finish():
    print("")
    if FAILS:
        print("ПРОВАЛЕНО %d:" % len(FAILS))
        for f in FAILS:
            print("  - " + f)
        sys.exit(1)
    print("Все проверки прошли.")
    sys.exit(0)
