# -*- coding: utf-8 -*-
"""Проверка, что сгенерированный код компилируется arm-none-eabi-gcc.

    r = compile_check(r"C:\\проект\\vs_gen")      # папка от generate()
    r.check()
    print(r)        # объекты, размеры, предупреждения, внешние символы

Каждый .c компилируется отдельно (`-c`, по умолчанию `-mcpu=cortex-m4
-mthumb -std=c99 -Wall -Wextra -O2`) над копией папки в рабочей папке
без пробелов и кириллицы. Затем `arm-none-eabi-nm` собирает
неразрешённые символы всех объектов вместе:

  * actions — функции действий модели: их пишет человек, это нормально;
  * libc    — memcpy, memset, __aeabi_*, а для C++ ещё __cxa_*,
    operator delete и т. п.: дадут libc/libstdc++ при сборке;
  * other   — всё остальное: генератору чего-то не хватает (например,
    не сгенерирован файл проекта) — r.ok == False.

Функции действий берутся из `extern ... Имя (...);` в сгенерированных
заголовках. Компилятор — env.gcc_bin(): VSKIT_GCC, MCU-Kit, PATH.
"""
import glob
import os
import re
import shutil
import subprocess

from . import env

DEFAULT_FLAGS = ("-mcpu=cortex-m4", "-mthumb", "-std=c99", "-Wall",
                 "-Wextra", "-O2")
LIBC = {"memcpy", "memset", "memmove", "memcmp", "strlen", "strcmp",
        "strncpy", "abort", "__aeabi_memcpy", "__aeabi_memset",
        "__aeabi_memclr", "__aeabi_memclr4", "__aeabi_memcpy4",
        "__aeabi_uidiv", "__aeabi_idiv", "__aeabi_uidivmod",
        "__aeabi_idivmod", "__aeabi_ldivmod", "__aeabi_uldivmod"}
_EXTERN = re.compile(r"^\s*extern\s+[\w\s\*]+?\b([A-Za-z_]\w*)\s*\(",
                     re.M)


def _runtime(sym):
    """Символ стандартной библиотеки C/C++ или ABI ARM."""
    return (sym in LIBC or sym.startswith(("__aeabi_", "__cxa_",
                                           "__gxx_personality", "_ZdlPv",
                                           "_Znwj", "_ZTVN10__cxxabiv",
                                           "_ZSt")))


class CompileError(RuntimeError):
    pass


class CompileResult:
    def __init__(self, work, objects, failed, log, warnings, actions, libc,
                 other, sizes, cmd):
        self.work = work
        self.objects = objects
        self.failed = failed
        self.log = log
        self.warnings = warnings
        self.actions = actions
        self.libc = libc
        self.other = other
        self.sizes = sizes
        self.cmd = cmd

    @property
    def ok(self):
        return not self.failed and not self.other and bool(self.objects)

    def check(self, max_warnings=None):
        if not self.ok:
            raise CompileError(repr(self))
        if max_warnings is not None and len(self.warnings) > max_warnings:
            raise CompileError("предупреждений %d > %d:\n%s" % (
                len(self.warnings), max_warnings, "\n".join(self.warnings)))
        return self

    def __repr__(self):
        lines = ["компиляция: %s, объектов %d, не собралось %d, "
                 "предупреждений %d" % ("OK" if self.ok else "ОШИБКА",
                                        len(self.objects), len(self.failed),
                                        len(self.warnings))]
        for f in self.failed:
            lines.append("  не собрался %s" % f)
        if self.failed:
            lines += ["  " + l for l in self.log.splitlines()
                      if "error" in l][:20]
        for name, (text, data, bss) in sorted(self.sizes.items()):
            lines.append("  %-28s text %6d  data %5d  bss %5d"
                         % (name, text, data, bss))
        if self.actions:
            lines.append("  действия (пишет человек): " +
                         ", ".join(self.actions))
        if self.libc:
            lines.append("  из libc: " + ", ".join(self.libc))
        if self.other:
            lines.append("  НЕ ХВАТАЕТ: " + ", ".join(self.other))
        return "\n".join(lines)


def _run(cmd, cwd):
    r = subprocess.run(cmd, capture_output=True, cwd=cwd, timeout=300)
    return r.returncode, (r.stdout + r.stderr).decode("utf-8", "replace")


def _nm(obj, cwd, flag):
    _rc, out = _run([env.gcc_tool("nm"), flag, obj], cwd)
    syms = set()
    for line in out.splitlines():
        parts = line.split()
        if flag == "-u" and len(parts) >= 2 and parts[0] == "U":
            syms.add(parts[1])
        elif flag == "--defined-only" and len(parts) >= 3:
            syms.add(parts[2])
    return syms


def action_names(folder):
    """Функции действий: `extern <тип> Имя (...)` в заголовках folder."""
    out = set()
    for h in glob.glob(os.path.join(folder, "*.h")):
        with open(h, encoding="utf-8", errors="replace") as f:
            out |= set(_EXTERN.findall(f.read()))
    return out


def compile_check(gen_dir, flags=DEFAULT_FLAGS, extra=(), includes=()):
    """Скомпилировать все .c/.cpp из gen_dir по отдельности и разобрать
    внешние символы. extra — добавочные ключи ('-DVS_TRUE=1'...)."""
    if not os.path.isdir(gen_dir):
        raise CompileError("нет папки %s" % gen_dir)
    job = env.job_dir("gcc")
    work = os.path.join(job, "src")
    shutil.copytree(gen_dir, work)
    gcc = env.gcc_tool("gcc")
    srcs = sorted(f for f in os.listdir(work)
                  if f.lower().endswith((".c", ".cpp")))
    objects, failed, logs, warns = [], [], [], []
    cmd = None
    for s in srcs:
        o = os.path.splitext(s)[0] + ".o"
        exe = gcc if s.lower().endswith(".c") else env.gcc_tool("g++")
        std = [f for f in flags if not (s.lower().endswith(".cpp") and
                                        f.startswith("-std=c"))]
        cmd = [exe] + std + list(extra) + ["-I."] + \
            ["-I" + i for i in includes] + ["-c", s, "-o", o]
        rc, out = _run(cmd, work)
        logs.append("$ " + " ".join(cmd) + "\n" + out)
        warns += [l.strip() for l in out.splitlines() if "warning:" in l]
        if rc == 0 and os.path.exists(os.path.join(work, o)):
            objects.append(o)
        else:
            failed.append(s)
    undef, defined = set(), set()
    sizes = {}
    for o in objects:
        undef |= _nm(o, work, "-u")
        defined |= _nm(o, work, "--defined-only")
        _rc, out = _run([env.gcc_tool("size"), o], work)
        rows = out.splitlines()
        if len(rows) >= 2:
            p = rows[1].split()
            sizes[o] = (int(p[0]), int(p[1]), int(p[2]))
    missing = undef - defined
    acts = action_names(work)
    actions = sorted(missing & acts)
    libc = sorted(s for s in missing - acts if _runtime(s))
    other = sorted(missing - acts - set(libc))
    log = "\n".join(logs)
    with open(os.path.join(job, "gcc.log"), "w", encoding="utf-8") as f:
        f.write(log)
    return CompileResult(work, objects, failed, log, warns, actions, libc,
                         other, sizes, cmd)
