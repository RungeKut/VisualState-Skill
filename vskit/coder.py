# -*- coding: utf-8 -*-
"""Генерация кода: Coder.exe (классический) и HCoder.exe (иерархический)
из командной строки, над копией проекта.

    r = generate(r"C:\\модель\\Project.vsp", r"C:\\проект\\vs_gen")
    r.check()          # ошибки модели -> CoderError с текстом Coder
    print(r)           # код возврата, ошибки, предупреждения, файлы

Порядок: файлы модели (.vsp, .vsr, .vtg, .vnw...) копируются в папку
задания, Coder запускается там с `-path<задание>\\out\\`, результат
копируется в out_dir. Оригинал модели и out_dir до копирования не
трогаются.

Ключи — словарём options: {"readable": 1, "D": 2} -> `-readable1 -D2`
(Coder пишет значение ВПРИТЫК к ключу). Системные ключи (-H, -S,
-apiprefix...) — через systems={"Sys": {"apiprefix": "Sys_"}}.
use_vtg=True добавляет `--l`: взять ключи, сохранённые в .vtg из
Navigator. Полный список ключей — options_help().

Имя системы, совпадающее с именем проекта, ломает код молча: файлы
проекта и системы называются одинаково, и один затирает другой при коде 0
(knowledge/30_ГРАБЛИ/30-02). generate() в этом случае сам задаёт
-projectheader/-projectsource = <проект>_prj.h/.c и пишет об этом в notes.
"""
import os
import re
import shutil
import subprocess
import time

from . import env
from . import model

MODEL_EXT = (".vsp", ".vsr", ".vtg", ".vnw", ".vws", ".stereotypes", ".vdi",
             ".vssm")


class CoderError(RuntimeError):
    pass


class CoderResult:
    def __init__(self, coder, cmd, rc, log, out_dir, files, report,
                 notes, seconds):
        self.coder = coder
        self.cmd = cmd
        self.rc = rc
        self.log = log
        self.out_dir = out_dir
        self.files = files
        self.report = report
        self.notes = notes
        self.seconds = seconds
        m = re.search(r"completed\s*-\s*(\d+)\s*error\(s\),\s*(\d+)\s*"
                      r"warning\(s\)", log)
        self.errors = int(m.group(1)) if m else None
        self.warnings = int(m.group(2)) if m else None
        self.messages = [l.strip() for l in log.splitlines()
                         if l.strip() and not _banner(l)]

    @property
    def ok(self):
        """Успех — код 0, строка «completed - 0 error(s)» и есть .c."""
        return (self.rc == 0 and self.errors == 0 and
                any(f.endswith((".c", ".cpp")) for f in self.files))

    def check(self):
        if not self.ok:
            raise CoderError("%s: код %s, ошибок %s\n%s" % (
                self.coder, self.rc, self.errors, "\n".join(self.messages)))
        return self

    def sources(self):
        return [os.path.join(self.out_dir, f) for f in self.files
                if f.endswith((".c", ".cpp"))]

    def __repr__(self):
        lines = ["%s: код %s, ошибок %s, предупреждений %s, %.1f с" % (
            self.coder, self.rc, self.errors, self.warnings, self.seconds)]
        lines += ["  " + m for m in self.messages]
        lines += ["  примечание: " + n for n in self.notes]
        lines.append("  файлы в %s: %s" % (self.out_dir, ", ".join(
            self.files)))
        return "\n".join(lines)


_BANNER = ("IAR Visual State", "Connecting to IAR Visual State license",
           "Found a IAR Visual State license", "Generating common files",
           "Generating files for", "Loading Project", "Building intermediate",
           "Copyright")


def _banner(line):
    s = line.strip()
    return any(s.startswith(b) or b in s for b in _BANNER) or \
        re.search(r"completed\s*-\s*0 error", s) is not None


def options_help(coder="hcoder"):
    """Справка по ключам: Coder/HCoder без аргументов печатают её и
    выходят (окна не открывают)."""
    exe = env.tool("HCoder" if coder == "hcoder" else "Coder")
    r = subprocess.run([exe], capture_output=True, timeout=60)
    return r.stdout.decode("cp1251", "replace")


