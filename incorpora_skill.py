#!/usr/bin/env python3
"""Incorpora le skill della cartella skills/ dentro print_doctor.py (blocco BUILTIN_SKILLS).

Uso:  python3 incorpora_skill.py

Le skill restano in skills/*.md (la fonte da modificare); i file che iniziano con "_" (es. _fonti.md)
vengono saltati. Va rilanciato dopo ogni modifica alle skill. Solo libreria standard."""
import json
import os
import re
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(QUI, "print_doctor.py")
SKILLS = os.path.join(QUI, "skills")
INIZIO = "# >>> SKILL INCORPORATE (blocco generato da incorpora_skill.py: non modificare a mano)\n"
FINE = "# <<< SKILL INCORPORATE\n"


def leggi_skill(path):
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        raise ValueError("manca l'intestazione --- name / description ---")
    name = desc = ""
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            k, v = k.strip().lower(), v.strip().strip('"').strip("'")
            if k == "name":
                name = v
            elif k == "description":
                desc = v
    stem = os.path.splitext(os.path.basename(path))[0]
    if name != stem:
        raise ValueError("name %r diverso dal nome del file" % name)
    if not desc:
        raise ValueError("description vuota")
    return name, desc, m.group(2)


def main():
    skills, errori = [], []
    for entry in sorted(os.listdir(SKILLS)):
        if entry.startswith(("_", ".")) or not entry.lower().endswith(".md"):
            continue
        try:
            skills.append(leggi_skill(os.path.join(SKILLS, entry)))
        except Exception as exc:
            errori.append("%s: %s" % (entry, exc))
    if errori or not skills:
        print("Niente di scritto.", *(errori or ["nessuna skill trovata in %s" % SKILLS]), sep="\n  ")
        return 1
    righe = [INIZIO, "BUILTIN_SKILLS = {\n"]
    for name, desc, body in skills:
        righe.append("    %s: {\n        \"description\": %s,\n        \"content\": %s,\n    },\n"
                     % (json.dumps(name), json.dumps(desc, ensure_ascii=False), json.dumps(body, ensure_ascii=False)))
    righe += ["}\n", FINE]
    blocco = "".join(righe)
    with open(PLUGIN, "r", encoding="utf-8") as fh:
        src = fh.read()
    if INIZIO in src and FINE in src:
        a, b = src.index(INIZIO), src.index(FINE) + len(FINE)
    else:                                   # prima volta: sostituisce il vecchio dizionario scritto a mano
        a = src.index("BUILTIN_SKILLS = {")
        b = src.index("\n\ndef parse_skill_text(", a)
    nuovo = src[:a] + blocco + src[b:]
    compile(nuovo, PLUGIN, "exec")          # controllo di sintassi prima di scrivere
    tmp = PLUGIN + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(nuovo)
    os.replace(tmp, PLUGIN)
    print("Incorporate %d skill (%d caratteri) in %s" % (len(skills), sum(len(s[2]) for s in skills), os.path.basename(PLUGIN)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
