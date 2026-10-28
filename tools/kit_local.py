# -*- coding: utf-8 -*-
"""Особое VisualState-Skill в общей проверке skill-skill/tools/check_docs.py.

С --project к стоп-словам добавляются имена файлов .vsp/.vsr проекта и
имена из самих моделей Visual State: системы, автоматы, состояния,
события, действия, переменные (целиком, от 5 символов, кроме служебных
вида initial1, Region1) — knowledge/40_СРЕДА/40-02.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GENERIC = {"vsproject", "topstate"}
PROJECT_EXT = (".vsp", ".vsr")
SERVICE = re.compile(r"^(initial|final|history|deephistory|choice|region|"
                     r"system|topstate|state|project|toplevelstatemachine|"
                     r"_?initialstate|_?shallowhistorystate)\d*$", re.I)


def model_names(vsp):
    """Имена из модели Visual State: системы, автоматы, вершины, элементы."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    try:
        from vskit import model
        p = model.load(vsp)
    except Exception:
        return set()
    names = {s.name for s in p.systems}
    for m in p.machines():
        names.add(m.name)
        names |= {v.name for v in m.vertices()}
        for items in m.elements.values():
            names |= {e.name for e in items}
    return {n for n in names if n and len(n) >= 5 and not SERVICE.match(n)
            and n.lower() not in GENERIC}


def project_words(project_dir):
    out = set()
    for dp, dn, fn in os.walk(project_dir):
        dn[:] = [d for d in dn if not d.startswith(".")]
        for f in fn:
            if f.lower().endswith(".vsp"):
                out |= model_names(os.path.join(dp, f))
    return out