def copy_model(vsp, dst):
    """Скопировать файлы модели проекта (все .vsp/.vsr/.vtg/... в папке
    проекта и .vsr, на которые он ссылается) в dst. Возвращает путь к
    копии .vsp."""
    src = os.path.dirname(os.path.abspath(vsp))
    os.makedirs(dst, exist_ok=True)
    for fn in os.listdir(src):
        if fn.lower().endswith(MODEL_EXT):
            shutil.copy2(os.path.join(src, fn), os.path.join(dst, fn))
    p = model.load(vsp)
    for s in p.systems:
        for f in s.files:
            a = os.path.normpath(os.path.join(src, f))
            b = os.path.normpath(os.path.join(dst, f))
            if not os.path.normcase(b).startswith(os.path.normcase(dst)):
                raise CoderError("файл автомата %s лежит вне папки проекта "
                                 "— скопируйте проект целиком вручную" % f)
            if not os.path.exists(b):
                os.makedirs(os.path.dirname(b), exist_ok=True)
                shutil.copy2(a, b)
    return os.path.join(dst, os.path.basename(vsp))


def _opt(k, v):
    if v is True:
        v = 1
    if v is False:
        v = 0
    return "-%s%s" % (k, "" if v is None else v)


def generate(vsp, out_dir, coder="hcoder", options=None, systems=None,
             use_vtg=False, clean=True, timeout=300):
    """Сгенерировать код проекта vsp в out_dir.

    coder: 'hcoder' (HCoder.exe — по умолчанию у новых проектов 9.x) или
    'classic' (Coder.exe). clean=True — очистить out_dir перед
    копированием результата. Возвращает CoderResult (его .check()
    бросает CoderError при неудаче)."""
    vsp = os.path.abspath(vsp)
    p = model.load(vsp)
    job = env.job_dir("coder")
    work = os.path.join(job, "model")
    wvsp = copy_model(vsp, work)
    gen = os.path.join(job, "out")
    opts = dict(options or {})
    notes = []
    sysnames = {s.name.lower() for s in p.systems}
    if p.name.lower() in sysnames and "projectheader" not in opts \
            and "projectsource" not in opts:
        opts["projectheader"] = "%s_prj.h" % p.name
        opts["projectsource"] = "%s_prj.c" % p.name
        notes.append("система %s называется как проект — файлы проекта "
                     "названы %s_prj.c/.h (30-02)" % (p.name, p.name))
    exe = env.tool("HCoder" if coder == "hcoder" else "Coder")
    cmd = [exe, os.path.basename(wvsp)]
    if use_vtg:
        cmd.append("--l")
    opts["path"] = gen + os.sep
    for k, v in opts.items():
        cmd.append(_opt(k, v))
    for sname, sopts in (systems or {}).items():
        cmd.append("-V" + sname)
        for k, v in sopts.items():
            cmd.append(_opt(k, v))
    t = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout,
                           cwd=work)
        rc = r.returncode
        log = r.stdout.decode("cp1251", "replace") + \
            r.stderr.decode("cp1251", "replace")
    except subprocess.TimeoutExpired:
        rc, log = None, "тайм-аут %d с" % timeout
    secs = time.time() - t
    files = sorted(os.listdir(gen)) if os.path.isdir(gen) else []
    report = ""
    for f in files:
        if f.lower().endswith(".cre"):
            with open(os.path.join(gen, f), encoding="utf-8",
                      errors="replace") as fh:
                report = fh.read()
    if files:
        if clean and os.path.isdir(out_dir):
            shutil.rmtree(out_dir)
        os.makedirs(out_dir, exist_ok=True)
        for f in files:
            shutil.copy2(os.path.join(gen, f), os.path.join(out_dir, f))
    with open(os.path.join(job, "coder.log"), "w", encoding="utf-8") as fh:
        fh.write(" ".join(cmd) + "\n\n" + log)
    return CoderResult("HCoder" if coder == "hcoder" else "Coder", cmd, rc,
                       log, out_dir, files, report, notes, secs)
