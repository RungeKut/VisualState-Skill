# -*- coding: utf-8 -*-
"""Проверка целостности базы знаний VisualState-Kit.

Выполняет раздел 9 файла knowledge/00_ПРАВИЛА.md:

  * у каждого файла базы есть шапка YAML с обязательными полями;
  * каждый файл присутствует в INDEX.md и наоборот;
  * нет двух файлов с одинаковым id;
  * id в шапке совпадает с именем файла;
  * записи со status: проверено имеют поле verified;
  * внутренние ссылки ведут на существующие файлы;
  * НИ ОДИН файл набора не упоминает изделие или посторонний проект;
  * на этой машине включён хук commit-msg, который проверяет текст коммита;
  * для этого клона задан автор коммитов (иначе уходят глобальные — рабочие).

Стоп-слова — в tools/stoplist.txt. Это ЛОКАЛЬНЫЙ файл: он в .gitignore и в
репозиторий не попадает — стоп-лист, лежащий в публичном репозитории, сам
публикует то, что должен скрывать. Поэтому ошибка и отсутствие файла
(проверять не по чему; его заводит setup.ps1), и его возвращение под git.

С ключом --project к стоп-словам добавляются имя папки проекта, имена
файлов .vsp/.vsr в ней и в её подпапках и имена из самих моделей:
системы, автоматы, состояния, события, действия, переменные (целиком,
не короче 5 символов, кроме служебных вида initial1, Region1).

Запуск:
    python tools/check_docs.py
    python tools/check_docs.py --project "D:\\путь\\к\\папке\\проекта"
"""
import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE = os.path.join(ROOT, "knowledge")
INDEX = os.path.join(KNOWLEDGE, "INDEX.md")

REQUIRED = ("id", "title", "status")
VALID_STATUS = ("проверено", "не проверено", "устарело", "действует")

STOPLIST = os.path.join(ROOT, "tools", "stoplist.txt")
SKIP = ("tools/stoplist.txt",)
TEXT_EXT = (".md", ".py", ".ps1", ".txt", ".il", ".tcl", ".bat", ".cfg",
            ".toml", ".json", ".yml")
PROJECT_EXT = (".VSP", ".VSR")
GENERIC = set("""board design project schematic test main build params kit
work temp data copy backup new old final model models vsproject workspace
system state states event events action actions region topstate machine
плата платы плате схема схемы проект проекта модуль блок версия копия
управления питания контроля модель модели автомат автоматы""".split())
SERVICE = re.compile(r"^(initial|final|history|deephistory|choice|region|"
                     r"system|topstate|state|project|toplevelstatemachine|"
                     r"_?initialstate|_?shallowhistorystate)\d*$", re.I)


def read(path):
    return io.open(path, encoding="utf-8").read()


