# -*- coding: utf-8 -*-
"""Проверка .vsp/.vsr по XML-схеме самого Visual State — без запуска
Visual State.

Схемы форматов 1..11 зашиты в программы поставки (Coder.exe, HCoder.exe,
Designer.exe... — блоки `<xs:schema ...>` в теле .exe). schemas()
вырезает их из HCoder.exe в рабочую папку (env.work_root()/xsd/<версия>);
в набор они не кладутся — это файлы IAR. Номер схемы = номер формата:
схема 1 без пространства имён, 2..11 —
http://www.iar.com/visualSTATE/2011/Modelfile.

    errs = validate(r"C:\\модель\\Lamp.vsr")    # [] — файл по схеме
    print(validate_project(r"C:\\модель\\Project.vsp"))

Нужен lxml (ставит tools/setup.ps1). Тот же разбор схемой делают Coder
и HCoder при загрузке: их ошибка «element 'X' is not allowed for content
model '(...)'» — нарушение порядка или состава элементов.
"""
import os
import re

from . import env, model

_CACHE = {}


def _qualify(m):
    """memberTypes без префикса: Xerces (внутри Visual State) их прощает,
    libxml2 (lxml) — нет; добавить 'vs:'."""
    names = [n if b":" in n else b"vs:" + n for n in m.group(1).split()]
    return b'memberTypes="' + b" ".join(names) + b'"'


def schemas():
    """{номер формата: путь к .xsd}, вырезанные из HCoder.exe."""
    if _CACHE:
        return dict(_CACHE)
    folder = os.path.join(env.work_root(), "xsd", env.version())
    os.makedirs(folder, exist_ok=True)
    have = sorted(f for f in os.listdir(folder) if f.endswith(".xsd"))
    if not have:
        with open(env.tool("HCoder"), "rb") as f:
            b = f.read()
        n = 0
        for m in re.finditer(rb"<xs:schema", b):
            s = m.start()
            st = b.rfind(b"<?xml", max(0, s - 400), s)
            e = b.find(b"</xs:schema>", s)
            if e < 0:
                continue
            n += 1
            text = b[st if st >= 0 else s:e + len(b"</xs:schema>")]
            if b'xmlns:vs="' in text:
                text = re.sub(rb'memberTypes="([^"]+)"', _qualify, text)
            with open(os.path.join(folder, "format%02d.xsd" % n), "wb") as f:
                f.write(text)
        have = sorted(f for f in os.listdir(folder) if f.endswith(".xsd"))
    for f in have:
        _CACHE[int(f[6:8])] = os.path.join(folder, f)
    return dict(_CACHE)


def validate(path):
    """Ошибки файла .vsp/.vsr по схеме его формата: ['строка N: текст']."""
    from lxml import etree
    doc = etree.parse(path)
    fmt = int(doc.getroot().get("format", "0") or 0)
    sch = schemas().get(fmt)
    if not sch:
        return ["нет схемы для format %s" % fmt]
    xs = etree.XMLSchema(etree.parse(sch))
    if xs.validate(doc):
        return []
    return ["строка %d: %s" % (e.line, e.message) for e in xs.error_log]


def validate_project(vsp):
    """{файл: [ошибки]} для .vsp и всех его .vsr."""
    p = model.load(vsp)
    out = {vsp: validate(vsp)}
    for m in p.machines():
        out[m.file] = validate(m.file)
    return out
