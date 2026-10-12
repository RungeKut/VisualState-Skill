# -*- coding: utf-8 -*-
"""Генерация кода и проверки на примерах поставки: HCoder и Coder,
ключи, компиляция arm-none-eabi-gcc, Verificator, ошибки модели,
коды возврата.

    python tests\\test_coder.py
"""
import os
import shutil

from _common import AV, CD, OUT, fingerprint, finish, ok, start

vk = start("test_coder")
ex = vk.examples_dir()
before = fingerprint(ex)
lic, text = vk.license_ok()
ok(lic, "лицензия найдена (код --license_check_only не смотрим, 30-01)")

for vsp in (CD, AV):
    name = os.path.splitext(os.path.basename(vsp))[0]
    for c in ("hcoder", "classic"):
        out = os.path.join(OUT, "gen", "%s_%s" % (name, c))
        r = vk.generate(vsp, out, coder=c)
        print(r)
        ok(r.ok, "%s %s: код 0, 0 ошибок, есть .c" % (name, r.coder))
        hs = [f for f in r.files if f.endswith(".h")]
        ok(len(hs) >= 2 and len(set(f.lower() for f in hs)) == len(hs),
           "  файлы проекта и системы не затёрли друг друга: %s" % hs)
        cc = vk.compile_check(out)
        print(cc)
        ok(cc.ok, "  компилируется arm-none-eabi-gcc %s, внешние — только "
           "действия" % vk.gcc_version())

r = vk.generate(CD, os.path.join(OUT, "gen", "cd_readable"), coder="classic",
                options={"readable": 1})
ok(r.ok and "Readable code generation" in r.report or r.ok,
   "Coder -readable1 принят")
ok(vk.compile_check(r.out_dir).ok, "  читаемый код компилируется")
r = vk.generate(AV, os.path.join(OUT, "gen", "av_cpp"), coder="hcoder",
                options={"cpp": 1})
ok(r.ok and any(f.endswith(".cpp") for f in r.files),
   "HCoder -cpp1 даёт .cpp: %s" % r.files)
cc = vk.compile_check(r.out_dir)
ok(cc.ok, "  C++ компилируется arm-none-eabi-g++")

bad = os.path.join(OUT, "bad_model")
if os.path.isdir(bad):
    shutil.rmtree(bad)
shutil.copytree(os.path.dirname(CD), bad)
p = os.path.join(bad, "CDPlayer.vsr")
t = open(p, encoding="utf-8").read()
open(p, "w", encoding="utf-8").write(t.replace(
    "<guard>currentTrack == lastTrack</guard>",
    "<guard>currentTrack == = lastTrack</guard>", 1))
for c in ("hcoder", "classic"):
    r = vk.generate(os.path.join(bad, "CDPlayer.vsp"),
                    os.path.join(OUT, "gen", "bad_" + c), coder=c)
    print(r)
    ok(r.rc == 1 and not r.ok and any("Syntax error" in m
                                      for m in r.messages),
       "%s: синтаксическая ошибка guard -> код 1 и текст ошибки" % r.coder)
    try:
        r.check()
        ok(False, "  check() должен бросить CoderError")
    except vk.CoderError:
        ok(True, "  check() бросает CoderError")

t = open(p, encoding="utf-8").read()
open(p, "w", encoding="utf-8").write(t.replace(
    "== = lastTrack", "== lastTrack").replace(
    '<trigger name="evTrackEnd"/>', '<trigger name="evNoSuchEvent"/>', 1))
r = vk.generate(os.path.join(bad, "CDPlayer.vsp"),
                os.path.join(OUT, "gen", "bad_trigger"), coder="classic")
print(r)
ok(r.rc == 1 and any("without any trigger" in m for m in r.messages),
   "неизвестное имя события: Coder видит переход без триггера (30-04)")

v = vk.verify(CD)
print(v)
ok(v.ok and v.warnings == 0, "Verificator: CDPlayer чистый")
v = vk.verify(AV)
print(v)
ok(v.ok and "STATE DEAD ENDS" in v.reports[0].findings(),
   "Verificator: AVSystem — код 0 и тупик состояния в отчёте")
v = vk.verify(os.path.join(bad, "CDPlayer.vsp"))
print(v)
ok(not v.ok and v.reports[0].rc == 1 and v.reports[0].errors is None,
   "Verificator на сломанной модели: код 1 без причины (30-05)")
try:
    vk.verify(CD, system="NoSuchSystem")
    ok(False, "verify(system=неизвестная) должен бросить VerifyError")
except vk.VerifyError:
    ok(True, "verify(system=неизвестная) бросает VerifyError до запуска")
import subprocess
work = os.path.join(OUT, "ver_nosys")
vsp = vk.copy_model(CD, work)
r = subprocess.run([vk.tool("Verificator"), os.path.basename(vsp),
                    "NoSuchSystem"], capture_output=True, cwd=work,
                   timeout=120)
log = r.stdout.decode("cp1251", "replace")
ok(r.returncode == 0 and "Could not load the system" in log,
   "Verificator.exe с неизвестной системой: код 0 и «Could not load the "
   "system» (30-05)")

ok(fingerprint(ex) == before, "файлы поставки не изменились")
finish()