def front_matter(text):
    """Разобрать шапку YAML (плоскую)."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    out = {}
    for line in text[3:end].splitlines():
        m = re.match(r"^([a-zA-Z_]+):\s*(.*)$", line.strip())
        if m:
            out[m.group(1)] = m.group(2).strip().strip('"')
    return out


def knowledge_files():
    out = []
    for dirpath, _dirnames, filenames in os.walk(KNOWLEDGE):
        for fn in sorted(filenames):
            if fn.endswith(".md") and fn != "INDEX.md":
                out.append(os.path.join(dirpath, fn))
    return sorted(out)


def rel(path):
    return os.path.relpath(path, KNOWLEDGE).replace("\\", "/")


def hook_enabled():
    """Включён ли хук commit-msg (core.hooksPath = tools/hooks)."""
    try:
        out = subprocess.check_output(
            ["git", "config", "--get", "core.hooksPath"],
            cwd=ROOT, stderr=subprocess.DEVNULL)
        return out.decode("utf-8", "replace").strip().replace("\\", "/") \
            == "tools/hooks"
    except Exception:
        return False


def local_author():
    """Автор коммитов, заданный для ЭТОГО клона: (имя, адрес) или None.

    Без локальной настройки git подставляет глобальные — на рабочей машине
    это рабочее имя и корпоративный адрес, и они уходят в публичную
    историю. В соседнем наборе так ушли три коммита.
    """
    vals = []
    for key in ("user.name", "user.email"):
        try:
            out = subprocess.check_output(
                ["git", "config", "--local", "--get", key],
                cwd=ROOT, stderr=subprocess.DEVNULL)
            vals.append(out.decode("utf-8", "replace").strip())
        except Exception:
            return None
    return tuple(vals) if all(vals) else None


def stoplist_tracked():
    """Лежит ли tools/stoplist.txt под git (а должен быть только локальным).

    .gitignore не мешает вернуть файл через git add -f или слиянием старой
    ветки; тогда при следующем push приметы изделий уйдут наружу.
    """
    try:
        out = subprocess.check_output(
            ["git", "ls-files", "--", "tools/stoplist.txt"],
            cwd=ROOT, stderr=subprocess.DEVNULL)
        return bool(out.strip())
    except Exception:
        return False


def repo_files():
    """Все текстовые файлы набора, кроме служебных и самих стоп-листов."""
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", "__pycache__", ".venv")]
        for fn in sorted(filenames):
            if not fn.lower().endswith(TEXT_EXT):
                continue
            full = os.path.join(dirpath, fn)
            r = os.path.relpath(full, ROOT).replace(os.sep, "/")
            if r in SKIP:
                continue
            out.append(full)
    return sorted(out)


def stop_words():
    """Стоп-слова из локального tools/stoplist.txt."""
    if not os.path.exists(STOPLIST):
        return set()
    out = set()
    for line in io.open(STOPLIST, encoding="utf-8-sig").read().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.add(line)
    return out


def model_names(vsp):
    """Имена из модели Visual State: системы, автоматы, вершины, элементы."""
    sys.path.insert(0, ROOT)
    try:
        from vskit import model
        p = model.load(vsp)
    except Exception:
        return set()
    names = {s.name for s in p.systems}
    for m in p.machines():
        names.add(m.name)
        names |= {v.name for v in m.vertices()}
        for items in m.elements.values():
            names |= {e.name for e in items}
    return {n for n in names if n and len(n) >= 5 and not SERVICE.match(n)
            and n.lower() not in GENERIC}


def project_words(project_dir):
    """Приметы изделия из папки проекта: её имя, имена моделей и имена
    внутри моделей Visual State."""
    if not project_dir or not os.path.isdir(project_dir):
        return set()
    names = [os.path.basename(os.path.abspath(project_dir))]
    out = set()
    for dp, dn, fn in os.walk(project_dir):
        dn[:] = [d for d in dn if not d.startswith(".")]
        for f in fn:
            stem, ext = os.path.splitext(f)
            if ext.upper() in PROJECT_EXT:
                names.append(stem)
            if ext.upper() == ".VSP":
                out |= model_names(os.path.join(dp, f))
    for name in names:
        for token in re.split(r"[^0-9A-Za-zА-Яа-яЁё]+", name):
            if len(token) >= 4 and token.lower() not in GENERIC \
                    and not SERVICE.match(token):
                out.add(token)
    return out


def main(project_dir=None):
    problems = []
    files = knowledge_files()
    ids = {}

    print("База знаний: %s" % KNOWLEDGE)
    print("Файлов найдено: %d" % len(files))
    print("Проверка на стоп-слова: %d файлов набора\n" % len(repo_files()))

    for path in files:
        r = rel(path)
        fm = front_matter(read(path))
        if fm is None:
            problems.append("%s: нет шапки YAML" % r)
            continue
        for field in REQUIRED:
            if field not in fm:
                problems.append("%s: в шапке нет поля %s" % (r, field))
        status = fm.get("status", "")
        if status and status not in VALID_STATUS:
            problems.append("%s: неизвестный status %r (допустимы: %s)"
                            % (r, status, ", ".join(VALID_STATUS)))
        if status == "проверено" and not fm.get("verified"):
            problems.append("%s: status «проверено», но нет поля verified — "
                            "запись не имеет силы (правило 3)" % r)
        if status == "проверено" and not fm.get("applies_to"):
            problems.append("%s: нет applies_to — неизвестно, на какой "
                            "версии проверено (правило 3)" % r)
        fid = fm.get("id", "")
        if fid:
            if fid in ids:
                problems.append("%s: id %s уже занят файлом %s"
                                % (r, fid, ids[fid]))
            else:
                ids[fid] = r
            base = os.path.basename(path)
            if not base.startswith(fid + "_") and base != "00_ПРАВИЛА.md":
                problems.append("%s: id %s не совпадает с именем файла"
                                % (r, fid))

    if not os.path.exists(INDEX):
        problems.append("нет INDEX.md")
    else:
        index_text = read(INDEX)
        linked = {l.replace("\\", "/") for l in
                  re.findall(r"\]\(([^)]+\.md)\)", index_text)}
        for path in files:
            if rel(path) not in linked:
                problems.append("%s: файла нет в INDEX.md (правило 5)"
                                % rel(path))
        existing = {rel(p) for p in files}
        for l in sorted(linked):
            if l not in existing and not l.startswith(".."):
                problems.append("INDEX.md ссылается на несуществующий %s" % l)
        width = None
        for n, line in enumerate(index_text.splitlines(), 1):
            if not line.startswith("|"):
                width = None
                continue
            cells = line.count("|")
            if width is None:
                width = cells
            elif cells != width:
                problems.append("INDEX.md, строка %d: %d ячеек вместо %d — "
                                "таблица испорчена" % (n, cells - 1,
                                                        width - 1))

    for path in files:
        base = os.path.dirname(path)
        for link in re.findall(r"\]\(([^)]+\.md)\)", read(path)):
            if link.startswith("http"):
                continue
            if not os.path.exists(os.path.normpath(os.path.join(base,
                                                                link))):
                problems.append("%s: битая ссылка -> %s" % (rel(path), link))

    if not os.path.exists(STOPLIST):
        problems.append(
            "нет tools/stoplist.txt — проверять набор не по чему. Файл "
            "локальный (в .gitignore); заводит его setup.ps1, приметы "
            "изделий вписываются туда")
    if stoplist_tracked():
        problems.append(
            "tools/stoplist.txt снова под git — при push приметы изделий "
            "уйдут в публичный репозиторий. Убрать: "
            "git rm --cached tools/stoplist.txt")
    project = project_words(project_dir)
    if project:
        print("Приметы изделия из папки проекта: %s\n"
              % ", ".join(sorted(project)))
    words = stop_words() | project
    for path in repo_files():
        text = read(path).lower()
        r = os.path.relpath(path, ROOT).replace(os.sep, "/")
        for word in sorted(words):
            if word.lower() in text:
                problems.append("%s: упоминание изделия или постороннего "
                                "проекта %r (правило 1)" % (r, word))

    if not hook_enabled():
        problems.append(
            "хук commit-msg не включён на этой машине — текст коммита никто "
            "не проверяет. Лечится: git config core.hooksPath tools/hooks "
            "(её же делает setup.ps1)")

    if local_author() is None:
        problems.append(
            "для этого клона не задан автор коммитов — git возьмёт глобальные "
            "имя и адрес (на рабочей машине — рабочие) и опубликует их. "
            "Задать: git config user.name \"<публичное имя>\" и "
            "git config user.email \"<публичный адрес>\" (40-02)")

    if problems:
        print("РАСХОЖДЕНИЯ (%d):" % len(problems))
        for p in problems:
            print("  - " + p)
    else:
        print("Расхождений нет.")
    print("\nЗанятые id: %s" % ", ".join(sorted(ids)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace")
    argv = sys.argv[1:]
    proj = None
    if "--project" in argv:
        i = argv.index("--project")
        if i + 1 >= len(argv):
            print("--project требует путь к папке проекта")
            sys.exit(2)
        proj = argv[i + 1]
    sys.exit(main(proj))
