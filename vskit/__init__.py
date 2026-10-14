# -*- coding: utf-8 -*-
"""vskit — IAR Visual State 9.1 из Python: модель текстом, код, проверки.

Проверенное поведение, ловушки и приёмы — в knowledge/ (начинать с
knowledge/INDEX.md).

Быстрый старт:

    import vskit as vk

    vk.utf8_console()
    p = vk.load(r"D:\\проект\\Model\\Project.vsp")    # .vsp/.vsr — это XML
    print(p)                                         # состояния, переходы

    r = vk.generate(p.file, r"D:\\проект\\vs_gen")     # HCoder над копией
    r.check()
    print(vk.compile_check(r.out_dir))               # arm-none-eabi-gcc
    print(vk.verify(p.file))                         # Verificator

Новая модель из описания:

    m = vk.Machine("Lamp")
    m.event("evToggle"); m.action("LampOn"); m.action("LampOff")
    m.state("Off", entry="LampOff()"); m.state("On", entry="LampOn()")
    m.initial("Off")
    m.trans("Off", "On", "evToggle"); m.trans("On", "Off", "evToggle")
    vsp = vk.Project("LampProject").add_system("Lamp_sys", m).save(r"C:\\w")

Симуляция в Validator (окно Validator откроется и закроется):

    with vk.Simulator(vsp) as s:
        s.deduct("SE_RESET"); print(s.deduct("evToggle"))
"""

__version__ = "0.2.0"

from .env import (bin_dir, examples_dir, gcc_bin, gcc_tool, gcc_version,
                  is_safe_path, job_dir, kit_root, license_ok, tool,
                  utf8_console, version, vs_root, work_root)
from .model import Project as Model, load, load_machine
from .design import Machine, Project, from_project, new_guid
from .coder import (CoderError, CoderResult, copy_model, generate,
                    options_help)
from .verificator import VerifyError, VerifyResult, verify
from .sim import ControlCenter, SimError, Simulator, designer_check, windows
from .build import CompileError, CompileResult, compile_check
from . import schema, smapi
from .schema import validate_project as schema_check
from .report import Report, full_check
from .shot import ShotError, designer_shot

__all__ = [
    "utf8_console", "vs_root", "bin_dir", "tool", "examples_dir", "version",
    "license_ok", "work_root", "job_dir", "is_safe_path", "kit_root",
    "gcc_bin", "gcc_tool", "gcc_version",
    "load", "load_machine", "Model",
    "Machine", "Project", "from_project", "new_guid",
    "generate", "options_help", "copy_model", "CoderResult", "CoderError",
    "verify", "VerifyResult", "VerifyError",
    "Simulator", "ControlCenter", "designer_check", "windows", "SimError",
    "compile_check", "CompileResult", "CompileError",
    "smapi", "schema", "schema_check", "Report", "full_check",
    "designer_shot", "ShotError",
]
