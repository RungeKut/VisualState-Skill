# -*- coding: utf-8 -*-
"""Validator и Designer из скрипта — через Control Center
(ControlCenter.exe, JSON-RPC 2.0 поверх TCP).

Пошаговая симуляция:

    with Simulator(r"C:\\модель\\Project.vsp") as s:
        s.deduct("SE_RESET")
        print(s.deduct("evPowerOn"))      # [('action', 'StartX', None), ...]
        s.deduct("evData", 5)             # аргументы события

Проверка, что Designer открывает модель (например, сгенерированную
vskit.design) без окон с вопросами:

    print(designer_check(r"C:\\модель\\Project.vsp"))

Что происходит: запускается ControlCenter.exe на свободном порту, ему
шлётся launchValidator (launchDesigner) с путём к КОПИИ проекта, затем
deductEvent на каждое событие. Ответ — список вызванных действий и
присваиваний в порядке выполнения. Если модели нужно значение, которое
возвращает действие (действие в guard или справа от присваивания),
Validator шлёт встречный запрос getActionFunctionCallResult; ответ
берётся из answers ({имя действия: значение или функция(*args)}), иначе 0.

Validator и Designer открывают свои окна и закрываются в конце через
quitValidator/quitDesigner без вопроса о сохранении. Окна видны на экране
человека, если не передать ControlCenter(desktop=HiddenDesktop()) из набора
HiddenDesktop-Kit: тогда Control Center, а за ним Designer/Validator живут
на скрытом рабочем столе (vskit.shot, knowledge/20_ПРИЁМЫ/20-05).

Проверенные правила (knowledge/10_API/10-04, 30_ГРАБЛИ/30-06):
  * каждое сообщение кончается переводом строки — без него Control
    Center молчит, ответ не приходит никогда;
  * неизвестное имя события — ответа нет вообще (ни ошибки, ни окна):
    имя сверяется с моделью ДО отправки;
  * Control Center слушает порт без проверки клиента — держать его
    запущенным только на время работы.
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import re
import socket
import subprocess
import time

from . import coder as _coder
from . import env
from . import model


class SimError(RuntimeError):
    pass


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def windows(exe_names=("Validator.exe", "Designer.exe")):
    """Видимые окна процессов Visual State: [(pid, класс, заголовок,
    [тексты дочерних окон])]. Окно-диалог — класс '#32770'."""
    u = ctypes.windll.user32
    k = ctypes.windll.kernel32
    out = []
    names = {n.lower() for n in exe_names}

    def exe_of(pid):
        h = k.OpenProcess(0x1000, False, pid)
        if not h:
            return ""
        buf = ctypes.create_unicode_buffer(1024)
        size = wt.DWORD(1024)
        ok = k.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
        k.CloseHandle(h)
        return os.path.basename(buf.value) if ok else ""

    def text(h):
        b = ctypes.create_unicode_buffer(1024)
        u.GetWindowTextW(h, b, 1024)
        return b.value

    def cls(h):
        b = ctypes.create_unicode_buffer(256)
        u.GetClassNameW(h, b, 256)
        return b.value

    proto = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def top(h, _l):
        if not u.IsWindowVisible(h):
            return True
        pid = wt.DWORD()
        u.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if exe_of(pid.value).lower() not in names:
            return True
        kids = []

        def child(c, _l2):
            t = text(c)
            if t:
                kids.append(t)
            return True

        if cls(h) == "#32770":
            u.EnumChildWindows(h, proto(child), 0)
        out.append((pid.value, cls(h), text(h), kids))
        return True

    u.EnumWindows(proto(top), 0)
    return out


VWS = """[Header]
Filetype=visualSTATE Validator workspace
Revision=3
[ProjectSetup]
ProjectFile=%s
IncludeExcluded=FALSE
AutoQueue=FALSE
TimerMsg=TRUE
PromptActions=FALSE
"""


def ensure_vws(vsp):
    """Рабочая область Validator рядом с КОПИЕЙ проекта: <проект>.vws с
    `IncludeExcluded=FALSE` в [ProjectSetup]. Нет файла или нет этого
    ключа (так у примера AVSystem) — Validator при загрузке открывает
    модальный вопрос «Include excluded items» и не загружает проект, пока
    человек не ответит (30-06). Существующие .vws дополняются ключом."""
    folder = os.path.dirname(vsp)
    found = [os.path.join(folder, f) for f in os.listdir(folder)
             if f.lower().endswith(".vws")]
    if not found:
        path = os.path.splitext(vsp)[0] + ".vws"
        with open(path, "w", encoding="ascii", newline="\r\n") as f:
            f.write(VWS % os.path.basename(vsp))
        return [path]
    for path in found:
        with open(path, encoding="latin-1") as f:
            text = f.read()
        if re.search(r"^IncludeExcluded=", text, re.M):
            continue
        text = re.sub(r"(^\[ProjectSetup\][^\n]*\n)",
                      r"\1IncludeExcluded=FALSE\n", text, count=1,
                      flags=re.M)
        if "IncludeExcluded=" not in text:
            text += "\n[ProjectSetup]\nIncludeExcluded=FALSE\n"
        with open(path, "w", encoding="latin-1", newline="") as f:
            f.write(text)
    return found


class ControlCenter:
    """Соединение с ControlCenter.exe, запущенным на время работы."""

    def __init__(self, timeout=30, answers=None, desktop=None):
        self.timeout = timeout
        self.answers = dict(answers or {})
        self.desktop = desktop
        self.trace = []
        self._proc = None
        self._sock = None
        self._buf = b""
        self._id = 100

    def start(self):
        self.port = _free_port()
        cmd = [env.tool("ControlCenter"), "-port%d" % self.port]
        if self.desktop is not None:
            self._proc = self.desktop.launch(cmd)
        else:
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        t = time.time()
        while True:
            try:
                self._sock = socket.create_connection(("127.0.0.1",
                                                       self.port), timeout=2)
                break
            except OSError:
                gone = (not self._proc.running if self.desktop is not None
                        else self._proc.poll() is not None)
                if time.time() - t > 20 or gone:
                    self.stop()
                    raise SimError("Control Center не принял соединение")
                time.sleep(0.3)
        self._sock.settimeout(self.timeout)
        return self

    def _send(self, obj):
        self._sock.sendall(json.dumps(obj).encode("utf-8") + b"\r\n")

    def _recv(self):
        dec = json.JSONDecoder()
        while True:
            text = self._buf.decode("utf-8", "replace").lstrip()
            if text:
                try:
                    obj, n = dec.raw_decode(text)
                    self._buf = text[n:].encode("utf-8")
                    return obj
                except ValueError:
                    pass
            try:
                chunk = self._sock.recv(65536)
            except socket.timeout:
                raise SimError("нет ответа %d с (неизвестное событие? "
                               "окно ждёт человека? — vskit.windows())"
                               % self.timeout)
            if not chunk:
                raise SimError("Control Center закрыл соединение")
            self._buf += chunk

    def call(self, method, params=None):
        """Один запрос JSON-RPC; встречные getActionFunctionCallResult
        обслуживаются по answers. Возвращает result."""
        self._id += 1
        msg = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            msg["params"] = params
        self._send(msg)
        while True:
            r = self._recv()
            if r.get("method") == "getActionFunctionCallResult":
                act = r.get("params", {}).get("action", {})
                name = act.get("actionName")
                args = act.get("actionArguments") or []
                a = self.answers.get(name, 0)
                val = a(*args) if callable(a) else a
                self.trace.append(("ask", name, args, val))
                self._send({"jsonrpc": "2.0", "id": r.get("id"),
                            "result": val})
                continue
            if "error" in r:
                raise SimError("%s: %s" % (method, r["error"]))
            return r.get("result")

    def stop(self):
        try:
            if self._sock is not None:
                try:
                    self.call("quit", {"all": True})
                except Exception:
                    pass
                self._sock.close()
        finally:
            self._sock = None
            if self._proc is not None:
                if self.desktop is not None:
                    t0 = time.time()
                    while self._proc.running and time.time() - t0 < 5:
                        time.sleep(0.1)
                    self._proc.terminate()
                else:
                    try:
                        self._proc.wait(5)
                    except subprocess.TimeoutExpired:
                        self._proc.kill()
                self._proc = None


class Simulator:
    """Validator под управлением скрипта. Работает над копией модели.
    desktop=HiddenDesktop() (HiddenDesktop-Kit) — окна Validator на скрытом
    столе, у человека их нет."""

    def __init__(self, vsp, answers=None, timeout=30, lookahead=False,
                 desktop=None):
        self.src = os.path.abspath(vsp)
        self.lookahead = lookahead
        self.cc = ControlCenter(timeout, answers, desktop)
        p = model.load(self.src)
        self.events = set(p.names("events")) | set(p.names("signals")) | \
            {"SE_RESET"}

    @property
    def trace(self):
        return self.cc.trace

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()

    def start(self):
        job = env.job_dir("sim")
        self.vsp = _coder.copy_model(self.src, os.path.join(job, "model"))
        ensure_vws(self.vsp)
        self._path = self.vsp.replace("\\", "/")
        self.cc.start()
        try:
            if self.cc.call("launchValidator",
                            {"projectPath": self._path}) is not True:
                raise SimError("launchValidator не вернул true")
            if not self.lookahead:
                self.cc.call("disableLookAheadGuardCheck",
                             {"projectPath": self._path, "disable": True})
        except Exception:
            self.stop()
            raise
        return self

    def deduct(self, event, *args):
        """Подать событие. Возвращает [(вид, имя, значение)]: ('action',
        имя, аргументы) или ('assign', переменная[индекс], значение)."""
        if event not in self.events:
            raise SimError("события %r нет в модели — Validator на такое "
                           "не отвечает вовсе (30-06)" % event)
        prm = {"projectPath": self._path, "eventName": event}
        if args:
            prm["eventArguments"] = list(args)
        res = self.cc.call("deductEvent", prm) or {}
        if not isinstance(res, dict):
            dialogs = [w for w in windows(("Validator.exe",))
                       if w[1] == "#32770"]
            raise SimError("Validator ответил %r; окна-диалоги: %s"
                           % (res, dialogs or "нет"))
        out = []
        for item in res.get("actions") or []:
            if "action" in item:
                a = item["action"]
                out.append(("action", a.get("actionName"),
                            a.get("actionArguments")))
            elif "assignment" in item:
                a = item["assignment"]
                name = a.get("assignedTo")
                if a.get("assignedToIndex") is not None:
                    name += "[%s]" % a["assignedToIndex"]
                out.append(("assign", name, a.get("value")))
            else:
                out.append(("other", json.dumps(item), None))
        self.cc.trace.append(("event", event, list(args), out))
        return out

    def stop(self):
        if self.cc._sock is not None:
            try:
                self.cc.call("quitValidator", {"projectPath": self._path})
            except Exception:
                pass
        self.cc.stop()


def designer_check(vsp, wait=8.0, save=False):
    """Открыть КОПИЮ модели в Designer и закрыть.

    save=True — перед закрытием сохранить копию самим Designer
    (saveDesigner): так видно, что Designer принял модель целиком —
    сохранённую копию можно разобрать vskit.load и сравнить.
    Возвращает {'ok': bool, 'result': ответ launchDesigner, 'windows':
    окна Designer через wait секунд, 'vsp': путь к копии}. ok — ответ
    true и нет окон-диалогов (#32770)."""
    src = os.path.abspath(vsp)
    job = env.job_dir("designer")
    wvsp = _coder.copy_model(src, os.path.join(job, "model"))
    path = wvsp.replace("\\", "/")
    cc = ControlCenter(timeout=120).start()
    saved = None
    try:
        res = cc.call("launchDesigner", {"projectPath": path})
        time.sleep(wait)
        wins = windows(("Designer.exe",))
        if save:
            saved = cc.call("saveDesigner", {"projectPath": path})
        try:
            cc.call("quitDesigner", {"projectPath": path})
        except SimError:
            pass
    finally:
        cc.stop()
    dialogs = [w for w in wins if w[1] == "#32770"]
    return {"ok": res is True and not dialogs and saved in (None, True),
            "result": res, "saved": saved, "windows": wins, "vsp": wvsp}
