# -*- coding: utf-8 -*-
"""Описание автомата — единственный файл, который правит человек.

Отвлечённый пример: кнопка с антидребезгом и долгим нажатием. Таймеры и
опрос вывода живут в коде пользователя: он присылает события evPress,
evRelease, evTimeout и реализует действия.

Правила описания — knowledge/20_ПРИЁМЫ/20-02.
"""
PROJECT = "ButtonProject"
SYSTEM = "ButtonSys"


def build(vk):
    m = vk.Machine("Button", expl="кнопка: короткое и долгое нажатие")
    m.event("evPress", expl="вывод кнопки перешёл в нажатое")
    m.event("evRelease", expl="вывод кнопки перешёл в отпущенное")
    m.event("evTimeout", expl="истёк таймер, запущенный TimerStart")
    m.action("TimerStart", ("ms", "VS_UINT16"))
    m.action("TimerStop")
    m.action("ReportShort")
    m.action("ReportLong")
    m.const("DEBOUNCE_MS", "VS_UINT16", 20)
    m.const("LONG_MS", "VS_UINT16", 800)

    m.state("Idle")
    m.state("Debounce", entry="TimerStart(DEBOUNCE_MS)", exit="TimerStop()")
    m.state("Pressed", entry="TimerStart(LONG_MS)", exit="TimerStop()")
    m.state("Held")
    m.initial("Idle")

    m.trans("Idle", "Debounce", "evPress")
    m.trans("Debounce", "Idle", "evRelease")
    m.trans("Debounce", "Pressed", "evTimeout")
    m.trans("Pressed", "Idle", "evRelease", do="ReportShort()")
    m.trans("Pressed", "Held", "evTimeout", do="ReportLong()")
    m.trans("Held", "Idle", "evRelease")

    p = vk.Project(PROJECT)
    p.add_system(SYSTEM, m)
    return p


SCENARIO = [
    ("SE_RESET", (), []),
    ("evPress", (), [("action", "TimerStart", [20])]),
    ("evTimeout", (), [("action", "TimerStop", None),
                       ("action", "TimerStart", [800])]),
    ("evRelease", (), [("action", "TimerStop", None),
                       ("action", "ReportShort", None)]),
]
