# -*- coding: utf-8 -*-
"""IAR State Machine API (StateMachineAPI64.dll) через ctypes — второй,
независимый от vskit.model способ прочитать модель, и пересохранение
модели в текущий формат.

API — C-библиотека из поставки (doc/StateMachineAPI: заголовок и HTML);
по документации лицензии не требует. Все функции возвращают 1 при успехе
и 0 при ошибке; текст ошибки — VSMGetErrorStringPtr.

    inv = inventory(r"C:\\модель\\Project.vsp")   # системы, вершины, переходы
    normalize(r"C:\\модель\\Project.vsp", r"C:\\копия")   # -> format 11

ОПАСНО: VSMProjectSave(путь, проект) пишет .vsp по новому пути, а файлы
.vsr — НА ИХ СТАРОЕ МЕСТО, со ссылкой на них из нового .vsp. Поэтому
normalize() сначала копирует модель и сохраняет копию в неё же
(knowledge/30_ГРАБЛИ/30-03).
"""
import ctypes
import os

from . import coder as _coder
from . import env

H = ctypes.c_size_t
_DLL = None


class ApiError(RuntimeError):
    pass


def dll():
    """Загруженная StateMachineAPI64.dll (один раз на процесс)."""
    global _DLL
    if _DLL is None:
        os.add_dll_directory(env.bin_dir())
        _DLL = ctypes.CDLL(env.tool("StateMachineAPI64.dll"))
    return _DLL


def _err():
    p = ctypes.c_char_p()
    dll().VSMGetErrorStringPtr(ctypes.byref(p))
    return (p.value or b"").decode("utf-8", "replace")


def _call(name, *args):
    if getattr(dll(), name)(*args) != 1:
        raise ApiError("%s: %s" % (name, _err()))


def api_version():
    v = ctypes.c_int()
    _call("VSMGetStateMachineAPIVersion", ctypes.byref(v))
    return v.value


def _str(fn, h):
    p = ctypes.c_char_p()
    if getattr(dll(), fn)(h, ctypes.byref(p)) != 1:
        return None
    return (p.value or b"").decode("utf-8", "replace")


def _handles(fn, owner):
    out = []
    n = 0
    while True:
        h = H()
        if getattr(dll(), fn)(owner, n, ctypes.byref(h)) != 1:
            return out
        out.append(h.value)
        n += 1


def load(vsp):
    """Хэндл проекта. Строки API — UTF-8, пути тоже: путь в ANSI (cp1251)
    с кириллицей API не находит — «is not a project file» (30-03)."""
    h = H()
    _call("VSMProjectLoad", os.path.abspath(vsp).encode("utf-8"),
          ctypes.byref(h))
    return h.value


def unload(h):
    dll().VSMProjectRemove(H(h))


def inventory(vsp):
    """Что видит API: {'systems': {система: [автоматы]}, 'vertices':
    [пути 'Автомат.Состояние.Под'], 'external': n, 'internal': n}."""
    hp = load(vsp)
    try:
        out = {"systems": {}, "vertices": [], "external": 0, "internal": 0}
        for hs in _handles("VSMSystemGetHandle", H(hp)):
            sname = _str("VSMSystemGetName", H(hs))
            tops = []
            for ht in _handles("VSMTopstateGetHandle", H(hs)):
                tname = _str("VSMVertexGetName", H(ht))
                tops.append(tname)
                _walk(H(ht), "", out)
            out["systems"][sname] = tops
        return out
    finally:
        unload(hp)


def _walk(hv, prefix, out):
    for hr in _handles("VSMRegionGetHandle", hv):
        for hx in _handles("VSMVertexGetHandle", H(hr)):
            name = _str("VSMVertexGetName", H(hx))
            path = prefix + name
            out["vertices"].append(path)
            out["external"] += len(_handles("VSMExternalTransitionGetHandle",
                                            H(hx)))
            out["internal"] += len(_handles("VSMInternalTransitionGetHandle",
                                            H(hx)))
            _walk(H(hx), path + ".", out)


def normalize(vsp, dst):
    """Копия модели в dst, пересохранённая API в текущий формат (11).
    Оригинал не трогается. Возвращает путь к новому .vsp."""
    wvsp = _coder.copy_model(vsp, dst)
    hp = load(wvsp)
    try:
        _call("VSMProjectSave", wvsp.encode("utf-8"), H(hp))
    finally:
        unload(hp)
    return wvsp
