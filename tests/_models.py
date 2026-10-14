# -*- coding: utf-8 -*-
"""Учебные модели для проверок раскладки и снимков: отвлечённое устройство."""


def gadget(vk):
    m = vk.Machine("Gadget")
    for e in ("evKey", "evTick", "evStop", "evMode"):
        m.event(e)
    for a in ("Beep", "Show", "Hide", "Log"):
        m.action(a)
    m.action("Pick", ("v", "VS_UINT8"))
    m.var("n", "VS_UINT8", 0, lo=0, hi=9)
    m.var("flag", "VS_BOOL", 0)
    m.state("Top")
    m.initial("Top")
    R1, R2 = "Linear", "Ring"
    m.state("Top.Idle", region=R1)
    m.state("Top.Gather", region=R1, exit="Hide()")
    m.state("Top.Held", region=R1)
    m.initial("Top.Idle", region=R1)
    m.trans("Top.Idle", "Top.Gather", "evKey", do=["n = 1", "Show()"])
    m.internal("Top.Gather", "evTick", guard="n < 4", do="n = n + 1")
    c1 = m.choice("Top", region=R1)
    c2 = m.choice("Top", region=R1)
    m.trans("Top.Gather", c1, "evStop", do="flag = 1")
    m.trans(c1, c2, None, guard="flag", do="Beep()")
    m.trans(c1, c2, None, otherwise=True, do="Log()")
    m.trans(c2, "Top.Idle", None, guard="n > 2")
    m.trans(c2, "Top.Held", None, otherwise=True)
    m.trans("Top.Held", "Top.Idle", "evKey")
    names = ("One", "Two", "Three", "Four")
    for i, s in enumerate(names):
        m.state("Top." + s, region=R2, entry="Pick(%d)" % i)
    m.initial("Top.One", region=R2)
    for i, s in enumerate(names):
        m.trans("Top." + s, "Top." + names[(i + 1) % 4], "evMode",
                guard="n == %d" % i, do="Show()")
    m.trans("Top.Three", "Top.One", "evStop")
    return m
