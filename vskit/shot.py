# -*- coding: utf-8 -*-
"""Снимок диаграммы Designer без помехи человеку — на скрытом столе.

    import vskit as vk
    vk.designer_shot(r"C:\\w\\Model.vsp", r"C:\\w\\all.png", zoom=50)
    vk.designer_shot(vsp, r"C:\\w\\sheet3.png", zoom=100,
                     open_path=[0, 0, 0, 0, 0, 3])

Control Center, а за ним Designer запускаются на скрытом рабочем столе
Windows (набор HiddenDesktop-Kit, библиотека hdkit): окон у человека нет,
фокус и мышь его. Окно растягивается до предела, масштаб выбирается в
выпадающем списке Designer (WM_COMMAND), лист региона (offPage) открывается
двойным кликом по узлу дерева проекта (PostMessage), снимок — PrintWindow.
Работает над КОПИЕЙ модели.

open_path — путь по дереву проекта: [0] — проект, дальше номера потомков:
система, автомат, регион, верхнее состояние, его регион (лист).
[0, 0, 0, 0, 0, k] — лист k-го региона верхнего состояния.

Проверено: knowledge/20_ПРИЁМЫ/20-05, 30_ГРАБЛИ/30-10. Правила работы со
скрытым столом, ловушки и приёмы — база HiddenDesktop-Kit.
"""
import os
import sys
import time

from . import coder as _coder
from . import env
from . import sim

ZOOM_CTRL_ID = 33054
SB_PAGEDOWN = 3


class ShotError(RuntimeError):
    pass


def _hdkit():
    cands = [os.environ.get("HDKIT_HOME", "")]
    for agent in (".claude", ".kimi-code"):
        link = os.path.join(os.path.expanduser("~"), agent, "skills",
                            "hidden-desktop")
        if os.path.isdir(link):
            cands.append(os.path.dirname(os.path.realpath(link)))
    for c in cands:
        if c and os.path.isdir(os.path.join(c, "hdkit")):
            if c not in sys.path:
                sys.path.insert(0, c)
            import hdkit
            return hdkit
    raise ShotError("набор HiddenDesktop-Kit не найден: задайте HDKIT_HOME "
                    "(tools/setup.ps1 набора)")


def _tree(main):
    for t in main.find_all(cls="SysTreeView32"):
        if t.visible and t.rect[2] > 100:
            return t
    raise ShotError("в Designer не найдено видимое дерево проекта")


def designer_shot(vsp, out, zoom=50, open_path=None, size=None, wait=25.0,
                  scroll_pages=0, settle=1.5):
    """Снять окно Designer с моделью vsp в файл out (PNG).

    zoom — масштаб из списка Designer: 5, 10, 25, 50, 75, 100, 200 … (%);
    open_path — путь к листу (см. модуль); size — (ширина, высота), по
    умолчанию предел окна; scroll_pages — на сколько страниц вниз
    прокрутить диаграмму. Возвращает dict: path, size, blank, title."""
    hd = _hdkit()
    from hdkit import HiddenDesktop, controls, max_window_size
    src = os.path.abspath(vsp)
    stem = os.path.splitext(os.path.basename(src))[0]
    job = env.job_dir("shot")
    wvsp = _coder.copy_model(src, os.path.join(job, "model"))
    path = wvsp.replace("\\", "/")
    with HiddenDesktop() as d:
        cc = sim.ControlCenter(timeout=120, desktop=d).start()
        try:
            if cc.call("launchDesigner", {"projectPath": path}) is not True:
                raise ShotError("launchDesigner не вернул true")
            main = d.wait_window(title=stem, timeout=wait,
                                 min_size=(600, 400))
            w, h = size or max_window_size()
            main.set_rect(0, 0, w, h)
            time.sleep(settle + 1.0)
            bad = [t for t in d.dialogs()]
            if bad:
                raise ShotError("диалоги мешают: %s" % bad)
            if open_path:
                controls.tree_open(_tree(main).hwnd, open_path)
                time.sleep(2.0)
            mdi = main.find(cls="MDIClient")
            if mdi is not None and mdi.children():
                doc = mdi.children()[0]
                cw, ch = mdi.client_size
                doc.set_rect(0, 0, cw, ch)
                time.sleep(1.0)
            combo = None
            for c in main.find_all(cls="ComboBox", ctrl_id=ZOOM_CTRL_ID):
                combo = c
            if combo is not None and zoom:
                items = controls.combo_items(combo.hwnd)
                want = "%d %%" % int(zoom)
                if want not in items:
                    raise ShotError("масштаба %s нет в списке: %s"
                                    % (want, items))
                controls.combo_select(combo.hwnd, items.index(want))
                time.sleep(1.5)
            if scroll_pages and mdi is not None and mdi.children():
                controls.scroll(mdi.children()[0].hwnd, SB_PAGEDOWN,
                                times=int(scroll_pages))
                time.sleep(1.0)
            img = main.capture()
            img.save(out)
            return {"path": out, "size": img.size, "blank": img.is_blank(),
                    "title": main.title}
        finally:
            try:
                cc.call("quitDesigner", {"projectPath": path})
            except Exception:
                pass
            time.sleep(0.5)
            cc.stop()
