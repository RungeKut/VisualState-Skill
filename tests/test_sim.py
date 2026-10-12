# -*- coding: utf-8 -*-
"""Симуляция в Validator через Control Center на примере CDPlayer:
последовательность событий -> ожидаемые действия и присваивания;
встречный запрос значения действия; закрытие окон. Открывает окно
Validator на несколько секунд.

    python tests\\test_sim.py
"""
from _common import AV, CD, finish, ok, start

vk = start("test_sim")

with vk.Simulator(CD) as s:
    seq = [
        ("SE_RESET", (), []),
        ("evPowerOnKey", (), [("action", "StartCDPlayer", None)]),
        ("evCDInserted", (1,), []),
        ("evPlayKey", (), [("assign", "lastTrack", 3),
                           ("assign", "currentTrack", 1),
                           ("action", "StartCDDrive", None),
                           ("action", "StartPlayingTrack", None),
                           ("action", "ShowTrackNumber", [1])]),
        ("evTrackEnd", (), [("action", "StopPlayingTrack", None),
                            ("assign", "currentTrack", 2),
                            ("action", "StartPlayingTrack", None),
                            ("action", "ShowTrackNumber", [2])]),
        ("evPowerOffKey", (), None),
    ]
    for ev, args, want in seq:
        got = s.deduct(ev, *args)
        print("  %s%s -> %s" % (ev, args, got))
        if want is not None:
            ok(got == want, "CDPlayer: %s" % ev)
        else:
            ok(("action", "ShutDownCDPlayer", None) in got,
               "CDPlayer: %s вызывает ShutDownCDPlayer" % ev)
ok(not vk.windows(), "Validator закрыт")

asked = []


def find_last(*args):
    asked.append(args)
    return 3


with vk.Simulator(AV, answers={"FindLastTrack": find_last}) as s:
    s.deduct("SE_RESET")
    s.deduct("evPowerKey")
    s.deduct("evDetect", 1)
    got = s.deduct("evPlayKey")
    print("  evPlayKey ->", got)
    ok(asked and ("assign", "lastTrack", 3) in got,
       "AVSystem: значение FindLastTrack() запрошено и подставлено")
ok(not vk.windows(), "Validator закрыт")
finish()
