# -*- coding: utf-8 -*-
"""Формальная проверка модели — Verificator.exe из командной строки.

    r = verify(r"C:\\модель\\Project.vsp")       # все системы проекта
    print(r)                                     # разделы отчёта .vre
    r.check()                                    # VerifyError, если ошибки

Verificator проверяет систему целиком: неиспользуемые и недостижимые
элементы, конфликты переходов, тупики (state/local/system dead ends),
выход за домены переменных, неоднозначные присваивания, очередь сигналов.
Окон не открывает. Ключ `-v<файл>` пишет отчёт в `<файл>.vre` (суффикс
.vre добавляется всегда). При синтаксической ошибке модели — код 1 и
строка «The Verificator didn't complete with success.» без причины
(причину показывает generate()); при неизвестной системе — та же строка,
но код 0. Успех поэтому — только по строке «completed - 0 error(s)»
(knowledge/30_ГРАБЛИ/30-05).

Валидатор (Validator.exe) — оконная программа без пакетного режима;
пошаговая симуляция из скрипта — vskit.sim (через Control Center).
"""
import os
import re
import subprocess
import time

from . import coder as _coder
from . import env
from . import model

SECTIONS = ("USE OF ALL ELEMENTS", "ACTIVATION OF ALL ELEMENTS", "CONFLICTS",
            "STATE DEAD ENDS", "LOCAL DEAD ENDS", "SYSTEM DEAD ENDS",
            "DOMAIN ERRORS", "AMBIGUOUS ASSIGNMENTS (static check)",
            "AMBIGUOUS ASSIGNMENTS (dynamic check)", "SIGNAL QUEUE")
CLEAN = ("None.", "All elements are used.", "All elements are activated.",
         "The signal queue has the right size.")


class VerifyError(RuntimeError):
    pass


class SystemReport:
    def __init__(self, system, rc, log, vre_text, seconds):
        self.system = system
        self.rc = rc
        self.log = log
        self.text = vre_text
        self.seconds = seconds
        m = re.search(r"completed\s*-\s*(\d+)\s*error\(s\),\s*(\d+)\s*"
                      r"warning\(s\)", log)
        self.errors = int(m.group(1)) if m else None
        self.warnings = int(m.group(2)) if m else None
        self.sections = _sections(vre_text)

    @property
    def ok(self):
        return self.rc == 0 and self.errors == 0

    def findings(self):
        """Разделы с замечаниями: {раздел: [строки]}."""
        return {k: v for k, v in self.sections.items()
                if v and not (len(v) == 1 and v[0] in CLEAN)}

    def __repr__(self):
        lines = ["система %s: код %s, ошибок %s, предупреждений %s" % (
            self.system, self.rc, self.errors, self.warnings)]
        if self.errors is None:
            lines.append("  " + " | ".join(l.strip() for l in
                                           self.log.splitlines()[-2:]))
        for k, v in self.findings().items():
            lines.append("  %s:" % k)
            lines += ["    " + x for x in v]
        return "\n".join(lines)


class VerifyResult:
    def __init__(self, reports):
        self.reports = reports

    @property
    def ok(self):
        return all(r.ok for r in self.reports)

    @property
    def warnings(self):
        return sum(r.warnings or 0 for r in self.reports)

    def check(self, allow_warnings=True):
        bad = [r for r in self.reports if not r.ok or
               (not allow_warnings and r.warnings)]
        if bad:
            raise VerifyError("\n".join(repr(r) for r in bad))
        return self

    def __repr__(self):
        return "\n".join(repr(r) for r in self.reports)


def _sections(text):
    out = {}
    cur = None
    for line in text.splitlines():
        s = line.strip()
        if s in SECTIONS:
            cur = s
            out[cur] = []
            continue
        if s == "--" or s.startswith("Verificator terminated"):
            cur = None
            continue
        if cur and s:
            out[cur].append(s)
    return out


def verify(vsp, system=None, args=(), timeout=600):
    """Проверить систему system (по умолчанию — каждую систему проекта)
    над копией модели. args — дополнительные ключи Verificator
    ('-xuse', '-h60'...)."""
    vsp = os.path.abspath(vsp)
    p = model.load(vsp)
    known = [s.name for s in p.systems]
    if system and system not in known:
        raise VerifyError("нет системы %r в проекте (есть: %s); сам "
                          "Verificator на это отвечает кодом 0 (30-05)"
                          % (system, ", ".join(known)))
    names = [system] if system else known
    job = env.job_dir("verify")
    wvsp = _coder.copy_model(vsp, os.path.join(job, "model"))
    reports = []
    for name in names:
        base = os.path.join(job, "ver_" + name)
        cmd = [env.tool("Verificator"), os.path.basename(wvsp), name,
               "-v" + base] + list(args)
        t = time.time()
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=timeout,
                               cwd=os.path.dirname(wvsp))
            rc = r.returncode
            log = r.stdout.decode("cp1251", "replace") + \
                r.stderr.decode("cp1251", "replace")
        except subprocess.TimeoutExpired:
            rc, log = None, "тайм-аут %d с" % timeout
        text = ""
        if os.path.exists(base + ".vre"):
            with open(base + ".vre", encoding="utf-8", errors="replace") as f:
                text = f.read()
        reports.append(SystemReport(name, rc, log, text, time.time() - t))
    return VerifyResult(reports)
