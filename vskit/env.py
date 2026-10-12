# -*- coding: utf-8 -*-
"""Окружение: где стоит IAR Visual State, где работать, где компилятор.

Пути ищутся, а не зашиваются. Порядок поиска:

    Visual State  VSKIT_VSROOT -> <Program Files (x86)>\\IAR Systems\\
                  Visual State * (самая свежая)
    рабочая папка VSKIT_WORK -> %LOCALAPPDATA%\\Temp\\vskit ->
                  %SystemDrive%\\vskit_work (первая без пробелов и кириллицы)
    GCC           VSKIT_GCC (папка bin) -> mcukit.gcc_bin() из MCU-Kit
                  (MCUKIT_HOME, затем E:\\Skills\\MCU-Kit) ->
                  arm-none-eabi-gcc в PATH

Coder и HCoder переносят кириллицу и пробелы в пути (проверено), но набор
всё равно работает над копией модели в рабочей папке: инструменты пишут
рядом с проектом отчёты, а StateMachineAPI переписывает .vsr на месте
(knowledge/30_ГРАБЛИ/30-03).
"""
import glob
import io
import os
import re
import shutil
import subprocess
import sys
import time


def utf8_console():
    """Перевести stdout/stderr в UTF-8, иначе print с кириллицей падает."""
    for name in ("stdout", "stderr"):
        s = getattr(sys, name)
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            setattr(sys, name, io.TextIOWrapper(s.buffer, encoding="utf-8",
                                                errors="replace"))


def kit_root():
    """Корень набора (папка, где лежат vskit/, knowledge/, skill/)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ver_key(path):
    return [int(x) for x in re.findall(r"\d+", path)] + [path]


def _pf():
    out = []
    for var in ("ProgramFiles(x86)", "ProgramFiles", "ProgramW6432"):
        v = os.environ.get(var)
        if v and v not in out:
            out.append(v)
    return out or [r"C:\Program Files (x86)", r"C:\Program Files"]


def vs_root():
    """Папка установки IAR Visual State (в ней bin64, doc, examples)."""
    v = os.environ.get("VSKIT_VSROOT")
    if v and os.path.exists(os.path.join(v, "bin64", "Coder.exe")):
        return os.path.normpath(v)
    found = []
    for pf in _pf():
        found += glob.glob(os.path.join(pf, "IAR Systems", "Visual State*",
                                        "bin64", "Coder.exe"))
    if found:
        return os.path.dirname(os.path.dirname(sorted(found,
                                                      key=_ver_key)[-1]))
    raise RuntimeError("IAR Visual State не найден. Установите его или "
                       "задайте VSKIT_VSROOT — папку, где лежит bin64.")


def bin_dir():
    """Папка с 64-битными программами Visual State."""
    return os.path.join(vs_root(), "bin64")


def tool(name):
    """Полный путь к программе Visual State: 'Coder', 'HCoder.exe'..."""
    if not name.lower().endswith((".exe", ".dll")):
        name += ".exe"
    p = os.path.join(bin_dir(), name)
    if not os.path.exists(p):
        raise RuntimeError("нет %s в %s" % (name, bin_dir()))
    return p


def examples_dir():
    """Папка примеров поставки (только читать: работать над копией)."""
    return os.path.join(vs_root(), "examples")


def _run(cmd, cwd=None, timeout=120):
    r = subprocess.run(cmd, capture_output=True, timeout=timeout, cwd=cwd)
    return (r.returncode, r.stdout.decode("cp1251", "replace"),
            r.stderr.decode("cp1251", "replace"))


_VERSION = None


def version():
    """Версия Visual State по заголовку Coder.exe, например '9.1.1.3863'.

    Coder.exe без аргументов печатает справку и выходит; окна не открывает.
    """
    global _VERSION
    if _VERSION is None:
        _rc, out, _err = _run([tool("Coder")], timeout=30)
        m = re.search(r"Coder\s+(\d+),\s*(\d+),\s*(\d+),\s*(\d+)", out)
        _VERSION = ".".join(m.groups()) if m else "?"
    return _VERSION


def license_ok():
    """Есть ли лицензия: (True/False, текст ответа).

    `Coder.exe --license_check_only` возвращает код 1 и тогда, когда
    лицензия найдена, — решает только строка «Found a ... license»
    (knowledge/30_ГРАБЛИ/30-01).
    """
    rc, out, err = _run([tool("Coder"), "--license_check_only"], timeout=60)
    text = (out + err).strip()
    return ("Found a IAR Visual State license" in text), text


def is_safe_path(path):
    """Путь только из ASCII и без пробелов."""
    try:
        path.encode("ascii")
    except UnicodeEncodeError:
        return False
    return " " not in path


def work_root():
    """Корень рабочих папок заданий (без пробелов и кириллицы)."""
    cands = []
    if os.environ.get("VSKIT_WORK"):
        cands.append(os.environ["VSKIT_WORK"])
    la = os.environ.get("LOCALAPPDATA")
    if la:
        cands.append(os.path.join(la, "Temp", "vskit"))
    cands.append(os.path.join(os.environ.get("SystemDrive", "C:") + "\\",
                              "vskit_work"))
    for c in cands:
        c = os.path.normpath(c)
        if is_safe_path(c):
            os.makedirs(c, exist_ok=True)
            return c
    raise RuntimeError("не нашлось рабочей папки без пробелов и кириллицы; "
                       "задайте VSKIT_WORK")


_JOB = re.compile(r"^[a-z]+-\d{8}-\d{6}-\d{3}$")


def job_dir(kind="job", keep=20):
    """Новая папка задания в work_root(); старые задания того же вида
    сверх `keep` удаляются."""
    root = work_root()
    t = time.time()
    name = "%s-%s-%03d" % (kind, time.strftime("%Y%m%d-%H%M%S",
                                              time.localtime(t)),
                           int((t % 1) * 1000))
    path = os.path.join(root, name)
    os.makedirs(path)
    old = sorted(d for d in os.listdir(root)
                 if _JOB.match(d) and d.startswith(kind + "-"))
    for d in old[:-keep] if keep else []:
        shutil.rmtree(os.path.join(root, d), ignore_errors=True)
    return path


def _mcukit():
    for root in (os.environ.get("MCUKIT_HOME"), r"E:\Skills\MCU-Kit"):
        if root and os.path.exists(os.path.join(root, "mcukit", "env.py")):
            if root not in sys.path:
                sys.path.insert(0, root)
            import mcukit
            return mcukit
    return None


def gcc_bin():
    """Папка с arm-none-eabi-gcc.exe (с завершающим разделителем)."""
    v = os.environ.get("VSKIT_GCC")
    if v and os.path.exists(os.path.join(v, "arm-none-eabi-gcc.exe")):
        return os.path.normpath(v) + os.sep
    mk = _mcukit()
    if mk is not None:
        try:
            return mk.gcc_bin()
        except RuntimeError:
            pass
    w = shutil.which("arm-none-eabi-gcc")
    if w:
        return os.path.dirname(w) + os.sep
    raise RuntimeError("arm-none-eabi-gcc не найден: задайте VSKIT_GCC "
                       "(папку bin) или поставьте MCU-Kit (MCUKIT_HOME).")


def gcc_tool(name):
    """Полный путь к утилите тулчейна: 'gcc', 'nm', 'size'."""
    return gcc_bin() + "arm-none-eabi-" + name + ".exe"


def gcc_version():
    """Версия arm-none-eabi-gcc строкой, например '10.3.1'."""
    _rc, out, _err = _run([gcc_tool("gcc"), "--version"], timeout=30)
    m = re.search(r"\)\s+(\d+\.\d+\.\d+)", out)
    return m.group(1) if m else (out.splitlines() or ["?"])[0]
