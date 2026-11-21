# /// script
# requires-python = ">=3.12"
# dependencies = []
#
# [tool.orcaslicer.plugin]
# name = "Print Doctor"
# description = "Chatta con un'IA che capisce i problemi di stampa e modifica i parametri di Orca (supporti, larghezze di linea, velocita, ritrazione, temperature). Funziona con il tuo abbonamento ChatGPT, OpenRouter, Anthropic, OpenAI, Gemini, Ollama e LM Studio. Gratuito: se ti e utile, offrimi un caffe su buymeacoffee.com/Marco.Piazza"
# author = "Marco Piazza"
# version = "0.4.0"
# ///
#
# Plugin gratuito e open source: licenza GNU AGPL v3 (vedi LICENSE). Solo libreria standard di Python.
# Struttura ricavata dalla documentazione ufficiale di OrcaSlicer (Plugin Development, Host, Host UI).
#
# Come funziona, in breve:
#  - il pannello (HTML) parla con il plugin tramite orca.postMessage / panel.post;
#  - ogni messaggio dell'utente: sul thread UI si legge lo stato di Orca (una "fotografia"),
#    poi un unico thread di lavoro chiama l'IA (rete) usando solo la fotografia;
#  - l'IA non modifica nulla da sola: propone le modifiche (strumento propose_changes);
#  - "Applica": il piano si prepara sul thread UI, poi il thread di lavoro chiama
#    orca.host.preset.<tipo>.begin_update() / set() / commit(): modifica il preset in uso,
#    come modifiche non salvate (come se l'utente cambiasse i campi a mano).

import base64
import collections
import difflib
import hashlib
import hmac
import http.client
import http.server
import json
import os
import queue
import re
import secrets
import ssl
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser

import orca

VERSION = "0.4.0"
TITLE = "Print Doctor"
PANEL_TITLE = "Print Doctor"      # titolo del pannello
PANEL_WIDTH = 330
TAB_TITLE = "Print Doctor"        # linguetta sulla destra quando il pannello e nascosto
TAB_WIDTH = 44
DONATE_URL = "https://buymeacoffee.com/Marco.Piazza"
MESHDAB_URL = "https://meshdab.com/"
SETTINGS_FILE = "impostazioni.json"        # niente "conf", "cert", "secret" nei nomi: Orca li blocca
MAX_STEPS = 12
HTTP_TIMEOUT = 300
ANTHROPIC_VERSION = "2026-10-21"
ANTHROPIC_BETA = "server-side-fallback-2026-07-01"

PROVIDERS = {
    "chatgpt": {"label": "ChatGPT", "kind": "responses", "base": "https://api.openai.com/v1", "model": "",
                "key": False, "login": True},
    "openrouter": {"label": "OpenRouter", "kind": "openai", "base": "https://openrouter.ai/api/v1",
                   "model": "anthropic/claude-opus-5.5", "key": True},
    "anthropic": {"label": "Anthropic", "kind": "anthropic", "base": "https://api.anthropic.com/v1",
                  "model": "claude-opus-5-5", "key": True},
    "openai": {"label": "OpenAI", "kind": "openai", "base": "https://api.openai.com/v1", "model": "", "key": True},
    "gemini": {"label": "Google Gemini", "kind": "openai",
               "base": "https://generativelanguage.googleapis.com/v1beta/openai", "model": "", "key": True},
    "ollama": {"label": "Ollama", "kind": "openai", "base": "http://localhost:11434/v1", "model": "", "key": False},
    "lmstudio": {"label": "LM Studio", "kind": "openai", "base": "http://localhost:1234/v1", "model": "", "key": False},
    "custom": {"label": "OpenAI compatible", "kind": "openai", "base": "", "model": "", "key": True},
}

# Pagine dove l'utente crea una chiave API (aperte nel browser dal pannello).
KEY_PAGES = {
    "openrouter": "https://openrouter.ai/settings/keys",
    "anthropic": "https://console.anthropic.com/settings/keys",
    "openai": "https://platform.openai.com/api-keys",
    "gemini": "https://aistudio.google.com/apikey",
}

# Sign in with ChatGPT per app open source: usa il piano ChatGPT dell'utente.
# https://developers.openai.com/siwc/token-sharing-open-source
CG_AUTH = "https://auth.openai.com"
CG_AUTHORIZE = CG_AUTH + "/api/accounts/authorize"
CG_TOKEN = CG_AUTH + "/api/accounts/oauth/token"
CG_RESOURCE = "https://api.openai.com/v1"           # destinatario dei token (resource)
CG_API = "https://api.openai.com/v1"                # indirizzo delle richieste
CG_SCOPES = "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct"
CG_PLAN_SCOPE = "chatgpt.tokens.use.direct"
CG_AGENT_NAME = "Print Doctor"
CG_USAGE_URL = "https://chatgpt.com/settings/usage"

# Chiavi che descrivono il preset e non vanno mai modificate dall'IA.
META_KEYS = {
    "name", "inherits", "from", "version", "is_custom_defined", "instantiation", "setting_id",
    "print_settings_id", "filament_settings_id", "printer_settings_id", "base_id", "type",
    "compatible_printers", "compatible_printers_condition", "compatible_prints",
    "compatible_prints_condition", "filament_vendor", "inherits_group", "printer_model",
    "printer_variant", "default_print_profile", "default_filament_profile",
}

SUMMARY_KEYS = {
    "process": [
        "layer_height", "initial_layer_print_height", "line_width", "outer_wall_line_width",
        "inner_wall_line_width", "sparse_infill_line_width", "wall_loops", "top_shell_layers",
        "bottom_shell_layers", "sparse_infill_density", "sparse_infill_pattern", "outer_wall_speed",
        "inner_wall_speed", "sparse_infill_speed", "initial_layer_speed", "travel_speed",
        "default_acceleration", "enable_support", "support_type", "support_style",
        "support_threshold_angle", "support_top_z_distance", "support_object_xy_distance",
        "support_on_build_plate_only", "brim_type", "brim_width", "seam_position", "ironing_type",
        "wall_generator", "elefant_foot_compensation",
    ],
    "filament": [
        "filament_type", "nozzle_temperature", "nozzle_temperature_initial_layer",
        "nozzle_temperature_range_low", "nozzle_temperature_range_high", "hot_plate_temp",
        "textured_plate_temp", "cool_plate_temp", "fan_min_speed", "fan_max_speed",
        "close_fan_the_first_x_layers", "overhang_fan_speed", "filament_flow_ratio",
        "filament_max_volumetric_speed", "filament_retraction_length", "filament_retraction_speed",
        "pressure_advance",
    ],
    "printer": ["nozzle_diameter", "retraction_length", "retraction_speed", "z_hop", "printable_height",
                "printer_structure"],
}


def log(*a):
    # print() finisce in data_dir()/log/python_*.log
    print("[print-doctor]", *a, flush=True)


# ------------------------------------------------------------------ utilita --

def to_plain(v):
    """Valore di Orca -> forma JSON dei preset (stringhe, liste di stringhe)."""
    if v is None:
        return None
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (list, tuple)):
        return [to_plain(x) for x in v]
    if isinstance(v, float):
        s = repr(v)
        return s[:-2] if s.endswith(".0") else s
    return str(v)


def show(v):
    """Valore leggibile per l'IA e per l'utente."""
    if isinstance(v, list):
        if not v:
            return "[]"
        if all(x == v[0] for x in v):
            return v[0] if len(v) == 1 else "%s (same for all %d variants)" % (v[0], len(v))
        return "[" + ", ".join(str(x) for x in v) + "]"
    return v


def short(v):
    if isinstance(v, list):
        if v and all(x == v[0] for x in v):
            return str(v[0])
        return "[" + ", ".join(str(x) for x in v) + "]"
    return "" if v is None else str(v)


def b64url(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def data_dir():
    """.../OrcaSlicer/orca_plugins/<plugin>/<file>.py  ->  .../OrcaSlicer"""
    p = os.path.abspath(__file__)
    while True:
        parent = os.path.dirname(p)
        if os.path.basename(p) == "orca_plugins":
            return parent
        if parent == p:
            return None
        p = parent


# ------------------------------------------------------------- preset Orca --

def collection(b, ptype):
    return {"process": b.prints, "filament": b.filaments, "printer": b.printers}[ptype]


def filament_target(b):
    """(preset, slot 1-based) del filamento su cui lavora l'assistente: quello aperto nella scheda
    Filamento se e caricato in uno slot, altrimenti lo slot 1."""
    try:
        names = list(b.current_filament_preset_names() or [])
    except Exception:
        names = []
    try:
        ed = b.filaments.edited_preset()
    except Exception:
        ed = None
    if ed is not None and ed.name in names:
        return ed, names.index(ed.name) + 1
    if names:
        p = b.filaments.find_preset(names[0])
        if ed is not None and p is not None and ed.name == p.name:
            p = ed
        return p, 1
    return ed, 1


def current_preset(b, ptype):
    """Il preset che l'utente vede, con le modifiche non ancora salvate."""
    if ptype == "filament":
        return filament_target(b)[0]
    coll = collection(b, ptype)
    try:
        p = coll.edited_preset()
        if p is not None:
            return p
    except Exception:
        pass
    fn = b.current_printer_preset if ptype == "printer" else b.current_print_preset
    return fn()


NUMERIC = re.compile(r"^\s*(-?\d+(\.\d+)?\s*%?|nil)\s*$")


def serialized(raw, new=None):
    """Valore nel formato testo di Orca per PresetTransaction.set().
    Con new=None serializza raw stesso (serve per annullare). Restituisce (valore, alternativa):
    l'alternativa usa l'altro separatore di lista, da provare se Orca rifiuta il primo."""
    if not isinstance(raw, (list, tuple)):
        if new is None:
            return to_plain(raw), None
        new = str(new).strip()
        if isinstance(raw, bool) and new.lower() in ("true", "false", "yes", "no", "on", "off"):
            new = "1" if new.lower() in ("true", "yes", "on") else "0"
        return new, None
    plain = ["nil" if x is None else to_plain(x) for x in raw]
    text_list = bool(raw) and all(isinstance(x, str) for x in raw) and \
        not all(NUMERIC.match(x) for x in raw if x.strip())     # "nil" = lista numerica con valori vuoti
    sep, other = (";", ",") if text_list else (",", ";")
    if new is None:
        parts = plain
    else:
        new = str(new).strip()
        n = max(len(raw), 1)
        parts = [x.strip() for x in re.split(r"[;,]", new)] if re.search(r"[;,]", new) else [new]
        if len(parts) != n:
            parts = [new] * n
    return sep.join(parts), other.join(parts)


# ---------------------------------------------------------------- fotografia --

def take_snapshot():
    b = orca.host.preset_bundle()
    snap = {"presets": {}, "values": {}, "plate": [], "filaments": [], "errors": []}
    for ptype in ("process", "filament", "printer"):
        try:
            p = current_preset(b, ptype)
        except Exception as exc:
            snap["errors"].append("%s: %r" % (ptype, exc))
            p = None
        if p is None:
            continue
        info = {"name": p.name, "system": bool(p.is_system), "dirty": bool(getattr(p, "is_dirty", False))}
        if ptype == "filament":
            info["slot"] = filament_target(b)[1]
        try:
            info["inherits"] = to_plain(p.config_value("inherits"))
        except Exception:
            pass
        snap["presets"][ptype] = info
        vals = {}
        try:
            for k in p.config_keys():
                try:
                    vals[k] = to_plain(p.config_value(k))
                except Exception:
                    pass
        except Exception as exc:
            snap["errors"].append("%s keys: %r" % (ptype, exc))
        snap["values"][ptype] = vals
    try:
        snap["filaments"] = [str(n) for n in (b.current_filament_preset_names() or [])]
    except Exception:
        pass
    try:
        snap["plate"] = plate_summary()
    except Exception as exc:
        snap["errors"].append("plate: %r" % (exc,))
    return snap


def plate_summary():
    out = []
    for i, obj in enumerate(orca.host.model().objects()):
        name = getattr(obj, "name", "") or ""
        if callable(name):
            name = name()
        info = {"name": str(name) or "object %d" % (i + 1)}
        try:
            vols = list(obj.volumes())
            info["parts"] = len(vols)
            lo, hi, tri, vol = [1e18] * 3, [-1e18] * 3, 0, 0.0
            for v in vols:
                m = v.mesh()
                bb = m.bounding_box()
                for a in range(3):
                    lo[a] = min(lo[a], bb.min[a])
                    hi[a] = max(hi[a], bb.max[a])
                tri += m.triangle_count()
                vol += abs(m.volume())
            if vols:
                info["size_mm"] = [round(hi[a] - lo[a], 1) for a in range(3)]
            info["triangles"] = tri
            info["volume_mm3"] = round(vol, 1)
        except Exception as exc:
            info["error"] = repr(exc)
        try:
            insts = list(obj.instances())
            info["copies"] = len(insts)
            if insts:
                sf = getattr(insts[0], "scaling_factor", None)
                sf = sf() if callable(sf) else sf
                if sf is not None:
                    info["scale"] = [round(float(x), 3) for x in sf]
        except Exception:
            pass
        out.append(info)
    return out


def context_text(snap):
    pr = snap["presets"]
    vals = snap["values"]
    lines = ["[Current OrcaSlicer state, read just now]"]
    names = {"printer": "Printer preset", "process": "Process (print) preset", "filament": "Filament preset"}
    for ptype in ("printer", "process", "filament"):
        if ptype in pr:
            p = pr[ptype]
            tag = "system" if p["system"] else "user"
            dirty = ", has unsaved edits" if p.get("dirty") else ""
            lines.append("- %s: %s (%s%s)" % (names[ptype], p["name"], tag, dirty))
    fils = snap.get("filaments") or []
    if len(fils) > 1:
        slot = (pr.get("filament") or {}).get("slot", 1)
        lines.append("- Filament slots: %s. Filament values below, and filament changes, are for slot %d; "
                     "if the problem is about another slot, tell the user to open that filament in the Filament tab and ask again."
                     % ("; ".join("%d=%s" % (i + 1, n) for i, n in enumerate(fils)), slot))
    for ptype in ("process", "filament", "printer"):
        v = vals.get(ptype) or {}
        items = ["%s=%s" % (k, short(v[k])) for k in SUMMARY_KEYS[ptype] if k in v]
        if items:
            lines.append("%s values: %s" % (ptype.capitalize(), "; ".join(items)))
    if snap.get("plate"):
        objs = []
        for o in snap["plate"][:12]:
            size = "x".join(str(x) for x in o.get("size_mm", [])) or "?"
            objs.append("%s %s mm%s" % (o["name"], size, " x%d" % o["copies"] if o.get("copies", 1) > 1 else ""))
        lines.append("Objects on the plate: " + "; ".join(objs))
    else:
        lines.append("Objects on the plate: none")
    return "\n".join(lines)


# -------------------------------------------------------------------- skill --
# Skill incluse nel plugin: generate da skills/*.md con incorpora_skill.py (non modificarle qui).
# L'utente puo aggiungerne altre nella cartella "skills" del plugin: un file .md, oppure una
# cartella con SKILL.md (intestazione name / description); quelle con lo stesso nome prevalgono.

# >>> SKILL INCORPORATE (blocco generato da incorpora_skill.py: non modificare a mano)
BUILTIN_SKILLS = {
    "calibration-guide": {
        "description": "Which OrcaSlicer calibration test (menu Calibration) fixes which defect, the order to run them, how to read each printed test and which Orca key receives the result. Read when the user asks how to calibrate or tune a new filament, or mentions a temperature tower, flow ratio / flow rate / extrusion multiplier test, pressure advance / K factor / linear advance / flow dynamics, retraction tower, max volumetric speed / max flowrate test, VFA, input shaping, jerk / cornering, tolerance test or adaptive PA.",
        "content": "# Calibration guide (OrcaSlicer 2.5.1)\n\n## Rules for the AI\n- The user runs every test from the **Calibration** menu in the top bar; each test opens a new project. Afterwards tell the user to start a new project to leave calibration mode.\n- Calibrate with the same printer, filament and process presets that will be used. The flow ratio test starts from the value already in the filament preset.\n- Choose the test, explain how to read it, do the arithmetic, propose the change. Printer/firmware results (input shaping, jerk, resonance avoidance) are entered by the user by hand.\n- Rule out hardware first, or the numbers are meaningless: dry filament, clean nozzle without partial clog, clean extruder gears, clean plate, correct first layer.\n- Bambu printers: when sending an Orca test, untick the flow (dynamics) calibration option in the send dialog, otherwise the printer measures its own value and the test is not what was printed.\n\n## Symptom → test → key\n| Symptom | Test | Result goes to |\n|---|---|---|\n| Stringing plus weak layers, saggy bridges, rough or dull walls | Temperature | `nozzle_temperature`, `nozzle_temperature_initial_layer` (filament) |\n| Under-extrusion or matte, rough walls only at high speed; extruder clicks | Max volumetric speed | `filament_max_volumetric_speed` (filament) |\n| Bulging or rounded corners, gaps right after corners, thin or blobby line ends, uneven seams | Pressure advance | `enable_pressure_advance`, `pressure_advance` (filament) |\n| Gaps or ridges between top lines, general over/under-extrusion, walls too thick | Flow ratio | `filament_flow_ratio` (filament) |\n| Strings and blobs once temperature is right | Retraction | `filament_retraction_length` (filament) |\n| Holes too small, parts do not fit | Tolerance test | `xy_hole_compensation`, `xy_contour_compensation` (process) |\n| Ringing / ghosting after sharp corners | Input shaping | printer firmware (by hand) |\n| Fine vertical ripples at certain speeds | VFA | printer resonance avoidance (by hand) or `outer_wall_speed` (process) |\n| Corners overshoot | Cornering | printer jerk / junction deviation (by hand) |\n| PA right at one speed, wrong at another | Adaptive PA | `adaptive_pressure_advance_model` (filament) |\n\n## Order\n1. Filament calibration, repeat for each new filament: **Temperature → Max flowrate → Pressure advance → Flow ratio → Retraction**. If flow ratio moved a lot, rerun a quick PA test.\n2. Advanced, mostly printer-related, only after hardware changes or moving the printer: Cornering → Input shaping → VFA → Adaptive PA.\n3. Tolerance last, because it depends on everything above.\n\n## Temperature (Calibration → Temperature)\n- Tower of blocks, each block printed at a different nozzle temperature. Keep start and end inside the filament's recommended range.\n- Read each block: stringing (cooler is usually better, too cold strings too), layer bonding (hotter is stronger), bridges/overhangs (too hot sags), finish.\n- Several good blocks: take the middle. For fast or high-flow printing take the upper part of the good range.\n- Save: `nozzle_temperature` (filament); `nozzle_temperature_initial_layer` equal or slightly higher. Safe limit: inside the filament's minimum..maximum range (enforced by the plugin). Never edit the range itself.\n\n## Max volumetric speed (Calibration → Max flowrate)\n- Default start 5, end 20 mm³/s, step 0.5. If it reaches the top intact, reprint with a higher end.\n- Read three heights from the bottom: (1) gloss lost / finish rougher, (2) quality lost: walls deform, first at curves, (3) failure: heavy deformation and under-extrusion.\n- Flow at a height = start + height_mm × step, or read it in Preview with the \"Flow\" colour scheme at that layer.\n- Save `filament_max_volumetric_speed` (filament) below point (2) with a 10-20 % margin, never at point (3). The plugin allows lowering freely but raising by at most +10 % per change; if the test shows a much higher limit, raise in steps or let the user set it by hand.\n- Point (1) is meant for a separate \"max external volumetric speed\" limit that is not a key in Orca 2.5.1; to keep visible surfaces glossy, lower `outer_wall_speed` and `top_surface_speed` (process) instead.\n- Faster flow needs the upper part of the temperature range. Bambu 0.2 mm nozzle: about 2 mm³/s.\n\n## Pressure advance (Calibration → Pressure advance)\n- Use the direct-drive or Bowden version matching the extruder. Marlin needs Linear Advance enabled (M900).\n- **Tower**: does not depend on the first layer. PA rises one step per mm of height: PA = start + step × height_mm (example 0 + 0.002 × 8 = 0.016).\n- **Pattern**: chevrons with printed values; pick the corner that is sharp and fully extruded, no bulge, no gap.\n- **Line**: fastest, depends on the first layer (enable bed mesh). Pick the most even line.\n- Too low PA: corners bulge and round off. Too high: gaps, thin or missing extrusion at corners and line starts.\n- Save: `enable_pressure_advance` = `1` and `pressure_advance` (filament). Direct-drive results are usually a few hundredths (examples 0.015-0.036).\n- Bambu Lab: the printer stores a K value per filament (Flow Dynamics calibration: automatic on X1, A1, H2 and P2S series, manual only on P1). When `enable_pressure_advance` is `1` the slicer value overrides the stored one. Expect about 10 % scatter between runs; automatic K on eddy-sensor printers (A1, H2D) is intentionally higher than a manual pattern result. With 0.2 mm nozzles automatic K is unreliable: use the manual pattern.\n- Prusa (MK4/S, MK3.9/S, XL, MINI/+): firmware Pressure Advance; the stock start G-code sets a tuned value per nozzle size and Prusa recommends keeping it. Override only when a test is clearly better.\n\n## Flow ratio (Calibration → Flow ratio)\n- **YOLO (recommended)**, Archimedean-chords blocks: range -0.05..+0.05, step 0.01 (\"perfectionist\": -0.04..+0.035, step 0.005). New = old + modifier (0.98 + 0.01 = 0.99).\n- **Pass 1 / Pass 2** (legacy, monotonic lines): new = old × (100 + modifier) / 100; Pass 2 covers -9..0 around the Pass 1 result.\n- Read the top surface under low-angle light: smoothest surface, no gaps between lines, little or no ridge where the inner spiral meets the outer arcs. Reject blocks with faint gaps.\n- Save `filament_flow_ratio` (filament). Plugin limit 0.8-1.2; typical results 0.95-1.05. Leave `print_flow_ratio` (process) at `1`: it multiplies the filament value.\n- Foaming filaments (LW-PLA, PLA Aero, LW-ASA) need ratios far below 0.8 (Bambu starts near 0.6): outside the plugin limit, the user sets it by hand.\n- Bambu X1 lidar auto flow: not for transparent, silk, sparkle, marble, metal-look or TPU; use the manual test.\n\n## Retraction (Calibration → Retraction test)\n- Tower with notches at increasing retraction length. Defaults 0 → 2 mm, step 0.1 (direct drive); Bowden 1 → 6 mm, step 0.2.\n- Choose the shortest length that gives a clean section. Read the length from the retraction-tower comment in the G-code preview at that height.\n- PLA and ABS are often clean from the bottom: 0.2-0.4 mm is then enough. Still stringy at the top: dry the filament and check that the nozzle is seated and not leaking; more retraction will not fix it.\n- Save `filament_retraction_length` (filament; `nil` = use the printer value). Limit 0..min(8 mm, max(2 mm, 2 × printer retraction)). Speed: `filament_retraction_speed`.\n\n## Tolerance (right-click plate → Add Handy Model → Orca Tolerance Test)\n- Six hex holes (0-0.4 mm clearance) plus a hex tester; check with a 6 mm hex key and calipers.\n- Holes too tight: increase `xy_hole_compensation` (positive = bigger holes). Outer size too big: negative `xy_contour_compensation`. Work in steps of 0.02-0.05 mm and reprint.\n- Filament shrinkage compensation is material data: the plugin does not change it; the user may set it by hand. First-layer flare is `elefant_foot_compensation` (see defect-dimensional-accuracy).\n\n## Cornering (Calibration → Cornering)\n- Skip if corners look fine. The firmware (Klipper, Marlin JD/jerk, RepRap) caps the value and Orca cannot see the cap: if the whole tower looks the same, the limit is reached.\n- Result goes to the printer profile (Motion ability → Jerk limitation) or firmware: by hand. In the process preset jerk keys (`default_jerk`, `outer_wall_jerk`) may only be lowered, never above the printer limits.\n\n## Input shaping (Calibration → Input shaping)\n- Prefer the printer's own automatic calibration when it has one (most recent printers; Prusa CORE One L and XL have integrated accelerometers, other Prusa models use an optional one).\n- Orca test: glossy opaque filament, Ringing Tower, 15-110 Hz, damping 0.1-0.2; read X/Y frequency from the heights, then the damping test. The user stores the values in firmware/printer settings and restores normal acceleration afterwards.\n\n## VFA (Calibration → VFA)\n- After input shaping. Tower at rising speeds (e.g. 20-200 mm/s, step 10) covering the outer-wall speeds used; find bands where walls get rougher.\n- Fix: printer resonance avoidance range (by hand), or keep `outer_wall_speed` (process) outside the bad band. Prusa CORE One/L and XL: run phase stepping calibration from the printer menu (a failed run usually means belt tension).\n\n## Adaptive pressure advance\n- Worth it on fast CoreXY printers with high-flow nozzles and a wide range of speeds and accelerations; useless with one speed and one acceleration. Validated on Klipper; on Marlin disable it if walls hesitate.\n- Run PA pattern tests for each pair, e.g. accelerations 1k/2k/4k × speeds 50/100/150/200 mm/s, PA step 0.001, never above the maximum acceleration recommended by input shaping.\n- Enter one line per test, \"PA, flow mm³/s, acceleration\", in `adaptive_pressure_advance_model`, set `adaptive_pressure_advance` = `1`, keep a median value in `pressure_advance` as fallback for tool changes and prime tower. `adaptive_pressure_advance_bridges`: about half the normal PA (0 disables). Leave `adaptive_pressure_advance_overhangs` at `0` until the model is proven.\n\n## Sources\n- https://www.orcaslicer.com/wiki/guides/calibration_guide.html\n- https://www.orcaslicer.com/wiki/calibration/temp_calib.html\n- https://www.orcaslicer.com/wiki/calibration/volumetric_speed_calib.html\n- https://www.orcaslicer.com/wiki/calibration/pressure_advance_calib.html\n- https://www.orcaslicer.com/wiki/calibration/flow_ratio_calib.html\n- https://www.orcaslicer.com/wiki/calibration/retraction_calib.html\n- https://www.orcaslicer.com/wiki/calibration/tolerance_calib.html\n- https://www.orcaslicer.com/wiki/calibration/cornering_calib.html\n- https://www.orcaslicer.com/wiki/calibration/input_shaping_calib.html\n- https://www.orcaslicer.com/wiki/calibration/vfa_calib.html\n- https://www.orcaslicer.com/wiki/calibration/adaptive_pressure_advance_calib.html\n- https://wiki.bambulab.com/en/bambu-studio/Calibration\n- https://wiki.bambulab.com/en/software/bambu-studio/calibration_pa\n- https://wiki.bambulab.com/en/software/bambu-studio/calibration_flow_rate\n- https://wiki.bambulab.com/en/knowledge-sharing/flowrate-calibration-by-microlidar\n- https://help.prusa3d.com/article/pressure-advance_814986\n- https://help.prusa3d.com/article/input-shaper-core-one-mk4-s-mk3-9-s-mk3-5-s-xl-mini_451816\n- https://help.prusa3d.com/article/phase-stepping-core-one-l-core-one_914247\n- https://help.prusa3d.com/article/phase-stepping-xl_681760\n- https://wiki.bambulab.com/en/knowledge-sharing/02-mm-nozzle-FAQ\n",
    },
    "defect-clogs-heat-creep": {
        "description": "Diagnosis and prevention (not repair) of clogs, heat creep, extrusion stopping mid print or missing at the start, grinding, filament stuck on the nozzle and blobs around the hotend. Read when the user reports a clog, clogged or jammed nozzle, heat creep, extruder clicking or skipping, ground filament, no extrusion, air printing, print stopped extruding, filament sticking to the nozzle or a blob on the hotend.",
        "content": "# Clogs, heat creep, grinding, blobs on the hotend\n\nScope: the plugin cannot clear a clog. Explain the checks and repair steps to the user, then use slicer settings only to prevent a repeat. Never \"fix\" a hardware cause with parameters.\n\n## How to recognize it\n- **Full clog**: toolhead moves but nothing comes out (\"air printing\"); filament does not come out when extruded from the printer screen at temperature.\n- **Partial clog**: thin, inconsistent lines, gaps, missing layers; filament curling up onto the nozzle (early sign).\n- **Clicking extruder**: loud clicks usually mean resistance in the nozzle/hotend; light clicks more often point to the gears (Prusa Nextruder guidance). Shavings or a bitten notch in the filament = grinding/stripping.\n- **Heat creep**: print starts fine, then extrusion fades or stops after some time with no error; typical with PLA (also TPU, PETG) in a closed or hot enclosure or a warm room. Filament softens too high in the heatbreak and swells.\n- **Stops mid print**, other causes: spool empty/tangled, brittle filament snapped, ground filament, overheated extruder motor driver.\n- **No extrusion at start**: nozzle drained by oozing during preheat; nozzle too close to the plate (extrusion recovers after 2-3 layers); ground filament; clog.\n- **Build-up on the nozzle**: residue grows on the nozzle outside during long prints (mostly PETG/PETG-CF), leaves gaps and rough spots.\n- **Blob on the hotend**: plastic wrapped around nozzle and heater block, usually after the first layers detach and stick to the nozzle.\n\n## Likely causes, most common first\n1. Heat creep from a hot printing environment: closed door/lid with PLA, high bed temperature heating the chamber, ambient above about 30-35 °C. Bambu: keep the enclosure at least 10 °C below the filament's glass transition.\n2. Debris in the nozzle: CF/GF particles, burnt material, high-temp filament residue after switching to PLA/PETG/TPU, dust, many short heat/cool cycles.\n3. Melt rate too low for the speed: nozzle temperature too low or speed/flow too high (filament does not fully melt).\n4. Extruder side: debris in the gears, wrong idler tension, filament softened and flattened by the gears (very soft TPU, damp PVA), inconsistent diameter (bad spool), filament sensor or cutter blocked (Bambu X1/P1).\n5. Very low flow for long times: very thin layers, very slow printing or long ironing → filament sits in the hot zone (feeds heat creep).\n6. Excessive retraction length/speed (pulls molten material into the cold zone; grinds filament).\n7. Wet filament (steam, swelling, partial clogs over time).\n8. Hardware cooling faults: hotend/heatsink fan slow or blocked, dust in heatsink fins, missing thermal paste, PTFE not seated, metal-filled filament conducting heat upward.\n9. Profile mismatch: high-flow nozzle printed with a standard profile (or the reverse), fiber-filled filament on a 0.2 mm nozzle.\n10. Blob/build-up: poor first-layer adhesion, wet PETG, flow too high, faulty nozzle wiper, many travels.\n\n## Questions worth asking (only when the answer changes the fix)\n- When did extrusion fail: from the first line, after some minutes/hours, at a specific height? (start → priming/Z offset/clog; later → heat creep/grinding/spool)\n- Can the printer extrude by hand from the screen at print temperature? Is there clicking, are there shavings?\n- Printer model, door/lid open or closed, room temperature, plate type and bed temperature?\n- Material, previous material in the nozzle (high-temp or CF/GF?), nozzle size and type (standard/high flow, brass/hardened)?\n- Any printer error (Bambu HMS: hotend fan speed, extruder overload)?\n\n## Slicer fixes\nPrevention only, after the clog is cleared. These settings do not unclog anything.\n\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| plate temperature key in use: `cool_plate_temp`, `textured_plate_temp`, `hot_plate_temp`, `eng_plate_temp`, `supertack_plate_temp` or `textured_cool_plate_temp` (filament) | decrease (PLA/TPU heat creep in enclosed printers) | -5 °C | raise at most +10 °C over current, never above 120 °C; Bambu PLA on textured PEI about 55 °C, Cool Plate about 35 °C | less adhesion: add brim if corners lift |\n| `nozzle_temperature` (filament) | increase if under-melting at high speed; decrease if heat creep with metal-filled filament or overheating | ±5 °C | inside the filament's nozzle temperature range | higher: more stringing; lower: under-extrusion |\n| `filament_max_volumetric_speed` (filament) | decrease if clogs/grinding appear at high speed | -10-20 % | lower freely; raise at most +10 % | slower print |\n| `layer_height` (process) | increase very thin layers (more flow, less heat creep) | e.g. 0.08 → 0.15-0.2 mm | ≤ 75 % of nozzle diameter | coarser surface |\n| `filament_retraction_length` (filament) | decrease if excessive | -0.2-0.5 mm | 0 .. min(8 mm, max(2 mm, 2x printer retraction)); direct drive about ≤ 2 mm | more stringing |\n| `filament_retraction_speed` (filament) | decrease if grinding | up to -50 % as a test | > 0 and ≤ max(1.5x printer value, 30 mm/s) | slightly more ooze |\n| `slow_down_min_speed` (filament) | increase if long very slow layers precede the jam | +5 mm/s | within machine limits | small layers cool less |\n| `ironing_type` (process) | `no ironing` if jams happen during ironing | - | - | rougher top surface |\n| `filament_long_retractions_when_cut` (filament) — BY HAND | disable (beta feature raises clog risk) | - | by hand only (plugin cannot check it): Filament → Setting overrides → Retraction → Long retraction when cut | more purge waste |\n| `skirt_loops` (process) | 1-2 to prime a drained nozzle | +1 | 0-10 | slightly more filament |\n| `filament_flow_ratio` (filament) | decrease for PETG build-up on nozzle | to 0.93-0.94 | 0.8-1.2 | under-extrusion below about 0.93 |\n| `fan_min_speed` / `fan_max_speed` (filament) | increase for PETG build-up on nozzle | +10-20 points | 0-100 % | weaker layer bonding |\n\nPETG build-up recipe (Bambu): dry the filament, check nozzle wear, then nozzle temperature -5 to -10 °C, max volumetric speed -4 to -5 mm³/s, a bit more cooling, flow 0.93-0.94; for many travels, retraction about 1.2-1.6 mm at 40-60 mm/s (inside the limits above) and parts closer together. For build-up, when print or volumetric speed is lowered, lower the nozzle temperature too.\n\n## Checks the user must do by hand (hardware, material, printer settings)\nSafety: power off before touching wiring; heat the nozzle only from the printer menu.\n- **Locate the clog**: heat and extrude from the screen. Bambu X1/P1: AMS disconnected, detach the hotend and push filament through by hand (passes → hotend clear, check the extruder).\n- **Clear the nozzle**: push fresh PLA at high temperature (Prusa: 260 °C after PLA, 280 °C after PETG/ASA, wait about 2 min); needle (0.3-0.35 mm) only in non-high-flow nozzles; cold pull (monthly as maintenance, nylon works well); replace the nozzle if nothing helps.\n- **After high-temp or CF/GF filaments** before PLA/PETG/TPU: unload at 250-300 °C, load the new filament and keep extruding while cooling to 220-240 °C until it flows clean.\n- **Heat creep**: PLA/TPU on X1/P1S/enclosed printers: open the door and/or remove the top glass, or use the Cool Plate. Check the hotend fan (Prusa MK3: 4000-4400 RPM), dust in the heatsink, thermal paste on the heatbreak thread, PTFE fully seated, E3D V6: about 0.5 mm gap nozzle hex to heater block. Unload filament while hot after printing.\n- **Extruder**: clean gear teeth, check idler tension and motor strength; Bambu: clean filament sensor, replace a dull cutter blade; cut off deformed filament.\n- **Filament**: dry it; diameter 1.75 ± 0.03 mm; avoid very soft TPU (85A) and damp PVA where unsupported; spool runs free, filament not brittle.\n- **Nozzle choice**: fiber-filled filament on 0.6-0.8 mm, never 0.2 mm; select the profile matching the installed nozzle (high flow vs standard).\n- **Start of print**: if extrusion returns after 2-3 layers, the nozzle is too close to the plate: Z offset/levelling (printer setting, by hand).\n- **Blob on hotend**: heat about 30 °C above print temperature, remove softened plastic with pliers away from heater/thermistor wires; refit the silicone sock; clean the plate, check first-layer adhesion; Bambu: enable nozzle clumping detection, check the nozzle wiper.\n- **Printer retraction (printer settings, user changes by hand)**: if the printer retraction length is very long for a direct drive, explain and let the user reduce it.\n\n## Calibration in Orca (menu Calibration → ...)\n- **Temperature** tower: confirm the filament is printed hot enough for its speed.\n- **Max flowrate** (max volumetric speed): find the real melt limit; put a value 10-20 % below the point where the walls start to deform into `filament_max_volumetric_speed`.\n- **Retraction test**: use the shortest clean length instead of a long guess.\n- **Flow ratio**: for PETG build-up or over-extrusion. See calibration-guide.\n\n## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)\n- **PLA**: most prone to heat creep (lowest softening point): door open or Cool Plate, moderate bed temperature, avoid very slow/thin printing for hours.\n- **PETG**: build-up on the nozzle and blobs; dry, flow 0.93-0.96, lower temperature when printing slower. Softens in hot enclosures too.\n- **ABS/ASA**: printed closed; clogs mostly from residue or too-low temperature. When switching to PLA afterwards, purge hot first.\n- **TPU**: heat creep and gear tangling; minimal retraction, slow printing, gentle load/unload (Bambu H2D: retract only twice at 175 °C, then pull it out).\n- **PA/PC**: dry thoroughly; residue when switching back to low-temp materials.\n- **CF/GF**: particles build up in the nozzle: larger hardened nozzle, regular cold pulls.\n\n## Sources\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/clog\n- https://wiki.bambulab.com/en/filament-acc/filament/heat-creep\n- https://wiki.bambulab.com/en/knowledge-sharing/how_to_avoid_nozzle_clogs\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/filament-sticks-to-nozzle\n- https://wiki.bambulab.com/en/x1/troubleshooting/how-to-check-which-part-is-clogged\n- https://wiki.bambulab.com/en/x1/troubleshooting/filament-not-extruding\n- https://wiki.bambulab.com/en/general/troubleshooting/extrusion-failure\n- https://wiki.bambulab.com/en/p2s/troubleshooting/hotend_blob\n- https://wiki.bambulab.com/en/h2/troubleshooting/tpu-clogging\n- https://wiki.bambulab.com/en/filament-acc/filament/dry-filament\n- https://wiki.bambulab.com/en/software/bambu-studio/parameter/retraction\n- https://help.prusa3d.com/article/extrusion-stopped-mid-print-heat-creep_1948\n- https://help.prusa3d.com/article/extruder-blob_2005\n- https://help.prusa3d.com/article/clogged-nozzle-core-one-core-one-l-xl-mk4-s-mk3-9-s_411823\n- https://help.prusa3d.com/article/cooling_127569\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_ironing.html\n- https://www.orcaslicer.com/wiki/printer_settings/extruder/printer_extruder_retraction.html\n- https://www.orcaslicer.com/wiki/calibration/volumetric_speed_calib.html\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/clogged-extruder/\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/stops-extruding-mid-print/\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/grinding-filament/\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/not-extruding-at-start-of-print/\n- https://www.obico.io/blog/3d-print-troubleshooting-guide/\n",
    },
    "defect-dimensional-accuracy": {
        "description": "Parts out of size: holes too small, pegs or screws that do not fit, outer dimensions too big or small, shrinkage that grows with part size, wrong Z height, ovals instead of circles, elephant foot as a dimensional error; Orca XY hole/contour compensation, elephant foot compensation, precise wall, polyholes and the tolerance test. Read when the user reports wrong dimensions, holes too tight, parts that do not fit together, tolerances, clearance, press fit, shrinkage, a part smaller or bigger than designed, or a flared bottom ruining the fit.",
        "content": "# Dimensional accuracy\n\n## How to recognize it\nAsk for caliper measurements versus the designed values before changing anything.\n- **Holes undersized** (most common): screws, pins, bearings or magnets do not go in; outer size is close to nominal.\n- **Outer size off by a constant amount** (e.g. always +0.15 mm on any size): line width / flow / wall placement.\n- **Error growing with part size** (e.g. -0.1 mm at 20 mm, -0.5 mm at 100 mm): thermal shrinkage of the material.\n- **Only the bottom layers wider**: elephant foot (first layer squish).\n- **Height off by up to one layer**: the model height is not a multiple of the layer height.\n- **Circles printed as ovals, or one axis off**: mechanics (belts, firmware steps), not the slicer.\n\n## Likely causes, most common first\n1. Holes shrink inward: plastic contracts toward the hole centre, round holes are approximated by short segments, and the seam bump sits inside the hole.\n2. Flow ratio too high (parts and walls oversize, bulging tops) or too low (undersize, gaps).\n3. Elephant foot: first layer squished by a low Z offset or soft from a hot bed, plus the weight of the layers above.\n4. Thermal shrinkage: highest on ABS/ASA, PA, PC; small on PLA and PETG; reduced by fibre-filled grades.\n5. Wall order: with inner walls printed first, the outer wall is pushed outward by the overlap.\n6. Mechanics: belts loose (ovals), wrong steps/mm or rotation distance in firmware (whole axis scaled).\n7. Model: low-resolution STL (faceted holes), holes close to the nozzle size (below about 1 mm), no chamfers or lead-ins, tolerances never designed in.\n8. Measuring error: measuring near the first layer, at corners (pressure advance effects), on a warm part, or squeezing the caliper.\n\n## Questions worth asking (only when the answer changes the fix)\n- What is too big or small: holes, outer size, bottom edge, height? By how much (mm)?\n- Is the error the same on a small and a large part, or proportional to size?\n- Which material and plate? Elephant foot compensation differs by plate type.\n- Was flow ratio calibrated for this filament?\n- Is the fit part designed with clearance (typically a few tenths of a mm for sliding fits)?\n\n## Slicer fixes\nFix the cause in this order: measurement → flow → elephant foot → holes/contours → shrinkage (by hand).\n\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `xy_hole_compensation` (process) | increase if holes are tight | +0.05 mm (hole diameter grows by 2× the value) | usually 0 to +0.2 mm; more points to a model or flow problem | affects every hole, also ones meant to be tight |\n| `xy_contour_compensation` (process) | decrease if outside is too big, increase if too small | ±0.05 mm | usually within ±0.15 mm | thin features and text get thinner or vanish with negative values |\n| `elefant_foot_compensation` (process) | increase if the base is flared | +0.05 mm; about 0.1-0.2 mm with a 0.4 mm nozzle | ≤ 0.25 mm with a 0.4 mm nozzle; skipped with a raft | brim may look detached in preview; too much: brim does not attach, thin first-layer details distort |\n| `elefant_foot_compensation_layers` (process) | increase if the flare spans several layers | 1 → 2-3 | integer ≥ 1 | compensation fades linearly over these layers |\n| `precise_outer_wall` (process) | enable | `1` | only works with `wall_sequence` = `inner wall/outer wall` | none relevant; more consistent outer wall |\n| `wall_sequence` (process) | outer wall undisturbed | `inner-outer-inner wall` (needs ≥ 3 walls) or `outer wall/inner wall` | | weaker overhangs; outer/inner makes the seam less consistent; `precise_outer_wall` is then ignored (use one or the other) |\n| `hole_to_polyhole` (process) | enable for round holes on pins/screws | `1` | | holes become polygons (by design) |\n| `precise_z_height` (process) | enable for exact height | `1` | | last few layers get adjusted heights |\n| `filament_flow_ratio` (filament) | adjust from the Flow Rate calibration | ±0.02 | 0.8-1.2 | wrong value causes gaps or bulging tops |\n| first-layer plate temperature of the plate in use, e.g. `textured_plate_temp_initial_layer`, `hot_plate_temp_initial_layer`, `cool_plate_temp_initial_layer`, `eng_plate_temp_initial_layer`, `supertack_plate_temp_initial_layer`, `textured_cool_plate_temp_initial_layer` (filament) | decrease if elephant foot persists | -5 °C | stay in the material's recommended bed range; increases at most +10 °C, never above 120 °C | weaker adhesion, more warping |\n| `seam_position` (process) | move the seam away from critical holes | `back` or `aligned` (or paint the seam) | | seam moves to another visible place |\n\nNotes:\n- XY compensation is the right tool for a constant error. A proportional error is shrinkage and is not fixed by XY compensation.\n- Hole and contour compensation are per filament and process: repeat the test when the material changes.\n\n## Checks the user must do by hand (hardware, material, printer settings)\n- **Measure correctly**: let the part cool to room temperature; measure the middle of a face, not corners; measure well above the first layer (or on a tall test piece, the upper layers only); light caliper pressure.\n- **Shrinkage is material data: the plugin never changes it.** If the error is proportional to size, the user can enter the filament's Shrinkage (XY) and Shrinkage (Z) values by hand in the filament preset, as measured / designed × 100% (a 20 mm cube measuring 19.9 mm gives 99.5%), or scale the object in Orca. Re-check holes afterwards.\n- **First layer**: correct Z offset and levelling (too low a nozzle makes the first layers wide for many layers); clean plate. See defect-first-layer.\n- **Belts**: correct tension; loose belts print circles as ovals. Bambu CoreXY: loosen the tensioner screws, move the toolhead, retighten, then run Vibration compensation. Prusa: see the belt checks in defect-layer-shift.\n- **Firmware steps / rotation distance** (printer side, by hand): only if a 100 mm part is off on one axis while flow and compensation are right.\n- **Filament**: dry it (moisture makes extrusion uneven); diameter should be within about ±0.02 mm of 1.75 mm.\n- **Model**: export STL at high resolution or import STEP; design clearances and chamfers; holes near nozzle size are not reliable.\n\n## Calibration in Orca (menu Calibration → ...)\n- **Calibration → Flow ratio** first (see calibration-guide), together with pressure advance; dimensional tests come last because they depend on all the others.\n- **Orca Tolerance Test**: right-click the plate → Add Handy models → Orca Tolerance Test. Hexagonal holes with 0, 0.05, 0.1, 0.2, 0.3, 0.4 mm clearance and a hex tester (or a 6 mm Allen key). The tightest hole that fits shows the clearance the printer needs; tune `xy_hole_compensation` and `xy_contour_compensation`, reprint, repeat.\n- **Screw hole test** (Bambu method): print a hole gauge with compensation 0, find the hole that fits a known screw snugly (an M6 is about 5.9 mm), enter that offset, reprint to confirm; add further offsets if needed.\n- **Elephant foot measurement**: print a 25 × 25 × 10 mm cube with compensation 0 and no brim (`brim_type` (process) = `no_brim`), let it cool on the plate, measure X and Y at the top and at the base (mid-face). Compensation ≈ average of (base - top) for X and Y, e.g. (0.09 + 0.11) / 2 = 0.10 mm. Repeat when changing plate type.\n\n## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)\n- PLA, PETG: low shrinkage; errors are usually flow, holes or elephant foot. A hotter bed increases elephant foot on any material.\n- ABS/ASA: noticeable shrinkage (often around 0.5-1%) and warping that also distorts size; keep the enclosure closed.\n- TPU: soft, measures smaller under caliper pressure; design generous clearances.\n- PA/PC: high shrinkage and moisture uptake; dry before printing and calibrating.\n- CF/GF filled: fibres limit shrinkage, usually the most dimensionally stable choice for fits.\n\n## Sources\n- https://wiki.bambulab.com/en/knowledge-sharing/3d-prints-shrinkage\n- https://wiki.bambulab.com/en/software/bambu-studio/xy-hole-contour-compensation\n- https://wiki.bambulab.com/en/software/bambu-studio/parameter/elephant-foot\n- https://wiki.bambulab.com/en/x1/maintenance/belt-tension\n- https://wiki.bambulab.com/en/p2s/maintenance/belt-tension\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/severe-layer-artifacts\n- https://help.prusa3d.com/article/elephant-foot-compensation_114487\n- https://www.orcaslicer.com/wiki/calibration/tolerance_calib.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_precision.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_and_surfaces.html\n- https://www.orcaslicer.com/wiki/guides/calibration_guide.html\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/dimensional-accuracy/\n- https://www.obico.io/blog/3d-print-troubleshooting-guide/\n",
    },
    "defect-extrusion": {
        "description": "Covers global or local under-extrusion, over-extrusion, inconsistent or bumpy extrusion, gaps between walls or between walls and infill, weak stringy infill and uneven gloss (shiny vs matte bands). Read when the user reports \"under-extruding\", \"not enough plastic\", \"gaps between lines/walls\", \"holes in walls\", \"too much plastic\", \"overfilled/rough surface\", \"weak infill\", \"infill not touching walls\", \"missing material at corners\" or \"different shine/gloss\".",
        "content": "# Extrusion problems (under, over, inconsistent, gloss)\n\n## How to recognize it\n- **Global under-extrusion**: thin separated lines everywhere; on a 3-wall cube the walls do not fuse at the top; fragile parts.\n- **Local**: gaps only in fast infill/long lines, or only at corners and line starts (pressure advance).\n- **Over-extrusion**: walls too wide, material piled near walls on top surfaces, rough overfilled look, nozzle dragging, parts too big.\n- **Inconsistent**: one line changes width; random bumps or bands not linked to geometry.\n- **Gaps between infill and walls**: infill not touching the inner wall; pinholes along edges.\n- **Weak infill**: thin, stringy, broken lines.\n- **Different gloss**: shiny vs matte zones where speed changes (overhang or layer-time slowdown).\n\n## Likely causes, most common first\n1. Resistance or partial clog: stuck spool, kinked/dirty PTFE tube, dirty or worn gears, wrong idler tension, debris in the nozzle (common after CF/GF). Sudden onset on a profile that used to work = almost always this.\n2. Flow above what the hotend can melt (speed × line width × layer height): under-extruded fast infill, weak layers, matte patches.\n3. Flow ratio wrong for this spool (differs by material, brand, even colour).\n4. Pressure advance wrong: missing material at corners/line starts, or lines not touching after accelerations when far too high (Bambu: 0.25 typed instead of 0.025).\n5. Nozzle temperature too low for the speed; steel/hardened nozzles need a bit more heat.\n6. Wet filament, or poor filament with variable diameter.\n7. Line width far below nozzle, extremely low layer height, too little infill/wall overlap, sparse infill too fast.\n8. Gloss: big speed (flow) differences on the same outer surface.\n\n## Questions worth asking (only when the answer changes the fix)\n- Sudden (hardware) or always with this filament (profile)?\n- Everywhere, only corners, only infill, only fast features?\n- Vendor filament on its stock profile or third-party? Flow / pressure advance ever calibrated for this spool?\n- Extruder clicking, ground filament, spool left out for days?\n- Which nozzle (size, brass/hardened) is installed, and does the printer profile match?\n\n## Slicer fixes\nFix hardware first (next section). Then, in this order:\n\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `filament_flow_ratio` (filament) | increase for gaps, decrease for overfill | ±0.02 (visual), or the result of the Orca flow test | 0.8-1.2; normal range 0.95-1.05 | masks hardware faults; Bambu filament: keep the profile default |\n| `filament_max_volumetric_speed` (filament) | decrease when fast features under-extrude | -10% to -20% | lower freely; raise at most +10% | slows every fast feature, longer print |\n| `nozzle_temperature` (filament) | increase if melt limit is reached at speed; decrease if overfilled and glossy-runny | +5 °C (max +10 °C) | inside the filament nozzle_temperature_range | stringing, overhang droop |\n| `sparse_infill_speed` / `inner_wall_speed` / `internal_solid_infill_speed` (process) | decrease | -20% to -30% | never above machine limits | longer print |\n| `pressure_advance` (filament, used when `enable_pressure_advance` = `1`) | set from calibration; lower if lines do not touch after accelerations | calibrated value only | typical 0.02-0.04 (fast direct drive); >0.1 almost never right | corner bulges or gaps if wrong |\n| `infill_wall_overlap` (process) | increase for gaps between sparse infill and walls | 15% → 20-25% | ≤ 30% | rough surface from excess at wall junction |\n| `top_bottom_infill_wall_overlap` (process) | increase for pinholes where solid infill meets walls | 25% → 30% | ≤ 35% | slight ridge at edges |\n| `line_width`, `inner_wall_line_width`, `sparse_infill_line_width` (process) | raise if set below the nozzle diameter | to 100-115% of nozzle | 75%-150% of nozzle | more flow needed per mm |\n| `layer_height` (process) | increase if very thin layers (≤0.08 mm) extrude unevenly or show \"fish scale\" at speed | to 0.12-0.20 mm | ≤ 75% of nozzle diameter | more visible layer lines |\n| `set_other_flow_ratios` = `1` + `outer_wall_flow_ratio` / `inner_wall_flow_ratio` / `sparse_infill_flow_ratio` (process) — BY HAND | per-feature tuning once filament flow is right | ±0.02-0.05 | by hand only (plugin cannot check it), keep 0.8-1.2; Process → Quality → Wall and surfaces, see defect-triage | can mask a wrong filament flow |\n\n**Weak infill**: lower `sparse_infill_speed` (up to -50% to test); `sparse_infill_line_width` ~115% of nozzle; `fill_multiline` (process) 2 for stronger infill at the same density; raise `sparse_infill_density` (process) in 5-10% steps; prefer `gyroid` or `cubic` for `sparse_infill_pattern` (process) on mechanical parts. Strength comes mainly from walls: `wall_loops` (process) +1. If `infill_combination` (process) = `1`, disable it (thicker combined infill layers need more flow). Do not set `infill_anchor_max` (process) to 0 (PETG especially benefits from anchors).\n\n**Gaps where a smaller section starts on a larger one (floor corners)**: `wall_loops` +1-2, `top_shell_layers` (process) +1-2, `sparse_infill_density` +10%.\n\n**Different gloss**: keep outer wall speed uniform.\n- `outer_wall_speed` (process) lower, towards the slowest speed in the Preview speed view (worst case: match bridge speed). On small models lower all speeds.\n- `dont_slow_down_outer_wall` (filament) = `1` keeps outer walls out of the layer-time slowdown (silk PLA, PETG); small layers then cool less.\n- `enable_overhang_speed` (process) = `0` removes overhang slowdowns; only if the model has mild overhangs (worse overhangs otherwise).\n- `max_volumetric_extrusion_rate_slope` (process): 300-350 mm³/s² on fast direct-drive printers with pressure advance; 10-15 (direct drive) or 5-10 (Bowden) on slow printers without PA. Disables arc fitting.\n- Fish-scale gloss at 0.08 mm and high speed: raise `layer_height` to 0.16 mm, or slow outer wall 20-30% and add +5-10 °C within range.\n- Print several objects together to avoid layer-time slowdowns.\n\n## Checks the user must do by hand (hardware, material, printer settings)\n- Spool turns freely; PTFE tube free of kinks, wear, debris.\n- Extruder gears clean and not worn, idler tension correct. Clean before any flow calibration or the result is wrong.\n- Partial clog: manual extrusion must give a straight, even strand; else cold pull or new nozzle (see defect-clogs-heat-creep).\n- Nozzle seated and tight. Prusa Nextruder (CORE One, MK4/S, MK3.9/S): nozzle pushed fully up, thumb screws hand-tight; after opening the gearbox cover run the gearbox alignment. XL: check the nozzle tube for dents. Bambu H2/A1/P2S: hotend clip and magnet seated, no wobble; X1/P1: nozzle fastening screws tight. A loose hotend causes random layer lines.\n- Installed nozzle matches the nozzle diameter in the printer profile (printer setting the user changes by hand); a mismatch gives systematically wrong flow.\n- Hardened or stainless nozzles often need +5-10 °C compared to brass.\n- First layer not set too close (Z offset is a printer setting the user adjusts by hand); a squashed first layer can choke extrusion.\n- Hotend heatsink fan working; PLA in a closed enclosure (Prusa: room above ~27 °C) can soften early and under-extrude.\n- Dry filament that pops or hisses (PETG, PA, TPU, PC most sensitive). Diameter should be 1.75 ± 0.02-0.05 mm; try a known-good spool.\n- When switching material, load the new filament at the higher temperature of the previous one.\n- Bambu: Sport/Ludicrous on the printer screen raise flow without more heat; change speeds in the slicer instead.\n\n## Calibration in Orca (menu Calibration → ...)\n- **Temperature**: temp tower; for high speed use the upper part of the good range.\n- **Flow ratio**: YOLO (recommended): smoothest block without gaps, new `filament_flow_ratio` = old ± modifier (Pass 1/2: old × (100 + modifier) / 100). Bambu: do not tick the printer's own \"Flow calibration\" when sending Orca tests.\n- **Pressure advance**: tower, pattern or line; save to `pressure_advance`. Bambu: Flow Dynamics calibration does the same job.\n- **Max flowrate**: note heights where gloss is lost, walls deform, extrusion fails; flow = start + height × step. Set `filament_max_volumetric_speed` 10-20% below the deformation point. For uniform gloss keep outer wall flow (layer height × line width × speed) under the gloss-loss value.\n- Order and reading: see calibration-guide.\n\n## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)\n- Typical max volumetric speed on standard hotends (always calibrate): PLA 12-20, PETG 8-15, ABS/ASA 10-16, TPU 2-5, PC 6-10, PA 8-12 mm³/s. Standard V6-class hotend 8-12, Nextruder 15-20, high-flow hotends 20-40 mm³/s.\n- **PLA**: easiest to melt; silk PLA shows gloss changes strongly, keep outer walls slow and uniform (about 40-60 mm/s).\n- **PETG**: viscous, sticks to the nozzle, needs lower flow; moisture sensitive.\n- **ABS/ASA**: melt slower than PLA; under-extrude at PLA speeds.\n- **TPU**: buckles if pushed; lowest flow; simple infill (`grid`); see material-tpu.\n- **PA/PC**: viscous, hygroscopic; dry before diagnosing.\n- **CF/GF, wood/metal fills**: wear brass and clog fine nozzles; hardened ≥0.4 mm (wood often ≥0.6 mm); see material-composites.\n\n## Sources\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/under-extrusion\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/different-gloss\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/severe-layer-artifacts\n- https://wiki.bambulab.com/en/knowledge-sharing/volumetric-speed\n- https://wiki.bambulab.com/en/knowledge-sharing/common-print-quality-problem\n- https://wiki.bambulab.com/en/knowledge-sharing/lines-not-connected\n- https://wiki.bambulab.com/en/software/bambu-studio/parameter/line-width\n- https://wiki.bambulab.com/en/filament/pla\n- https://help.prusa3d.com/article/under-extrusion_2007\n- https://help.prusa3d.com/article/under-extrusion-nextruder-printers_821253\n- https://help.prusa3d.com/article/extrusion-multiplier-calibration_2257\n- https://help.prusa3d.com/article/max-volumetric-speed_127176\n- https://help.prusa3d.com/article/problems-with-infill_1994\n- https://help.prusa3d.com/article/infill_42\n- https://help.prusa3d.com/article/infill-patterns_177130\n- https://www.orcaslicer.com/wiki/calibration/flow_ratio_calib.html\n- https://www.orcaslicer.com/wiki/calibration/volumetric_speed_calib.html\n- https://www.orcaslicer.com/wiki/calibration/pressure_advance_calib.html\n- https://www.orcaslicer.com/wiki/material_settings/filament/material_flow_ratio_and_pressure_advance.html\n- https://www.orcaslicer.com/wiki/material_settings/filament/material_volumetric_speed_limitation.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_line_width.html\n- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_infill.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_and_surfaces.html\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/under-extrusion/\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/inconsistent-extrusion/\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/weak-infill/\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/gaps-between-infill-and-outline/\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/gaps-in-floor-corners/\n",
    },
    "defect-first-layer": {
        "description": "First layer problems: filament not sticking, lines dragged or peeling, gaps between lines, lines too squished with ridges, uneven first layer across the bed, elephant foot (flared base), parts stuck too hard to remove. Read when the user reports the first layer not sticking, bad bed adhesion, gaps or ridges in the first layer, nozzle scraping the plate, elephant foot, or a print that will not come off.",
        "content": "# First layer: not sticking, too squished, gaps, ridges, elephant foot, too stuck\n\n## How to recognize it\n- Good first layer: flat, even lines that just merge, no gaps or ridges, same look over the whole plate; small flaws on 5-10% of the area are normal.\n- Nozzle too high: round, thin or wavy lines, gaps between lines, lines that drag or curl, parts loose mid print, blobs/spaghetti.\n- Nozzle too low: lines flattened to a thin, see-through film, ridges between lines, rough or overflowing surface, edges curling up, nozzle scraping, little or no extrusion on layer 1 (can clog).\n- Good in some spots, bad in others: fingerprints/residue (patchy) or levelling/uneven plate (one side or one zone differs).\n- Lines not touching each other or the wall although Z looks right: pressure advance (K) far too high, or under-extrusion.\n- Elephant foot: the bottom 1-3 layers are wider than the walls above (a lip at the base). As a fit/tolerance issue also see defect-dimensional-accuracy.\n- Too stuck: the part cannot be removed, PEI tears or chips.\n- Corners lifting later in the print: defect-warping.\n\n## Likely causes, most common first\n1. Dirty plate (skin oil, dust, old glue).\n2. Nozzle-to-plate distance wrong (Z offset / Live Z / levelling stale or skipped).\n3. Wrong plate type selected in Orca: wrong bed temperature; Bambu Textured PEI also loses its automatic 0.04 mm lower offset.\n4. Bed temperature too low (not sticking) or too high (elephant foot, too stuck, PLA heat creep).\n5. First layer printed too fast; part fan on during the first layers.\n6. Flow too low or too high (uncalibrated flow ratio), partial clog, dirty nozzle tip, wet filament.\n7. Mechanical: nozzle/hotend loose or set at the wrong height, plate not seated or debris under it, worn plate coating.\n8. Too stuck: PETG/TPU on smooth PEI without glue, bed too hot, nozzle too low.\n\n## Questions worth asking (only when the answer changes the fix)\n- A top-down photo of the first layer or of a one-layer test square.\n- Which plate is on the printer, which plate type is set in Orca, glue? When was it last washed?\n- Did this combination work before; what changed (plate, nozzle, printer moved)? Levelling enabled at start? Where on the plate is it bad?\n- For too stuck: material, plate, did they wait for the plate to cool?\n\n## Slicer fixes\nBed temperature: change only the _initial_layer key of the plate in use (filament): `textured_plate_temp_initial_layer`, `hot_plate_temp_initial_layer`, `cool_plate_temp_initial_layer`, `textured_cool_plate_temp_initial_layer`, `eng_plate_temp_initial_layer`, `supertack_plate_temp_initial_layer`.\n\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `initial_layer_speed` (process) | decrease (not sticking) | -25%, e.g. 30 mm/s for walls | never above printer limits | slower first layer |\n| `initial_layer_infill_speed` (process) | decrease (not sticking) | -25%, e.g. 60 mm/s | never above printer limits | slower first layer |\n| `close_fan_the_first_x_layers` (filament) | increase | to 1-3 | ≤ 5 layers | - |\n| plate _initial_layer temp (filament) | not sticking: increase; elephant foot / too stuck: decrease | ±5 °C | ≤ +10 °C over current, never above 120 °C | hotter: elephant foot, PLA heat creep |\n| `initial_layer_print_height` (process) | increase for uneven or textured plates | to 0.25 mm on a 0.4 mm nozzle | ≤ 65% of nozzle recommended, hard limit 75%, min 0.1 mm | user may need to re-check Z/Live Z |\n| `initial_layer_line_width` (process) | increase | to 0.5 mm on a 0.4 mm nozzle | ≤ 0.6 mm on a 0.4 mm nozzle | wider first-layer footprint |\n| `nozzle_temperature_initial_layer` (filament) | increase (not sticking) | +5 °C | inside nozzle_temperature_range_low..high | stringing, elephant foot |\n| `first_layer_flow_ratio` (process) — BY HAND | gaps: increase; ridges/overflow: decrease | ±0.02-0.05 | by hand only (plugin cannot check it), keep 0.9-1.1; Process → Quality → Wall and surfaces, see defect-triage | needs `set_other_flow_ratios` = `1`; does not fix wrong Z |\n| `initial_layer_acceleration` (process) | decrease | -25% | never above printer limits | slower first layer |\n| `brim_type` / `brim_width` (process) | small footprints: `outer_only`, 3-5 mm | - | ≤ 18 mm | brim removal |\n| `elefant_foot_compensation` (process) | increase (elephant foot) | 0.1-0.2 mm on a 0.4 mm nozzle | ≤ 0.3 mm | brim may print detached; thin first-layer features shrink |\n| `elefant_foot_compensation_layers` (process) | increase | 1 → 2-3 | - | - |\n| `raft_layers` (process) | 0 → 2-3 for worn/uneven plates or tiny contact | - | 2-4 | rough bottom, time; disables elephant foot compensation |\n| `pressure_advance` (filament) | if lines do not touch and value looks 10× too high | recalibrate, do not guess | Bambu: typical 0.02-0.04, > 0.05 rare | only active with `enable_pressure_advance` = `1` |\n\nNotes for the AI:\n- First decide from the photo if the nozzle is too high or too low. Z is a hardware matter: explain it, never fake it with flow or temperature.\n- Bed and speed first, line width/height next, flow last. Calibrate `filament_flow_ratio` (filament) before touching `first_layer_flow_ratio` (by hand, see the table).\n- Elephant foot: lower the first-layer bed temperature 5 °C, then add compensation. A raft disables it.\n- Too stuck: lower the _initial_layer plate temperature 5 °C and give the hand checks below.\n\n## Checks the user must do by hand (hardware, material, printer settings)\n- Clean the plate. Bambu textured/smooth PEI: warm water and dish soap with a sponge or soft brush, rinse, dry, do not touch the surface. Prusa: IPA 90%+ on the cold sheet with an unscented towel; dish soap + warm water if IPA stops working; acetone about once a month on smooth PEI only (not on textured/satin sheets, never before PETG). SuperTack: soap and water, no acetone or strong solvents, no stiff brush.\n- Plate type in Orca must match the plate on the printer (selector in the Prepare tab). The AI cannot change it.\n- Bed levelling: run it after moving the printer or maintenance; keep levelling enabled at print start (Bambu). Clean the nozzle tip first.\n- Nozzle height. Bambu: re-run levelling; some newer models offer Calibration → First Layer Calibration on the screen in 0.01 mm steps (negative = closer). Prusa MK3/MINI: Live Adjust Z during the first layer or First Layer Calibration from the LCD; one value per sheet type (Steel sheet profiles). Prusa MK4/CORE One/XL (load cell): automatic; long-press the knob to fine-tune (not saved). Do not over-squish to fix adhesion: it damages the sheet and can clog.\n- Printer setting, changed only by the user by hand: `z_offset` in the printer preset (negative = closer). Only if the printer has no Live Z or first-layer calibration; 0.01-0.02 mm steps. The plugin never edits it.\n- Hardware. Bambu X1/P1: hotend screws tight, hotend straight. A1/H2/P2S: nozzle buckle locked; A1: loose heater-assembly screws give wrong probing. Prusa Nextruder: nozzle fully up, expansion joints facing the carriage centre, Loadcell test.\n- Plate seated flat, nothing under it, not bent. Worn coating: use the other side or replace.\n- Glue: needed on the Bambu Engineering Plate and smooth PEI for non-PLA; thin layer on cold plate. As release layer it also fixes too stuck PETG/TPU/PC.\n- Too stuck: let the plate cool (Bambu PEI: ≤ 35 °C) and flex it. SuperTack: reheat to about 50 °C or wet the edge with alcohol, then scrape.\n- Partial clog or dirty nozzle: cold pull (defect-clogs-heat-creep). Wet filament: dry it.\n- Test: a one-layer 0.2 mm square over most of the plate. Gaps = too high or under-extrusion; ridges = too low or flow too high; patches = dirty; one zone different = levelling or debris.\n\n## Calibration in Orca (menu Calibration → ...)\n- Nozzle height is calibrated on the printer, not in Orca.\n- Calibration → Flow ratio: when gaps or ridges remain with correct Z; result goes to `filament_flow_ratio` (filament).\n- Calibration → Pressure advance: when lines do not touch each other or the walls; result to `pressure_advance` (filament). Bambu printers can use their own Flow Dynamics calibration.\n- Elephant foot value (Bambu method): print a 25×25×10 mm cube with `elefant_foot_compensation` = 0 and `brim_type` = `no_brim`, let it cool, measure the bottom and the top in X and Y with calipers at mid-side; average the two (bottom - top) differences and enter it. Different plates need different values. See calibration-guide.\n\n## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)\n- PLA: easy. Bambu Textured PEI 55-65 °C, SuperTack works from about 40 °C, old Cool Plate needs glue. On textured sheets the nozzle must be a bit closer to fill the texture; small PLA parts on textured may need a brim (Prusa).\n- PETG: bonds too strongly to smooth PEI (tears it): glue or textured sheet. Prusa: bed 85/90 °C, nozzle 230/240 °C (first/other layers); a little more squish than PLA.\n- ABS/ASA: bed 90-110 °C, part fan off for the first layers, glue on PEI.\n- TPU: textured sheet without glue; on smooth PEI use glue (too strong bond). Never on SuperTack. Print slowly.\n- PA/PC: glue on PEI; PA sticks poorly to standard PEI (Prusa PA Nylon sheet). Dry the filament first.\n- CF/GF: a bad first layer easily clogs; use at least a 0.4 mm nozzle and 0.2 mm first layer (Prusa). Bambu: glue stick for PA-CF/GF, PET-CF, ASA-CF.\n- SuperTack: Bambu PLA Silk sticks too hard; Support for PLA/PETG must not touch it (2+ raft layers).\n\n## Sources\n- https://wiki.bambulab.com/en/knowledge-sharing/first-layer-not-sticking\n- https://wiki.bambulab.com/en/knowledge-sharing/identify-and-fix-first-layer-issues-with-a-test-print\n- https://wiki.bambulab.com/en/knowledge-sharing/lines-not-connected\n- https://wiki.bambulab.com/en/x1/troubleshooting/first-layer-printing-optimization-guide\n- https://wiki.bambulab.com/en/h3c/troubleshooting/first-layer-quality-calibration\n- https://wiki.bambulab.com/en/general/textured-PEI-plate-not-working-as-expected\n- https://wiki.bambulab.com/en/filament-acc/acc/plates\n- https://wiki.bambulab.com/en/filament-acc/acc/bambu-cool-plate-supertack\n- https://wiki.bambulab.com/en/PLA/PETG-with-bambu-bool-plate-supertack\n- https://wiki.bambulab.com/en/filament-acc/acc/pei-plate-clean-guide\n- https://wiki.bambulab.com/en/software/bambu-studio/parameter/elephant-foot\n- https://help.prusa3d.com/article/first-layer-issues_1804\n- https://help.prusa3d.com/article/live-adjust-z_112427\n- https://help.prusa3d.com/article/first-layer-calibration-i3_112364\n- https://help.prusa3d.com/article/first-layer-calibration-mini-mini_229122\n- https://help.prusa3d.com/article/print-surface-preparation_686951\n- https://help.prusa3d.com/article/elephant-foot-compensation_114487\n- https://help.prusa3d.com/article/petg_2059\n- https://help.prusa3d.com/article/flexible-materials_2057\n- https://help.prusa3d.com/article/special-pa-nylon-steel-sheet_341570\n- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_initial_layer_speed.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_layer_height.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_line_width.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_and_surfaces.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_precision.html\n- https://www.orcaslicer.com/wiki/material_settings/filament/material_temperatures.html\n- https://www.orcaslicer.com/wiki/calibration/flow_ratio_calib.html\n",
    },
    "defect-layer-adhesion": {
        "description": "Weak bonding between layers: layers splitting or separating, horizontal cracks along layer lines (often on tall ABS/ASA/PC or CF parts), delamination, parts that snap or peel apart along the layers. Read when the user reports layer separation, layers splitting, cracks in the walls, delamination, weak or brittle parts that break along layer lines.",
        "content": "# Layer separation, splitting, cracks, weak layer bonding\n\n## How to recognize it\n- Cracking from thermal stress: clean horizontal cuts along a layer line, edges often bent slightly upward or outward; typical on tall or large ABS, ASA, PC, PET-CF, PA-CF parts, frequently on the side facing a fan, a door or a draft.\n- Weak bonding: the part breaks or peels apart along layer lines with little force; surface may look matte or rough where flow was too high for the hotend.\n- One thin or missing layer at a single height (a groove all around) is not cracking: usually a short under-extrusion (partial clog, tangled spool): see defect-clogs-heat-creep and defect-extrusion.\n- Gaps between walls and infill, weak infill: defect-extrusion. Base lifting at the corners together with cracks: also defect-warping.\n\n## Likely causes, most common first\n1. Too much cooling for the material: part/auxiliary fan, drafts, open-frame printer or open doors (ABS/ASA/PC/PA are very sensitive to cold air).\n2. Nozzle temperature too low for the filament, or too low for the speed being printed.\n3. Printing too fast / volumetric flow too high: the plastic leaves the nozzle colder and has less time to fuse.\n4. Shrinkage forces larger than the bond: large parts in high-shrink materials, cold room, no enclosure.\n5. Under-extrusion: flow ratio too low, partial clog, wet filament (popping, bubbles).\n6. Layer height too large for the nozzle (above about 75-80% of nozzle diameter).\n7. Material: fibre-filled filaments have weaker layer bonding by nature; PLA is brittle across layers.\n\n## Questions worth asking (only when the answer changes the fix)\n- Material and brand, enclosed or open printer, doors/lid closed, drafts nearby?\n- Did it crack during the print (thermal stress) or break later under load (weak bonding or orientation)?\n- Where are the cracks: at what height, which side?\n- Popping or hissing while printing (wet filament)?\n- Was the profile edited (speeds, fan, temperature, layer height)? Nozzle diameter and layer height?\n- Direction of the load on the part: parts are weakest when pulled across the layers; reorienting can solve a strength problem without any setting change.\n\n## Slicer fixes\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `nozzle_temperature` (filament) | increase | +5 °C per step (also `nozzle_temperature_initial_layer` if low) | inside the filament's nozzle_temperature_range_low..high | stringing, softer overhangs and small features |\n| `fan_max_speed` (filament) | decrease | -10-20 points; ABS/ASA about 30-40% or less, large ABS parts 0 | PLA/PETG: keep enough for overhangs | overhangs and bridges droop |\n| `fan_min_speed` (filament) | decrease | -10-20 points | ≥ 0 | as above |\n| `additional_cooling_fan_speed` (filament) | decrease, 0 for ABS/ASA/PC | -20-30 points | printers with an auxiliary fan | small details cool less |\n| `reduce_fan_stop_start_freq` (filament) | `0` for ABS/ASA/PC | - | - | fan stops on long layers |\n| `fan_cooling_layer_time` (filament) | decrease (fan starts only on very short layers) | -25% | ≥ 0 | small layers cool less |\n| `outer_wall_speed` / `inner_wall_speed` (process) | decrease | -20-30% (Bambu ABS example: inner 150, outer 100 mm/s) | never above printer machine limits | longer print |\n| `filament_max_volumetric_speed` (filament) | decrease | -10-20% | lower freely; raise at most +10% | caps all speeds, longer print |\n| plate temp pair for the plate in use (filament): `textured_plate_temp`, `hot_plate_temp`, `eng_plate_temp`, `cool_plate_temp`, `textured_cool_plate_temp`, `supertack_plate_temp` (and their _initial_layer versions) | increase | +5 °C | ≤ +10 °C over current, never above 120 °C | helps the lower part only; PLA/PETG elephant foot |\n| `layer_height` (process) | decrease when above about 75% of nozzle | e.g. 0.32 → 0.2 mm on 0.4 mm | ≤ 75% of nozzle diameter, min 0.04 mm | longer print |\n| `filament_flow_ratio` (filament) | increase only if under-extrusion is confirmed (better: calibrate) | +0.02 | 0.8-1.2 | over-extrusion, rough surface |\n| `wall_loops` (process) | increase (strength) | +1-2 (structural parts: about 5 walls, 25% infill) | - | time, material; more shrink stress on large ABS/PC |\n| `draft_shield` (process) | `enabled` for ABS/ASA/PC on open frames | with `skirt_loops` ≥ 1 | - | filament, time |\n\nNotes for the AI:\n- Order: reduce cooling (ABS/ASA/PC) or raise nozzle temperature (PLA/PETG) first, then slow down / cap volumetric flow, then layer height. Hardware and environment (enclosure, drafts, wet filament, clog) come before all of these.\n- After lowering the fan, check overhangs and bridges in the preview; restore `overhang_fan_speed` (filament) if they matter.\n- If the fan must stay high (overhangs) and bonding suffers, raise the nozzle temperature a step instead of removing all cooling (Prusa).\n- More walls and denser infill make parts stronger but increase shrinkage stress on large ABS/PC parts: there prefer temperature, cooling and enclosure changes.\n\n## Checks the user must do by hand (hardware, material, printer settings)\n- Enclosure: close doors and top cover for ABS/ASA/PC/PA; keep the printer away from windows, AC vents and fans. Ventilate the room without blowing on the printer.\n- Printers with active chamber heating: the user can raise the chamber temperature by about 5 °C on the printer (Bambu suggestion). The plugin never changes chamber settings.\n- Partial clog or dirty nozzle (one weak layer, thin lines): cold pull / unclog as in the printer guide (defect-clogs-heat-creep).\n- Wet filament (popping, bubbles, rough surface): dry it, store sealed with desiccant. PA and PC absorb moisture within hours.\n- Part cooling fan and shroud: fan working, shroud not blocked, deformed or melted.\n- Start from the vendor filament profile for the material; most cases come from custom profiles with wrong temperatures or too much cooling (Prusa).\n- Material choice: large ABS parts that keep cracking: suggest ASA, or PETG where heat resistance allows.\n- Orientation: rotate the part so the main load runs along the layers, not across them.\n\n## Calibration in Orca (menu Calibration → ...)\n- Calibration → Temperature: print the tower and choose the block with the best layer bonding; for fast printing use the upper part of the good range. Result → `nozzle_temperature` (filament).\n- Calibration → Max flowrate (max volumetric speed test): read where the surface loses gloss (a sign of degrading bonding) and where walls deform; set `filament_max_volumetric_speed` below the quality-loss point.\n- Calibration → Flow ratio: rules out under-extrusion; result → `filament_flow_ratio` (filament).\n- See calibration-guide for order and reading.\n\n## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)\n- PLA: weaker layer bonding than other materials, breaks along layers or shatters on impact. Usual range 195-220 °C by brand; raise in 5 °C steps until layers bond. Keep cooling for quality; bonding problems are mostly temperature or speed.\n- PETG: good layer adhesion. For maximum toughness print hotter and with little or no fan (accept worse overhangs).\n- ABS: very sensitive to cold air: fan off or low, enclosure, draft shield on open frames. Typical nozzle range starts around 220-235 °C; much lower gives easy splitting.\n- ASA: like ABS but more tolerant; still needs stable warm surroundings for large parts.\n- TPU: excellent layer bonding; poor bonding usually means printing too fast (under-extrusion).\n- PA/PC: high shrink and moisture uptake: dry first, enclose, minimal fan. PA has excellent layer bonding when dry.\n- CF/GF: fibres reduce layer-to-layer adhesion (PET-CF and PA-CF crack easily): higher end of the temperature range, slower walls, low fan, enclosure.\n\n## Sources\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/interlayer-cracking\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/warping-falling-off-collapsing\n- https://wiki.bambulab.com/en/knowledge-sharing/printed-model-warping\n- https://wiki.bambulab.com/en/general/engineering-plate-not-working-as-expected\n- https://wiki.bambulab.com/en/general/filament-guide-material-table\n- https://help.prusa3d.com/article/layer-separation-and-splitting-fdm_1806\n- https://help.prusa3d.com/article/warping_2011\n- https://help.prusa3d.com/article/cooling_127569\n- https://help.prusa3d.com/article/abs_2058\n- https://help.prusa3d.com/article/asa_1809\n- https://help.prusa3d.com/article/petg_2059\n- https://help.prusa3d.com/article/pla_2062\n- https://help.prusa3d.com/article/polyamide-nylon_167188\n- https://help.prusa3d.com/article/polycarbonate-pc_165812\n- https://help.prusa3d.com/article/flexible-materials_2057\n- https://help.prusa3d.com/article/composite-materials-filled-with-carbon-kevlar-or-glass_167387\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/layer-separation-and-splitting/\n- https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html\n- https://www.orcaslicer.com/wiki/material_settings/filament/material_temperatures.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_layer_height.html\n- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_walls.html\n- https://www.orcaslicer.com/wiki/print_settings/others/others_settings_skirt.html\n- https://www.orcaslicer.com/wiki/calibration/temp_calib.html\n- https://www.orcaslicer.com/wiki/calibration/volumetric_speed_calib.html\n- https://www.orcaslicer.com/wiki/calibration/flow_ratio_calib.html\n",
    },
    "defect-layer-shift": {
        "description": "Layer shifts (diagnosis and prevention only): whole layers offset in X or Y, staircase shifts, leaning prints; mostly hardware (belts, pulleys, obstructions, collisions, overheated drivers) with a few preventive slicer changes. Read when the user reports shifted layers, layers moved sideways, a step or offset in the print, a staircase or leaning print, or the printer clicking/knocking and the print continuing misaligned.",
        "content": "# Layer shift\n\nLayer shift is a **hardware or collision problem**. Most printers are open loop: if the toolhead loses steps it keeps printing at the wrong place. The slicer cannot correct a shift; it can only lower the risk. Explain the hand checks first; propose preset changes only as prevention.\n\n## How to recognize it\n- Everything above a certain height is offset sideways in X or Y; the print continues normally on top of the offset.\n- **Single shift**: usually one event (nozzle hit a curled edge or blob, cable or object caught, a bump to the printer).\n- **Staircase** (several shifts in the same direction): typically a loose or misaligned motor pulley or a slipping belt.\n- **Leaning print**: many small shifts in one direction.\n- A clicking or thumping noise from a motor at the moment of the shift means skipped steps.\n- Not a layer shift: elephant foot (defect-first-layer), corners lifting (defect-warping), seam line (defect-seam-zits-blobs), ripples after corners (defect-ringing-ghosting), wrong overall size (defect-dimensional-accuracy).\n\n## Likely causes, most common first\n1. **Nozzle collides with the print**: curled overhangs, warped corners, blobs from sticky filament (PETG) collecting on the nozzle, very sparse infill under top layers.\n2. **Belts and pulleys**: belt too loose (slips) or too tight (friction), pulley set screws loose or not on the flat of the motor shaft.\n3. **Obstruction of the motion**: filament scraps around a belt or pulley, cable bundle or cable chain catching, PTFE tube or cables snagging (Bambu A series), purge waste piling up at the chute (Bambu), dirty or dry rods and bearings.\n4. **Too fast for the motors**: speed or acceleration above what the axes can hold, especially when a faster speed mode is selected on the printer screen mid-print (Bambu Ludicrous), or stealth/silent mode on large prints (Prusa).\n5. **Electronics too hot or underpowered**: motor drivers overheating (e.g. Bambu P1P fully enclosed without an MC board fan), insufficient motor current.\n6. Non-original hotends that are taller than stock (Bambu), external bumps, unstable table.\n\n## Questions worth asking (only when the answer changes the fix)\n- One shift or several in the same direction? Which axis?\n- At what height, and what was printing then (travel over a top surface, an overhang, a filament change, a tall thin section)?\n- Any clicking or grinding noise? Was the speed mode changed on the printer?\n- Is the printer enclosed and hot (long ABS/ASA prints, P1P with an enclosure)?\n- Does the same file shift at the same height every time? (repeatable = geometry/collision; random = mechanics/electronics)\n\n## Slicer fixes\nPrevention only, after the hand checks. All values must stay within the printer's machine limits.\n\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `filament_z_hop` (filament) | increase | set 0.2-0.4 mm | 0-2 mm; nil = printer value | slightly longer travel, a bit more stringing |\n| `filament_retract_lift_enforce` (filament) | set | `All Surfaces` | nil = printer value | more lifts, more time |\n| `travel_acceleration` (process) | decrease | -25% | within machine max acceleration | longer print |\n| `default_acceleration` (process) | decrease | -20% | within machine limits; 0 = printer value | longer print |\n| `travel_speed` (process) | decrease | -20 to -30% | within machine max speed | longer print, slightly more oozing |\n| `enable_prime_tower` (process) | enable for PETG blobs on the nozzle | `1` | needs space on the plate | extra filament and time |\n| `sparse_infill_density` (process) | increase if top layers sag and get hit | +5 points (e.g. 15% → 20%) | | more material and time |\n\nFor collisions with curled or warped areas, treat the cause: overhang cooling and slowdown (`enable_overhang_speed` (process), `slowdown_for_curled_perimeters` (process), `overhang_fan_speed` (filament); see defect-overhangs-bridges) and adhesion/warping (see defect-warping).\n\n## Checks the user must do by hand (hardware, material, printer settings)\n- **Move each axis by hand with the printer off**: smooth, no tight spots. On CoreXY (Bambu X1/P1/P2S/H2, Prusa CORE One, XL) also move along both diagonals: a rough diagonal points to the motor or pulley driving it.\n- **Belt tension**:\n  - Bambu X1/P1/H2/P2S: printer off, loosen the 4 tensioner screws 1-2 turns, move the toolhead around, park it at the rear, retighten (no over-torque); then run Vibration compensation. Bambu A1: loosen the tension screw(s) about one turn, move the axis three times, retighten, calibrate.\n  - Prusa MK3S+: Support → Belt Status, best around 250 (X) and 275 (Y), ±15; near 240 loosen, near 290 tighten. Other Prusa: belt sounds like a low bass note and can be pinched with slight resistance. XL: inspect the belt clamps.\n- **Pulleys**: both set screws tight, one on the flat of the shaft, pulley aligned so the belt runs straight. Test by holding the motor shaft and pushing the axis: no play allowed. Prusa MINI: the X pulley screw is reachable through a hole on top of the extruder (2 mm Allen key).\n- **Obstructions**: filament around belts or pulleys, cable bundle or chain hitting the frame, purge waste at the chute, PTFE tubes. Watching a video of the print helps.\n- **Rods and bearings**: clean and lubricate (Prusa lubricant or lithium grease); Bambu X1/P1: clean the carbon rods.\n- **Printer options**: Bambu \"Auto-recovery from step loss\" (X1, A, H2, P2S, X2D: printer screen → Print options; P1: from Bambu Studio). Prusa: use normal mode instead of stealth for large or complex prints (stealth also disables crash detection). Do not raise the speed mode on the printer screen for large prints.\n- **Electronics**: enclosed Bambu P1P needs the MC board fan; motors warm but not too hot to touch.\n- **Machine limits (printer settings, the user changes them by hand, the plugin never does)**: `machine_max_acceleration_x`, `machine_max_acceleration_y`, `machine_max_speed_x`, `machine_max_speed_y`. If presets keep hitting these limits and shifts persist, the user can lower them.\n- **Geometry**: tall slender parts are more prone to shifts and knock-overs: add a brim, reorient, or cut the model into parts.\n\n## Calibration in Orca (menu Calibration → ...)\n- No Orca test fixes a layer shift. After belt or pulley work, run the printer's own resonance calibration (Bambu Vibration compensation, Prusa input shaper with an accelerometer if hardware changed).\n- Do not run Calibration → Input Shaping or Calibration → Cornering until shifts are solved: they push acceleration and speed high on purpose.\n\n## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)\n- PLA: fast profiles plus curled overhangs are the usual collision; improve overhang cooling.\n- PETG: sticks to the nozzle and builds blobs that catch the print; dry the filament, consider a prime tower and z-hop.\n- ABS/ASA: warping and curling corners get hit; keep the enclosure closed, use a brim.\n- TPU: printed slowly, shifts are rare; strings or blobs on the nozzle can still catch.\n- PA/PC and CF composites: warping-prone; Bambu suggests the Smooth PEI plate with glue for PAHT-CF to avoid warp-related shifts.\n\n## Sources\n- https://wiki.bambulab.com/en/knowledge-sharing/layer-shifts\n- https://wiki.bambulab.com/en/general/bambu-mods-to-avoid\n- https://wiki.bambulab.com/en/software/bambu-studio/remote-control\n- https://wiki.bambulab.com/en/x1/maintenance/belt-tension\n- https://wiki.bambulab.com/en/a1/maintenance/belt_tension\n- https://wiki.bambulab.com/en/p2s/maintenance/belt-tension\n- https://wiki.bambulab.com/en/h2/maintenance/belt-tension\n- https://wiki.bambulab.com/en/bambu-studio/manual/3d-print-large-files\n- https://help.prusa3d.com/article/layer-shifting_2020\n- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_acceleration.html\n- https://www.orcaslicer.com/wiki/printer_settings/motion%20ability/printer_motion_ability.html\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/layer-shifting/\n- https://www.obico.io/blog/3d-print-troubleshooting-guide/\n",
    },
    "defect-multimaterial": {
        "description": "Multi-material and multi-colour printing with AMS, MMU or multi-tool/dual-nozzle printers - flushing (purge) volumes, prime/wipe tower stability, colour bleeding and contamination, ooze from idle nozzles, weak bonds between materials, and reducing purge waste. Read when the user reports colours mixing or bleeding, wrong colour streaks after a filament change, a prime tower that falls, wobbles or collects blobs, drips or strings from the idle nozzle, too much purge/poop or a huge tower, or parts of different materials coming apart.",
        "content": "# Multi-material: flushing, prime tower, colour bleeding, ooze, waste\n\n## How to recognize it\n- Colour bleeding: the new colour starts tinted with the previous one (worst from dark to light), streaks in light areas, or infill colour showing through thin or translucent walls.\n- Contaminated supported surfaces: strings or gaps under supports printed with a support filament (support material mixed with model material or vice versa).\n- Prime tower trouble: tower leans, topples or detaches, blobs build up on it, the nozzle scrapes or knocks it.\n- Idle-nozzle ooze (dual nozzle, tool changer, IDEX): drips, strings or blobs on the part from the parked nozzle, or ooze dropped where the tool change or heat-up happens.\n- Bubbles or pits right after filament changes (air in the re-melted tip).\n- Waste: big purge per change, heavy tower, long print time.\n- Material boundaries split apart (e.g. TPU on PLA/PETG, PLA on PETG).\n\n## Likely causes, most common first\n1. Flushing volume too low for that colour pair (dark -> light, silk/glitter, support or soluble filaments need more).\n2. Flush into infill/objects with few walls or light/translucent outer colour.\n3. Prime tower too tall and thin, no brim, poor plate adhesion, or walls printed in a filament that does not bond to the others.\n4. Wet filament (main cause of ooze from preheated idle nozzles and of bubbles after changes).\n5. Idle nozzle kept at full temperature, or the heat-up wait happening above the part.\n6. Materials that do not bond chemically at the boundary.\n7. Many filament changes per layer (orientation, thin layers) multiplying waste.\n\n## Questions worth asking (only when the answer changes the fix)\n- Printer type: single nozzle with AMS/MMU (flush volumes) or dual nozzle / tool changer (ooze, prime volume)? Bambu printers always use the Type 1 tower; most others use Type 2.\n- Which colour/material pairs show the problem, and in which direction?\n- Is the goal quality (no bleeding) or saving filament/time?\n- Flush into infill/objects enabled? Light or translucent walls? Filament dried recently?\n\n## Slicer fixes\nFlushing volumes are not a preset key: they live in the Flushing volumes dialog (button next to the project filament list) as a from/to matrix plus a multiplier. The plugin cannot change them; tell the user to edit them by hand (see Checks). Raise the cell of the pair that bleeds (or the multiplier) in small steps until the tint is gone; lower the multiplier to 0.8-0.9 only after a test print shows no tint.\n\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `enable_prime_tower` (process) | set `1` for multi-colour | on | not available with by-object printing | material, plate space |\n| `flush_into_infill` (process) | `0` if colour shows through walls; `1` to save waste | toggle | needs prime tower | mixed-colour infill visible through light/translucent walls |\n| `wall_loops` (process) | increase when flushed infill shows through | +1 | | more time |\n| `flush_into_support` (process) | `0` with support filaments that must stay pure (e.g. Support for ABS), else `1` | toggle | needs prime tower | slightly weaker support when on |\n| `filament_prime_volume` (filament) | increase on bubbles/tint right after changes (Type 1 tower, e.g. Bambu) | +10-15 mm³ | PC: 45 mm³ or more; Bambu H2D ABS with Support for ABS: 90 mm³ | bigger tower |\n| `prime_volume` (process) | increase (Type 2 tower, fixed purge per change) | +10 mm³ | default 45 mm³ | bigger tower |\n| `prime_tower_brim_width` (process) | increase if the tower detaches or wobbles | +2 mm | -1 = auto from height | plate area |\n| `wipe_tower_wall_type` (process) | rib (default); cone on Type 2 towers for tall thin towers | enum | rectangle, cone, rib | cone has a wider base |\n| `prime_tower_width` (process) | increase (not possible with rib wall type) | +10 mm | | more material |\n| `prime_tower_enable_framework` (process) | set `1` (Type 1) if the tower has hollow zones | on | boolean | more material |\n| `wipe_tower_max_purge_speed` (process) | decrease (Type 2) if blobs get knocked or the tower shakes | -10-20 mm/s | default 90 mm/s, min 10 | slower changes |\n| `prime_tower_infill_gap` (process) | increase (Type 1) if material piles up on the tower | +25 % | 100-200 % (default 150 %) | larger tower |\n| `wipe_tower_filament` (process) | set one filament (not soluble/flexible) for tower walls when mixing material types | filament index | 0 = any | that filament used on every tower layer |\n| `ooze_prevention` (process) | set `1` on multi-tool printers with idle-nozzle ooze | on | boolean | slower tool changes (reheat) |\n| `filament_change_length` (filament) — BY HAND | increase if the outgoing nozzle oozes (dual nozzle) | +5 mm | by hand only (plugin cannot check it): Filament → Multimaterial; 0 = no ramming | more waste |\n| `filament_ramming_travel_time` (filament) — BY HAND | increase for runny filaments like TPU | +1 s | by hand only: Filament → Multimaterial; 0 = off | longer change |\n| `filament_multitool_ramming` (filament) — BY HAND | enable on tool changers with a wipe tower | on | by hand only: Filament → Multimaterial | small extra waste |\n| `interlocking_beam` (process) | set `1` where materials do not bond (TPU + rigid, PLA + PETG) | on | width default 0.8 mm, layers 2, depth 2 | more changes |\n| `mmu_segmented_region_max_width` / `mmu_segmented_region_interlocking_depth` (process) | set for painted parts whose colours separate | +1 mm | 0 = off; ignored with beams | colour boundary less sharp inside |\n| `interface_shells` (process) | set `1` for translucent multi-material parts | on | boolean | more material |\n| `wipe_tower_no_sparse_layers` (process) | `1` to cut waste/time | on | collision risk; Orca rejects unsafe layouts | timelapse/clumping detection disable it |\n| `wipe_tower_sparse_layers_combination` (process) | `1` (safe alternative) | on | only at low layer heights | less saving |\n| `layer_height` (process) | increase to cut the number of changes | +0.04 mm | ≤ 75 % of nozzle diameter | coarser surface |\n\nNotes for the AI:\n- With a prime tower, `independent_support_layer_height` (process) is ignored and all objects must use the same raft layers.\n- Type 2 towers use `prime_volume` per change unless the printer is a single-extruder MMU with purge in prime tower (then the flush matrix is used). Type 1 uses `filament_prime_volume` per filament (and `filament_prime_volume_nc` for hotend changes).\n- Infill colour bleeding is fixed by more walls or turning flush into infill off, not by more flush.\n\n## Checks the user must do by hand (hardware, material, printer settings)\n- Flushing volumes dialog: raise the cells for the bleeding pairs. Guide values: Prusa MMU soluble supports at least 200-240 mm³ per change (240+ when coming from PVA/BVOH); Bambu Support for ABS -> ABS up to 800; stringy surfaces above support filament: about double the original. Recalculate restores auto values.\n- Dry the filament, especially PVA, BVOH, PETG, PC, TPU; keep AMS/dry box below about 20 % RH for PVA.\n- Temperature of idle tools (filament Idle temperature, process Temperature variation under Ooze prevention): the plugin cannot change temperature keys; the user lowers them by hand if idle nozzles ooze.\n- Printer settings (by hand, Type 2 multi-tool only): Wait for temperature on wipe tower (`wait_for_temp_on_wipe_tower`) parks the heat-up ooze beside the tower; Tool change on wipe tower (`tool_change_on_wipe_tower`) issues the change over the tower, not over the part. Check that firmware macros do not already wait for temperature.\n- Tower on a clean plate area, away from tall parts when no-sparse-layers is used.\n- Clean nozzle wiper, purge chute and nozzle tip; check AMS/MMU cutter and PTFE path if changes fail.\n- Reduce waste by layout: put colour changes low in the part (tower stops at the last change), print several copies per plate, add \"Flush into this object\" parts of similar height, rotate tall multi-colour parts only if their colours run vertically. Compare by slicing.\n- Prusa XL: the purge tower can be turned off only with well-dried filament; check the print regularly.\n- Bambu H2D/H2C: grouping the filaments with the largest mutual flush on different nozzles removes that flush.\n\n## Calibration in Orca (menu Calibration -> ...)\n- Flow rate and Pressure advance per filament (each filament keeps its own values), Temperature and Max volumetric speed for each material.\n- Flush volumes: no built-in test; print a small two-colour cube with the worst pair (dark -> light) and adjust the matrix cell. See calibration-guide.\n\n## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)\n- PLA: easiest; glossy/silk and glitter variants need more flush. PLA + PETG bond poorly: good as support pair, use beam interlocking for mixed parts.\n- PETG: dry first; keep the prime volume generous; PVA is not compatible, use BVOH or PLA interfaces.\n- ABS/ASA: Support for ABS is hard to flush out; high flush from support to ABS, flush into infill/support off, more prime volume (Bambu H2D: about 90 mm³). Long changes overcool layers: keep the enclosure closed.\n- TPU: dry thoroughly; oozes from a parked nozzle; use ramming and travel time after ramming; beam interlocking against rigid parts. Bambu H2D: TPU on the left nozzle blocks the right one.\n- PA/PC: very hygroscopic and runny when hot; PC needs about 45 mm³ or more prime volume.\n- CF/GF: check AMS and nozzle compatibility in the vendor filament guide before loading.\n\n## Sources\n- https://wiki.bambulab.com/en/software/bambu-studio/reduce-wasting-during-filament-change\n- https://wiki.bambulab.com/en/software/bambu-studio/parameter/prime-tower\n- https://wiki.bambulab.com/en/software/bambu-studio/multi-color-printing\n- https://wiki.bambulab.com/en/software/bambu-studio/h2c-purge-mode\n- https://wiki.bambulab.com/en/software/bambu-studio/manual/dual-nozzles-slicing-filament-grouping\n- https://wiki.bambulab.com/en/software/bambu-studio/beam-interlocking\n- https://wiki.bambulab.com/en/h2/manual/soft-and-hard-filament-multi-material-printing-guide\n- https://wiki.bambulab.com/en/filament/support\n- https://wiki.bambulab.com/en/filament-acc/filament/support-for-abs\n- https://wiki.bambulab.com/en/filament-acc/filament/pva-printing-guide\n- https://help.prusa3d.com/article/wipe-tower_125010\n- https://help.prusa3d.com/article/purging-volumes-mmu_125097\n- https://help.prusa3d.com/article/multi-material-painting_262620\n- https://help.prusa3d.com/article/mutliple-extruders-settings-interlocking-advanced-bonding_867124\n- https://help.prusa3d.com/article/water-soluble-materials-pva-bvoh_162860\n- https://help.prusa3d.com/article/water-soluble-bvoh-pva_167012\n- https://help.prusa3d.com/article/printing-without-purge-tower-on-the-xl-multi-tool_649633\n- https://help.prusa3d.com/article/support-settings-for-the-xl_681927\n- https://www.orcaslicer.com/wiki/print_settings/multimaterial/multimaterial_settings_prime_tower.html\n- https://www.orcaslicer.com/wiki/print_settings/multimaterial/multimaterial_settings_flush_options.html\n- https://www.orcaslicer.com/wiki/print_settings/multimaterial/multimaterial_settings_ooze_prevention.html\n- https://www.orcaslicer.com/wiki/print_settings/multimaterial/multimaterial_settings_advanced.html\n- https://www.orcaslicer.com/wiki/material_settings/multimaterial/material_multimaterial.html\n- https://www.orcaslicer.com/wiki/printer_settings/multimaterial/printer_multimaterial_wipe_tower.html\n",
    },
    "defect-overhangs-bridges": {
        "description": "Drooping, sagging or curling overhangs and bridges (unsupported walls, ceilings, hole tops, spans between two points) and the Orca overhang/bridge speed, flow, cooling and support-threshold settings that fix them. Read when the user reports droopy or saggy overhangs, curled-up overhang edges, a messy underside, bridge strings that sag, break or leave gaps, or a rough ceiling over a hole or gap.",
        "content": "# Overhangs and bridges: drooping, curling, sagging\n\n## How to recognize it\n- Overhang droop: walls that lean outward look ragged, wavy or melted on the underside; layers sag and stack unevenly. Gets worse as the angle approaches horizontal.\n- Overhang curl: the edge of an overhang lifts up (often at sharp corners like a boat bow) and the nozzle may hit it on following layers.\n- Bridge sag: lines spanning a gap hang down in the middle, droop as loose strings or break.\n- Bridge gaps: bridge lines stay round and do not touch each other, leaving a see-through or ribbed ceiling.\n- Ask which side of the part and which feature (wall, hole top, flat ceiling); check the Preview with the \"Line type\" view to see whether Orca actually printed the area as bridge or overhang wall.\n\n## Likely causes, most common first\n1. Geometry beyond what the material can do: overhang angle (measured from the bed) below about 45° needs support; very long bridges sag no matter what.\n2. Not enough cooling on overhangs and bridges (fan too low, overhang fan threshold too high, enclosed chamber too warm for PLA/PETG/TPU).\n3. Overhang walls or bridges printed too fast (overhang slowdown off or not slow enough, high outer wall speed).\n4. Nozzle temperature at the top of the range: hot plastic stays soft longer and droops.\n5. Bridge flow/density/thickness not matched to the span: too little material makes lines that do not touch or snap; too much makes them hang.\n6. Bridge direction not across the shortest span (Orca normally picks it automatically).\n7. Thick layers: each layer steps out further over the one below.\n8. Hardware: part cooling fan weak, dirty or obstructed duct, wet filament.\n\n## Questions worth asking (only when the answer changes the fix)\n- Material and printer (enclosed or open)? Decides how much fan and whether to open the door.\n- Overhang or bridge, and roughly how long is the span / what angle? Long spans and angles below ~45° go to supports first.\n- Sagging lines or gaps between lines? Opposite bridge-flow directions.\n- Does the overhang curl upward or droop downward? Curl -> cooling + curled-perimeter slowdown; droop -> speed/temperature/cooling.\n- Are supports acceptable? If not, use the no-support levers (speed, cooling, angle limit, geometry change).\n\n## Slicer fixes\nCheck first that `detect_overhang_wall` (process) is `1`; most overhang features depend on it. Change one or two things at a time and reprint a small test.\n\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `enable_overhang_bridge_fan` (filament) | set `1` | on | boolean | none for PLA; more warping risk on ABS/ASA/PA/PC |\n| `overhang_fan_speed` (filament) | increase | +10-20 % | max 100 %; ABS/ASA/PA/PC raise cautiously | cooling can weaken layer bonding and warp high-temp materials |\n| `overhang_fan_threshold` (filament) | lower | one enum step (e.g. `50%` -> `25%` -> `10%`) | enum `0%`,`10%`,`25%`,`50%`,`75%`,`95%` | `0%` forces the overhang fan on all outer walls |\n| `enable_overhang_speed` (process) | set `1` | on | boolean | longer print time |\n| `overhang_3_4_speed` / `overhang_4_4_speed` (process) | decrease | -5 to -10 mm/s (or a lower % of wall speed) | about 10 mm/s minimum; 0 = no slowdown | time; big speed jumps can leave wall marks if PA is off |\n| `overhang_1_4_speed` / `overhang_2_4_speed` (process) | decrease if mild overhangs are rough | -10 mm/s | typical overhang range 10-60 mm/s | time |\n| `slowdown_for_curled_perimeters` (process) | set `1` for curling at corners | on | boolean | possible wall artifacts at high speeds; needs good PA |\n| `bridge_speed` (process) | decrease when bridges sag | -5 mm/s | about 10 mm/s minimum; test 10-50 mm/s | slower is not always better: test per filament |\n| `nozzle_temperature` (filament) | decrease | -5 °C | inside nozzle_temperature_range_low..high | under-extrusion, weaker layers if too low |\n| `bridge_flow` (process) — BY HAND | lower if lines sag/hang; raise if lines do not touch | ±0.05 | by hand only (plugin cannot check it), keep 0.7-1.5: Process → Quality → Bridging → Flow ratio | low: thin, breaking lines; high: hanging bulges |\n| `bridge_density` (process) | raise if gaps between bridge lines | +5 % | 100-125 % | over-extruded bridge surface |\n| `thick_bridges` (process) | `1` for long spans; `0` for short spans and nicer look | toggle | boolean | on: stronger but rougher, can sag on short bridges; off: thin lines can snap on long or low-layer bridges |\n| `enable_extra_bridge_layer` (process) | set `external_bridge_only` | enum | `disabled`, `external_bridge_only`, `internal_bridge_only`, `apply_to_all` | slightly more time |\n| `bridge_angle` (process) | set to the direction of the shortest span if auto picks badly | degrees | 0 = auto (default), 0-180 | wrong angle makes spans longer |\n| `extra_perimeters_on_overhangs` (process) | set `1` for steep overhangs and unanchored bridges | on | boolean; needs `detect_overhang_wall` | more time |\n| `overhang_reverse` (process) | set `1` for steep overhangs and curling | on | boolean | texture on outer wall; add `overhang_reverse_internal_only` = `1` to keep the outer wall smooth |\n| `outer_wall_speed` (process) | decrease when all overhangs are rough | -10-20 % | never above printer limits | time |\n| `layer_height` (process) | decrease | -0.04 mm | ≤ 75 % of nozzle diameter, min 0.04 mm | longer print |\n| `enable_support` (process) + `support_threshold_angle` (process) | enable for angles below ~45° or long bridges; raise threshold to support more | +5° | 0-90; Orca default 30 | material, removal marks (see defect-supports) |\n| `max_bridge_length` (process, tree support) / `bridge_no_support` (process, normal support) | lower length / set `0` so long bridges get supported | -5 mm | 0 = support all bridges | more support |\n| `make_overhang_printable` (process) + `make_overhang_printable_angle` (process) | enable, angle 45-60° | on | changes the model shape (adds cone material) | only when shape change is acceptable |\n| `counterbore_hole_bridging` (process) | `partiallybridge` or `sacrificiallayer` for counterbores | enum | `none`,`partiallybridge`,`sacrificiallayer` | sacrificial layer must be broken out |\n\nNotes for the AI:\n- Bridge flow logic in Orca: values below 1.0 reduce material per line and tighten spacing (less sag); above 1.0 add material at the same spacing (better line contact). Internal bridges over infill use `internal_bridge_flow` (process, by hand, same menu) and `thick_internal_bridges` (process) - see defect-top-surface for pillowing.\n- Overhang speeds as % are taken from outer/inner wall speed. When overhangs are 100 % unsupported Orca treats them as bridges and `bridge_speed` applies.\n- For long bridges the most reliable fix is a support enforcer (painted support) in the middle of the span, which splits it into two short bridges.\n\n## Checks the user must do by hand (hardware, material, printer settings)\n- Part cooling fan: spins at full speed, duct clean and not cracked or blocked. Bambu printers with an auxiliary fan: check that it works; whether the printer has one is a printer setting (`auxiliary_fan`) the user changes by hand only if wrong.\n- PLA, PETG, TPU on enclosed printers: open the front door and/or top lid for overhang-heavy prints. Do not do this for ABS, ASA, PA, PC (warping, weak layers).\n- Filament dry (wet filament oozes and makes bubbly, weak bridges).\n- Orientation: rotate the part so overhangs face up or bridges become shorter; split with the Cut tool; chamfer instead of flat overhangs in CAD.\n- Paint support enforcers under the worst overhang or in the middle of a long bridge (Prepare -> Support painting).\n- Nozzle not partially clogged (inconsistent flow ruins bridges first).\n\n## Calibration in Orca (menu Calibration → ...)\n- Temperature: pick the tower block with the cleanest overhangs and bridges that still bonds well (if several look good, take the middle of that range); too hot causes sagging. Value goes to `nozzle_temperature`.\n- Flow ratio and Pressure advance first, so overhang slowdowns do not create blobs at speed transitions.\n- Max flowrate (max volumetric speed) if you also raise other speeds.\n- Bridges: no dedicated Orca test; print a bridge test model several times with per-object `bridge_flow` (by hand) / `bridge_speed` overrides and keep the best (see calibration-guide).\n\n## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)\n- PLA: best overhangs of all; overhang fan 100 %, slightly lower temperature (e.g. Bambu PLA around 205 °C on later layers) and slow overhang speeds. Open the enclosure.\n- PETG: droops and strings more; lower temperature 5-10 °C within range, strong overhang fan, slower bridges; open the enclosure.\n- ABS/ASA: keep the enclosure closed; use moderate overhang fan and slower speeds rather than full cooling; rely on supports earlier.\n- TPU: slow everything; cooling helps; open the enclosure.\n- PA/PC: like ABS - limited cooling, enclosure closed, support earlier.\n- CF/GF filled: similar to the base polymer; fibres make lines stiffer but rougher.\n- See the material-* skills for full profiles.\n\n## Sources\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/overhang\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/bridging\n- https://wiki.bambulab.com/en/software/bambu-studio/parameter/bridge\n- https://wiki.bambulab.com/en/software/bambu-studio/slow-down-for-overhang\n- https://wiki.bambulab.com/en/software/bambu-studio/support\n- https://help.prusa3d.com/article/poor-bridging_1802\n- https://help.prusa3d.com/article/support-material_1698\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/poor-bridging/\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/poor-surface-above-supports/\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/curling-or-rough-corners/\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_overhangs.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_bridging.html\n- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_overhang_speed.html\n- https://www.orcaslicer.com/wiki/print_settings/support/support_settings_advanced.html\n- https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html\n- https://www.orcaslicer.com/wiki/calibration/temp_calib.html\n",
    },
    "defect-overheating-small-features": {
        "description": "Covers overheated small parts (melted, droopy or rounded tips, spires, pins, deformed small layers), small features or thin walls that are missing or not printed, and gaps in the middle of thin walls. Read when the user reports \"melted tip\", \"top of the cone is a blob\", \"small parts deformed\", \"overheating\", \"droopy layers\", \"details missing\", \"text/thin wall not printed\", \"thin wall has a gap in the middle\" or \"feature disappears in preview\".",
        "content": "# Overheating of small features, missing small features, gaps in thin walls\n\n## How to recognize it\n- **Overheating**: tips of cones, spires, pins and small towers are melted, rounded, curled or blobby; small cross-sections sag or lean; layers look glossy and soft while larger parts on the same plate are fine. Usually worse near the top of a part where layers get smaller.\n- **Small features missing**: text, fins, thin walls or sharp details are absent already in the slicer Preview (a slicing issue), or present in Preview but not on the print (extrusion issue, see defect-extrusion).\n- **Gaps in thin walls**: a wall a few lines thick shows a slit or holes between its two sides, or a zig-zag fill that does not fuse.\n\n## Likely causes, most common first\nOverheating:\n1. Layer printed too fast for it to cool: minimum layer time too short, or slowdown for layer cooling disabled. Typical with single small objects.\n2. Not enough part cooling: fan too low for the material, or the part cooling fan not working (hardware).\n3. Nozzle too hot for the speed actually used (small layers are slowed down, so they need less heat).\n4. Outer walls excluded from the slowdown, or minimum print speed so high that the target layer time cannot be reached.\n5. Enclosed printer with doors/lid closed while printing PLA or PETG: warm chamber, weak cooling.\n6. Printer speed mode raised from the printer screen (Bambu Sport/Ludicrous) on a small model.\n\nMissing features / thin-wall gaps:\n1. Feature thinner than what the wall generator can print: Classic cannot place a closed loop narrower than its line width; Arachne skips features below the minimum feature size.\n2. Wall thickness that is not a good multiple of the line width (Classic leaves a gap in the middle).\n3. Negative X-Y contour compensation or large elephant-foot compensation shrinking thin features.\n4. Nozzle too large for the detail (hardware).\n\n## Questions worth asking (only when the answer changes the fix)\n- One small object alone on the plate, or many? (Printing several copies is the simplest overheating fix.)\n- Is the feature missing in the slicer Preview, or only on the print?\n- Which wall generator is active (Arachne or Classic)?\n- Enclosed printer: door and lid open or closed during PLA/PETG?\n- Does the part cooling fan spin at 100% when tested from the printer menu?\n\n## Slicer fixes\nOverheating (most effective and least risky first):\n\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `slow_down_for_layer_cooling` (filament) | set `1` | - | - | small layers print slower |\n| `slow_down_layer_time` (filament) | increase (minimum layer time) | +2-4 s (e.g. 4 → 8 s for PLA) | 0-1000 s; large values make small parts very slow | longer print; very slow extrusion can cause heat creep |\n| `fan_max_speed` (filament) | increase | +10-20% (PLA up to 100%) | 0-100%; keep moderate for ABS/ASA/PC | warping/cracking on ABS/ASA, weaker layer bonding on PETG |\n| `fan_cooling_layer_time` (filament) | increase so the fan ramps up on more layers | +10-20 s | 0-1000 s | more cooling on medium layers |\n| `slow_down_min_speed` (filament) | decrease so the layer time can actually be reached | to 10-20 mm/s | > 0; extremely low speeds risk heat creep | longer print |\n| `dont_slow_down_outer_wall` (filament) | set `0` for small detailed parts | - | - | gloss may vary between layers (see defect-extrusion) |\n| `nozzle_temperature` (filament) | decrease | -5 °C (max -10 °C) | inside the filament nozzle_temperature_range | under-extrusion and weaker layers if too cold |\n| `small_perimeter_speed` (process) | decrease | 50% → 30-40% of outer wall | ≥ 1 mm/s | slower small loops |\n| `small_perimeter_threshold` (process) | increase so more small loops are slowed | 0 → 5-10 mm radius | 0 disables | longer print |\n| `outer_wall_speed` (process) | decrease on small models | -20-30% | machine limits | longer print |\n| `additional_cooling_fan_speed` (filament) | increase on printers with an auxiliary part-cooling fan (Bambu H2, P and X series) | +10-20% | 0-100%; only works if the printer has and enables the auxiliary fan | warping on ABS/ASA, more noise |\n| `reduce_fan_stop_start_freq` (filament) | `1` keeps the fan always on at least at minimum speed | - | not for ABS/ASA/PC | - |\n\nModel-level fixes the AI should suggest in words: print 2+ copies or add a small sacrificial tower placed some centimetres away so each layer takes longer; keep `print_sequence` (process) = `by layer` (printing `by object` loses this benefit).\n\nMissing small features:\n\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `wall_generator` (process) | `arachne` | - | - | Arachne can leave more seams or uneven walls on some models |\n| `min_feature_size` (process) | decrease (Arachne) | 25% → 10-15% of nozzle | 0% = no filter | very thin features print poorly, strings/blobs |\n| `min_bead_width` (process) | decrease slightly so widened thin features stay closer to size | 85% → 70-75% | keep ≥ ~50% | weaker, under-filled thin walls |\n| `detect_thin_wall` (process) | `1` (Classic only; ignored with Arachne) | - | - | single open lines, overlaps, weak thin walls |\n| `outer_wall_line_width` / `inner_wall_line_width` (process) | decrease so a narrow feature fits | to 90-100% of nozzle | ≥ 75% of nozzle | weaker walls, slower |\n| `xy_contour_compensation` (process) | set to 0 if negative | - | - | parts may come out slightly larger |\n| `only_one_wall_top` (process) | `1` for tiny top areas such as letters | - | - | - |\n\nGaps in thin walls:\n\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `wall_generator` (process) | `arachne` (adapts line width to the wall) | - | - | see above |\n| `wall_transition_angle` (process) | increase if wedge-shaped walls leave a gap in the middle | +5° | 1-59° | more transitions, possible over-extrusion |\n| `wall_transition_filter_deviation` (process) | decrease if transitions leave gaps; increase to reduce start/stops | ±5% | default 25% | over-extrusion or more travel |\n| `wall_distribution_count` (process) | increase to spread width changes over more walls | 1 → 2-3 | ≥ 1 | outer wall width varies more |\n| `outer_wall_line_width` / `inner_wall_line_width` (process) | make the wall a whole number of lines (e.g. 1.0 mm wall = 2 × 0.5 mm) | ±0.05 mm | 75%-150% of nozzle | more or less flow per line |\n| `filter_out_gap_fill` (process, Classic wall gap fill) | lower so short gaps between walls are filled | towards 0 mm | - | more small moves |\n| `filament_flow_ratio` (filament) | if walls are thin because of under-extrusion | see defect-extrusion | 0.8-1.2 | - |\n\n## Checks the user must do by hand (hardware, material, printer settings)\n- Part cooling fan: test it at 100% from the printer menu (Bambu: Device tab → part cooling fan). Not spinning, noisy or blocked duct = hardware fault (fan, cable, toolhead board); no setting fixes it.\n- The part cooling duct on the toolhead must be fitted and unobstructed: it directs the air to the area around the nozzle.\n- Auxiliary fan: only used if the printer setting `auxiliary_fan` is enabled in the printer preset (printer setting the user changes by hand).\n- Enclosed printers with PLA/PETG: open the front door and/or lid; a warm chamber weakens cooling and can soften filament in the extruder.\n- Bambu: do not raise the speed mode on the printer screen for small models; adjust speeds in the slicer.\n- Detail finer than the nozzle: a smaller nozzle (e.g. 0.2-0.3 mm) is a hardware change, and the nozzle diameter in the printer preset must then be changed by the user. Otherwise thicken the features in CAD (wider than the nozzle diameter).\n- For thin walls designed in CAD: two walls of 0.45 mm at 0.2 mm layers make about 0.86 mm, not 0.9 mm, because lines overlap; design to the slicer's line spacing.\n\n## Calibration in Orca (menu Calibration → ...)\n- **Temperature**: find the lowest temperature that still extrudes well at your speeds; small features prefer the cooler end.\n- **Flow ratio**: thin walls depend on correct flow.\n- No dedicated cooling test: verify in the Preview speed and layer-time views that small layers are slowed down; see calibration-guide.\n\n## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)\n- **PLA**: needs as much cooling as possible; fan high, minimum layer time several seconds; most prone to melted tips.\n- **PETG**: less fan than PLA; for small parts use longer layer time and the low end of its temperature range.\n- **ABS/ASA**: little cooling; prefer longer layer time, copies on the plate or a cooling tower over a stronger fan (fan causes cracks and warping).\n- **TPU**: some flexibles need little fan; rely on layer time; fine features are hard, thicken them.\n- **PA/PC**: PC needs little fan; rely on layer time and lower speed for small parts.\n- **CF**: fibres improve stiffness but need ≥ 0.4 mm hardened nozzles, so very fine details are often impossible (see material-composites).\n\n## Sources\n- https://wiki.bambulab.com/en/knowledge-sharing/melted-prints\n- https://wiki.bambulab.com/en/software/bambu-studio/auto-cooling\n- https://wiki.bambulab.com/en/software/bambu-studio/wall-generator\n- https://wiki.bambulab.com/en/software/bambu-studio/WallGenerator\n- https://wiki.bambulab.com/en/filament/pla\n- https://wiki.bambulab.com/en/filament-acc/acc/fans\n- https://help.prusa3d.com/article/cooling_127569\n- https://help.prusa3d.com/article/arachne-perimeter-generator_352769\n- https://help.prusa3d.com/article/layers-and-perimeters_1748\n- https://help.prusa3d.com/article/petg_2059\n- https://help.prusa3d.com/article/composite-materials-filled-with-carbon-kevlar-or-glass_167387\n- https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_generator.html\n- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_walls.html\n- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_other_layers_speed.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_precision.html\n- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_infill.html\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/overheating/\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/small-features-not-printed/\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/gaps-in-thin-walls/\n- https://www.matterhackers.com/articles/3d-printer-troubleshooting-guide\n",
    },
    "defect-ringing-ghosting": {
        "description": "Ringing/ghosting (fading echoes after corners, edges, holes or letters), vertical fine artifacts (VFA, salmon skin), vertical ribs and wobble on walls, with Orca acceleration/speed/jerk fixes and the Input Shaping, Cornering and VFA tests. Read when the user reports ghosting, ringing, echoes, ripples or waves after corners, a shadow of a feature repeated on the wall, vertical lines or ribs on walls, salmon skin, wavy or wobbly walls.",
        "content": "# Ringing, ghosting and VFA\n\n## How to recognize it\n- **Ringing / ghosting**: a short train of ripples right after a sharp corner, edge, hole or embossed text, evenly spaced and fading with distance. They sit on the wall printed *after* the corner, in the direction of travel.- **Axis clue**: ripples on only some faces point to one axis (X or Y): check that axis's belt, pulley and bearings first. On bed-slinger printers (Prusa MK/MINI, Bambu A1/A1 mini) the Y axis moves the bed.\n- **VFA (vertical fine artifacts) / salmon skin**: very fine, regular vertical lines over whole walls, also on curved walls and far from corners. They appear or vanish in specific speed bands. A common subtype is motor resonance rippling (MRR) from the stepper motors.\n- **Look-alikes, route elsewhere**:\n  - Horizontal bands repeating every few layers (Z wobble, temperature swings, filament diameter): see the hand checks below and defect-extrusion.\n  - One horizontal line or bulge where a bridge, roof or overhang starts (the Benchy hull line): shrinkage of the bridge pulls the wall, plus a sudden flow change. Covered by the last rows of the fixes table.\n  - Random irregular layer lines: often a loose hotend (hand checks).\n  - Rough texture on purpose: `fuzzy_skin` (process) is not `disabled_fuzzy`.\n\n## Likely causes, most common first\n1. Outer wall acceleration and speed too high for the frame: the toolhead's inertia at a direction change excites the frame and the belts.\n2. The printer's own resonance compensation (input shaper / vibration compensation) is missing or out of date: printer moved to another surface, belts re-tensioned, firmware update, new parts.\n3. Mechanics: loose or uneven belts, loose pulley set screws or frame screws, dry or dirty rods and bearings, a table or shelf that wobbles.\n4. Cornering limits (jerk, junction deviation) too permissive.\n5. VFA: stepper motor resonance at certain speeds, motor-to-motor variance.\n6. Very tall, slender parts swaying as they grow (wobble rising with height).\n\n## Questions worth asking (only when the answer changes the fix)\n- Ripples after corners, or fine lines everywhere? (ringing vs VFA)\n- Which faces show it? (axis, belt to check)\n- Printer and firmware: Bambu, Prusa (input shaper firmware), Klipper, Marlin 2 (junction deviation or classic jerk)? Decides which jerk key the printer actually uses.\n- Was the printer moved, belts adjusted or parts changed since the last good print? If yes, recalibrate the printer before changing presets.\n- Was a speed mode raised on the printer screen (Bambu Sport/Ludicrous, Prusa Tune → Speed)? That overrides the slicer.\n\n## Slicer fixes\nRead the current values first. Change one or two rows per round and reprint a small test (a box with sharp corners and embossed text).\n\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `outer_wall_acceleration` (process) | decrease | -25 to -40% (e.g. 5000 → 3000) | never above the printer's max acceleration; ≥ 500 | longer print; ignored if `default_acceleration` is 0 (Orca then sends no acceleration commands) |\n| `outer_wall_speed` (process) | decrease (ringing); move out of a bad band (VFA) | -20%, or the nearest clean speed from the VFA test | within machine limits; also capped by `filament_max_volumetric_speed` | longer print; a lower speed can land in another VFA band |\n| `default_acceleration` (process) | decrease | -20% | within machine limits; 0 = printer firmware value | slows every feature; only if ringing also shows on inner features |\n| `outer_wall_jerk` (process) | decrease | -2 mm/s (e.g. 9 → 7) | ≤ printer max jerk; 0 = use `default_jerk`; no effect while `default_jerk` (process) is 0 (printer's own jerk) | slower corners; used by classic-jerk Marlin, RepRap and Klipper (as corner velocity); Marlin 2 with junction deviation ignores it |\n| `default_junction_deviation` (process) | decrease | -0.002 to -0.005 mm | 0.01-0.3 mm accepted by Marlin 2; ≤ printer max junction deviation | Marlin 2 only; slower corners |\n| `max_volumetric_extrusion_rate_slope` (process) | set (bulge line where speed drops, not true ringing) | 35-50 mm³/s² at 1000 mm/s² accel, 70-100 at 2000, 145-200 at 4000 (0.42 mm line, 0.16 mm layer; +25% at 0.2 mm layer) | 0 = off; stay below those maxima or it has no effect | longer print, larger G-code, turns off arc fitting; use `extrusion_rate_smoothing_external_perimeter_only` = `1` to limit it to visible walls |\n| `overhang_fan_speed` (filament) | decrease (Benchy-hull line under bridges) | -10 to -20 points | keep enough for the overhangs you have | droopier overhangs |\n| `infill_wall_overlap` (process) | decrease (same line) | 15% → 5% | ≥ 0% | weaker infill-to-wall bond |\n\nNotes:\n- Vibration grows with print speed and with abrupt direction changes: lower outer wall acceleration and speed first, before touching other features.\n- Every speed, acceleration and jerk is clamped by the printer's Motion ability limits. If the preset already sits above them, changing it does nothing: check the printer limits first.\n- Slowing the outer wall to the bridge speed also hides the hull line, at a time cost.\n\n## Checks the user must do by hand (hardware, material, printer settings)\n- **Belts**: equal, correct tension on both axes; a loose belt lowers the resonance frequency and makes vibration compensation less effective.\n  - Bambu X1/P1/H2/P2S: printer off, loosen the 4 tensioner screws 1-2 turns (do not remove), move the toolhead back and forth, park it at the rear, retighten without over-torquing; the spring sets the tension. Bambu A1: loosen the X/Y screws about one turn, move the axis by hand three times, retighten.\n  - Prusa: plucked belt should give a low bass tone; MK3S+ Support → Belt Status, about 240-300 is fine (lower number = tighter).\n- **Recalibrate the printer's resonance compensation** after moving it, belt work or firmware updates: Bambu screen → Calibration → Vibration compensation (and motor noise cancellation where offered); Prusa input shaper is factory calibrated, recalibrate with the accelerometer only after hardware changes (CORE One L and XL have it built in).\n- **Prusa phase stepping** (CORE One, CORE One L, XL) targets VFA and motor noise; calibrate from the printer menu, never next to another printer that is moving. On the XL, enabling it disables crash detection.\n- **Mechanics**: pulley set screws, frame/PSU/display/bed screws, rubber or foam feet in place, rods and bearings clean and lubricated (Bambu X1/P1: clean the carbon rods), belt not rubbing on plastic parts.\n- **Surface**: firm, non-wobbling table; a heavy tile under the printer helps; avoid very soft padding under light printers (Prusa MINI).\n- **Printer settings (the user changes them by hand, the plugin never does)**: Printer settings → Motion ability → Resonance Compensation: `input_shaping_emit`, `input_shaping_type`, `input_shaping_freq_x`, `input_shaping_freq_y`, `input_shaping_damp_x`, `input_shaping_damp_y`; Resonance avoidance `resonance_avoidance` with `min_resonance_avoidance_speed` / `max_resonance_avoidance_speed` (outer wall speed inside the band is pushed to its edges; good fix for a VFA band); limits `machine_max_acceleration_x`, `machine_max_acceleration_y`, `machine_max_jerk_x`, `machine_max_jerk_y`, `machine_max_junction_deviation`.\n- **Horizontal banding / wobble**: Z lead screw or Z belt (clean, straight, aligned, not binding), hotend temperature stable within about ±2 °C (PID tune), filament with consistent diameter, hotend firmly seated (Bambu H2/P2S/A1: clip and magnet; X1/P1: hotend screws).\n- **Tall slender parts**: add a brim, reorient, or split the model.\n\n## Calibration in Orca (menu Calibration → ...)\nRun the filament calibrations first (see calibration-guide).\n- **Calibration → Input Shaping**: only for printers without automatic accelerometer calibration (Bambu and recent Prusa do it themselves, use that). Opaque glossy filament; frequency test on the Ringing Tower (Fast Tower if ringing is heavy), 15-110 Hz to start, measure the height where ripples are least per axis and read the frequency; then the damping test (start 0.1-0.2). The test raises speed and acceleration on purpose. The user saves results in firmware and/or the printer settings by hand.\n- **Calibration → Cornering**: finds the highest jerk / junction deviation that keeps corners sharp. Mostly useful to raise cornering speed; the firmware may cap the value.\n- **Calibration → VFA**: speed tower covering every outer wall speed you use (e.g. 20-200 mm/s, step 10). Find speeds where walls get rough, then set `outer_wall_speed` outside that band or have the user enable resonance avoidance by hand. Run it after input shaping.\n\n## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)\n- Opaque, glossy filaments make ringing most visible (Orca recommends them for its tests). Judge fixes on the same filament.\n- PLA: usually printed with the fastest profiles; lower outer wall acceleration and speed first.\n- PETG, ABS/ASA: normally slower profiles; if ringing appears, check printer mode and belts before presets.\n- TPU and other soft materials: printed slowly, ringing is rare; bulges at speed changes are more likely (soft filament lags), smoothing helps.\n- PA/PC and CF: low max volumetric speed often caps outer wall speed already; focus on acceleration and mechanics.\n\n## Sources\n- https://help.prusa3d.com/article/ghosting_1801\n- https://help.prusa3d.com/article/input-shaper-core-one-mk4-s-mk3-9-s-mk3-5-s-xl-mini_451816\n- https://help.prusa3d.com/article/phase-stepping-core-one-l-core-one_914247\n- https://help.prusa3d.com/article/phase-stepping-xl_681760\n- https://help.prusa3d.com/article/vibration-when-printing-mk3s-mk2-5s_2177\n- https://help.prusa3d.com/article/vibration-noise-when-printing-mini-mini_264110\n- https://wiki.bambulab.com/en/general/printer-calibration\n- https://wiki.bambulab.com/en/x1/maintenance/belt-tension\n- https://wiki.bambulab.com/en/a1/maintenance/belt_tension\n- https://wiki.bambulab.com/en/p2s/maintenance/belt-tension\n- https://wiki.bambulab.com/en/h2/maintenance/belt-tension\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/severe-layer-artifacts\n- https://wiki.bambulab.com/en/bambu-studio/manual/3d-print-large-files\n- https://wiki.bambulab.com/en/knowledge-sharing/layer-shifts\n- https://help.prusa3d.com/article/layer-shifting_2020\n- https://www.orcaslicer.com/wiki/calibration/input_shaping_calib.html\n- https://www.orcaslicer.com/wiki/calibration/vfa_calib.html\n- https://www.orcaslicer.com/wiki/calibration/cornering_calib.html\n- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_acceleration.html\n- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_jerk_xy.html\n- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_advanced.html\n- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_other_layers_speed.html\n- https://www.orcaslicer.com/wiki/printer_settings/motion%20ability/printer_motion_ability.html\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/vibrations-and-ringing/\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/lines-on-the-side-of-print/\n- https://www.obico.io/blog/3d-print-troubleshooting-guide/\n",
    },
    "defect-seam-zits-blobs": {
        "description": "Visible Z seam, zits, pimples, blobs and bulges or dents at the start/end of wall loops: seam position, seam gap, scarf joint seam, wipe options, wall order, pressure advance, retraction at the seam, random dots from wet filament. Read when the user reports a visible seam, seam line, Z seam, zipper, zits, pimples, dots, bumps or blobs on the walls, a gap or dent at the seam, or asks about scarf seam or wipe.",
        "content": "# Seam, zits and blobs\n\n## How to recognize it\n- **Seam line**: a vertical line of small bumps or a slight groove where each wall loop starts and ends. Unavoidable in FDM (except spiral vase); goal is to hide it or make it clean. Most visible on cylinders and smooth curves without corners.\n- **Bulge/blob at the seam end**: wider line where the loop closes → nozzle still pressurized (pressure advance too low, flow too high, seam gap too small).\n- **Blob at the seam start**: material oozed or was over-primed after travel/deretraction.\n- **Gap or dent at the seam**: pressure advance too high, seam gap too large, too much retraction or ooze lost during travel.\n- **Zits scattered over the whole surface**: seam position `random`, or wet filament (steam bursts; often with popping and stringing).\n- **Larger blobs at random places**: material accumulated on the nozzle and dropped off (often PETG, see defect-clogs-heat-creep), or travel crossing walls.\n- Tip from Simplify3D's method: watch an outer wall print. Defect appears as the loop starts → priming/ooze problem; appears as the loop ends → pressure/coasting problem.\n\n## Likely causes, most common first\n1. Seam placement: `random` or `nearest` on smooth/visible faces; no corner to hide the seam.\n2. Pressure advance not calibrated (too low → bulge at end; too high → gap at end).\n3. Ooze during travel before the outer wall starts: slow travel, long travel, outer wall printed first after a long move, retraction weak or extra restart too high.\n4. Over-extrusion (flow ratio too high).\n5. Wet filament (random dots/zits).\n6. Wall order outer-first (`outer wall/inner wall`) puts the outer wall straight after a travel.\n7. Hardware: high-flow/volcano or CHT-type nozzles and larger nozzle diameters have poorer extrusion control at seams; mechanical tolerance (belts, toolhead rigidity) when stopping.\n\n## Questions worth asking (only when the answer changes the fix)\n- Is the defect a line in one place, or dots everywhere? (line → seam settings; everywhere → seam position or moisture)\n- Bulge, blob or gap/dent? At start or end of the loop?\n- Does the model have a back side or a corner where the seam can hide?\n- Pressure advance calibrated for this filament? Standard or high-flow nozzle?\n- Cosmetic only, or does the part need strength at the seam?\n\n## Slicer fixes\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `seam_position` (process) | `aligned`, `aligned_back` or `back` (from `random`/`nearest`) | - | - | aligned line instead of scattered zits; `random` only for strength (pins, round parts) |\n| `pressure_advance` (filament) + `enable_pressure_advance` (filament) | set calibrated value | from PA calibration | 0-2, use the calibrated value | wrong value moves the defect to corners |\n| `seam_gap` (process) | bulge: increase; visible gap: decrease | ±5 % of nozzle | ≥ 0; 0-15 % typical on a tuned printer (default 10 %) | larger gap can leave a hole in the loop |\n| `wall_sequence` (process) | `inner-outer-inner wall` (best) or `inner wall/outer wall` | - | - | IOI needs 3+ walls and lowers overhang quality |\n| `wipe_before_external_loop` (process) | enable `1` | - | useful with outer/inner or inner-outer-inner order | small inward deretraction move |\n| `wipe_on_loops` (process) | enable `1` | - | needs 2+ walls | tucks the loop end inward |\n| `role_based_wipe_speed` (process) | enable `1` | - | - | otherwise `wipe_speed` (process) applies, % of travel speed |\n| `wipe_inward` (process) | enable `1` | `wipe_inward_distance` 50 % | needs `filament_wipe` = `1`, 2+ walls and inner walls printed first | falls back to normal wipe where no room |\n| `filament_wipe` (filament) | enable `1` | `filament_wipe_distance` 1-2 mm | ≥ 0 | - |\n| `seam_slope_type` (process) | `external` (contour) or `all` (contour and holes) | - | beta; not used on first layer or spiral vase | slight time increase; less effective on sharp corners/overhangs |\n| `seam_slope_conditional` (process) | enable `1` with scarf | `scarf_angle_threshold` default 155 | - | scarf only on smooth loops; corners keep a normal seam |\n| `scarf_joint_speed` (process) | lower | e.g. 100 % → 50-80 % of wall speed | keep < 100 mm/s | slower walls |\n| `seam_slope_min_length` (process) | default 20 mm | ±5 mm | 0 disables scarf | - |\n| `travel_speed` (process) | increase | +20-50 mm/s | never above machine limits | ringing; also raise `travel_acceleration` (process) within limits |\n| `filament_retraction_minimum_travel` (filament) | increase for seams | 2-4 mm | ≥ 0 | fewer retract/deretract cycles before the outer wall; may add strings across small gaps |\n| `filament_retract_when_changing_layer` (filament) | enable `1` | - | - | each layer starts depressurized |\n| `filament_flow_ratio` (filament) | decrease if over-extruding | -0.01 to -0.02 | 0.8-1.2 | under-extrusion if too low |\n| `filament_retract_restart_extra` (filament) — BY HAND | small negative only for a blob at loop start | -0.02 to -0.05 mm | by hand only (plugin cannot check it), keep within ±0.1 mm: Filament → Setting overrides → Retraction → Extra length on restart; `nil` = printer value | gap at seam start if overdone |\n| `outer_wall_speed` (process) | decrease | -10-20 % | ≥ 1 mm/s | longer print |\n| `staggered_inner_seams` (process) | enable `1` for strength/watertightness | - | - | does not hide the outer seam |\n| `spiral_mode` (process) | `1` only for single-wall vases | - | one wall, no infill/top | no seam on walls at all |\n\nOrder of attack: seam position/painting → pressure advance → seam gap → wall order and wipe options → scarf seam → travel/retraction details. Two valid strategies (Orca wiki): hide the seam (scarf seam on smooth models) or make it small and consistent (seam gap, role based wipe speed, wipe on loops, wipe inward, wipe before external loop). Wipe options make the seam more consistent, not invisible.\n\nSeam vs stringing conflict: a higher travel distance threshold helps seams but may add strings across small gaps; if both defects exist, fix stringing first (see defect-stringing), then raise the threshold only if strings stay away.\n\n## Checks the user must do by hand (hardware, material, printer settings)\n- **Seam painting**: with Orca's Seam painting tool, paint seam enforcers/blockers on the model to put the seam on an edge or the back. Newer Orca builds also offer Precise Seam modifiers (right-click object → Add Precise Seam) that pin the seam to a point or zone and survive model edits; the plugin cannot paint, the user must.\n- Orient the model so a corner or the back faces where the seam goes; fewer objects per plate means less travel before outer walls.\n- **Dry the filament** if zits are random and the nozzle pops (see materials-overview).\n- **Nozzle**: high-flow/volcano nozzles and large diameters give worse seams; a 0.2-0.4 mm standard nozzle gives the cleanest seams. Replace worn nozzles.\n- **Printer retraction (printer settings, user changes by hand)**: Printer settings → Extruder → Retraction (length, wipe, retract amount before wipe). Explain; the plugin only uses filament overrides.\n- Belts and toolhead rigidity: loose belts make the loop end inconsistent.\n\n## Calibration in Orca (menu Calibration → ...)\n1. **Pressure Advance** (first): look at corners and seams of the test; save into the filament preset. For high-speed printers consider adaptive pressure advance.\n2. **Flow ratio**: if walls look overfilled.\n3. **Retraction test**: shortest clean length into `filament_retraction_length`.\n4. Then adjust `seam_gap` in small steps. See calibration-guide.\n\n## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)\n- **PLA**: best seams once pressure advance is tuned; zits usually seam position or moisture.\n- **PETG**: oozes, so blobs at seams and material dropping from the nozzle are common: flow 0.93-0.96, a bit lower temperature, wipe enabled, dry spool.\n- **ABS/ASA**: seams generally clean; check pressure advance and flow.\n- **TPU**: little retraction possible; rely on seam position, slow outer walls and pressure advance; dry it.\n- **PA/PC**: moisture causes random zits; dry before printing.\n- **CF/GF filled**: abrasive fill wears brass nozzles and a worn nozzle oozes more and gives worse seams; use a hardened nozzle and check wear.\n\n## Sources\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_seam.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_and_surfaces.html\n- https://www.orcaslicer.com/wiki/print_prepare/prepare_precise_seam.html\n- https://www.orcaslicer.com/wiki/print_prepare/prepare_seam_painting.html\n- https://www.orcaslicer.com/wiki/printer_settings/extruder/printer_extruder_retraction.html\n- https://www.orcaslicer.com/wiki/calibration/pressure_advance_calib.html\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/seam\n- https://wiki.bambulab.com/en/software/bambu-studio/Seam\n- https://wiki.bambulab.com/en/knowledge-sharing/dots-on-the-print\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/filament-sticks-to-nozzle\n- https://help.prusa3d.com/article/seam-position_151069\n- https://help.prusa3d.com/article/seam-painting_168620\n- https://help.prusa3d.com/article/drying-filament_332086\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/blobs-and-zits/\n- https://www.obico.io/blog/3d-print-troubleshooting-guide/\n",
    },
    "defect-stringing": {
        "description": "Stringing and oozing: thin strings, hairs, wisps and cobwebs between separate parts or across gaps, caused by molten filament leaking during travel moves (retraction, temperature, wet filament, travel, plate layout). Read when the user reports stringing, strings, hairs, hairy print, cobwebs, spider webs, wisps, whiskers, oozing or threads between parts.",
        "content": "# Stringing and oozing\n\n## How to recognize it\n- Thin threads or cobwebs spanning open space between towers, separate objects or features of one object; fine hairs on the surface.\n- Oozing: material keeps leaking when the nozzle should not extrude; small drips or lumps where travel moves start or end, residue building up on the nozzle.\n- Many fine hairs everywhere plus popping/hissing, bubbles or a rough, matte-dull surface: almost always wet filament, not retraction.\n- Strings only between objects on a crowded plate: travel/plate layout. Strings inside one part across small gaps: retraction threshold or temperature.\n- Related: blobs or zits at the seam (see defect-seam-zits-blobs); material building up on the outside of the nozzle or a blob on the hotend (see defect-clogs-heat-creep); ooze from the idle nozzle in multi-material (see defect-multimaterial).\n\n## Likely causes, most common first\n1. **Wet filament.** Moisture turns to steam in the nozzle, the melt expands and keeps flowing. Retraction tuning cannot fully fix it. PETG, TPU, PA, PC, PVA and wood-filled PLA are the most sensitive; even new spools can be wet.\n2. **Nozzle temperature too high** for the material or for the actual speed: the melt is too fluid. Slow prints need a lower temperature than fast ones (more time in the melt zone).\n3. **Retraction too short or too slow**, or not triggered on short travels (travel distance threshold too high).\n4. **Long travels over open space**: many separate objects far apart, printing layer by layer, travels crossing walls, slow travel.\n5. **Pressure advance not calibrated / too low**: the nozzle is still pressurized at the end of a line and leaks during travel.\n6. **Over-extrusion** (flow ratio too high), especially PETG.\n7. **Z-hop**: vertical lifts on every retraction can pull threads; normal lift strings more than spiral/slope.\n8. **Hardware**: worn or enlarged nozzle, wrong nozzle size selected in the profile, residue film inside/outside the nozzle (long PETG runs), leaking or badly assembled hotend, poor heatbreak cooling. High-flow/volcano nozzles and large nozzles ooze more by design.\n9. **Low-density/foaming filaments** (e.g. PLA Aero, LW-PLA) used with normal flow and temperature.\n\n## Questions worth asking (only when the answer changes the fix)\n- Material and brand; how long the spool was open and how it is stored; any popping sounds or bubbles? (yes → dry first, before any setting change)\n- Direct drive or Bowden extruder? (decides the retraction range)\n- Strings only between separate objects, or also inside one part?\n- Was pressure advance, temperature or retraction ever calibrated for this filament?\n- Standard or high-flow nozzle, and which diameter?\n\n## Slicer fixes\nRead the current values first. Retraction overrides in the filament preset show `nil` when they inherit the printer value: read the printer value before computing a new one. Change 1-2 keys per test print.\n\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `nozzle_temperature` (filament) | decrease | -5 °C per test | inside the filament's nozzle temperature range | too low: under-extrusion, weak layers; going much too low can also string |\n| `filament_retraction_length` (filament) | increase | +0.2 mm direct drive, +0.5 mm Bowden | 0 .. min(8 mm, max(2 mm, 2x printer retraction)); direct drive usually ≤ 2 mm | too long: clogs, under-extrusion after travel, gaps at seams |\n| `filament_retraction_speed` (filament) | increase | +5-10 mm/s | > 0 and ≤ max(1.5x printer value, 30 mm/s) | too fast: ground filament, skipped extruder steps |\n| `reduce_crossing_wall` (process) | enable `1` | - | - | slightly longer print time; set `max_travel_detour_distance` (process) to limit detours (0 = no limit) |\n| `travel_speed` (process) | increase | +20-50 mm/s | never above the printer's machine limits | ringing, missed steps if too fast |\n| `filament_retraction_minimum_travel` (filament) | decrease | e.g. 2 → 1 mm | ≥ 0 | more retractions, longer print, more extruder wear; strings across small gaps disappear |\n| `filament_wipe` (filament) | enable `1` | - | - | none relevant; cleans the tip while retracting |\n| `filament_wipe_distance` (filament) | increase | +0.5 mm (1-2 mm typical) | ≥ 0 | longer wipe is limited by retraction length/speed |\n| `filament_retract_when_changing_layer` (filament) | enable `1` | - | - | none relevant |\n| `filament_z_hop` (filament) | decrease | e.g. 0.4 → 0.2 mm | 0-2 mm | less clearance: nozzle may hit curled parts/top surfaces |\n| `filament_z_hop_types` (filament) | set `Spiral Lift` or `Auto Lift` | - | - | `Auto Lift` picks slope or spiral per travel |\n| `print_sequence` (process) — BY HAND | `by object` for several small parts | - | by hand only (collision risk the plugin cannot check): Process → Others → Special mode → Print sequence; only if parts fit the printer's extruder clearance; Orca warns about collisions | parts cool less between layers; collision risk |\n| `pressure_advance` (filament) with `enable_pressure_advance` (filament) | set calibrated value | from the PA calibration | 0-2; use the calibrated value, no guessing | wrong value moves the defect to corners/seams |\n| `filament_flow_ratio` (filament) | decrease if over-extruding | -0.01 to -0.02 | 0.8-1.2 | under-extrusion, weaker layers |\n| `wipe_on_loops` (process) | enable `1` | - | needs 2+ walls | small inward move cleans the nozzle before travel |\n\nNotes for the AI:\n- Order of attack: dry filament → temperature → retraction (calibrated) → travel/avoid crossing walls → wipe/Z-hop → layout/print sequence.\n- `reduce_infill_retraction` (process) skips retractions for travel inside infill; it hides oozing inside the part and does not cause visible strings. Leave as is unless strings appear inside open infill.\n- Bambu guidance for PETG with strings/nozzle build-up: about 1.2-1.6 mm and 40-60 mm/s retraction, flow ratio 0.93-0.96; keep retraction under about 2 mm on direct drive and inside the Safe limit column.\n- Low-density PLA (Aero/LW): vendor values use flow well below 0.8, which the plugin cannot set: tell the user to use the vendor's profile or set it by hand (Filament → Filament → Flow ratio and Pressure Advance → Flow ratio); meanwhile lower `nozzle_temperature` and dry the spool.\n- If strings are still bad at the top of a clean retraction tower, stop raising retraction: dry the filament and check the nozzle.\n\n## Checks the user must do by hand (hardware, material, printer settings)\n- **Dry the filament** (see materials-overview for times): typical PLA 45-55 °C, PETG 55-65 °C, TPU 60-75 °C, PA/PC 80-90 °C. Store sealed with desiccant (Bambu: below 20 % RH). Try a different spool to confirm.\n- **Nozzle**: check for wear (brass after CF/GF or long use) and that the installed nozzle diameter matches the selected printer profile; replace a worn nozzle.\n- **Clean the nozzle**: a film of old filament (often PETG) on or inside the tip drags strings; heat and clean it, remove residue from previous materials.\n- **Hotend assembly**: if parts were changed recently, check for leaks and correct assembly; Prusa: poor heat dissipation in the hotend can cause stringing, renew the thermal paste on the heatbreak threads that sit in the heatsink.\n- **Printer retraction (printer settings, user changes by hand)**: Printer settings → Extruder → Retraction: length, speed, Z-hop. The plugin only uses the filament overrides; if the printer value is 0 or extreme, explain and let the user fix it. Bowden printers need much longer retraction than direct drive.\n- **Plate layout**: place objects closer together; fewer objects per plate reduces travel.\n- Finished parts: a very short pass of a heat gun (about 200 °C, 1-2 s) removes fine strings; longer exposure deforms the part.\n\n## Calibration in Orca (menu Calibration → ...)\n1. **Temperature**: temperature tower; choose the block with least stringing that still bonds well; the result goes into `nozzle_temperature`.\n2. **Pressure Advance**: result into `pressure_advance` with `enable_pressure_advance` = `1`.\n3. **Retraction test**: tower with a different retraction length per section. Defaults 0-2 mm step 0.1 mm suit direct drive; for Bowden use about 1-6 mm step 0.2 mm. Pick the shortest length that gives a clean tower; measure the height and find the \"Calib_Retraction_tower\" comment in the G-code preview to read the length. Result into `filament_retraction_length`. PLA/ABS are often clean from the bottom: 0.2-0.4 mm is enough then.\n4. Flow rate if over-extrusion is suspected (see calibration-guide).\n\n## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)\n- **PLA**: low stringing when dry; check temperature first. Silk/high-speed variants are more fluid. Aero/LW foaming PLA needs low flow and low temperature (vendor profile).\n- **PETG/PCTG**: strings and oozes the most; lower temperature 5-10 °C, flow 0.93-0.96, slightly longer/faster retraction, dry it (very hygroscopic), clean the nozzle regularly.\n- **ABS/ASA**: little stringing; short retraction (0.2-0.4 mm) is usually enough; look at temperature and moisture.\n- **TPU**: hygroscopic, dry it first. Keep retraction short (long or fast retraction jams soft filament); increase in small steps (+0.2 mm) only if leaking is severe. Avoid many objects per plate printed by layer; prefer `print_sequence` = `by object` and avoid crossing walls.\n- **PA/PC**: very hygroscopic: drying is mandatory, strings are usually moisture.\n- **CF/GF filled**: abrasive, enlarge brass nozzles over time → more ooze; use a hardened nozzle and check wear.\n\n## Sources\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/stringing-oozing\n- https://wiki.bambulab.com/en/software/bambu-studio/parameter/retraction\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/filament-sticks-to-nozzle\n- https://wiki.bambulab.com/en/filament-acc/filament/dry-filament\n- https://wiki.bambulab.com/en/knowledge-sharing/tpu-printing-guide\n- https://help.prusa3d.com/article/stringing-and-oozing_1805\n- https://help.prusa3d.com/article/drying-filament_332086\n- https://www.orcaslicer.com/wiki/calibration/retraction_calib.html\n- https://www.orcaslicer.com/wiki/calibration/temp_calib.html\n- https://www.orcaslicer.com/wiki/printer_settings/extruder/printer_extruder_retraction.html\n- https://www.orcaslicer.com/wiki/printer_settings/extruder/printer_extruder_z_hop.html\n- https://www.orcaslicer.com/wiki/material_settings/setting%20overrides/material_setting_overrides.html\n- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_travel.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_and_surfaces.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_seam.html\n- https://www.orcaslicer.com/wiki/print_settings/others/others_settings_g_code_output.html\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/stringing-or-oozing/\n- https://www.obico.io/blog/3d-print-troubleshooting-guide/\n",
    },
    "defect-supports": {
        "description": "Support problems - hard to remove or fused supports, supports falling or breaking mid print, rough or scarred surfaces above supports, too many or too few supports, dedicated and soluble support filaments. Read when the user reports supports that won't come off, broken or toppled supports or tree branches, an ugly, droopy or stringy underside above supports, support marks on the model, or supports appearing where they are not wanted or missing where needed.",
        "content": "# Supports: removal, failure, scars, amount\n\n## How to recognize it\n- Hard to remove: support or interface welds to the part, breaks into pieces, leaves residue; walls fused to supports at the sides.\n- Bad surface above supports: underside droopy, stringy or rippled, gaps between lines, or marks where the support touched.\n- Failing supports: towers or tree branches topple, detach from the plate, snap mid print; the overhang above then prints into air (spaghetti).\n- Too many: supports on the model surface, in holes, under small overhangs or short bridges. Too few: islands start in mid-air, sagging where support was expected.\n- Check the Preview to see where supports touch the model.\n\n## Likely causes, most common first\n1. Z/XY gap and interface density not balanced (small gap: good surface but welded; large gap: easy removal but droop).\n2. Same material for model and support with a top Z distance of 0 (only works with dedicated support or soluble interface filament).\n3. Thin, tall or sparse supports (tree tips too thin, small footprint) with poor plate adhesion or too much speed.\n4. Wrong type: tree under large flat overhangs (rough), normal grid on organic shapes (hard-to-reach support).\n5. Threshold angle and \"everywhere\" placement generating supports on the model.\n6. Mismatched or wet support filament (PVA, Support for PA/PET), or supports left too long on hygroscopic parts.\n\n## Questions worth asking (only when the answer changes the fix)\n- Same filament for support, or a dedicated/soluble support filament (which one)? Decides whether top Z distance 0 is allowed.\n- Problem is removal, surface quality, falling, or amount? Pick the matching table below.\n- Normal or tree support (separate keys)?\n- Do supports stand on the plate or on the model?\n- Multi-material printer (AMS/MMU/tool changer)? Enables support-interface filament options.\n\n## Slicer fixes\nChange one or two values, reslice, check Preview. Distances are rounded to layer height multiples unless `independent_support_layer_height` (process) is `1`.\n\n### A. Supports hard to remove / fused to the part\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `support_top_z_distance` (process) | increase | +0.05 mm | same material: about 0.1-0.25 mm (Orca default 0.2); 0 only with support/soluble interface filament | rougher, droopier underside |\n| `support_object_xy_distance` (process) | increase | +0.1 mm | 0.2-0.5 mm typical (key 0-10) | support reaches less of the overhang edge |\n| `support_interface_spacing` (process) | increase | +0.1 mm | 0 = solid interface | rougher underside |\n| `support_interface_pattern` (process) | `concentric` (peels in one piece) or `rectilinear` | enum | auto, rectilinear, concentric, spiralinset, `rectilinear_interlaced`, grid | interlaced and grid are stiffer and harder to remove |\n| `support_material_interface_fan_speed` (filament) | increase above normal fan | +20 % | 0-100; -1 = off | weaker bond is the goal; too much can warp ABS/ASA |\n| `support_base_pattern` (process) | `rectilinear` | enum | default, rectilinear, rectilinear-grid, honeycomb, lightning, hollow | rectilinear is the easiest to remove but least sturdy |\n| `support_interface_speed` (process) | increase (dedicated support filament) | +10 mm/s | never above printer limits | less stable interface; warping risk on ABS |\n| `support_style` (process) | `snug` when normal supports spread along walls | enum | default, grid, snug, organic, `tree_slim`, `tree_strong`, `tree_hybrid` | tall snug towers less stable |\n| `tree_support_branch_distance_organic` / `tree_support_branch_distance` (process) | increase | +1 mm | 1-10 mm | fewer contact points, rougher underside |\n\n### B. Rough or droopy surface above supports\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `support_interface_top_layers` (process) | increase | +1 | 2-4 | more material, harder to peel |\n| `support_interface_spacing` (process) | decrease | -0.1 mm | 0 = solid | harder removal |\n| `support_top_z_distance` (process) | decrease | -0.05 mm | see table A | harder removal |\n| `support_type` (process) | `normal(auto)` or `support_style` = `tree_hybrid` for big flat overhangs | enum | `normal(auto)`, `tree(auto)`, `normal(manual)`, `tree(manual)` | more material than tree |\n| `support_ironing` (process) | set `1` (needs top interface layers or raft) | on | `support_ironing_flow` default 10 % | more time; top interface printed solid |\n| `layer_height` (process) | decrease | -0.04 mm | ≤ 75 % of nozzle diameter, min 0.04 mm | longer print |\n| `tree_support_top_rate` (process, organic) | increase only if interface layers are not enough | +10 % | default 30 % | harder removal; interface layers are preferred |\n| `support_interface_filament` (process) | dedicated support filament slot, then `support_top_z_distance` = 0 | filament index | matching support material only | tool changes, purge (see defect-multimaterial) |\n| `support_bottom_z_distance` / `support_interface_bottom_layers` (process) | adjust where support stands on the model: more bottom layers protect that surface | +1 layer / +0.05 mm | -1 = same as top | harder removal there |\n\n### C. Supports falling, breaking or detaching\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `support_speed` (process) | decrease | -10-20 % | never above printer limits | time |\n| `support_base_pattern_spacing` (process) | decrease | -0.5 mm | default 2.5 mm | more material, harder removal |\n| `support_base_pattern` (process) | `rectilinear-grid` or `honeycomb` | enum | see table A | harder removal |\n| `tree_support_branch_diameter_organic` / `tree_support_branch_diameter` (process) | increase | +1 mm | 1-10 mm | more material |\n| `tree_support_branch_diameter_angle` (process, organic) | increase | +2° | 0-15° | wider bases |\n| `tree_support_angle_slow` (process, organic) | decrease (more vertical branches) | -5° | 10-85° | less reach around the model |\n| `tree_support_wall_count` (process) | set 2 | +1 | 0-2 (0 = auto) | harder removal |\n| `tree_support_auto_brim` / `tree_support_brim_width` (process; slim/strong/hybrid) | on, or wider brim | +2 mm | 0 = no brim | more plate area |\n| `raft_first_layer_expansion` / `raft_first_layer_density` (process) | increase for normal supports on the plate | +1 mm / +10 % | density 10-100 % | more material |\n| `support_style` (process) | `grid` (stable) or `tree_strong` instead of slim/snug | enum | see table A | more material |\n\n### D. Too many or too few supports\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `support_threshold_angle` (process) | lower = fewer supports; raise = more | ±5° | 1-90, default 30; 0 = special (overlap threshold) | too low: drooping overhangs |\n| `support_on_build_plate_only` (process) | set `1` to stop supports on the model | on | check unsupported areas in Preview | some overhangs left unsupported |\n| `support_remove_small_overhang` (process) | set `1` | on | boolean | rare tiny droops |\n| `support_critical_regions_only` (process) | set `1` (tree(auto) only) | on | boolean | only sharp tails/cantilevers supported |\n| `bridge_no_support` (process, normal) / `max_bridge_length` (process, tree) | on / raise length | +5 mm | default 10 mm | long bridges may sag |\n| `support_type` (process) | `normal(manual)` / `tree(manual)` + painted enforcers | enum | | only painted areas supported |\n| `enable_support` (process) | `1` if overhangs are missing support | on | | see too-many rows |\n\n## Checks the user must do by hand (hardware, material, printer settings)\n- Support painting (Prepare -> Support painting, or add a Support blocker / enforcer shape): block supports on cosmetic faces and inside holes, enforce under critical islands or mid-span of long bridges.\n- Orientation or cutting the model so fewer, shorter supports are needed.\n- Clean plate, good first layer: small support footprints detach first.\n- Match support filament to the model material: Support for PLA only with PLA, Support for PA/PET only with PA/PET; PVA is not for PETG. Mismatched pairs can clog the nozzle.\n- Dry support filaments (PVA, BVOH, Support for PA/PET) and keep them below ~20 % RH while printing; wet PVA clogs and strings.\n- Remove supports within about 2 h on PA/PA-CF parts and with PVA or Support for PA/PET; if they have absorbed moisture, dry the part, let it cool, then remove.\n- Pliers/knife and eye protection: snapped pieces can fly.\n- Dissolving: PVA/BVOH in warm water (max about 45 °C for PLA parts), hours to overnight, brush off residue. Support for ABS (HIPS) can be dissolved in d-limonene: ventilation, FKM gloves, no open flames or hot surfaces.\n\n## Calibration in Orca (menu Calibration -> ...)\n- No support test. Run Temperature and Flow rate first; then print a small overhang test with 2-3 `support_top_z_distance` values as per-object overrides. See calibration-guide.\n\n## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)\n- PLA: same-material top Z about 0.2 mm; best interface: Support for PLA, PVA or BVOH (top Z 0). PETG works as interface-only support for PLA.\n- PETG: welds to PETG supports; PLA as interface-only works well (PLA and PETG bond poorly). Use BVOH, not PVA, as soluble support.\n- ABS/ASA: Support for ABS (HIPS; listed for ABS) as interface; grid style for normal supports; more interface layers ease removal. Purge between them matters (see defect-multimaterial).\n- TPU: bonds strongly to TPU supports; larger Z/XY distance or orientation without supports.\n- PA/PC and CF/GF: ABS or ASA can support PA6-CF, PAHT-CF, PET-CF; ASA bonds weakly to PA-CF, so use it for interface and body. Remove supports promptly (moisture).\n- PVA: base + interface for internal supports, interface only when supports start on the plate (poor plate adhesion); normal supports, not tree.\n\n## Sources\n- https://wiki.bambulab.com/en/software/bambu-studio/support\n- https://wiki.bambulab.com/en/filament/support\n- https://wiki.bambulab.com/en/filament-acc/filament/support-for-abs\n- https://wiki.bambulab.com/en/filament-acc/filament/h2d-pla-and-petg-mutual-support\n- https://wiki.bambulab.com/en/filament-acc/filament/pva-printing-guide\n- https://wiki.bambulab.com/en/software/bambu-studio/support-painting\n- https://help.prusa3d.com/article/support-material_1698\n- https://help.prusa3d.com/article/failing-supports_1807\n- https://help.prusa3d.com/article/bad-looking-surface-above-supports_1803\n- https://help.prusa3d.com/article/organic-supports_480131\n- https://help.prusa3d.com/article/paint-on-supports_168584\n- https://help.prusa3d.com/article/water-soluble-materials-pva-bvoh_162860\n- https://help.prusa3d.com/article/water-soluble-bvoh-pva_167012\n- https://help.prusa3d.com/article/flexible-materials_2057\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/poor-surface-above-supports/\n- https://www.orcaslicer.com/wiki/print_settings/support/support_settings_support.html\n- https://www.orcaslicer.com/wiki/print_settings/support/support_settings_advanced.html\n- https://www.orcaslicer.com/wiki/print_settings/support/support_settings_tree.html\n- https://www.orcaslicer.com/wiki/print_settings/support/support_settings_filament.html\n- https://www.orcaslicer.com/wiki/print_settings/support/support_settings_raft.html\n- https://www.orcaslicer.com/wiki/print_settings/support/support_settings_ironing.html\n",
    },
    "defect-top-surface": {
        "description": "Covers top-surface defects: pillowing, holes or gaps in the top layers, pinholes along the walls, ridges and overfilled tops, scars or scratches from the nozzle, visible lines or uneven texture on top, and ironing setup and ironing problems. Read when the user reports \"pillowing\", \"holes on top\", \"top layer not closed\", \"gaps in top layer\", \"bumpy top\", \"scratches/scars on top\", \"lines on the top surface\", \"rough top\" or asks about \"ironing\".",
        "content": "# Top surface defects and ironing\n\n## How to recognize it\n- **Pillowing**: bumps, sagging lines or small holes on the top surface, often in a grid matching the infill cells below; worse on thin top shells, low infill, thin layers and curved or sloped tops.\n- **Gaps in top layers**: top lines do not touch each other (under-extrusion) or pinholes stay where the top infill meets the walls.\n- **Overfilled top**: ridges, material piled along the walls, rough or wavy surface; the nozzle can drag excess plastic.\n- **Scars / scratches**: grooves or smears along travel paths across finished top layers.\n- **Lines or uneven texture**: ridges where zig-zag lines change direction, different sheen between areas, visible infill pattern through a thin top.\n- **Ironing problems**: shiny unironed grooves (ironing flow too low), plastic pushed to the edges (too high), fuzzy edges, part knocked off, clog during ironing.\n\n## Likely causes, most common first\n1. Top shell too thin for the layer height: few top layers bridge over sparse infill and sag. Aim for about 0.8-1.0 mm of solid top (e.g. 4-5 layers at 0.2 mm, 8-9 at 0.1 mm).\n2. Sparse infill too sparse for the top to bridge on (low density, wide-cell pattern).\n3. Under-extrusion (flow ratio, partial clog, dirty extruder): even slight under-extrusion is visible on top. See defect-extrusion.\n4. Over-extrusion: ridges at the walls and nozzle dragging (scars).\n5. Sloped or curved tops: small internal bridges are filtered out by default, so solid infill curls over unsupported spots and pillows.\n6. Travel over finished top layers without Z-hop.\n7. Top surface printed too fast or with high acceleration; rectilinear top pattern.\n8. Wrong pressure advance: bulges or thin starts at each line end near the walls.\n\n## Questions worth asking (only when the answer changes the fix)\n- Holes/bumps everywhere on top, only near the walls, or only on curved/sloped areas?\n- Layer height, top shell layers and infill density in use (read them from the process preset).\n- Scratches: do they follow travel moves between parts or islands?\n- Is the top surface flat (ironing helps) or curved (ironing is useless there)?\n- Was flow calibrated for this spool?\n\n## Slicer fixes\nPillowing / holes (most effective and least risky first):\n\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `top_shell_layers` (process) | increase | +1-2 layers | about 0.8-1.0 mm total top thickness is enough for most prints | more time and material |\n| `top_shell_thickness` (process) | increase (adds layers automatically at thin layer heights) | 0.6 → 0.8-1.0 mm | 0 disables it | more time and material |\n| `sparse_infill_density` (process) | increase | +5-10% (e.g. 15% → 20-25%) | rarely needed above 30-40% for top support | heavier part, longer print |\n| `dont_filter_internal_bridges` (process) | `limited` for sloped or curved tops; `nofilter` only for heavily sloped tops | one enum step | default `disabled` = filter | extra internal bridges, more time |\n| `thick_internal_bridges` (process) | keep `1` (default) when printing over sparse infill | - | - | slightly worse look of internal bridges, more reliable support |\n| `top_surface_speed` (process) | decrease | -20-30% | machine limits | longer print |\n| `top_surface_acceleration` (process) | decrease | -20-30% | machine limits | longer print |\n| `top_bottom_infill_wall_overlap` (process) | increase for pinholes along walls | 25% → 30% | ≤ 35% | small ridge at the edge |\n| `filament_flow_ratio` (filament) | increase if top lines do not touch | +0.02 or calibrate | 0.8-1.2 | over-extrusion elsewhere if overdone |\n| `top_surface_expansion` (process) | increase when the top is interrupted by raised text or bosses leaving holes around them | 1-5 mm | 0 disables | may reach the walls and leave a hull line; `top_surface_expansion_margin` keeps distance |\n\nOverfilled top, ridges, lines:\n\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `filament_flow_ratio` (filament) | decrease if the whole print is overfilled | -0.02 or calibrate | 0.8-1.2 | under-extrusion if overdone |\n| `top_solid_infill_flow_ratio` (process) — BY HAND | decrease if only the top is overfilled | 1.0 → 0.95-0.98 | by hand only (plugin cannot check it), keep 0.8-1.2; Process → Quality → Wall and surfaces → Surface flow ratio, see defect-triage | gaps if too low |\n| `top_surface_pattern` (process) | `monotonicline` (default) or `monotonic` instead of `rectilinear`; `concentric` or `archimedeanchords` for round tops | - | - | concentric/spiral patterns take longer |\n| `top_surface_line_width` (process) | 100-105% of nozzle | - | ≤ 150% of nozzle; below 100% bonds worse | narrower = slower |\n| `only_one_wall_top` (process) | `1` for small tops such as letters, so the pattern covers them | - | - | slightly weaker top edge |\n| `small_area_infill_flow_compensation` (process) | `1` (beta) for overfilled small solid areas | - | only with rectilinear, aligned rectilinear, monotonic, monotonic line patterns | uses the compensation model; experimental |\n\nScars from travel:\n\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| fix over-extrusion first | - | - | - | - |\n| `filament_z_hop` (filament) | increase | 0.2-0.4 mm | 0-2 mm; `nil` = printer value | slightly more stringing, longer travels |\n| `filament_retract_lift_enforce` (filament) | `Top Only` to lift only over top surfaces | - | `nil` = printer value | - |\n\n### Ironing (flat tops only)\nIroning reruns the nozzle over the last top layer with a tiny flow at the same height. It only works on flat, horizontal surfaces; on curved or organic shapes it adds time for no benefit. Calibrate flow first: ironing is very sensitive to it.\n\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `ironing_type` (process) | `top` (all top surfaces) or `topmost` (last layer only); `solid` only for clearer translucent parts | - | default `no ironing` | much longer print, mostly with `solid` |\n| `ironing_flow` (process) | increase if unironed grooves remain; decrease if plastic piles at edges | ±2% from the default 10% | keep small; thinner layers may need a bit more | over-extruded, rough surface if too high |\n| `ironing_spacing` (process) | decrease for smoother finish | 0.1 mm default | ≤ nozzle diameter | longer ironing |\n| `ironing_speed` (process) | decrease | default 20 mm/s | slower = better | longer print, more heat-creep risk |\n| `ironing_inset` (process) | increase if edges build up | +0.1-0.2 mm | 0 = half the nozzle diameter | edges stay unironed |\n| `ironing_pattern` (process) | `concentric` for round or rounded tops | - | - | - |\n| `ironing_angle` (process) | offset to the top infill direction (45 is a common good choice) | - | 0-359 | - |\n| `ironing_fan_speed` (filament) | lower than normal to reduce clogging at the low flow | - | -1 disables | - |\n\nPer-filament overrides exist: `filament_ironing_flow`, `filament_ironing_spacing`, `filament_ironing_inset`, `filament_ironing_speed` (filament). Alternative to ironing: print the flat face down on the plate; the bottom face is usually smoother than an ironed top.\n\n## Checks the user must do by hand (hardware, material, printer settings)\n- Partial clog, dirty extruder gears or filament path drag cause top gaps and falsify any flow test: clean before calibrating (see defect-clogs-heat-creep).\n- The nozzle installed must match the nozzle diameter of the printer profile (printer setting the user changes by hand); a mismatch gives wrong top flow.\n- Printer Z-hop height and lift rules are printer settings; the AI may only use the filament overrides above.\n- Ironing pushes on the part: make sure the part is well stuck to the plate (clean plate, brim if needed).\n- Ironing and heat creep: low, slow flow can clog, mainly PLA in hot rooms or enclosed printers with doors closed. Check hotend cooling; open the door/lid for PLA on enclosed printers.\n- Wet filament gives rough, bubbly tops; dry it.\n\n## Calibration in Orca (menu Calibration → ...)\n- **Flow ratio** (YOLO recommended): the blocks are judged on the top surface, smoothest without gaps; exactly the criterion for this defect.\n- **Pressure advance**: for bulges or thin spots at line ends near walls.\n- **Temperature**: if tops are rough or dull at the chosen speed.\n- See calibration-guide for order and reading.\n\n## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)\n- **PLA**: pillowing is most frequent with PLA; more top layers, more infill and slower top speed help. Irons very well but is the most heat-creep prone during ironing (summer, closed enclosure). Silk PLA: `archimedeanchords` top pattern gives more luster.\n- **PETG**: irons well but excess plastic sticks to the nozzle, darkens and can drop on the part; keep nozzle clean, moderate ironing flow.\n- **ABS/ASA**: ASA irons very well, giving very smooth tops.\n- **TPU**: avoid ironing; strong buildup on the nozzle and clog risk.\n- **PA/PC**: dry the filament first; moisture shows as rough, pitted tops.\n- **CF and wood fills**: wood-filled filaments iron poorly (Prusa). For CF/GF see material-composites.\n\n## Sources\n- https://wiki.bambulab.com/en/knowledge-sharing/common-print-quality-problem\n- https://wiki.bambulab.com/en/software/bambu-studio/parameter/ironing\n- https://wiki.bambulab.com/en/filament/pla\n- https://help.prusa3d.com/article/ironing_177488\n- https://help.prusa3d.com/article/layers-and-perimeters_1748\n- https://help.prusa3d.com/article/infill-patterns_177130\n- https://help.prusa3d.com/article/extrusion-multiplier-calibration_2257\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_ironing.html\n- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_top_bottom_shells.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_and_surfaces.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_bridging.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_line_width.html\n- https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html\n- https://www.orcaslicer.com/wiki/calibration/flow_ratio_calib.html\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/gaps-in-top-layers/\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/scars-on-top-surface/\n- https://www.matterhackers.com/articles/3d-printer-troubleshooting-guide\n- https://www.obico.io/blog/3d-print-troubleshooting-guide/\n",
    },
    "defect-triage": {
        "description": "Start here for any print problem: maps what the user sees (strings, lifting corners, gaps, lines on walls, blobs, cracks, shifted layers, clogs, failed supports, wrong size) to the right defect skill and gives the diagnostic order and plugin limits. Read when the user describes a bad print but the defect is unclear, or several defects at once.",
        "content": "# Print defect triage\n\n## Method (follow in this order)\n1. **Pin down the symptom.** Ask for a photo if none was given. Locate the defect: first layer, walls, top surface, under overhangs, around supports, at layer changes, only on one object, only in one part of the plate.\n2. **Ask what changed.** New spool or brand, filament left out for days, new or edited profile, new plate, different printer mode (silent/sport), hardware work. A defect that appeared suddenly on a profile that used to work points to hardware or material, not to the profile.\n3. **Read the current settings** (process + filament) before proposing anything, and identify printer, nozzle diameter, plate type and material.\n4. **Rule out hardware and material first** when the symptom points there (see \"Hardware first\" below). Explain these checks to the user; never try to compensate a mechanical fault with parameters.\n5. **Calibrate before tuning.** If flow, pressure advance, temperature or max volumetric speed were never calibrated for this filament, recommend the matching calibration (see calibration-guide) instead of guessing values.\n6. **Change few settings, in small steps**, most effective and least risky first. Say what each change costs (time, strength, surface). One defect per round; ask the user to reprint (ideally a small test) before the next round.\n\n## Symptom → skill\n| What the user sees or says | Skill |\n|---|---|\n| strings, hairs, cobwebs, wisps between parts; oozing during travel | defect-stringing |\n| visible seam line, zits, pimples, blobs on walls, bumps where layers start | defect-seam-zits-blobs |\n| nozzle not extruding, extrusion stops mid print, clicking extruder, ground filament, filament balled on the nozzle, heat creep | defect-clogs-heat-creep |\n| corners lifting, part detaching, curling at the base, print knocked off | defect-warping |\n| first layer not sticking, too squished, ridges or gaps in the first layer, elephant foot, part impossible to remove | defect-first-layer |\n| layers splitting, cracks in tall parts, delamination, part breaks along layer lines | defect-layer-adhesion |\n| gaps between lines or walls, thin weak walls, holes in walls, too much material, rough overfilled surfaces, uneven gloss | defect-extrusion |\n| pillowing, holes or gaps on the top, scratches or lines on top surfaces, ironing problems | defect-top-surface |\n| small parts or tips melted/deformed, thin walls or tiny features missing, gaps inside thin walls | defect-overheating-small-features |\n| ghosting, ringing, echoes after corners, ripples, vertical bands/fine vertical artefacts (VFA), wobble, salmon skin | defect-ringing-ghosting |\n| whole layers offset sideways, staircase shift | defect-layer-shift |\n| spaghetti, print collapsed or turned into a tangle mid print | find what failed first: part came loose (defect-warping, defect-first-layer), support fell (defect-supports), extrusion stopped (defect-clogs-heat-creep) |\n| part too big/small, holes too tight, pegs do not fit, shrinkage, warped dimensions | defect-dimensional-accuracy |\n| drooping or curling overhangs, sagging or broken bridges | defect-overhangs-bridges |\n| supports hard to remove, falling over, failing mid print, ugly surface above supports, too many or missing supports | defect-supports |\n| AMS/MMU/multi-tool: colour bleeding, too much purge waste, prime tower problems, ooze from the idle nozzle | defect-multimaterial |\n| which temperature/plate/fan for a material, drying, material choice | materials-overview, then material-pla, material-petg, material-abs-asa, material-tpu, material-pa-pc, material-composites, material-special |\n| no defect, a goal: print faster / less filament; stronger or watertight part; smoother surface, finer detail, vase mode, fuzzy skin | goal-faster-prints, goal-stronger-parts, goal-surface-quality |\n| which calibration to run and in which order | calibration-guide |\n| exact key name, value format, enum values, PrusaSlicer/Cura name translation | orca-settings-reference |\n| printer-specific behaviour (enclosure, AMS, Nextruder, limits) | printers-bambu, printers-prusa |\n\nCombined symptoms: strings + blobs usually share a cause (too hot, wet filament, weak retraction): start with defect-stringing. Gaps on top + weak walls + rough sound from the extruder: start with defect-clogs-heat-creep, then defect-extrusion. Droopy overhangs + melted small tips: cooling problem, defect-overheating-small-features and defect-overhangs-bridges.\n\n## Hardware first (explain, do not fix with settings)\n- **Wet filament**: popping/hissing, steam, bubbles, rough surface, many strings, brittle filament (PETG, TPU, PA, PC, PVA most sensitive). → dry it (see materials-overview).\n- **Plate**: fingerprints/grease, wrong side or wrong plate type selected, worn PEI, missing glue where required.\n- **Z offset / levelling**: first layer uniformly too high or too squished, or only on one side.\n- **Partial clog, worn nozzle, dirty extruder gears**: under-extrusion that appeared suddenly, clicking, inconsistent lines; abrasive (CF/GF) filament on a brass nozzle.\n- **Part cooling fan not spinning or blocked**: sudden droopy overhangs and melted details.\n- **Belts, pulleys, loose parts, collisions**: layer shifts, ringing that got worse over time.\n- **Environment**: drafts, cold room, open door on an enclosed printer for ABS/ASA (or closed door for PLA on enclosed printers, which can soften PLA in the extruder).\n\n## What the plugin may change (keep proposals inside this)\n- Only **process** and **filament** preset keys. Printer settings (printer retraction, Z offset, machine limits, nozzle diameter) are explained to the user, never changed.\n- Never: custom G-code or post-processing scripts, material data (diameter, density, type, shrinkage), filament temperature ranges, chamber heating.\n- Limits: nozzle temperature inside the filament range; plate temperature at most +10 °C over the current value (max 120 °C); `filament_flow_ratio` 0.8-1.2; `filament_max_volumetric_speed` at most +10%; `layer_height` and `initial_layer_print_height` ≤ 75% of the nozzle; `filament_retraction_length` 0 .. min(8 mm, max(2 mm, 2× printer retraction)); `filament_retraction_speed` and `filament_deretraction_speed` > 0 and ≤ max(1.5× printer value, 30 mm/s); `filament_z_hop` 0-2 mm; speeds, accelerations and jerk within the machine limits.\n- If the right fix is outside these limits, say so and tell the user what to do by hand.\n\n## Settings the plugin cannot check: the user changes them by hand\nNever put these in a proposal: the plugin cannot verify a safe value for them. Explain the change and guide the user step by step, using the menu path and the Orca wiki page:\n- Per-feature flow ratios (`first_layer_flow_ratio`, `outer_wall_flow_ratio`, `inner_wall_flow_ratio`, `top_solid_infill_flow_ratio`, `bottom_solid_infill_flow_ratio`, `sparse_infill_flow_ratio`, `internal_solid_infill_flow_ratio`, `overhang_flow_ratio`, `gap_fill_flow_ratio`, `support_flow_ratio`, `support_interface_flow_ratio`, switch `set_other_flow_ratios`): Process → Quality → Wall and surfaces → Surface flow ratio (per-feature ratios appear after enabling \"Set other flow ratios\"); https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_and_surfaces.html. Keep them 0.8-1.2; they multiply the filament flow ratio.\n- Also by hand only, flow ratios in other sections: `brim_flow_ratio` (Process → Others → Brim), `scarf_joint_flow_ratio` (Process → Quality → Seam → Scarf joint seam), `spiral_starting_flow_ratio` and `spiral_finishing_flow_ratio` (Process → Others → Special mode → Spiral vase).\n- Bridge flow (`bridge_flow`, `internal_bridge_flow`): Process → Quality → Bridging → Flow ratio; https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_bridging.html.\n- Extra length on restart (`filament_retract_restart_extra`, `filament_retract_restart_extra_toolchange`): Filament → Setting overrides → Retraction → Extra length on restart; https://www.orcaslicer.com/wiki/material_settings/setting%20overrides/material_setting_overrides.html. Only tiny values (±0.1 mm).\n- Air filtration and exhaust fan (`activate_air_filtration`, `activate_air_filtration_during_print`, `activate_air_filtration_on_completion`, `during_print_exhaust_fan_speed`, `complete_print_exhaust_fan_speed`): Filament → Cooling → Exhaust fan; https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html.\n- Temperature keys other than nozzle and plate temperatures (the plugin blocks them), e.g. idle/standby nozzle temperature for multi-tool ooze prevention: Filament → Multimaterial and Process → Multimaterial → Ooze prevention.\n- Values outside the plugin limits (e.g. flow ratio below 0.8 for foaming PLA/ASA, a bigger jump in max volumetric speed after a calibration): same approach, give the field name as shown in Orca and its tab.\n- Printer settings (printer retraction, Z offset, machine limits, nozzle): Printer settings tab, see https://www.orcaslicer.com/wiki/printer_settings/extruder/printer_extruder_retraction.html and the other pages under https://www.orcaslicer.com/wiki/printer_settings/.\nIn each fixes table these rows are marked \"BY HAND\".\n\n## Sources\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality\n- https://wiki.bambulab.com/en/knowledge-sharing/troubleshooting-printing-issues\n- https://wiki.bambulab.com/en/knowledge-sharing/common-print-quality-problem\n- https://www.prusa3d.com/print-quality-troubleshooting\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/\n- https://www.obico.io/blog/3d-print-troubleshooting-guide/\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_and_surfaces.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_bridging.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_seam.html\n- https://www.orcaslicer.com/wiki/print_settings/others/others_settings_brim.html\n- https://www.orcaslicer.com/wiki/print_settings/others/others_settings_special_mode.html\n- https://www.orcaslicer.com/wiki/material_settings/setting%20overrides/material_setting_overrides.html\n- https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html\n- https://www.orcaslicer.com/wiki/printer_settings/extruder/printer_extruder_retraction.html\n",
    },
    "defect-warping": {
        "description": "Warping and lifting of the part: corners or edges curling up off the plate, a curved bottom, the base peeling during the print, parts coming loose or popping off mid print, the ripple left where the nozzle hits a lifted corner. Read when the user reports warping, corners lifting, edges curling, the print detaching or falling off the bed mid print, or a bent bottom face.",
        "content": "# Warping, lifting corners, part detaching mid print\n\n## How to recognize it\n- Corners or edges rise off the plate during the print, mostly on large, flat or long parts with sharp corners; after removal the bottom face is curved.\n- A horizontal ridge a few mm above the plate on the side walls: the nozzle hit a corner that had already lifted. Slight lifting can mimic flow or top-surface defects: check that the base is flat before tuning extrusion.\n- The whole part slides or pops off mid print: grip problem (plate, plate type, Z) or the nozzle knocking over a tall thin part.\n- Only the first layer peels or never sticks: use defect-first-layer. Curling tips or overhangs high in the part: defect-overhangs-bridges / defect-overheating-small-features. Horizontal cracks between layers on ABS/ASA/PC: same thermal stress, see defect-layer-adhesion.\n\n## Likely causes, most common first\n1. Dirty plate (skin oil from fingers is the top cause).\n2. Plate type selected in Orca does not match the physical plate: the bed is heated to the wrong plate temperature. Bambu: on a Textured PEI plate the printer lowers the nozzle 0.04 mm only if Textured PEI is the selected plate type.\n3. Material shrinkage vs. cold surroundings: risk order PC > PA-CF > PA > ABS > ASA > PETG > PLA. Drafts (window, AC, desk fan) and rooms below about 20 °C make even PLA/PETG lift; large ABS/ASA/PC/PA parts warp on open-frame printers.\n4. Bed temperature too low for material and plate.\n5. Too much part cooling: fan running in the first layers, strong auxiliary fan, high fan on ABS/ASA/PC.\n6. First layer not squished enough (Z offset, levelling): see defect-first-layer.\n7. Small contact area or sharp corners and no brim.\n8. Large part with dense infill (above ~50%) or straight-line infill (grid, triangles): more internal shrink tension.\n9. High speed: more stress in the part and more shear from the nozzle.\n\n## Questions worth asking (only when the answer changes the fix)\n- Which plate is physically on the printer, which plate type is selected in Orca, glue or not?\n- Open-frame or enclosed printer, doors/lid closed, room temperature, draft sources nearby?\n- Does it lift in the first few layers (grip) or after several mm (shrink stress, environment)?\n- When was the plate last washed with soap? Was it touched?\n- Part size, infill density and pattern; one object or several?\n\n## Slicer fixes\nChange the plate temperature pair that matches the plate in use: `textured_plate_temp`/`textured_plate_temp_initial_layer` (Textured PEI), `hot_plate_temp`/`hot_plate_temp_initial_layer` (Smooth PEI / High Temp), `cool_plate_temp`/`cool_plate_temp_initial_layer`, `textured_cool_plate_temp`/`textured_cool_plate_temp_initial_layer`, `eng_plate_temp`/`eng_plate_temp_initial_layer`, `supertack_plate_temp`/`supertack_plate_temp_initial_layer`.\n\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `brim_type` (process) | `outer_only` (or `auto_brim`); for corners only `brim_ears` (mouse-ears value of `brim_type`) or `painted` | - | - | brim to trim off the bottom edge |\n| `brim_width` (process) | increase | to 5 mm; PLA corners 8-10 mm | ≤ 18 mm | more material; ear radius when **brim_ears** |\n| `brim_object_gap` (process) | decrease | to 0-0.05 mm | 0..2 mm | brim harder to remove |\n| plate temp pair for the plate in use (filament) | increase | +5 °C (open printer in a cold room: +10 °C) | ≤ +10 °C over current, never above 120 °C | PLA/PETG: elephant foot, heat creep in enclosed printers |\n| `close_fan_the_first_x_layers` (filament) | increase | to 3 | 1-5 layers | weaker overhangs/bridges in those layers |\n| `additional_cooling_fan_speed` (filament) | decrease | -20-30 points (PLA: 40-50%) | 0-100%; only printers with an auxiliary fan | small details cool less |\n| `fan_max_speed` / `fan_min_speed` (filament) | decrease (ABS/ASA/PC/PA) | -10-20 points; ABS about 30-40% max | keep enough cooling for PLA/PETG | overhangs droop |\n| `reduce_fan_stop_start_freq` (filament) | `0` for ABS/ASA/PC | - | - | fan stops on long layers |\n| `internal_bridge_fan_speed` (filament) | set below the normal fan speed | - | -1 = use overhang fan; needs `enable_overhang_bridge_fan` = `1` | rougher internal bridges |\n| `sparse_infill_pattern` (process) | `gyroid` on large flat parts | - | - | slower slicing |\n| `sparse_infill_density` (process) | decrease on large parts | to 15-25% | avoid > 50% on large parts | lower strength |\n| `draft_shield` (process) | `enabled` (ABS/ASA/PC, open frame) | with `skirt_loops` ≥ 1 | - | more filament and time |\n| `raft_layers` (process) | from 0 to 2-4 | +1 | 2-4 usual | rough bottom, time; disables elephant foot compensation |\n| `initial_layer_speed` / `initial_layer_infill_speed` (process) | decrease | -20-30% | never above printer limits | longer first layer |\n| `slow_down_layers` (process) | increase | to 2-3 | - | slightly longer print |\n| `outer_wall_speed`, `inner_wall_speed`, `sparse_infill_speed`, `default_acceleration` (process) | decrease (high-warp material, tall thin parts) | -20-30% | never above printer machine limits | longer print |\n| `brim_use_efc_outline` (process) | `1` when `elefant_foot_compensation` > 0 leaves a gap between brim and part | - | - | brim may fuse with upper layers |\n| `enable_support` (process) | `1` for tall thin parts knocked over | - | - | support marks |\n\nNotes for the AI:\n- Brim first: least risk, fixes most corner lifting. `auto_brim` sizes the brim from height, footprint, speed and material and can produce no brim on small parts; set `outer_only` + `brim_width` when the user needs it to hold.\n- **brim_ears**: ears at corners sharper than `brim_ears_max_angle` (default 125); `painted`: the user paints ears in the Prepare tab (Brim ears painting tool); `brim_ears_outer_only` = `1` skips ears inside holes.\n- With `elefant_foot_compensation` > 0 the preview shows a gap between brim and part; it is normally filled by squish. If the printed brim does not touch the part, reduce the compensation or enable `brim_use_efc_outline`.\n- Do not stack several fan reductions on PLA/PETG at once: overhangs and small parts depend on cooling.\n\n## Checks the user must do by hand (hardware, material, printer settings)\n- Wash the plate: warm water + dish soap (no lotion-type soaps), rinse, dry, hold by the edges. Clean plate test (Bambu): water spreads as a film; beads and streams mean residue. Textured PEI: soap and sponge/brush, never acetone. Prusa smooth PEI: IPA 90%+ when cold, acetone only occasionally; never acetone on textured/satin sheets or SuperTack.\n- Select the plate type in Orca (Prepare tab plate selector) that matches the plate on the printer. The AI cannot change it; tell the user.\n- Glue: thin, even layer. Often needed for ABS/ASA/PA/PC on PEI, always on the Bambu Engineering Plate, on smooth PEI for everything except PLA (also protects the sheet). Bambu Cool Plate (old) needs glue even for PLA.\n- Re-run bed levelling (always after moving the printer); first layer must be slightly squished (defect-first-layer).\n- Enclosure: close doors and top cover; Bambu suggests 40 °C+ inside for ABS/ASA. The plugin never changes chamber heating: on printers with active chamber heating the user sets it by hand.\n- Remove drafts: windows, AC vents, fans. Ventilate the room for ABS/ASA without blowing on the printer.\n- Place warp-prone parts near the plate centre; printing several objects together keeps more heat around them (Prusa).\n- Open-frame printers (Bambu A1, MK4 without enclosure): large ABS/ASA/PC parts almost always warp; suggest PLA, PETG, PLA-CF or PETG-CF.\n- Design: rounded corners warp less than sharp ones; small discs at corners (a few layers tall) act like ears.\n- Wet filament (crackling, bubbly surface): dry it.\n- Bambu: nozzle clips fastened correctly. Tall parts collapsing: check belt tension.\n\n## Calibration in Orca (menu Calibration → ...)\nNo calibration measures warping. Fix the first layer first (defect-first-layer). Calibration → Temperature only if the filament runs outside its usual range. See calibration-guide.\n\n## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)\n- PLA: low shrink. Bambu Textured PEI 55-65 °C; Cool Plate / SuperTack 35-45 °C. Room below 20 °C or open printer: +10 °C bed. Enclosed printers with bed > 45 °C: open door/lid to avoid heat creep.\n- PETG: low warping. Bambu PEI plates 60-80 °C; SuperTack gen 2 about 55-60 °C (X/P series profiles may use 65 °C). Bonds too strongly to smooth PEI: use glue as release layer.\n- ABS/ASA: high shrink. Bed 90-100 °C (Bambu); Prusa ABS 100 °C (80-110 by part size), ASA 105/110 °C. Enclosure, low or no fan, glue on PEI, draft shield if open frame. ASA warps less than ABS.\n- TPU: hardly warps; never on SuperTack.\n- PA/PC: highest shrink. Bed 100-120 °C (Bambu), enclosure, glue, dry filament. PC: fewer walls and lower infill on large parts reduce lifting; avoid parts covering the whole plate. PA: Prusa recommends its PA Nylon sheet.\n- CF/GF: PA-CF stays high-warp (enclosure, glue); PLA-CF and PETG-CF suit large flat parts. `auto_brim` gives PLA-CF/PET-CF/PA-CF wider brims. Bambu: glue stick for PA-CF/GF, PET-CF, ASA-CF.\n\n## Sources\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/warping-falling-off-collapsing\n- https://wiki.bambulab.com/en/knowledge-sharing/printed-model-warping\n- https://wiki.bambulab.com/en/software/bambu-studio/use-disc-to-avoid-warping\n- https://wiki.bambulab.com/en/software/bambu-studio/brim-ears\n- https://wiki.bambulab.com/en/software/bambu-studio/auto-brim\n- https://wiki.bambulab.com/en/filament-acc/acc/plates\n- https://wiki.bambulab.com/en/filament-acc/acc/pei-plate-clean-guide\n- https://wiki.bambulab.com/en/general/how-to-use-bbl-liquid-glue\n- https://wiki.bambulab.com/en/general/filament-guide-material-table\n- https://wiki.bambulab.com/en/general/engineering-plate-not-working-as-expected\n- https://wiki.bambulab.com/en/filament-acc/acc/bambu-cool-plate-supertack\n- https://help.prusa3d.com/article/warping_2011\n- https://help.prusa3d.com/article/first-layer-issues_1804\n- https://help.prusa3d.com/article/print-surface-preparation_686951\n- https://help.prusa3d.com/article/skirt-and-brim_133969\n- https://help.prusa3d.com/article/abs_2058\n- https://help.prusa3d.com/article/asa_1809\n- https://help.prusa3d.com/article/polycarbonate-pc_165812\n- https://help.prusa3d.com/article/polyamide-nylon_167188\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/warping/\n- https://www.orcaslicer.com/wiki/print_settings/others/others_settings_brim.html\n- https://www.orcaslicer.com/wiki/print_settings/others/others_settings_skirt.html\n- https://www.orcaslicer.com/wiki/print_settings/support/support_settings_raft.html\n- https://www.orcaslicer.com/wiki/print_prepare/prepare_brim_ears_painting.html\n- https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html\n- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_patterns.html\n",
    },
    "goal-faster-prints": {
        "description": "Goal skill for shorter print time and/or less filament - layer height, walls and shells, infill density and pattern (lightning, adaptive cubic), speeds against the filament's max volumetric speed, accelerations, supports, brim, variable layer height, reading Orca's time estimate, and what each saving costs. Read when the user asks \"make it print faster\", \"reduce print time\", \"it takes too long\", \"use less filament\", \"save material\", \"draft mode\", \"quick prototype\".",
        "content": "# Faster prints and less filament\n\nEvery saving is paid with strength, looks or risk. Find where the time goes, cut plastic first, then raise what is still below a cap. State the price of each change.\n\n## What to ask first\n- Less time, less filament, or both?\n- What may get worse: looks (prototype, hidden part) or strength (decorative part)? If neither, say that the gain will be small.\n- Printer, nozzle, material. Is the filament's max volumetric speed a vendor value, a calibrated one or a guess?\n- Ask the user to slice and read the Preview tab:\n  - total time and the Line Type legend (time and share per feature: outer wall, inner wall, sparse infill, support, travel);\n  - colour scheme \"Flow\" (mm³/s): large areas sitting at the filament's cap mean the hotend is the limit;\n  - colour scheme \"Speed\": real speeds after the cap and the cooling slowdown.\n- How to read it:\n  - most time in sparse infill or support: pattern, density, support rows;\n  - most time in walls: layer height, wall count, wall speeds;\n  - Flow at the cap almost everywhere: mm/s settings do nothing; only less plastic or a higher cap helps;\n  - speeds far below the settings on a small part: acceleration or minimum layer time is the limit.\n\n## Levers, biggest gain first\n| Key (preset) | Change | Typical step | Safe limit | What it costs |\n|---|---|---|---|---|\n| `layer_height` (process) | increase | 0.2 → 0.24 or 0.28 on a 0.4 mm nozzle | ≤ 75% of nozzle diameter (0.30 on 0.4 mm), min 0.04 mm | visible layer lines, rougher curves and overhangs, weaker bonding near the limit; more flow per mm, so the cap bites at lower mm/s |\n| `sparse_infill_pattern` (process) | change | visual parts: `lightning` or `supportcubic`; large functional parts: `adaptivecubic`; quick: `rectilinear`, `zigzag`, `grid`, `cubic` | avoid `gyroid`, `honeycomb`, `3dhoneycomb`, `tpmsfk`, `hilbertcurve` | `lightning` and `supportcubic` only hold up the top: no strength, uneven layer times; `grid` crosses itself in each layer (nozzle noise at speed) |\n| `sparse_infill_density` (process) | decrease | -5 points, down to 10-15% | about 10%; with `lightning` it is the density right under the top | less crush resistance and stiffness; top sags over wide cells |\n| `wall_loops` (process) | decrease | 3 → 2 | ≥ 2 on anything handled or loaded | largest strength loss per minute saved; infill shows through |\n| `top_shell_layers`, `bottom_shell_layers` (process) | decrease | -1 | top ≥ 3; `top_shell_thickness` (process) adds layers back when count × layer height is below it | pillowing, holes on top (defect-top-surface) |\n| `inner_wall_speed`, `sparse_infill_speed`, `internal_solid_infill_speed` (process) | increase | +10-20% per round | ≤ printer machine limits; no effect once the flow reaches `filament_max_volumetric_speed` | weaker layer bonding close to the cap, ringing, noise |\n| `default_acceleration`, `inner_wall_acceleration`, `sparse_infill_acceleration`, `travel_acceleration` (process) | increase | +20-30% | ≤ printer max acceleration; `default_acceleration` 0 = firmware values, the others are ignored | ringing, noise; keep `outer_wall_acceleration` and `top_surface_acceleration` low |\n| `filament_max_volumetric_speed` (filament) | increase, only after Calibration → Max flowrate | to the measured quality limit minus 10-20% | plugin: at most +10%; more only by hand | under-extrusion, matte patches, weak layers, clicking extruder, clogs |\n| `nozzle_temperature` (filament) | increase when printing close to the cap | +5-10 °C | inside the filament's temperature range | stringing, drooping overhangs, soft small details |\n| `infill_combination` (process) | `1` | `infill_combination_max_layer_height` (process) `100%` fastest, `80%` stronger | works only if 2 × `layer_height` fits in the nozzle diameter (0.2 on 0.4 mm yes; 0.24-0.28 no) | infill needs double flow (cap); weaker infill |\n| `inner_wall_line_width` (process) | increase | to 110-125% of nozzle | ≤ 150% of nozzle | saves time only if a wall loop is dropped for the same thickness; more flow per mm |\n| `support_type`, `support_style` (process) | `tree(auto)` with `default` or `tree_slim`; `snug` for normal supports | - | - | slim supports can fail under heavy overhangs (defect-supports) |\n| `support_threshold_angle` (process) | decrease | 30 → 25 or 20 | what the material still prints cleanly | drooping steep overhangs |\n| `brim_type` (process) | `no_brim` | - | not for ABS/ASA/PA, tall thin parts, small footprints | warping, parts knocked loose (defect-warping) |\n| `ironing_type` (process) | `no ironing` | - | - | no ironed top; ironing is among the slowest features |\n| `reduce_infill_retraction` (process) | `1` | - | - | slight ooze inside the infill |\n| `outer_wall_speed`, `top_surface_speed` (process) | increase, last of all | +10-20% | ≤ machine limits and the cap | gloss changes, ringing, rough top: visible quality goes first |\n\nNotes for the AI:\n- Flow (mm³/s) ≈ layer height × line width × speed: 0.2 × 0.45 mm at 200 mm/s = 18 mm³/s. Orca lowers every speed whose flow would exceed `filament_max_volumetric_speed`: highest useful speed = cap ÷ (layer height × line width).\n- At the cap, time ≈ plastic volume ÷ cap: thicker layers stop saving time. Remove plastic (infill, walls, supports) or raise the cap with a calibration. If a tall-layer profile is capped everywhere, a lower layer height gives more detail in about the same time.\n- Typical caps (Prusa): PLA 12-20, PETG 8-15, ABS/ASA 10-16, PA 8-12, PC 6-10, TPU 2-5 mm³/s; classic all-metal hotend 8-12, Prusa Nextruder 15-20, high-flow 20-40. Vendor presets hold tested values.\n- Keep inner-wall flow below the cap for bonding; after a Max flowrate test keep a 10-20% margin.\n- `fill_multiline` (process) `2` uses the same material: `gyroid` and `honeycomb` print about 15-20% faster, crossing patterns (`grid`, `cubic`) can get slower.\n- Never pair `lightning` with `alternate_extra_wall` (process).\n- Recipes for a 0.4 mm nozzle:\n  - Draft / visual prototype: `layer_height` 0.28, `wall_loops` 2, `lightning` or `adaptivecubic` at 10-15%, 3 top and 3 bottom layers, no ironing.\n  - Functional but quicker: keep walls, temperature and outer wall; `adaptivecubic` or `cubic` at 15%; inner-wall and infill speeds up to the cap.\n  - Less filament only: infill pattern and density, supports, brim; leave speeds alone.\n\n## Limits you cannot tune past (explain to the user)\n- **Hotend melt rate.** Above it walls come out thinner than sliced, surfaces turn matte, layers bond badly, the extruder clicks, the nozzle clogs.\n- **Machine limits.** Orca clamps process speeds, accelerations and jerk to the printer's Motion ability values; the plugin never edits printer settings.\n- **Minimum layer time.** Layers shorter than `slow_down_layer_time` (filament) are slowed, down to `slow_down_min_speed` (filament), so the plastic can set. On small or pointed parts speed settings do not help, and a lower layer time trades minutes for melted tips (defect-overheating-small-features).\n- **Small parts never reach the set speed**: only accelerations change their time, at the cost of ringing.\n- **First layer.** Leave `initial_layer_speed` (process) alone: a failed first layer costs more than it saves.\n- **Overhangs.** Keep `enable_overhang_speed` (process) on.\n- **The estimate** is the slicer's own: real time can differ, and a speed mode set on the printer changes it.\n\n## Checks and choices the user makes by hand\n- **Orientation**: a lower part with fewer supports prints faster. Auto orient (Prepare toolbar) looks for the least support; orientation also changes strength (goal-stronger-parts).\n- **Variable layer height** (Prepare toolbar, object selected): Adaptive with the Quality/Speed slider toward Speed, then Smooth. Thick layers go on vertical walls, thin ones only on curves. The range comes from the min/max layer height in the printer's extruder settings. Restrictions (Bambu documentation): a prime tower needs the same layer profile on all objects; not available with organic tree supports. The plugin cannot apply this tool.\n- **Per-object settings**: in the Process panel switch from Global to Objects and give walls and dense infill only to the object that needs them; a modifier (right-click → Add modifier) covers one region.\n- **Calibration → Max flowrate** (calibration-guide): the only sound way to raise the flow cap.\n- **Printer speed modes** (Bambu Sport / Ludicrous, set on the printer): Sport suits prototypes that must still work; Ludicrous is for drafts and costs surface, detail and layer bonding.\n- **Larger nozzle** (hardware plus the matching printer preset): 0.6 mm allows thicker layers, wider lines and a somewhat higher cap; fine detail is lost.\n- **Machine limits** (Printer settings → Motion ability): only by hand, within the manufacturer's values.\n\n## Related skills\n- goal-stronger-parts, goal-surface-quality (the opposite trades).\n- calibration-guide, defect-extrusion, defect-layer-adhesion, defect-ringing-ghosting, defect-top-surface, defect-supports, defect-warping, defect-overheating-small-features.\n- printers-bambu, printers-prusa (speed modes, hotend flow).\n\n## Sources\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_layer_height.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_line_width.html\n- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_walls.html\n- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_top_bottom_shells.html\n- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_infill.html\n- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_advanced.html\n- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_patterns.html\n- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_patterns_quick_reference.html\n- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_other_layers_speed.html\n- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_acceleration.html\n- https://www.orcaslicer.com/wiki/print_settings/support/support_settings_support.html\n- https://www.orcaslicer.com/wiki/print_settings/others/others_settings_brim.html\n- https://www.orcaslicer.com/wiki/material_settings/filament/material_volumetric_speed_limitation.html\n- https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html\n- https://www.orcaslicer.com/wiki/calibration/volumetric_speed_calib.html\n- https://www.orcaslicer.com/wiki/print_prepare/prepare_variable_layer_height.html\n- https://www.orcaslicer.com/wiki/print_prepare/prepare_auto_orient.html\n- https://wiki.bambulab.com/en/knowledge-sharing/volumetric-speed\n- https://wiki.bambulab.com/en/software/bambu-studio/layer-height\n- https://wiki.bambulab.com/en/software/bambu-studio/adaptive-layer-height\n- https://wiki.bambulab.com/en/software/bambu-studio/fill-patterns\n- https://wiki.bambulab.com/en/software/bambu-studio/parameter/strength-advance-settings\n- https://wiki.bambulab.com/en/software/bambu-studio/how-to-set-slicing-parameters\n- https://wiki.bambulab.com/en/software/bambu-studio/view-slicing-information\n- https://help.prusa3d.com/article/max-volumetric-speed_127176\n- https://help.prusa3d.com/article/speed-settings_480325\n- https://help.prusa3d.com/article/infill_42\n- https://help.prusa3d.com/article/infill-patterns_177130\n- https://help.prusa3d.com/article/layers-and-perimeters_1748\n",
    },
    "goal-stronger-parts": {
        "description": "Goal skill for stronger, tougher and watertight parts - wall loops versus infill, infill pattern and density, line width, layer height, nozzle temperature and cooling for layer bonding, overlaps, top/bottom shells, orientation on the plate, material choice, parts that take screws or loads. Read when the user asks \"make it stronger\", \"it breaks\", \"it snapped\", \"more solid\", \"more rigid\", \"functional part\", \"watertight\", \"airtight\", \"it leaks\", \"holds a screw\".",
        "content": "# Stronger, tougher and watertight parts\n\nA printed part is strong along its lines and weak between layers. Order: orientation and material (the user decides), then walls, then layer bonding (temperature, cooling, flow), then infill. A part that split while printing is a defect: defect-layer-adhesion.\n\n## What to ask first\n- How does it fail or what must it resist: snapping along layer lines, bending, crushing, impact, a screw pulling out, leaking?\n- Direction of the load compared with the layers (ask for a photo of the part as it lies on the plate).\n- Material, printer, nozzle, enclosure; does the part work in heat or outdoors?\n- Current `wall_loops`, `sparse_infill_density`, `layer_height`, temperature and fan (read the presets).\n- Watertight: just holding water, or pressure? Never promise food safety.\n- Did it break at a thin section that is already solid? Then only design, orientation or material help.\n\n## Levers, biggest gain first\n| Key (preset) | Change | Typical step | Safe limit | What it costs |\n|---|---|---|---|---|\n| `wall_loops` (process) | increase | +1-2: 2 → 3-4; loaded parts 4-5 | none; once the walls fill the section more loops change nothing | time, material; more shrink stress on large ABS/ASA/PC parts |\n| `nozzle_temperature` (filament) | increase | +5 °C per round, up to +10 | inside the filament's temperature range | stringing, drooping overhangs, soft small details |\n| `fan_max_speed`, `fan_min_speed` (filament) | decrease (PETG, ABS/ASA, PA, PC) | -10 to -20 points | PLA: keep cooling; check overhangs in the preview | drooping overhangs and bridges |\n| `outer_wall_speed`, `inner_wall_speed` (process) | decrease | -20-30% | - | longer print |\n| `filament_max_volumetric_speed` (filament) | decrease | -10-20% | lowering is free; raising max +10% | caps every speed, longer print |\n| `layer_height` (process) | bring to the middle of the range | 0.15-0.2 mm on a 0.4 mm nozzle | ≤ 60-65% of nozzle for strength (plugin limit 75%, min 0.04) | time; very thin layers only add interfaces that can fail |\n| `inner_wall_line_width`, `outer_wall_line_width` (process) | increase | inner to 120%, outer to 105-120% of nozzle | ≤ 150% of nozzle | more flow per mm (speed cap), less fine detail |\n| `sparse_infill_density` (process) | increase | +5-10 points, to 25-40% | above 30% rarely pays | time, material, warping stress on ABS/PC |\n| `sparse_infill_pattern` (process) | change | `cubic` (strong and quick), `gyroid` or `tpmsd` (equal in all directions, slow), `honeycomb`, `tri-hexagon`, `grid` | not `lightning`, `supportcubic`, `line`, `concentric` on loaded parts | curved patterns print slower; `grid`, `triangles` pile material at the crossings |\n| `fill_multiline` (process) | increase | `2` or `3` | ≤ 3 with crossing patterns | same material in thicker infill walls with larger cells: keep enough top layers |\n| `top_shell_layers`, `bottom_shell_layers` (process) | increase | +1-2 | aim for 0.8-1.0 mm; `top_shell_thickness`, `bottom_shell_thickness` (process) enforce a minimum | time, material |\n| `infill_wall_overlap` (process) | increase | 15% → 20-25% | ≤ 30% | infill pushes the outer wall out, shows through |\n| `alternate_extra_wall` (process) | `1` | - | not with `lightning`; set `ensure_vertical_shell_thickness` (process) to `ensure_moderate` | time; uneven wall count |\n| `gap_fill_target` (process) | `everywhere` | - | - | time; possible over-fill in solid areas |\n| `minimum_sparse_infill_area` (process) | increase | 15 → 50-100 mm² | - | small regions become solid: more material |\n| `extra_solid_infills` (process) — BY HAND | set | `10#2` = 2 solid layers every 10; or a list of layer numbers | by hand only (free-text field the plugin cannot check): Process → Strength → Infill | long layers can leave a faint band on the walls |\n| `filament_flow_ratio` (filament) | increase (watertight parts, confirmed under-fill) | +0.02, at most +0.05 | 0.8-1.2; better: Calibration → Flow ratio | rough surface, tighter fits, stringing |\n\nNotes for the AI:\n- **Walls before infill.** Strength comes mainly from the wall count; infill adds crush resistance and stiffness and supports the top. Add walls first, infill second.\n- **Bonding depends on heat.** Plastic laid colder or faster than the hotend can melt it fuses badly: a hotter nozzle, less fan and lower flow help all together. Orca advises keeping inner walls well below the volumetric cap and a 10-20% margin after a Max flowrate test.\n- **Wall order.** Keep `wall_sequence` (process) on `inner wall/outer wall` (default): overhanging walls print against a wall already laid. Leave `is_infill_first` (process) at `0`. `precise_outer_wall` (process) only removes the overlap next to the outer wall; Orca states it does not reduce strength.\n- **Thin features.** `wall_generator` (process) `arachne` fills thin walls with variable-width lines; with `classic`, `detect_thin_wall` (process) prints single open lines that are weak, and the gap fill between walls adds strength: do not filter it out.\n- `ensure_vertical_shell_thickness` (process): keep `ensure_all` on sloped or domed parts, otherwise the shell gets thin on slopes.\n- Large ABS/ASA/PC parts: more walls and dense infill raise shrink stress and cracking; there work on enclosure, fan and temperature first (defect-layer-adhesion, defect-warping).\n- Recipes for a 0.4 mm nozzle:\n  - Functional bracket, clip, hook: `wall_loops` 4, `cubic` or `gyroid` at 25%, `layer_height` 0.2, 5 top and 4 bottom layers, `nozzle_temperature` +5 °C.\n  - Part that takes screws: `wall_loops` 4-5 (the walls around a hole follow the same count), `minimum_sparse_infill_area` 50, solid layers at the height of the load with `extra_solid_infills`, or a modifier around the hole (by hand, below).\n  - Gears and parts under torque: `fill_multiline` `2`-`3` transfers torque better.\n  - Watertight: `wall_loops` 3-4, `layer_height` 0.15-0.2, `outer_wall_line_width` and `inner_wall_line_width` +5-10%, `nozzle_temperature` +5-10 °C, `filament_flow_ratio` +0.02 to +0.05, `bottom_surface_pattern` (process) `concentric`; for leaks where floor and wall meet, `top_bottom_infill_wall_overlap` (process) 25% → 30-35%. Even wall thickness matters: thick walls with sparse infill leak into the cavity. Single-wall vases: a wider line (0.6 mm on a 0.4 mm nozzle), see goal-surface-quality.\n\n## Limits you cannot tune past (explain to the user)\n- **Layers are the weak direction.** No setting makes the bond between layers as strong as the lines themselves. A part pulled or bent across its layers needs a different orientation.\n- **Solid sections.** Where the walls already fill the whole section, more walls or infill change nothing: the feature must be thicker (design) or the material different.\n- **Material.** Heat resistance, brittleness and toughness belong to the plastic: see materials-overview and material-pla, material-petg, material-abs-asa, material-pa-pc, material-composites, material-tpu. High-shrink materials (ABS, ASA, PC, PA-CF, PET-CF) crack between layers without an enclosure.\n- **Flow above the hotend's limit** gives under-filled, colder lines and weak layers.\n- **Wet filament** prints with voids: weak and leaky whatever the settings.\n- **Nozzle size.** A 0.2 mm nozzle lays thin lines that bond less: parts are weaker than with 0.4 or 0.6 mm.\n- **Watertight is never guaranteed** and is not food-safe: pores remain between layers. Not for hazardous liquids.\n- **100% infill** is rarely the answer: more shrink stress, worse surfaces, much more time.\n\n## Checks and choices the user makes by hand\n- **Orientation** (most effective, free): rotate the part (Rotate or Lay on face in the Prepare toolbar) so that the main load runs along the layers, not across them. Hooks, clips, tabs and pins: lay them so the layer lines follow their length. Auto orient optimizes for supports, not for strength: check its result. Then `align_infill_direction_to_model` (process) `1` keeps infill directions fixed to the part.\n- **Local reinforcement**: right-click the object → Add modifier, place the shape over the hole, boss or thin arm, and set more wall loops or a higher infill density on that modifier in the object list. Per-object values are set by switching the Process panel from Global to Objects.\n- **Dry the filament** before a functional or watertight print (PETG, TPU, PA, PC above all): materials-overview.\n- **Enclosure and drafts** for ABS/ASA/PC/PA: doors and lid closed, no fan or window nearby. Chamber heating is set on the printer by the user; the plugin never changes it.\n- **Calibrations** (calibration-guide): Temperature (pick the block with the best bonding), Max flowrate, Flow ratio.\n- **Larger nozzle** (hardware plus the matching printer preset): thicker, wider lines and stronger parts, less detail.\n- **Hole sizes for screws and inserts**: defect-dimensional-accuracy.\n- **Leak test**: fill with water and leave it on a paper towel; a leak where floor and wall meet calls for more overlap (recipe above).\n\n## Related skills\n- defect-layer-adhesion (splitting, cracks), defect-extrusion (gaps, weak infill), defect-warping, defect-dimensional-accuracy.\n- materials-overview and the material-* skills; calibration-guide.\n- goal-faster-prints, goal-surface-quality (opposite trades: thin layers and slow outer walls do not add strength).\n\n## Sources\n- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_walls.html\n- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_infill.html\n- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_advanced.html\n- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_top_bottom_shells.html\n- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_patterns.html\n- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_patterns_quick_reference.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_line_width.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_layer_height.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_and_surfaces.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_precision.html\n- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_other_layers_speed.html\n- https://www.orcaslicer.com/wiki/calibration/volumetric_speed_calib.html\n- https://www.orcaslicer.com/wiki/print_prepare/prepare_auto_orient.html\n- https://wiki.bambulab.com/en/filament/reduce-vase-leaking-guide\n- https://wiki.bambulab.com/en/software/bambu-studio/fill-patterns\n- https://wiki.bambulab.com/en/software/bambu-studio/parameter/strength-advance-settings\n- https://wiki.bambulab.com/en/knowledge-sharing/volumetric-speed\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/interlayer-cracking\n- https://wiki.bambulab.com/en/filament-acc/filament/support-for-abs\n- https://wiki.bambulab.com/en/knowledge-sharing/02-mm-nozzle-FAQ\n- https://wiki.bambulab.com/en/software/bambu-studio/how-to-set-slicing-parameters\n- https://help.prusa3d.com/article/watertight-prints_112324\n- https://help.prusa3d.com/article/layers-and-perimeters_1748\n- https://help.prusa3d.com/article/infill_42\n- https://help.prusa3d.com/article/infill-patterns_177130\n- https://help.prusa3d.com/article/layer-separation-and-splitting-fdm_1806\n",
    },
    "goal-surface-quality": {
        "description": "Goal skill for the best-looking surfaces and finest detail - finer layer height, variable layer height, outer wall speed and acceleration, wall order, wall generator (Arachne vs classic), line widths and small details, even gloss, top surfaces and ironing, seam, spiral vase mode and its limits, fuzzy skin. Read when the user asks \"smoother\", \"better quality\", \"finer detail\", \"hide layer lines\", \"nicer surface\", \"shiny or matte bands\", \"small text\", \"vase mode\", \"fuzzy skin\", \"miniatures\".",
        "content": "# Best surface quality and fine detail\n\nThe user wants a better look and pays with time. Ask which surface matters; a real defect goes to its own skill (ringing, seam, zits, pillowing, supports, overhangs).\n\n## What to ask first\n- Which surface: vertical walls, curved or sloped tops (stair-steps), flat top, underside or supported areas, small text and details?\n- What bothers them: layer lines, the seam, shiny/dull bands, roughness, missing or rounded details?\n- Material (silk, glossy and translucent filaments show every speed change), printer, nozzle diameter.\n- How much extra time is acceptable: halving the layer height roughly doubles the time.\n- Vase mode: is the model one closed outline per layer (vase, pot, lampshade), or does it have handles, islands, inner structures?\n- Was the filament dried and calibrated (flow, pressure advance)?\n\n## Levers, biggest gain first\n| Key (preset) | Change | Typical step | Safe limit | What it costs |\n|---|---|---|---|---|\n| `layer_height` (process) | decrease | 0.2 → 0.16 → 0.12 on a 0.4 mm nozzle | ≥ 20% of nozzle (0.08 on 0.4 mm), plugin min 0.04; little visible gain below 0.10 | time grows almost in proportion; no gain in XY detail; very thin layers printed fast look scaly |\n| `outer_wall_speed` (process) | decrease, keep it uniform | -20-30%; silk or glossy filaments 40-60 mm/s | - | time |\n| `dont_slow_down_outer_wall` (filament) | `1` | - | not on tiny or pointed parts that overheat | even gloss, but short layers cool less and inner features slow down more |\n| `outer_wall_acceleration` (process) | decrease | -25-40% | ≤ printer limit; ignored when `default_acceleration` is 0 | time; details in defect-ringing-ghosting |\n| `wall_sequence` (process) | `inner-outer-inner wall` | needs `wall_loops` ≥ 3 | models without steep overhangs | best outer surface and accuracy; worse overhangs |\n| `precise_outer_wall` (process) | `1` when the order stays `inner wall/outer wall` | - | ignored with the other orders | none known; more even layers |\n| `infill_wall_overlap` (process) | decrease (infill pattern visible outside) | 15% → 10% | ≥ 0% | weaker infill-to-wall bond |\n| `top_surface_pattern` (process) | `monotonicline` or `monotonic`; round or silk tops: `concentric`, `archimedeanchords` | - | - | spiral patterns are slower |\n| `top_surface_speed` (process) | decrease | -20-30% | - | time |\n| `only_one_wall_top` (process) | `1` | - | - | cleaner flat tops and small lettering |\n| `ironing_type` (process) | `top` or `topmost`, flat tops only | defaults first | see defect-top-surface | much more time; heat-creep risk; edges a little less sharp |\n| `seam_position` (process) | `aligned` or `back` | - | see defect-seam-zits-blobs | seam concentrated on one line |\n| `reduce_crossing_wall` (process) | `1` | - | - | fewer travel marks and strings on walls; slightly longer print |\n| `outer_wall_line_width` (process) | 105-120% of nozzle normally; narrower for tiny text | e.g. 0.45 → 0.40 on a 0.4 mm nozzle | 75-150% of nozzle; below 100% bonding suffers | thinner, weaker walls |\n| `min_feature_size` (process) | decrease (Arachne, thin details missing in the preview) | 25% → 15-10% | ≥ 0% | tiny moves, blobs or strings on tiny features |\n| `wall_generator` (process) | `arachne` for thin walls, text, logos; `classic` if Arachne gives uneven walls or odd seams | - | - | `classic` drops features thinner than two lines |\n| `nozzle_temperature` (filament) | increase for more gloss, silk filaments | +5 °C | inside the filament's temperature range | stringing, softer overhangs |\n| `fuzzy_skin` (process) | `external` (contour), `all` (contour and holes), `allwalls` | `fuzzy_skin_thickness` (process) 0.1-0.3, `fuzzy_skin_point_distance` (process) 0.3-0.8 | thickness below the outer wall line width; keep `fuzzy_skin_first_layer` (process) `0` | rough matte texture on walls only; slower; sizes and fits change |\n| `spiral_mode` (process) | `1` for vases | see the vase section | one closed outline per layer | single wall, no infill, no top |\n\nNotes for the AI:\n- **Layer height sets vertical resolution only**: XY detail comes from line width and nozzle. Thinner layers also improve overhangs. With thin layers leave `top_shell_thickness` (process) on: it keeps the top solid.\n- **Gloss follows speed and flow**: slow, hot plastic is glossy, fast plastic matte. Bands appear where the outer wall slows down (overhangs, minimum layer time). Remedies: `outer_wall_speed` close to the slowest wall speed shown in the Preview \"Speed\" view, `dont_slow_down_outer_wall`, a 0.16 mm layer, several parts on the plate (by hand).\n- **Wall order.** `inner-outer-inner wall` prints the outer wall undisturbed. `outer wall/inner wall` gives similar walls but less consistent seams. `inner wall/outer wall` stays best for overhangs. Keep `is_infill_first` (process) `0`.\n- **Arachne.** `wall_distribution_count` (process) 1 keeps width changes in the innermost wall, so outer walls stay even.\n- **Bulge or line where speed changes** (start of an overhang or bridge): `max_volumetric_extrusion_rate_slope` (process), values in defect-ringing-ghosting.\n- **Top surfaces**: `top_surface_line_width` (process) 100-105% of nozzle; ironing only helps flat tops parallel to the bed (defect-top-surface).\n- **Fuzzy skin** hides layer lines, ringing and seams and adds grip; it acts on walls only, never on top and bottom faces. `fuzzy_skin_mode` (process): `displacement` is the classic look but weakens the shell and slows the print; `extrusion` (needs `arachne`) keeps speed and strength with a milder texture; `combined` sits between. `fuzzy_skin` `none` = only areas painted by the user; `disabled_fuzzy` = off. Keep it off mating faces and holes that must fit.\n\n### Spiral vase\n- Propose `spiral_mode` `1` together with `wall_loops` 1, `top_shell_layers` 0, `sparse_infill_density` `0%`, `enable_support` `0` (all process). When the user ticks Spiral vase by hand (Process → Others → Special mode), Orca offers to apply these itself: usually the simpler route.\n- Result: one continuous wall rising in a spiral, no seam above the bottom layers; `bottom_shell_layers` (process) still applies.\n- `spiral_mode_smooth` (process) `1` also smooths XY moves: no seam on slanted walls, but it can leave bumps on vases with sharp edges; best on smooth shapes. `spiral_mode_max_xy_smoothing` (process) default `200%` of nozzle.\n- Stronger or tighter vase: `outer_wall_line_width` up to 0.6 mm on a 0.4 mm nozzle (≤ 150% of nozzle); for leaks see goal-stronger-parts.\n- Limits: the model must be a solid with one closed outline per layer; handles, islands and inner walls come out floating or missing. One object per plate, or `print_sequence` (process) `by object`. Timelapse must be traditional; Bambu A1 / A1 mini make no timelapse in vase mode. A single wall is fragile.\n\n## Limits you cannot tune past (explain to the user)\n- **Layer lines never disappear**, and shallow slopes always show stair-steps: orientation and variable layer height reduce them more than any global setting.\n- **XY detail is bounded by the nozzle**: features thinner than about one line are thinned, widened or skipped. Finer needs a smaller nozzle.\n- **Every layer has a start and an end** except in vase mode: the seam can be hidden, not removed.\n- **Ringing and fine vertical ripples are mechanical**: lower acceleration hides them, printer calibration fixes them (defect-ringing-ghosting).\n- **Supported and steeply overhanging faces stay rougher** than the rest (defect-supports, defect-overhangs-bridges).\n- **Material**: wet filament prints rough with uneven gloss whatever the profile.\n\n## Checks and choices the user makes by hand\n- **Orientation**: put the display face upright rather than as a shallow curved top; a face printed on the plate copies the plate's finish (smooth or textured).\n- **Variable layer height** (Prepare toolbar, object selected): Adaptive with the slider toward Quality, then Smooth (repeat if needed). Thin layers go only on curved tops and shallow slopes. Abrupt layer-height changes show as horizontal lines: always smooth. The range is the min/max layer height of the printer's extruder settings. Restrictions (Bambu documentation): a prime tower needs the same profile on all objects; not with organic tree supports. The plugin cannot apply this tool.\n- **Painted fuzzy skin and seam**: paint tools in the Prepare toolbar (painted fuzzy skin needs `fuzzy_skin` `none`, not `disabled_fuzzy`).\n- **Spiral start/end flow** (`spiral_starting_flow_ratio`, `spiral_finishing_flow_ratio`, process): BY HAND only, Process → Others → Special mode → Spiral vase; the plugin cannot check them.\n- **Smaller nozzle** (hardware plus the matching printer preset): 0.2 mm for miniatures and tiny text; very low flow limit (about 2 mm³/s on Bambu), no filled, glow or sparkle filaments, weaker parts.\n- **More parts on the plate** lengthen each layer: fewer cooling slowdowns on small parts.\n- **Dry the filament; run Flow ratio and Pressure advance calibrations** (calibration-guide) before judging the surface.\n\n## Related skills\n- defect-seam-zits-blobs, defect-top-surface, defect-ringing-ghosting, defect-overhangs-bridges, defect-supports, defect-overheating-small-features, defect-extrusion (uneven gloss).\n- material-pla (silk, matte), calibration-guide, goal-faster-prints, goal-stronger-parts.\n\n## Sources\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_layer_height.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_line_width.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_and_surfaces.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_generator.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_precision.html\n- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_ironing.html\n- https://www.orcaslicer.com/wiki/print_settings/others/others_settings_special_mode.html\n- https://www.orcaslicer.com/wiki/print_settings/others/others_settings_fuzzy_skin.html\n- https://www.orcaslicer.com/wiki/print_prepare/prepare_variable_layer_height.html\n- https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html\n- https://wiki.bambulab.com/en/software/bambu-studio/layer-height\n- https://wiki.bambulab.com/en/software/bambu-studio/adaptive-layer-height\n- https://wiki.bambulab.com/en/software/bambu-studio/spiral-vase\n- https://wiki.bambulab.com/en/software/bambu-studio/parameter/fuzzy-skin\n- https://wiki.bambulab.com/en/software/bambu-studio/parameter/quality-advance-settings\n- https://wiki.bambulab.com/en/software/bambu-studio/wall-generator\n- https://wiki.bambulab.com/en/software/bambu-studio/WallGenerator\n- https://wiki.bambulab.com/en/software/bambu-studio/parameter/line-width\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/different-gloss\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/severe-layer-artifacts\n- https://wiki.bambulab.com/en/x1/manual/printing-with-silk-filaments\n- https://wiki.bambulab.com/en/knowledge-sharing/02-mm-nozzle-FAQ\n- https://help.prusa3d.com/article/layers-and-perimeters_1748\n- https://help.prusa3d.com/article/arachne-perimeter-generator_352769\n- https://help.prusa3d.com/article/fuzzy-skin_246186\n- https://help.prusa3d.com/article/ironing_177488\n",
    },
    "material-abs-asa": {
        "description": "ABS, ASA and ASA Aero (foaming ASA): enclosure and chamber heat, bed and plate keys, low part cooling, warping and layer-crack prevention, shrinkage, drying, styrene fumes and air filtration, ASA Aero lightweight settings. Read when the user prints ABS or ASA and asks for settings or reports ABS/ASA warping, corners lifting, layers splitting or cracking on tall parts, parts detaching, bad smell or fumes, parts shrinking, or printing ABS on an open printer.",
        "content": "# ABS and ASA\n\nABS: tough, heat resistant (Bambu ABS HDT about 87 °C), acetone-smoothable, yellows and embrittles outdoors. ASA: the outdoor version with UV and weather resistance (HDT about 100 °C), slightly less warping and odour. Both shrink while cooling (about 1-2%), warp strongly, have weak Z adhesion (Bambu impact Z: ABS 7.4, ASA 4.9 kJ/m² vs PLA 13.8) and release styrene.\n\n## Baseline (start from the vendor preset)\n| Item | Typical value | Notes |\n|---|---|---|\n| `nozzle_temperature` (filament) | ABS 240-260 °C (Prusa 255), ASA 245-265 °C (Prusa 260) | Bambu range 240-280 °C for both. |\n| Bed, PEI or Engineering plate | 90-110 °C (Bambu 90-100; Prusa ABS 100, ASA 105 first layer / 110) | Bigger part = hotter bed. Glue stick on every plate. |\n| Cool Plate / Cool Plate SuperTack | do not use | SuperTack coating is for PLA/PETG only. |\n| Part cooling | low; 10-20% only where steep overhangs or small parts curl; off for the first layers | Too much fan = warping and layer cracks. |\n| Enclosure | required for anything but small parts | Bambu: not for P1P or A-series (open frames). |\n\nBed keys per plate (filament preset, each with an \"_initial_layer\" twin): `eng_plate_temp` (Engineering Plate), `hot_plate_temp` (Smooth PEI / High Temp Plate), `textured_plate_temp` (Textured PEI). Change only the one matching the plate selected in Orca.\n\n## Slicer fixes (warping, cracks, detachment)\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `brim_type` / `brim_width` (process) | `outer_only`; `brim_ears` (mouse-ears value of `brim_type`) on sharp corners | +3 mm | 0-100 mm | removal marks |\n| `eng_plate_temp` / `hot_plate_temp` / `textured_plate_temp` (+ \"_initial_layer\") (filament) | increase for lifting corners | +5 °C | max +10 °C per change, ≤ 120 °C | elephant foot |\n| `fan_max_speed` / `fan_min_speed` (filament) | decrease for cracks between layers and warping | -10% | ≥ 0; keep 10-20% if small overhangs curl | worse overhangs/bridges |\n| `close_fan_the_first_x_layers` (filament) | increase for first-layer lift | to 3 | 0-5 | none |\n| `draft_shield` (process) | `enabled` on open-frame printers, with `skirt_loops` ≥ 1 (the shield is automatically as tall as the tallest object; `skirt_height` only counts when it is `disabled`) | on | n/a | more material/time |\n| `sparse_infill_density` (process) | decrease on large flat parts | ≤ 25%, with `sparse_infill_pattern` (process) = `gyroid` (shrinks evenly) | ≤ 50% | less strength |\n| `wall_loops` (process) | do not exceed 6; 2 walls + 15% infill is enough for non-structural parts | -1 | ≥ 2 | less strength |\n| `nozzle_temperature` (filament) | increase for layer splitting / cracks | +5 °C | inside nozzle_temperature_range_low..high | more odour, stringing |\n| `outer_wall_speed`, `inner_wall_speed`, `sparse_infill_speed` (process) | decrease for warping and cracks on big parts | -20% | ≤ printer limits | longer print |\n| `print_sequence` (process) — BY HAND | `by object` for many small parts | n/a | by hand only: Process → Others → Special mode → Print sequence; gantry clearance limits | long layer times otherwise weaken small parts |\n\n- Shrinkage: parts come out about 1-2% small. The plugin may not change filament shrinkage data: route to defect-dimensional-accuracy and explain to the user that shrinkage compensation is set by hand in the filament preset.\n- Orientation: loads must not pull layers apart. A part tilted about 45° balances warping and strength (Bambu); large flat contact areas warp most.\n- Air filtration (BY HAND, the plugin cannot check it; Filament → Cooling → Exhaust fan; printers with an exhaust fan): `activate_air_filtration` = `1`, `complete_print_exhaust_fan_speed` high to clear fumes after the print; keep `during_print_exhaust_fan_speed` low on warping-prone parts because exhausting during the print removes chamber heat. Higher chamber temperature also lowers filter efficiency (Orca wiki).\n\n## ASA Aero (foaming, Bambu)\nLightweight RC/outdoor parts. Density falls as temperature rises (220 °C ≈ no foam, 260 °C ≈ 86% foam). High temperature, low speed.\n- Flow ratio 0.42-0.7 is needed; the plugin cannot set `filament_flow_ratio` below 0.8, so explain the value and let the user set it by hand (Filament → Filament → Flow ratio).\n- Bambu reference values (process): `line_width` 0.48 mm, `slice_closing_radius` 0.02 mm, `bridge_flow` 0.7 (BY HAND, the plugin cannot check it: Process → Quality → Bridging → Flow ratio), `reduce_crossing_wall` `1` with `max_travel_detour_distance` `90%`, `wall_loops` 1, `top_shell_layers` 0, `bottom_shell_layers` 2, `sparse_infill_density` `0%`, all feature speeds 80 mm/s, `default_acceleration` 5000, `outer_wall_acceleration` 3000 (never above printer limits), `brim_type` `outer_only` 3 mm with `brim_object_gap` 0.2 mm, `enable_prime_tower` 0, `slicing_mode` `even_odd`.\n- Supports only if needed: `support_threshold_angle` 50, `support_top_z_distance` 0.26 mm, `support_interface_top_layers` 3, `support_interface_spacing` 0.2 mm, `support_object_xy_distance` 0.6 mm.\n- Avoid travel-heavy models; print one part or `by object`. Fan neither very low nor very high.\n- 0.4 mm nozzle only; Smooth PEI with glue or Engineering plate, not Textured PEI (bottom tears on removal).\n\n## Checks the user must do by hand\n- Enclosure and chamber heat: close door and top lid. Chamber heating and chamber temperature settings are not changed by the assistant. Bambu H2/X1E/X2D heat the chamber actively; on X1C/P1S without chamber heating, preheat the bed at maximum for about 15 min before printing in a cold room. No enclosure: small parts only, draft shield on, no drafts.\n- Ventilation: styrene can cause dizziness or nausea; print in a ventilated room, not a bedroom, but keep drafts away from the printer. Replace Bambu activated-carbon filters about every 1,440 printing hours; clean the carbon rod and glass after about 5 kg of ABS/ASA.\n- Prusa enclosure: long ABS/ASA sessions can deform the printer's own PETG/PLA parts (fan shroud): consider reprinting them in a heat-resistant material.\n- Plate: clean, then glue stick (Bambu glue on all plates; Prusa smooth PEI or textured/satin with glue). Never ABS juice or acetone on Prusa powder-coated sheets; Prusa smooth PEI tolerates occasional acetone. Bambu Engineering plate: glue always.\n- Bambu: do not feed ABS/ASA from the AMS lite; the AMS is fine.\n- Dry: 80 °C for 4-8 h (Prusa ASA 80 °C / 4 h; Bambu 75-85 °C / 8 h). AMS 2 Pro (max 65 °C) cannot dry it fully; AMS HT 80 °C / 8 h. Remove PLA/TPU spools from the dryer first.\n- Ring-shaped bulges where a thick base meets thin walls: add an inner fillet in CAD.\n\n## Material notes\n- Post-processing: wet/dry sanding, acetone vapour smoothing and acetone welding (both ABS and ASA); smoothing rounds edges.\n- ABS for low-cost technical parts and acetone finish; ASA for anything outdoors.\n- ABS-GF, ASA-CF: see material-composites. PC and PC blends: see material-pa-pc. Supports for ABS: see material-special.\n\n## Calibration in Orca\nCalibration → Temperature, Flow ratio, Pressure advance, Max flowrate; print tests inside the closed enclosure so results match real prints (calibration-guide).\n\n## Sources\n- https://wiki.bambulab.com/en/filament/abs_asa_pc\n- https://wiki.bambulab.com/en/filament-acc/filament/asa-aero-printing-guide\n- https://wiki.bambulab.com/en/general/filament-guide-material-table\n- https://wiki.bambulab.com/en/filament-acc/filament/slice-param\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/warping-falling-off-collapsing\n- https://wiki.bambulab.com/en/filament-acc/filament/dry-filament\n- https://wiki.bambulab.com/en/filament-acc/acc/plates\n- https://help.prusa3d.com/article/abs_2058\n- https://help.prusa3d.com/article/asa_1809\n- https://help.prusa3d.com/article/warping_2011\n- https://help.prusa3d.com/article/smooth-steel-sheet_196550\n- https://help.prusa3d.com/article/textured-steel-sheet_196534\n- https://help.prusa3d.com/article/drying-filament_332086\n- https://www.orcaslicer.com/wiki/material_settings/filament/material_temperatures.html\n- https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html\n- https://www.orcaslicer.com/wiki/print_settings/others/others_settings_skirt.html\n- https://wiki.bambulab.com/en/filament-acc/acc/fans\n",
    },
    "material-composites": {
        "description": "Fibre- and particle-filled filaments (PLA-CF, PETG-CF, PA-CF/GF, PAHT-CF, PA6-CF/GF, PET-CF, ASA-CF, ABS-GF, PC-CF, PP-CF, PPA-CF, PPS-CF, wood, metal, magnetite, tungsten, glow): hardened nozzles and nozzle wear, clog prevention, speed and flow caps, drying, plates and the Orca keys to adjust. Read when the user prints carbon fibre, glass fibre, wood, metal-filled or glow filament and reports clogs, under-extrusion that gets worse over time, a worn nozzle, brittle or breaking filament, rough or matte-uneven surfaces, weak layers or AMS feeding problems.",
        "content": "# Composite filaments (CF, GF, wood, metal, other particles)\n\n## What changes versus the base polymer\n- Fibres (carbon, glass, aramid) make parts stiffer, more heat resistant and dimensionally stable, and cut warping a lot (PA-CF, PP-CF, ASA-CF, ABS-GF warp far less than the unfilled grade).\n- The price: lower impact strength and weaker layer-to-layer bond, brittle filament, higher clog risk, abrasive wear on nozzle, extruder gears and PTFE tubes.\n- Printing temperature is usually the base polymer's, sometimes slightly higher. Plate, enclosure and drying rules of the base polymer still apply (material-pla, material-petg, material-abs-asa, material-pa-pc, material-special).\n- Wood fills: mostly cosmetic, weaker, clog-prone (large particles), very hygroscopic. Metal-powder fills (copper, steel, magnetite, tungsten): heavy, abrasive, weaker layers; can be sanded and polished. \"Metallic-look\" PLA with pigment only is not abrasive.\n- Cheap composites more often clog, ooze and snap: brand quality matters.\n\n## Nozzle rules (hardware: explain, never \"fix\" with settings)\n- **Hardened steel (or tungsten carbide, ObXidian-type, diamond-tipped) nozzle required** for CF/GF, metal powder, glow-in-the-dark and other hard particles. Brass and stainless wear quickly: the bore widens, flow and precision drift and extrusion becomes inconsistent.\n- **Diameter**: never 0.2 mm (very high clog risk); prefer **0.6 mm** for CF/GF and wood with large particles; 0.4 mm hardened works for most (layer 0.15-0.3 mm, ~100 mm/s max), and is the first choice for Bambu PLA-CF, PETG-CF and particle PLAs. 0.4 mm high-flow nozzles are not recommended for PLA-CF, PETG-CF, PA-CF and PET-CF.\n- Orca checks hardness: the nozzle type and nozzle HRC in the printer settings (see the hand checks below) must match the installed nozzle (brass 2, stainless 20, hardened steel 55, tungsten carbide 85). If Orca warns about nozzle hardness, the fix is the real nozzle, not the filament profile.\n- Worn nozzle suspected (flow and precision drifting after abrasive spools): inspect or replace the nozzle; do not compensate with flow settings.\n\n## Feeding and AMS (Bambu)\n- Brittle or rough filaments can snap or wear tubes: PET-CF, PPA-CF and PPS-CF are not AMS-compatible (external spool, short smooth path, no tight bends); PA-CF/PAHT-CF only for Bambu grades; PETG-CF fine in AMS but not AMS lite; most CF/GF not for AMS lite. Rough filaments slowly grind AMS PTFE tubes.\n- H2D: print PET-CF/PPA-CF/PPS-CF from the left hotend to avoid a sharp tube bend on the right.\n\n## Start values (spool label wins)\n| Material | Nozzle °C | Bed °C | Glue | Max volumetric speed | Notes |\n|---|---|---|---|---|---|\n| PLA-CF | 210-240 | 45-65 | optional | as PLA, lower if clogs | dry 50-60 °C, 8 h recommended |\n| PETG-CF | 240-270 | 60-80 | release layer on smooth PEI | as PETG | Bambu default flow ratio 0.95 |\n| ASA-CF | 240-280 | 90-100 | glue stick | 18 mm³/s | enclosure; speed < 250 mm/s |\n| ABS-GF | 240-280 | 90-100 | liquid glue | 12 mm³/s | enclosure; speed < 180 mm/s |\n| PA6-GF | 260-300 | 100-110 | glue stick | 10.5 mm³/s | enclosure; speed < 130 mm/s |\n| PA-CF / PAHT-CF / PA6-CF | 260-300 | 100-110 | glue stick | 8 mm³/s | enclosure; speed < 100 mm/s |\n| PET-CF | 260-300 | 80-110 | glue stick | 8 mm³/s | not AMS; speed < 100 mm/s |\n| PPA-CF | 285-320 | 100-120 | glue stick | 8 mm³/s | enclosure; oven-dry hot |\n| PPS-CF | 310-340 | 100-120 | glue stick | 6 mm³/s | Bambu X1E/H2 only |\n| Wood (PLA) | 190-240 | as PLA | - | as PLA | ≥ 0.6 mm nozzle for coarse fills; must be dried |\n| PETG Magnetite 40% | 270 ±5 | 100 ±10 | textured/satin sheet | - | hardened; do not clean the sheet with IPA |\n| PETG Tungsten 75% | 260 ±10 | 80 ±10 | glue on smooth PEI | - | hardened; no part cooling |\n\nDrying (oven): PA6/PAHT/PET-CF 80 °C 8-12 h; ABS-GF/ASA-CF 80 °C 8 h; PETG-CF 60-65 °C 8 h; PPA-CF 100-140 °C 8-12 h (an AMS HT may not dry PPA-CF/PPS-CF fully). PA6-CF loses about a third of its strength when humid; PPS-CF barely changes. Wet composites string, ooze and leave a rough, uneven texture.\n\n## Slicer fixes\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `filament_max_volumetric_speed` (filament) | decrease to the cap in the table when clogs, skipping or under-extrusion appear at speed | to cap, then -10% | lower freely; raise at most +10% | longer print |\n| `outer_wall_speed` (process) | decrease and keep it constant over the part for even gloss | to ≤ 100 mm/s on high-temp composites | machine limits | longer print |\n| `layer_height` (process) | increase if a 0.4 mm nozzle clogs at fine layers | to 0.2 mm (0.4 nozzle) / 0.3 mm (0.6 nozzle) | ≤ 75% of nozzle diameter | coarser surface |\n| `filament_flow_ratio` (filament) | lower slightly if dried filament still clogs or over-extrudes (PETG-CF: 0.93-0.94) | -0.01 to -0.02 | 0.8-1.2 | under-extrusion if overdone; run Flow Rate calibration |\n| `nozzle_temperature` (filament) | increase for weak layers or poor melt at speed | +5 °C | inside the filament's recommended range | more oozing |\n| `support_type` = `normal(auto)` with `support_style` = `grid`, or `support_type` = `tree(auto)` with `support_style` = `tree_hybrid` (process) | use for heavy or tall composite parts; tree supports alone can be unstable | - | - | harder removal |\n| `enable_support` (process) under long bridges | add on PA/PET/PPS composites | - | - | support marks |\n| `sparse_infill_pattern` = `gyroid`, `sparse_infill_density`, `wall_loops` (process) | for strength | +1 wall / +10% | ≤ 6 walls, ≤ 50% infill | more warping risk, more time |\n| plate key of the plate in use (`textured_plate_temp`, `hot_plate_temp`, `eng_plate_temp`, `cool_plate_temp` and _initial_layer variants) (filament) | increase if PA/PET composites lift | +5 °C | +10 °C over current, ≤ 120 °C | harder removal |\n| `fan_min_speed`, `fan_max_speed` (filament) | set to 0 only for PETG Tungsten; otherwise keep the base polymer's cooling | - | 0-100% | overhang quality |\n\n## Checks the user must do by hand\n- Install the right nozzle (hardened, 0.4 or 0.6 mm) and set it in printer settings (`nozzle_type`, `nozzle_hrc`: printer settings, by hand).\n- Dry the filament and print from a dry box; check the desiccant.\n- First layer must be correct (Z offset, clean plate): a squashed first layer is a common clog trigger with fibres.\n- Clean the nozzle before long composite jobs (cold pull, not on coated ObXidian-type nozzles); avoid many short start/stop jobs that build residue.\n- After high-temp composites, purge at the old temperature before loading PLA/PETG/TPU.\n- Wear gloves and eye protection when handling, removing supports or sanding fibre parts (fine sharp fibres).\n- Clean the extruder gears more often; abrasive dust accumulates.\n\n## Calibration in Orca\nCalibration → Flow ratio and Pressure Advance per spool; Calibration → Max flowrate after drying (keep the result at or below the vendor cap). Temperature tower if layers are weak. See calibration-guide.\n\n## Related skills\ndefect-clogs-heat-creep (clogs), defect-extrusion (inconsistent extrusion), defect-layer-adhesion (weak layers), defect-multimaterial (AMS and purge).\n\n## Sources\n- https://wiki.bambulab.com/en/general/filament-guide-material-table\n- https://wiki.bambulab.com/en/filament/absgf_pa6gf\n- https://wiki.bambulab.com/en/filament/asacf_pahtcf\n- https://wiki.bambulab.com/en/filament/petcf_ppacf\n- https://wiki.bambulab.com/en/filament/petg\n- https://wiki.bambulab.com/en/filament/pla\n- https://wiki.bambulab.com/en/filament-acc/acc/nozzles\n- https://wiki.bambulab.com/en/filament-acc/filament/dry-filament\n- https://wiki.bambulab.com/en/knowledge-sharing/how_to_avoid_nozzle_clogs\n- https://help.prusa3d.com/article/composite-materials-filled-with-carbon-kevlar-or-glass_167387\n- https://help.prusa3d.com/article/composite-materials-with-metal-or-wood-particles_166863\n- https://help.prusa3d.com/article/petg-magnetite-40_1078164\n- https://help.prusa3d.com/article/petg-tungsten_1080996\n- https://help.prusa3d.com/article/prusa-nozzle-types-for-nextruder-printers_928993\n- https://help.prusa3d.com/article/different-nozzle-types_2193\n- https://www.orcaslicer.com/wiki/printer_settings/basic%20information/printer_basic_information_accessory.html\n",
    },
    "material-pa-pc": {
        "description": "Printing nylon (PA6, PA11, PA12/PAHT) and polycarbonate (PC, PC Blend, PC FR) in Orca: temperatures, plates and glue, drying, enclosure, warping and layer cracking, and which filament/process keys to adjust. Read when the user prints nylon, PA or PC/polycarbonate and reports warping, corners lifting, cracks between layers, bubbles, popping or foamy surface, weak or brittle parts, poor bed adhesion or a damaged plate.",
        "content": "# PA (nylon) and PC (polycarbonate)\n\nScope: unfilled PA and PC and their blends. Fibre-filled grades (PA-CF, PA6-GF, PAHT-CF, PC-CF): read material-composites as well (hardened nozzle, clog risk, speed caps); warping and drying advice here still applies.\n\n## Material profile (start values; the spool label wins)\n| | PA (nylon) | PC and PC blends |\n|---|---|---|\n| Nozzle | 240-285 °C (pure PA often ~285 °C) | 260-290 °C (PC Blend ~275 °C) |\n| Bed | 100-110 °C, with glue | 100-115 °C (first layer ~110, then ~115), with glue |\n| Enclosure | required for pure PA; CF-filled PA warps far less | required for anything larger than small parts |\n| Drying (oven/dryer) | 80-85 °C, 8-12 h (stay below 90 °C) | 75-85 °C, 5-8 h |\n| Moisture | extreme: can absorb up to ~10% of its weight | pure PC extreme; PC Blend absorbs much less |\n| Plate | Prusa Special PA Nylon sheet (no glue), or textured/satin/engineering/smooth PEI with glue stick | textured or satin PEI with glue stick; Bambu engineering/smooth/textured with glue stick |\n| Fumes | strong odour, ultrafine particles: ventilate | moderate odour |\n\n- PA6-based parts lose a large share of stiffness and strength when they take up water; PA12-based grades (PAHT) absorb roughly half as much as standard PA.\n- Bambu: PA and PC need an enclosed printer (not P1P or A-series), are not for AMS lite, and want glue stick (liquid glue is not recommended for PA/PC). PC is not recommended with a 0.2 mm nozzle.\n- Pure PA is a good cleaning filament for cold pulls.\n\n## How to recognize material-specific problems\n- **Wet filament**: popping/hissing, steam at the nozzle, bubbles and voids in walls, foamy or rough surface, uneven layers, strings, weak parts. Most common root cause with PA and PC: check before touching any setting.\n- **Warping / lifting / part detaching**: shrinkage on cooling; worst on large flat parts, sharp corners, dense infill, cold room or open door.\n- **Cracks between layers** (tall walls splitting): internal cooling stress larger than layer bond. Causes: too much fan, cold chamber, filament not fully melted (too cold or too fast), clogged nozzle.\n- **Plate damage / part ripped PEI**: PC bonds too strongly to bare smooth PEI; PA sheet damaged by IPA or acetone.\n- **Sagging bridges**: hot material cools slowly; add supports under long bridges.\n\n## Diagnostic order\n1. Filament dry? (when in doubt, dry it: see table above; materials-overview for methods).\n2. Door and lid closed, no drafts; room not cold (Prusa: below ~18 °C the bed may fail to hold PC temperatures).\n3. Right plate, clean (dish soap and water), glue applied where required.\n4. Only then change slicer values, one or two per round.\n\n## Slicer fixes\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| plate keys for the plate in use: `textured_plate_temp`, `hot_plate_temp`, `eng_plate_temp` and their _initial_layer variants, e.g. `textured_plate_temp_initial_layer` (filament) | increase against warping/lifting | +5 °C | at most +10 °C over current, never above 120 °C | elephant foot, part harder to remove |\n| `fan_max_speed` (filament) | decrease against layer cracks/warping | -10 points | ≥ 0; keep some fan for bridges | droopier overhangs and bridges |\n| `fan_min_speed` (filament) | decrease | -5 to -10 points | ≤ `fan_max_speed` | as above |\n| `close_fan_the_first_x_layers` (filament) | increase | +1 to +2 layers | 1-5 layers | first overhangs above the base less cooled |\n| `nozzle_temperature` (filament) | increase for weak layers/cracks/under-melting; decrease for oozing | ±5 °C | inside the filament's recommended range (plugin-checked) | hotter = more stringing and oozing |\n| `brim_type` (process) = `outer_only` with `brim_width` (process) | enable for small footprints, corners, any PC/PA part that lifts | 5-10 mm | 10 mm usually enough | brim removal, slight mark on the edge |\n| `sparse_infill_density` (process) | decrease on large parts | -5 to -10% | keep ≤ 50% | weaker part |\n| `wall_loops` (process) | fewer on large warping PC parts; more for strength on small parts | ±1 | ≤ 6 | more walls = more shrink stress |\n| `outer_wall_speed`, `inner_wall_speed` (process) | decrease if layers crack or look under-melted | -10 to -20% | never above machine limits | longer print |\n| `filament_max_volumetric_speed` (filament) | decrease when fast sections under-extrude or crack | -10 to -20% | may be lowered freely, raised at most +10% | longer print |\n| `draft_shield` (process) = `enabled` | open-frame printer or draughty room | - | - | extra material and time |\n| `enable_support` (process) under long bridges | add | - | - | support marks |\n| `activate_air_filtration` (filament) = 1 — BY HAND | odour control on printers with a filter fan | - | by hand only (plugin cannot check it): Filament → Cooling → Exhaust fan; only if the printer has one | none |\n\nStrength without warping: `sparse_infill_pattern` = `gyroid`, infill ≤ 50%, ≤ 6 walls; orient the part so the main load runs along the layers, not across them (a ~45° tilt is a compromise between warping and Z strength). For warping in depth see defect-warping; for cracks see defect-layer-adhesion.\n\n## Checks the user must do by hand\n- **Dry** the spool, then print from a sealed box or AMS with fresh desiccant. Check spool heat rating before drying (Bambu low-temp spools ~70 °C max; old black Prusament spools only ~45 °C unless screwed together).\n- **Chamber**: keep door and lid closed. Bambu X1C/P1S: preheat the bed at maximum for ~15 min before starting to warm the chamber. Chamber heating (H2 series, X1E) is a printer/filament option the plugin does not change: tell the user to check it.\n- **Plate**: clean with dish soap and hot water (no acetone on Bambu plates); glue stick for PA and PC; never PC on bare smooth PEI. Prusa Special PA Nylon sheet: water and dish soap only, never IPA, acetone or alcohol cleaners.\n- **Model**: rounded corners warp less than sharp ones; split or shrink full-bed parts.\n- **Nozzle**: filled grades need hardened steel; set the correct nozzle type in printer settings (`nozzle_type`, printer setting, changed by hand).\n- **Next filament**: before switching to PLA/PETG, purge at the PA/PC temperature first, then cool down while extruding, or the old residue clogs.\n- **Bambu H2D/H2C**: PA/PC belong to the high-temperature group and cannot share a job with PLA/PETG/TPU/PVA.\n\n## Calibration in Orca\nDry the filament first, then: Calibration → Temperature (temp tower inside the range), Flow Rate, Pressure Advance, Max Volumetric Speed. Results go to `nozzle_temperature`, `filament_flow_ratio`, `pressure_advance` and `filament_max_volumetric_speed` (filament). See calibration-guide.\n\n## Material notes\n- PA-CF/PAHT-CF/PA6-GF: much less warping, hardened nozzle, lower volumetric caps (material-composites).\n- PC FR and PC Blend: easier than pure PC; same plate and drying rules.\n- Prusa PC Blend on satin sheet can print without glue occasionally; regular use still benefits from glue as protection.\n\n## Sources\n- https://wiki.bambulab.com/en/filament/abs_asa_pc\n- https://wiki.bambulab.com/en/filament/absgf_pa6gf\n- https://wiki.bambulab.com/en/filament/asacf_pahtcf\n- https://wiki.bambulab.com/en/filament/petcf_ppacf\n- https://wiki.bambulab.com/en/general/filament-guide-material-table\n- https://wiki.bambulab.com/en/filament-acc/filament/dry-filament\n- https://wiki.bambulab.com/en/filament-acc/filament/slice-param\n- https://wiki.bambulab.com/en/filament-acc/filament/h2d-filament-config-limit\n- https://wiki.bambulab.com/en/knowledge-sharing/how_to_avoid_nozzle_clogs\n- https://help.prusa3d.com/article/polyamide-nylon_167188\n- https://help.prusa3d.com/article/polycarbonate-pc_165812\n- https://help.prusa3d.com/article/special-pa-nylon-steel-sheet_341570\n- https://help.prusa3d.com/article/drying-filament_332086\n- https://help.prusa3d.com/filament-material-guide\n- https://www.orcaslicer.com/wiki/material_settings/filament/material_temperatures.html\n- https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html\n",
    },
    "material-petg": {
        "description": "PETG family (PETG basic, PETG-HF high-flow, matte, translucent/transparent PETG, PETG V0, CPE, PCTG): temperatures, plate choice and bed keys, cooling trade-off, flow ratio window, stringing and nozzle build-up, wet-filament printing, transparency recipe. Read when the user prints PETG, PETG HF, CPE or PCTG and asks for settings or reports PETG stringing, oozing, blobs or filament sticking to the nozzle, PETG stuck too hard to the plate or tearing PEI, clogging, cloudy transparent PETG, poor PETG bridges or supports that will not come off.",
        "content": "# PETG, PETG-HF, CPE, PCTG\n\nTough, heat-resistant to about 70-80 °C, good layer adhesion, low warping, glossy. Weak points: stringing and oozing, poor bridges/overhangs, bonds very hard to smooth PEI and to its own supports, scratches easily, fairly hygroscopic. Good for mechanical, outdoor and water-exposed parts.\n\n## Baseline (start from the vendor preset)\n| Item | Typical value | Notes |\n|---|---|---|\n| `nozzle_temperature` (filament) | PETG 230-250 °C (Prusa 240, first layer 230; Bambu PETG range 240-270) | PETG-HF and translucent 230-260; PETG V0 220-240; CPE about 275 °C. |\n| Bed, PEI (smooth/textured) or Engineering plate | 70-80 °C (Bambu range 60-80, Prusa 85-90) | Smooth PEI only with a glue-stick separation layer. |\n| Bed, Cool Plate SuperTack | 55-65 °C | Original (non-SuperTack) Bambu Cool Plate: not recommended. |\n| `filament_flow_ratio` (filament) | 0.93-0.96 (Bambu PETG default 0.95) | Below 0.93 weak/gappy; above 0.96 oozing and nozzle build-up. |\n| Cooling | moderate | First few layers no fan (`close_fan_the_first_x_layers`), then partial fan; more fan = detail, less fan = stronger part. |\n\nBed keys per plate (filament preset, each with an \"_initial_layer\" twin): `supertack_plate_temp`, `cool_plate_temp`, `textured_cool_plate_temp`, `eng_plate_temp`, `hot_plate_temp` (Smooth PEI / High Temp), `textured_plate_temp`. Change only the one matching the plate selected in Orca.\n\n## Slicer fixes for PETG problems (dry the filament first: most PETG stringing is moisture)\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `filament_flow_ratio` (filament) | decrease for oozing, blobs, material on the nozzle | to 0.93-0.94 | 0.8-1.2; do not go below 0.93 for PETG | under-extrusion, weaker layers |\n| `nozzle_temperature` (filament) | decrease when printing slowly or stringing | -5 °C (up to -10) | inside nozzle_temperature_range_low..high | weaker layers if too cold |\n| `filament_max_volumetric_speed` (filament) | decrease for build-up, clogs, wet PETG-HF | -4 mm³/s | lower freely, raise ≤ +10% | slower print; lower temperature with it |\n| `fan_max_speed` (filament) | increase for nozzle build-up and stringing | +10-20% | 0-100% | less layer strength, more warping |\n| `filament_retraction_length` (filament) | increase for strings on travel | +0.2 mm, typical 1.2-1.6 mm | 0..min(8, max(2, 2× printer retraction)) mm; keep < 2 mm on direct drive | too long = clog; nil = printer value |\n| `filament_retraction_speed` (filament) | increase with the length | 40-60 mm/s | > 0, ≤ max(1.5× printer value, 30 mm/s) | grinding if excessive |\n| `line_width` / `inner_wall_line_width` (process) | decrease if material collects on the nozzle | 0.36-0.40 mm on a 0.4 nozzle | 0.75-1.5× nozzle diameter | slightly weaker part |\n| `outer_wall_speed` (process) | decrease for bumps/dips after overhangs or speed changes | about 90 mm/s | ≤ printer limits | longer print |\n| `max_volumetric_extrusion_rate_slope` (process) | enable (non-zero) to smooth flow changes | 35-50 mm³/s² at 1000 mm/s² outer-wall acceleration, 70-100 at 2000, 145-200 at 4000 (0.42 mm line, 0.16 mm layer) | 0 = off; above those values it has no effect | turns off arc fitting; slightly longer print |\n| `brim_type` / `brim_width` (process) | `outer_only` for lifting corners or large parts | +3 mm | 0-100 mm | removal marks |\n| `wall_loops` (process) | increase for strength instead of more infill | +1 | ≤ 6 walls, infill ≤ 50% | more shrinkage stress/warping |\n\n- Seam on an overhang ruins that surface: move it with `seam_position` (process) or seam painting.\n- Strength: walls give more than infill; orient so the load is not across layers.\n- Wet PETG-HF with no dryer available: print slower and cooler (Bambu \"Generic PETG HF\" uses about 220 °C and 16 mm³/s); do not speed up at that temperature. Dry it as soon as possible.\n\n## Supports\nPETG fuses strongly to PETG supports. Options:\n- Larger `support_top_z_distance` and `support_object_xy_distance` (process); see defect-supports.\n- Multi-material: PLA as support interface for PETG (and PETG for PLA) separates cleanly. Use the other material only for the interface (`support_interface_filament`, process), not the whole base; Bambu tested only PLA Basic with PETG Basic/HF. Both on Smooth or Textured PEI at about 60 °C, door open on enclosed printers. When PETG is the support for PLA, Bambu limits PETG `filament_max_volumetric_speed` to about 10 mm³/s.\n\n## Translucent / transparent PETG\nPETG is amorphous and clears better than PLA. Only with fully dried filament:\n- `wall_loops` 1, `top_shell_layers` 0, `bottom_shell_layers` 0, `sparse_infill_density` `100%` (process). At 100% Orca prints the infill as internal solid infill: set `internal_solid_infill_pattern` `rectilinear` and `solid_infill_direction` 0 or 90 (process).\n- `layer_height` 0.1 mm, `line_width` 0.5 mm, all speeds about 20 mm/s.\n- Moderately higher `nozzle_temperature` and `filament_flow_ratio` (fills gaps between lines).\n- Part cooling off (`fan_min_speed` and `fan_max_speed` 0, filament) for slow, even cooling.\n- 0.8 mm nozzle recommended (hardware, user); sand the surface afterwards. Complex geometry limits clarity regardless of settings.\n\n## Variants\n- PETG-HF: high-flow PETG tuned for speed; same temperature logic (faster = hotter). Very sensitive to moisture.\n- PETG matte (Bambu): Textured PEI, Smooth PEI or Cool Plate SuperTack.\n- PETG V0 (Prusament, self-extinguishing): more hygroscopic than PETG; dry 6 h at 55 °C before use if not stored dry; satin/textured sheet.\n- CPE: copolyester between PETG and ABS, prints like PETG at about 275 °C nozzle / 90 °C bed; same smooth-PEI warning.\n- PCTG: Bambu lists it with PLA/PETG as low-temperature filament (no heated chamber). Use the vendor's ranges.\n- PETG-CF, glow/Ultraglow PETG: abrasive, hardened nozzle, prefer 0.6 mm: see material-composites.\n\n## Checks the user must do by hand\n- Dry PETG: oven 55-65 °C for 6-8 h (Prusa 55 °C / 6 h; Bambu 65 °C / 8 h); Bambu AMS 2 Pro/HT 65 °C, 8 h; heated-bed drying on enclosed Bambu printers 75-85 °C, 12 h, spool covered and flipped every 6 h. Store below 20% RH with desiccant. Popping, bubbles, heavy stringing = wet.\n- Plate: Prusa satin or textured sheet. Never bare smooth PEI: PETG can tear the surface; apply a thin glue-stick layer. Bambu: glue helps on Engineering plate; brim for large parts.\n- Enclosed printers: PETG softens at 60-80 °C. With the bed above about 70 °C, open the door or lift the lid to avoid heat creep; in a cold room an enclosure helps layer strength. Never heated-chamber temperatures (above about 45 °C).\n- Material building up on the nozzle with dry filament: check the nozzle for wear and replace it; check the nozzle wiper (Bambu) for wear or a loose mount.\n- Many long travel moves (plate layout) increase oozing: arrange parts closer.\n- Ring-shaped bulges where a thick base meets thin walls: add an inner fillet/chamfer in CAD.\n\n## Calibration in Orca\nCalibration → Temperature, Flow ratio (expect 0.93-0.96), Pressure advance, Retraction test, Max flowrate. On Bambu printers do not tick the printer's own flow calibration in the send dialog for these tests (calibration-guide).\n\n## Sources\n- https://wiki.bambulab.com/en/filament/petg\n- https://wiki.bambulab.com/en/filament-acc/filament/petg-hf-unfinished-drying\n- https://wiki.bambulab.com/en/knowledge-sharing/transparent-petg\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/filament-sticks-to-nozzle\n- https://wiki.bambulab.com/en/filament-acc/filament/h2d-pla-and-petg-mutual-support\n- https://wiki.bambulab.com/en/general/filament-guide-material-table\n- https://wiki.bambulab.com/en/filament-acc/filament/dry-filament\n- https://wiki.bambulab.com/en/filament-acc/acc/plates\n- https://wiki.bambulab.com/en/h2c/h2c-filament-printing-guide\n- https://help.prusa3d.com/article/petg_2059\n- https://help.prusa3d.com/article/petg-v0_1050343\n- https://help.prusa3d.com/article/cpe_166877\n- https://help.prusa3d.com/article/prusament-petg-ultraglow-troubleshooting_1043965\n- https://help.prusa3d.com/article/smooth-steel-sheet_196550\n- https://help.prusa3d.com/article/drying-filament_332086\n- https://www.orcaslicer.com/wiki/material_settings/filament/material_flow_ratio_and_pressure_advance.html\n- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_advanced.html\n- https://www.orcaslicer.com/wiki/calibration/flow_ratio_calib.html\n- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_infill.html\n",
    },
    "material-pla": {
        "description": "PLA and its variants (basic, matte, PLA+/tough, high-speed, silk, translucent, wood, LW-PLA/PLA Aero foaming): temperatures, plate and bed keys, cooling, drying, heat creep in enclosed printers and variant-specific Orca settings. Read when the user prints PLA, silk PLA, matte PLA, PLA+, transparent PLA, LW-PLA, foaming PLA or PLA Aero and asks for settings or reports dull/uneven silk shine, brittle silk parts, PLA clogging in a closed printer, oozing foaming PLA or cloudy transparent PLA.",
        "content": "# PLA and PLA variants\n\nPLA is the easiest material: low temperature, minimal warping, strong part cooling. Weak points: softens at about 55-60 °C (Bambu PLA Basic HDT 57 °C), brittle, poor UV/heat resistance, layers split on impact. Not for parts in hot cars, outdoors or near heat; suggest PETG/ASA instead (see material-petg, material-abs-asa).\n\n## Baseline (start from the vendor preset; change only what the symptom needs)\n| Item | Typical value | Notes |\n|---|---|---|\n| `nozzle_temperature` (filament) | 200-220 °C (Prusa: 210, first layer 215) | Whole family 190-240 °C; silk 210-240 °C. Faster printing needs the hotter end. |\n| Bed, smooth/textured PEI or Engineering plate | 45-65 °C (Prusa PEI: 60 °C) | Engineering plate needs glue. |\n| Bed, Cool Plate / Cool Plate SuperTack | 35-45 °C | SuperTack is for PLA/PETG only. |\n| Part cooling | strong after the first layers | `close_fan_the_first_x_layers` (filament) 1-3 for adhesion. |\n| `filament_max_volumetric_speed` (filament) | from the vendor preset | Calibrate per brand/colour; high-speed PLA allows more. |\n\nBed keys are per plate type (all filament preset, each with an \"_initial_layer\" twin): `cool_plate_temp` (Cool Plate), `supertack_plate_temp` (Cool Plate SuperTack), `textured_cool_plate_temp` (Textured Cool Plate), `eng_plate_temp` (Engineering Plate), `hot_plate_temp` (High Temp / Smooth PEI Plate), `textured_plate_temp` (Textured PEI Plate). Change only the one matching the plate selected in Orca; a value of 0 means \"plate not supported by this filament\". If the selected plate type does not match the physical plate, adhesion fails: tell the user to fix the plate selection first.\n\n## Slicer fixes for common PLA problems\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `hot_plate_temp` / `textured_plate_temp` (filament) | decrease when PLA clogs in an enclosed printer | -5 °C | stay ≥ 45 °C on PEI; max +10 °C per change, ≤ 120 °C | less adhesion; add brim if corners lift |\n| `nozzle_temperature` (filament) | increase for under-melting at high speed or weak layers; decrease for stringing at low speed | ±5 °C | inside filament nozzle_temperature_range_low..high | hotter = more stringing; colder = weak layers |\n| `close_fan_the_first_x_layers` (filament) | increase when the first layer lifts | 1 → 3 | 0-3 | none relevant for PLA |\n| `brim_type` / `brim_width` (process) | `outer_only`, 8-10 mm for small footprints or lifting corners | +3 mm | 0-100 mm | brim removal marks |\n| `filament_retraction_length` (filament) | increase for stringing (after drying) | +0.2 mm | 0..min(8, max(2, 2× printer retraction)) mm | clog risk if too long; nil = printer value |\n| `filament_max_volumetric_speed` (filament) | decrease if fast PLA under-extrudes | -2 mm³/s | lower freely, raise ≤ +10% | longer print |\n| `filament_flow_ratio` (filament) | tune with the flow calibration | ±0.02 | 0.8-1.2 | dimensions change |\n\n## Variants\n### Matte, PLA+, tough, high-speed PLA\n- Print as standard PLA within the range printed on the spool. Matte and basic PLA usually need no drying out of the bag.\n- High-speed PLA: speed and nozzle temperature go together. Raise `nozzle_temperature` toward the top of the range before raising speed, and run Calibration → Max flowrate to set `filament_max_volumetric_speed`.\n\n### Silk PLA (pearlescent additive)\nShine depends on outer-wall speed and on keeping that speed constant.\n- `outer_wall_speed` (process): 40-60 mm/s, start at 50. Fast walls look dull.\n- `dont_slow_down_outer_wall` (filament) = `1`: layer-time slowdown no longer changes wall speed (removes bright/dull bands). Inner walls and infill get slowed more instead.\n- `layer_height` (process) 0.16 mm on curved surfaces (≤ 75% of nozzle diameter).\n- `top_surface_pattern` (process): `archimedeanchords` or `concentric` for shinier tops.\n- `nozzle_temperature` / `nozzle_temperature_initial_layer` (filament): silk usually wants 210-240 °C; Bambu Silk is tuned around 235 °C (stay inside the filament range).\n- Gloss bands from overhang slowdown or minimum layer time: check the Speed view in preview; print several parts together so layers last longer.\n- Z strength is only about 65% of basic PLA: orient loads in XY, raise `wall_loops` and `sparse_infill_density` (process), slow down thin tall parts and add supports.\n- Hardware: 0.2/0.4 mm nozzles recommended, 0.6/0.8 not; avoid the Cool Plate SuperTack. Dual-colour silk has an oval cross-section and can twist: not recommended on Bambu A-series.\n- Orient the main display surface vertical: flat curved surfaces show steps and lose gloss.\n\n### Translucent / transparent PLA\nPLA is semi-crystalline, so it never gets as clear as PETG. Recipe (only with fully dry filament):\n- 1 wall (`wall_loops` = 1), `top_shell_layers` = 0, `bottom_shell_layers` = 0, `sparse_infill_density` = `100%` (process). At 100% Orca prints the infill as internal solid infill, so the straight-line pattern goes in `internal_solid_infill_pattern` = `rectilinear` with `solid_infill_direction` 0 or 90 (process).\n- `layer_height` 0.1 mm, `line_width` 0.5 mm, all speeds about 20 mm/s (process).\n- Slightly higher `nozzle_temperature` and `filament_flow_ratio` (filament).\n- Reduce part cooling (`fan_max_speed`, `fan_min_speed`, filament). Turning it fully off makes PLA warp: reduce moderately according to part thickness.\n- A 0.8 mm nozzle (user hardware change) gives fewer line boundaries; sand afterwards.\n\n### PLA Wood\nMust be dried; wood powder absorbs water and causes stringing. Not for 0.2 mm nozzles; AMS lite not recommended. Noticeable wood smell: ventilate.\n\n### LW-PLA / PLA Aero (active foaming)\nExpansion grows with temperature (Prusa LW-PLA: up to about 3× near 240-250 °C; faster printing needs more heat for the same foaming). Retraction barely works because the melt keeps expanding: oozing on travel is normal.\n- Prefer vase mode: `spiral_mode` = `1`, `wall_loops` 1, `top_shell_layers` 0, `sparse_infill_density` `0%`, `slicing_mode` = `even_odd`, `wall_generator` = `classic`, `print_sequence` = `by object` for several parts (process).\n- Same speed for all features, `enable_overhang_speed` = `0`, moderate acceleration.\n- Normal mode: low or zero `filament_retraction_length`, `filament_z_hop` 0, `seam_position` `nearest`; check the preview for unnecessary travel.\n- Foaming needs flow ratio far below 1 (0.35-0.95 depending on temperature). The plugin cannot set `filament_flow_ratio` below 0.8: explain the value and let the user set it by hand (Filament → Filament → Flow ratio).\n- Bambu PLA Aero: 0.4 mm nozzle only; disable the printer's dynamic flow calibration in the print dialog (user action).\n- Damp foaming PLA leaks much more: dry deeply first.\n\n### PLA-CF, PLA Glow, Marble, Sparkle\nAbrasive or particle-filled: hardened nozzle, no 0.2 mm nozzle. See material-composites.\n\n## Checks the user must do by hand\n- Heat creep in enclosed printers (Bambu X1/P1S/P2S/H2, any printer in a closed enclosure): with the bed above about 45 °C, open the door and/or remove the top lid, or use a low-temperature plate. Prusa: in a closed Original Prusa Enclosure with the room above about 27 °C, PLA can under-extrude or clog. Room 10-30 °C is ideal; in summer also lower the bed 5-10 °C. Bambu groups PLA as low-temperature filament: never in a heated chamber (over about 45 °C).\n- After ABS/PC/PETG, load PLA at the previous (hotter) material temperature so it pushes the residue out, or do a cold pull first.\n- Clean the plate with warm water and dish soap (Bambu) or IPA (Prusa); no fingerprints. Let the plate cool before removing parts.\n- Prusa sheets: satin or smooth PEI give the best PLA adhesion; on the textured sheet the first layer must be slightly lower (live-Z, printer calibration). Small PLA parts on textured/satin may need a brim.\n- Ring-shaped bulges where a thick base meets thin walls (box or boat hull) come from internal bridges touching the walls: add an inner fillet/chamfer in CAD.\n- PLA is not food-safe as printed (layer grooves trap bacteria).\n\n## Drying\nStandard PLA is barely hygroscopic (fine at 50-60% RH). Dry when stringing or popping appears, and always for silk, wood, Aero, translucent and CF:\n- Standard PLA: 45-50 °C, 6-8 h.\n- Silk / wood / Aero: 55 °C, 8 h (oven or dryer). Bambu AMS 2 Pro / AMS HT: 45 °C, 12 h. Heated-bed drying (enclosed Bambu, spool covered, flipped every 6 h): 60-75 °C, 12 h.\n- Never let a dryer exceed the spool's rating; static drying of PLA can fuse the coils.\n\n## Calibration in Orca\nCalibration → Temperature (tower) for a new brand/colour, then Flow ratio, Pressure advance, Max flowrate, Retraction test (calibration-guide).\n\n## Sources\n- https://wiki.bambulab.com/en/filament/pla\n- https://wiki.bambulab.com/en/x1/manual/printing-with-silk-filaments\n- https://wiki.bambulab.com/en/general/filament-guide-material-table\n- https://wiki.bambulab.com/en/knowledge-sharing/transparent-petg\n- https://wiki.bambulab.com/en/filament-acc/filament/dry-filament\n- https://wiki.bambulab.com/en/filament-acc/filament/heat-creep\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/different-gloss\n- https://wiki.bambulab.com/en/filament-acc/filament/slice-param\n- https://wiki.bambulab.com/en/filament-acc/acc/plates\n- https://wiki.bambulab.com/en/h2c/h2c-filament-printing-guide\n- https://help.prusa3d.com/article/pla_2062\n- https://help.prusa3d.com/article/lw-pla_304914\n- https://help.prusa3d.com/article/drying-filament_332086\n- https://help.prusa3d.com/article/under-extrusion-nextruder-printers_821253\n- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/warping-falling-off-collapsing\n- https://help.prusa3d.com/article/satin-steel-sheet_196526\n- https://help.prusa3d.com/article/textured-steel-sheet_196534\n- https://www.orcaslicer.com/wiki/material_settings/filament/material_temperatures.html\n- https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html\n- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_infill.html\n",
    },
    "material-special": {
        "description": "Support and soluble filaments (PVA, BVOH, HIPS, Bambu Support for ABS, Support for PLA, PLA/PETG and PA/PET), polypropylene (PP, PP-CF), PVB and high-temperature niche materials (PPS, PEI/Ultem): pairing rules, drying, plates, support and purge settings in Orca. Read when the user prints soluble or break-away supports, PVA that clogs or will not stick, supports that do not dissolve, PP that will not stick or warps, PVB for smoothing, or asks about PPS or PEI/Ultem.",
        "content": "# Special materials: soluble and support filaments, PP, PVB, PPS, PEI\n\n## Support filaments: pairing (wrong pairs clog or do not bond)\n| Support filament | Use with | Removal | Moisture |\n|---|---|---|---|\n| PVA | PLA (incl. PLA-CF/GF). Not with PETG | dissolves in water | extreme |\n| BVOH | PLA and PETG; stiffer, prints more reliably than PVA | dissolves in water | extreme |\n| HIPS / Bambu Support for ABS (HIPS based) | ABS (also PETG) | break-away, or d-limonene | low |\n| Bambu Support for PLA | PLA (not PLA Aero) | break-away | low |\n| Bambu Support for PLA/PETG | PLA and PETG | break-away | moderate |\n| Bambu Support for PA/PET | PA, PA-CF, PET-CF | break-away; remove within ~2 h of print end | high |\n| PVB | PLA-like temperatures | dissolves in IPA | high |\n\nNeeds a multi-material system (AMS, MMU, XL, H2D/H2C dual nozzle). Bambu: PVA not recommended on A-series/AMS lite (open spools re-absorb water; keep prints with PVA on AMS lite under ~1 h); H2D must not print PVA in one hotend and PETG in the other at the same time.\n\n## PVA / BVOH\n- Nozzle: PVA ~190-215 °C, BVOH ~215 °C; bed ~45-60 °C. Bonds poorly to PEI: avoid PVA directly on the plate where possible.\n- Moisture is the main failure: wet PVA turns soft and sticky, will not feed, tangles in gears, clogs the hotend and does not stick. Freshly dried PVA in a ~55% RH room is degraded within 1-3 h; keep it in a sealed box below 20% RH. Dried PVA bends stiffer than PLA: a quick dryness test.\n- Drying: 75-85 °C, 8-12 h in an oven or dryer; AMS HT 85 °C ~18 h; an AMS 2 Pro (65 °C) cannot dry it completely. Put it in the dry box right after drying, without letting it cool in room air.\n- Low flow: about 4 mm³/s versus ~15 mm³/s for PLA, so long print times.\n- Dissolve in warm water (max ~45 °C for PLA parts), hours to overnight, then brush. Porous parts can take water inside.\n\n## Slicer settings for soluble and break-away supports\n| Key (preset) | Direction | Typical value | Safe limit | Side effects |\n|---|---|---|---|---|\n| `support_interface_filament` and `support_filament` (process) | select the support filament slot | full soluble: both = PVA/BVOH; interface-only: base = model filament | slot must hold the support filament | full soluble costs more material and time |\n| `support_top_z_distance` (process) | 0 for soluble interfaces | 0 | - | supported surface fused if the support filament is wrong |\n| `support_type` = `normal(auto)`, `support_style` = `grid` (process) | prefer over tree when PVA is the body | - | - | more material |\n| `support_interface_not_for_body` (process) | 1 with break-away/soluble interface over a default base | 1 | - | none |\n| `flush_into_support`, `flush_into_infill` (process) | 0 for soluble supports and for Support for ABS (mixed-in model filament stops PVA dissolving and weakens HIPS supports) | 0 | - | more purge on the tower |\n| `prime_volume` (process) / `filament_minimal_purge_on_wipe_tower` (filament) | increase if supported faces show strings, gaps or residue | x1.5-2 | - | more waste |\n| `filament_max_volumetric_speed` (filament, PVA/BVOH) | keep low | ~4 mm³/s | lower freely, raise max +10% | slower supports |\n| `support_interface_top_layers` (process) | increase for easier removal of break-away supports | +1 | 0-3 | more material |\n| `support_interface_speed` (process) | increase slightly if break-away supports are hard to remove; decrease if the part does not stick to the interface | ±10-20% | machine limits | too fast can lift or warp |\n| `support_top_z_distance` (process, break-away only) | decrease if the model will not bond onto the interface | -0.05 mm | ≥ 0 | harder removal |\n| `bridge_speed` (process) | increase if break-away supports bond too hard (Bambu: 100-150 mm/s) | +20 mm/s | machine limits | bridge sag |\n\nPurge between model and support filament happens in the flushing-volumes dialog (not a preset key): tell the user to raise it; for changes to/from PVA or BVOH ~200-240 mm³ or more, doubling the default if residue shows; Support for ABS → ABS needs a very large value (Bambu uses 800). Bambu H2D with ABS + Support for ABS: `filament_prime_volume` (filament, ABS) 90 mm³ and `fan_min_speed` (filament, ABS) 50%. Do not use the adaptive (variable) layer height tool with Support for ABS. With ABS + Support for ABS, model layers at the height of support swaps are weaker (overcooling during swaps, residue): orient so loads do not cross those layers. Prime tower note: with a prime tower, independent support layer height is ignored.\n\n## HIPS and limonene\n- Nozzle 225-255 °C, bed 100-110 °C; ABS-like, lighter, lower shrink; sticks to PEI sheets, use a brim for small contact areas. Not hygroscopic (drying optional, ~80 °C 4 h).\n- d-Limonene also attacks some ABS/ASA grades: soak briefly to loosen the HIPS, then pull it off, instead of dissolving fully. Limonene: flash point ~48 °C (no flames, no hot bed nearby), ventilated room, fluororubber or laminated gloves (not latex).\n\n## PP (polypropylene)\n- Nozzle 220-270 °C (brand dependent), bed 80-100 °C. Very low adhesion to PEI: use a PP sheet, PP tape on smooth PEI, or a PP-specific adhesive. Prusa PP sheet: clean cold with ~90% IPA, never acetone; it also works for PLA, PETG and TPU.\n- Strong warping: enclosure, `brim_type` `outer_only` with `brim_width` 5-10 mm (process), sparse infill. Prints better with a hotter `nozzle_temperature` for layer bond and a cooler `nozzle_temperature_initial_layer` (filament), both inside the filament range.\n- PP-CF/PP-GF warp almost not at all (hardened nozzle: material-composites). Dry PP-CF/GF ~70 °C 2-4 h.\n\n## PVB\n- Nozzle 205-225 °C, bed ~75 °C, PLA-like and low warping; smooth PEI or satin sheet (poor on powder-coated textured). Smoothed with IPA (vapour, bath, brush).\n- Clear parts: `spiral_mode` = 1 (process) with a 0.8 mm nozzle; extra walls stay visible after smoothing. Weak layer bond, PLA-like heat resistance: not for mechanical parts.\n- Hygroscopic: dry 45 °C, 8 h.\n\n## PPS and PEI (Ultem): specialist printers only\n- PPS: nozzle 330-370 °C, bed 120-150 °C, actively heated chamber ≥ 65 °C, dry ≥ 4 h at 110 °C, HT adhesive in several layers. PPS-CF (Bambu, X1E/H2 only): 310-340 °C, bed 100-120 °C, brittle (no tight tube bends, external dry box), hardened nozzle.\n- PEI 9085/1010: nozzle 370-420 °C, bed 150-155 °C, chamber 85-90 °C, dry 130-150 °C (1010: 150 °C, 6-8 h; regains moisture within tens of minutes), thin HT adhesive layer, always a brim, round compact bases, slow speed, remove supports while warm. Wet PEI gives a foamy base, bubbles and strings.\n- These bed and chamber values exceed what the plugin may set (bed max 120 °C, no chamber control): explain to the user that a high-temperature printer and its vendor profile are required.\n\n## Checks the user must do by hand\n- Dry and store soluble/PA support filaments sealed; replace saturated desiccant (silica beads turn purple).\n- Load the support filament in the slot the profile expects; the printer cannot detect it.\n- Set flushing volumes in the flushing dialog; calibrate the MMU/AMS feeding for soft PVA.\n- Choose the plate (PP sheet/tape for PP; smooth PEI or satin for PVB).\n\n## Calibration in Orca\nCalibration → Flow ratio and Max flowrate for PVA/BVOH and PP after drying; Temperature tower for PP and PVB. See calibration-guide; purge tuning in defect-multimaterial, support geometry in defect-supports.\n\n## Sources\n- https://wiki.bambulab.com/en/filament/support\n- https://wiki.bambulab.com/en/filament-acc/filament/pva-printing-guide\n- https://wiki.bambulab.com/en/filament-acc/filament/support-for-abs\n- https://wiki.bambulab.com/en/filament-acc/filament/h2d-filament-config-limit\n- https://wiki.bambulab.com/en/filament-acc/filament/dry-filament\n- https://wiki.bambulab.com/en/knowledge-sharing/desiccant-status\n- https://wiki.bambulab.com/en/filament/petcf_ppacf\n- https://wiki.bambulab.com/en/h2/manual/PPA-PPS-printing-guide\n- https://wiki.bambulab.com/en/general/filament-guide-material-table\n- https://help.prusa3d.com/article/water-soluble-bvoh-pva_167012\n- https://help.prusa3d.com/article/water-soluble-materials-pva-bvoh_162860\n- https://help.prusa3d.com/article/hips_167118\n- https://help.prusa3d.com/article/polypropylene-pp_167126\n- https://help.prusa3d.com/article/pp-steel-sheet_815373\n- https://help.prusa3d.com/article/pvb_196708\n- https://help.prusa3d.com/article/pps-polyphenylene-sulfide_788028\n- https://help.prusa3d.com/article/pei-ultem_725809\n- https://help.prusa3d.com/article/how-to-print-with-pei-1010_794930\n- https://help.prusa3d.com/article/drying-filament_332086\n- https://www.orcaslicer.com/wiki/print_settings/support/support_settings_filament.html\n- https://www.orcaslicer.com/wiki/print_settings/multimaterial/multimaterial_settings_flush_options.html\n",
    },
    "material-tpu": {
        "description": "TPU and other flexible filaments (TPU 95A, 90A, 85A and softer, TPE/TPEE, \"TPU for AMS\"): feeding path and hardware limits, slow speed and volumetric limit, low retraction, temperatures and plate/bed keys, drying, supports and part removal. Read when the user prints TPU, flexible or rubber-like filament and asks for settings or reports TPU not feeding, tangling in the extruder gears, under-extrusion or holes in TPU walls, stringing or oozing with TPU, TPU stuck too hard to the plate, or TPU failing in the AMS.",
        "content": "# TPU and flexible filaments\n\nElastic, wear and impact resistant, low shrinkage and almost no warping, excellent layer adhesion. Hardness is given in Shore A: lower number = softer = harder to print (95A is the easiest; 85A and below need special feeding). Typical uses: tyres, gaskets, bumpers, watch bands, phone cases, shoe soles. Weak points: feeding (the filament buckles), stringing, very poor bridges/overhangs, supports hard to remove, hygroscopic.\n\n## Baseline (start from the vendor preset)\n| Item | Typical value | Notes |\n|---|---|---|\n| `nozzle_temperature` (filament) | 220-240 °C (Bambu 85A/90A: 225 °C; Prusa TPU 95A 220-240) | +5 °C lowers flow resistance; too hot gives bubbles and stringing. |\n| Bed (PEI, Engineering, satin/textured) | 30-45 °C on Bambu plates; up to 55-75 °C on Prusa sheets for large parts | Adhesion is rarely the problem: removal is. |\n| Cool Plate SuperTack | never | Bonds too strongly. |\n| Speed | slow: about 20 mm/s typical, 30-40 mm/s max for soft grades | Bambu: keep the preset's volumetric limit, do not raise speed. |\n| Retraction | short or off | Long retractions cause holes and jams. |\n| Part cooling | low or off | Lower fan if the nozzle clogs (Prusa). |\n\nBed keys per plate (filament preset, each with an \"_initial_layer\" twin): `textured_plate_temp`, `hot_plate_temp` (Smooth PEI / High Temp), `eng_plate_temp`, `cool_plate_temp`, `textured_cool_plate_temp`. Change only the one matching the plate selected in Orca.\n\n## Slicer fixes\n| Key (preset) | Direction | Typical step | Safe limit | Side effects |\n|---|---|---|---|---|\n| `filament_max_volumetric_speed` (filament) | decrease for under-extrusion, skipping, tangling | -1 mm³/s | lower freely, raise ≤ +10% | longer print |\n| `filament_retraction_length` (filament) | decrease for holes / brief gaps after travel | -0.2 mm (0 is acceptable) | 0..min(8, max(2, 2× printer retraction)) mm | more stringing; nil = printer value |\n| `filament_retraction_length` (filament) | increase only for heavy oozing, after drying | +0.1-0.2 mm | same | jams in the gears |\n| `print_sequence` (process) — BY HAND | `by object` when many parts are on the plate | n/a | by hand only: Process → Others → Special mode → Print sequence; gantry clearance | fewer long travels = fewer strings |\n| `nozzle_temperature` (filament) | +5 °C for under-extrusion/clogs; -5 °C for bubbles and strings | ±5 °C | inside nozzle_temperature_range_low..high | see left |\n| `fan_max_speed` (filament) | decrease when the nozzle clogs | -10-20% | 0-100% | worse overhangs |\n| `wall_loops`, `top_shell_layers`, `bottom_shell_layers`, `sparse_infill_density` (process) | lower for a softer part, higher for a stiffer/stronger one | ±1 wall, ±10% | n/a | softness/strength trade-off |\n| `brim_type` / `brim_width` (process) | add a brim (`outer_only`) for large parts on satin sheets | +3 mm | 0-100 mm | removal effort |\n\nSupports:\n- Best: PLA as support material for TPU (multi-material): removes more easily and avoids tangled support surfaces. Pick a PLA colour close to the TPU to avoid staining.\n- TPU-only supports: `support_type` `normal(auto)`, `support_base_pattern` `rectilinear-grid` (Bambu, single nozzle). Bigger gaps: `support_top_z_distance` about 0.3 mm and `support_object_xy_distance` at least one line width (process).\n- Avoid tall thin TPU parts: they wobble and fail. Bridges and overhangs are poor: orient or design them out.\n\n## Checks the user must do by hand (most TPU failures are feeding hardware)\n- Feeding path: as short and straight as possible, spool rotating freely and raised above the extruder inlet. Soft TPU (95A and below) must not go through the AMS, AMS lite or AMS 2 Pro; only \"TPU for AMS\" can. AMS HT works as a sealed box with its rear TPU outlet; AMS 3H via the bypass port. A 5.8 L dry box with a side opening is preferred (TPU spools widen when dried).\n- Bambu A1/A1 mini: TPU 90A or harder (not 85A). H2D/H2C: TPU on the right hotend only; 85A fed directly into the extruder, or with the top-feed rack. P-series: place the part toward the front centre of the bed to reduce tube friction. The optional TPU Feeding Assist Module (H2/X/P) reduces resistance.\n- Nozzle: no 0.2 mm. TPU 85A needs 0.6 mm or larger (or the TPU high-flow hotend) on Bambu; standard high-flow nozzles are not recommended for 85A/90A. Use a new or cold-pulled nozzle; never one that printed CF/GF filament.\n- Extruder: Prusa: loosen the idler (about 1.5 turns) so the gears grip gently; CORE One+/L have a switch to loosen the filament sensor lever; on the XL and CORE One feed through the tube manually. Bambu: clean the extruder gears, replace worn ones. Load slowly with short extrude clicks so the TPU does not wrap around the gears; if it tangles, the extruder must be opened and cleared.\n- Bambu A1 TPU 90A: disable dynamic flow calibration in the print dialog. Automatic filament change and runout sensors may not work with flexibles.\n- Dry before printing (Bambu: required). Oven 60-70 °C for 4-8 h (Prusa TPU 60 °C / 4-6 h; Bambu 70 °C / 8 h); AMS HT 75 °C, 18 h; heated bed of enclosed Bambu printers 80-90 °C, 12-16 h. AMS 2 Pro (max 65 °C) does not dry it fully. Store below 20% RH.\n- TPU left loaded for a long time between prints can deform in the extruder: unload and reload.\n- Plates: Bambu Textured PEI without glue (glue makes it stick too much); other Bambu plates with glue. Prusa: textured sheet without glue, satin and smooth PEI only with a glue-stick separation layer (bare smooth PEI gets damaged). Removal: let the plate cool (Prusa textured: warm to about 40 °C), lift a corner and spray alcohol into the gap, never force it.\n- Enclosed printers: TPU softens below 60 °C; keep the chamber cool (door open if the bed is above about 45 °C).\n\n## Calibration in Orca\nCalibration → Temperature and Max flowrate (start from a low range); Retraction test with the default 0-2 mm range and 0.1 mm steps, choosing the shortest clean length; then Flow ratio and Pressure advance as for other filaments (calibration-guide). Bambu A1 series with TPU 90A: leave the printer-side dynamic flow calibration off.\n\n## Sources\n- https://wiki.bambulab.com/en/knowledge-sharing/tpu-printing-guide\n- https://wiki.bambulab.com/en/filament-acc/filament/tpu-85a-90a-printing-guide-for-a-series\n- https://wiki.bambulab.com/en/filament-acc/filament/tpu-85a-90a-printing-guide-for-p-series\n- https://wiki.bambulab.com/en/h2/h2d-tpu-printing-guide\n- https://wiki.bambulab.com/en/h2/troubleshooting/tpu-clogging\n- https://wiki.bambulab.com/en/h2c/h2c-filament-printing-guide\n- https://wiki.bambulab.com/en/general/filament-guide-material-table\n- https://wiki.bambulab.com/en/filament-acc/filament/dry-filament\n- https://help.prusa3d.com/article/flexible-materials_2057\n- https://help.prusa3d.com/article/prusament-tpu-95a-material-guide_899653\n- https://help.prusa3d.com/article/satin-steel-sheet_196526\n- https://help.prusa3d.com/article/textured-steel-sheet_196534\n- https://help.prusa3d.com/article/smooth-steel-sheet_196550\n- https://help.prusa3d.com/article/drying-filament_332086\n- https://www.orcaslicer.com/wiki/material_settings/filament/material_temperatures.html\n- https://www.orcaslicer.com/wiki/calibration/retraction_calib.html\n",
    },
    "materials-overview": {
        "description": "Quick comparison of all filament materials (PLA, PETG/PCTG, ABS/ASA, TPU, PA/nylon, PC, CF/GF composites, wood/metal fills, PVA/BVOH, HIPS, support filaments, PP, PVB, PPS, PEI) with nozzle and bed ranges, enclosure and hardened-nozzle needs, drying table, wet-filament signs, plate choice and the Orca plate-temperature keys; routes to the material-* skill. Read when the user asks which material, temperature, plate, glue or drying settings to use, whether filament is wet or must be dried, or mentions a material before a defect is clear.",
        "content": "# Materials overview\n\nValues are start points for a 0.4 mm nozzle; the spool label and a temperature tower win. Detail and fixes live in the routed skill.\n\n## Comparison table\n| Material | Nozzle °C | Bed °C | Enclosure | Hardened nozzle | Skill |\n|---|---|---|---|---|---|\n| PLA (basic, matte, silk, PLA+) | 200-220 (family 190-240) | 45-65 PEI, 35-45 Cool Plate | no; open door if bed > 45 °C | no | material-pla |\n| PETG, PETG-HF, PCTG, CPE | 230-250 | 70-80 | no; open door if bed > ~70 °C | no | material-petg |\n| ABS / ASA | 240-265 | 90-110 | yes | no | material-abs-asa |\n| TPU / flexibles | 220-240 | 30-45 | no | no | material-tpu |\n| PA (nylon) | 240-285 | 100-110 + glue | yes | no (yes for filled) | material-pa-pc |\n| PC, PC Blend, PC-ABS | 260-290 | 100-115 + glue | yes | no | material-pa-pc |\n| PLA-CF / PETG-CF | 210-240 / 240-270 | as base | as base | yes | material-composites |\n| ABS-GF, ASA-CF | 240-280 | 90-100 + glue | yes | yes | material-composites |\n| PA-CF/GF, PAHT-CF, PET-CF | 260-300 | 80-110 + glue stick | yes | yes | material-composites |\n| PPA-CF / PPS-CF | 285-320 / 310-340 | 100-120 + glue stick | yes (PPS-CF: Bambu X1E/H2 only) | yes | material-composites |\n| Wood-filled | as base (190-240 PLA) | as base | no | no, but ≥ 0.6 mm nozzle for coarse fills | material-composites |\n| Metal-powder, glow, magnetite, tungsten | as base | as base | no | yes | material-composites |\n| PVA / BVOH | 190-215 | 45-60 | no | no | material-special |\n| HIPS, Support for ABS | 225-255 | 100-110 | yes | no | material-special |\n| Support for PLA, PLA/PETG | 190-240 | as model | as model | no | material-special |\n| Support for PA/PET | 260-300 | as model | yes | yes | material-special |\n| PP | 220-250 | 80-100, PP sheet/tape | recommended | no | material-special |\n| PVB | 205-225 | ~75 | no | no | material-special |\n| PPS, PEI/Ultem | 330-430 | 120-150 | heated chamber | - | material-special (beyond plugin limits) |\n\nMaterial groups that must not share a print or a hot chamber (Bambu H2D/H2C enforce it; the chamber logic applies to any enclosed printer): low-temperature PLA, PETG, TPU, PVA, BVOH vs high-temperature ABS, ASA, PC, PA, PET-CF, PPS, PPA. Low-temperature filaments soften in the extruder above ~45 °C chamber and clog.\n\n## Is the filament wet?\nSigns: popping or hissing at the nozzle, steam, bubbles or holes in walls, rough or foamy surface, sudden heavy stringing or oozing, weak or brittle layers, blobs; damp PVA/BVOH turns soft and fails to feed. When unsure, dry it: no slicer setting compensates. Most sensitive: PVA, BVOH, PA, PC, TPU, Support for PA/PET, PPA/PPS, PEI, PVB, wood fills, PETG.\n\n## Drying table (oven or filament dryer)\n| Material | Temperature | Time | Need |\n|---|---|---|---|\n| PLA basic/matte | 45-50 °C | 6-8 h | only if symptoms |\n| PLA silk, PLA-CF, Support for PLA | 50-55 °C | 8 h | recommended |\n| PLA wood | 55-65 °C | 8 h | required |\n| PVB | 45 °C | 8 h | required |\n| PETG, PETG-CF, PCTG | 55-65 °C | 6-8 h | recommended |\n| TPU | 60-70 °C | 4-8 h | required |\n| PP-CF/GF | 70 °C | 2-4 h | recommended |\n| ABS, ASA, ABS-GF, ASA-CF | 75-85 °C | 4-8 h | recommended |\n| Support for PLA/PETG | 75 °C | 8 h | recommended |\n| Support for ABS / HIPS | 80 °C | 4 h | optional |\n| PC, PC Blend | 75-85 °C | 5-8 h | required |\n| PA, PA-CF/GF, PAHT-CF, PET-CF | 80-85 °C | 8-12 h | required |\n| PVA, Support for PA/PET | 75-85 °C | 8-12 h | required |\n| PPA-CF | 100-140 °C | 8-12 h | required |\n| PPS | 110 °C | ≥ 4 h | required |\n| PEI 1010 | 150 °C | 6-8 h | required |\n\nRules (explain to the user, these are hand actions):\n- Never exceed the spool's heat rating (Bambu low-temp spools ~70 °C, high-temp ~90 °C; old black Prusament spools ~45 °C unless screwed together; new Prusament black 90 °C, grey 150 °C). Too hot fuses the coils.\n- Home ovens drift: check with a separate thermometer.\n- Bambu AMS 2 Pro reaches 65 °C (cannot fully dry ABS/ASA/PC/PA/TPU/PVA); AMS HT and AMS 3H reach 85 °C (not enough for PPA-CF/PPS-CF). Remove PLA/TPU from the AMS before a hot drying cycle.\n- Heated-bed drying (enclosed Bambu printers only): unload the filament, cover the spool with its box, flip every 6 h; roughly 10-15 °C above the oven value, ~12 h.\n- After drying, move the spool straight into a sealed box or AMS with active desiccant (silica beads turning purple = saturated; regenerate at 80-90 °C, never above 100 °C). Keep PVA and similar below 20% RH.\n\n## Plate choice and Orca bed keys\nBed temperature keys are filament keys, one per plate type, each with an _initial_layer twin. Change only the one matching the plate selected in Orca (a value of 0 means the filament does not support that plate). Plugin limit: at most +10 °C over the current value, never above 120 °C.\n| Plate in Orca | Key | Good for |\n|---|---|---|\n| Cool Plate | `cool_plate_temp` | PLA, PVA |\n| Cool Plate SuperTack | `supertack_plate_temp` | PLA, PETG only |\n| Textured Cool Plate | `textured_cool_plate_temp` | follow the filament preset (0 = not supported) |\n| Engineering Plate | `eng_plate_temp` | ABS, ASA, PC, PA, composites (glue); PLA needs glue |\n| High Temp / Smooth PEI | `hot_plate_temp` | PLA without glue; ABS/ASA, PETG, PC, TPU only with a glue layer (it protects the PEI) |\n| Textured PEI | `textured_plate_temp` | PLA, PETG, TPU (no glue); ABS/ASA, PC, PA with glue stick |\n\n- Glue stick: PA, PC, ASA-CF, PA/PAHT/PA6-CF/GF, PET-CF, PPA-CF, PPS-CF; liquid glue suits ABS-GF but is not recommended for PA/PC.\n- Prusa sheets: Special PA Nylon sheet for polyamides (clean with water and dish soap only); PP sheet for polypropylene (clean with ~90% IPA, no acetone); satin or textured for PC Blend, PETG Magnetite and Tungsten; smooth PEI for PVB.\n- Clean plates with dish soap and hot water; no acetone on Bambu plates.\n\n## Hardened nozzle\nRequired for CF/GF, metal powder, glow-in-the-dark and other hard particles; brass and stainless wear fast. Avoid 0.2 mm nozzles with any fill; prefer 0.6 mm for CF/GF. Details in material-composites.\n\n## Sources\n- https://wiki.bambulab.com/en/general/filament-guide-material-table\n- https://wiki.bambulab.com/en/filament-acc/filament/dry-filament\n- https://wiki.bambulab.com/en/knowledge-sharing/desiccant-status\n- https://wiki.bambulab.com/en/filament-acc/filament/h2d-filament-config-limit\n- https://wiki.bambulab.com/en/filament/beginner\n- https://wiki.bambulab.com/en/filament/support\n- https://wiki.bambulab.com/en/filament/petcf_ppacf\n- https://help.prusa3d.com/filament-material-guide\n- https://help.prusa3d.com/article/drying-filament_332086\n- https://help.prusa3d.com/article/special-pa-nylon-steel-sheet_341570\n- https://help.prusa3d.com/article/pp-steel-sheet_815373\n- https://help.prusa3d.com/article/pps-polyphenylene-sulfide_788028\n- https://help.prusa3d.com/article/how-to-print-with-pei-1010_794930\n- https://help.prusa3d.com/article/composite-materials-with-metal-or-wood-particles_166863\n- https://help.prusa3d.com/article/petg-magnetite-40_1078164\n- https://help.prusa3d.com/article/petg-tungsten_1080996\n- https://help.prusa3d.com/article/pvb_196708\n- https://help.prusa3d.com/article/polycarbonate-pc_165812\n- https://www.orcaslicer.com/wiki/material_settings/filament/material_temperatures.html\n",
    },
    "orca-settings-reference": {
        "description": "OrcaSlicer 2.5.1 settings reference - value formats (bool, %, mm-or-%, enums, lists, nil), which preset owns which key, plate temperature keys, filament retraction overrides, and PrusaSlicer / Simplify3D / Cura names translated to Orca keys. Read when the user quotes a setting from another slicer or a video (\"extrusion multiplier\", \"perimeters\", \"fill density\", \"retraction distance\", \"coasting\", \"combing\", \"horizontal expansion\"), when unsure of a key name, unit or allowed values, or when a change has no effect.",
        "content": "# OrcaSlicer settings reference (2.5.1)\n\n## Which preset owns what\n- **Process**: layers, walls, shells, infill, speeds, accelerations, jerk, line widths, per-feature flow ratios (`outer_wall_flow_ratio` etc., need `set_other_flow_ratios` = `1`; BY HAND: Process → Quality → Wall and surfaces → Surface flow ratio), seam, ironing, supports, brim/skirt/raft, XY compensation, prime tower.\n- **Filament**: nozzle and plate temperatures, fans and layer-time slowdown, `filament_flow_ratio`, pressure advance, `filament_max_volumetric_speed`, retraction / z-hop / wipe overrides, ironing overrides.\n- **Printer** (read-only for the plugin): nozzle, default retraction and z-hop, Z offset, layer height and machine limits, firmware.\n- Per-object / modifier settings override the process preset: if a change has no effect, ask the user to check them.\n\n## Value formats\n- Boolean: `1` / `0`.\n- Integer, float: plain number without unit (`0.2`, `45`); the unit is fixed per key.\n- Percentage: write the `%` (`15%`).\n- Float-or-percent (mm or %): a number is absolute, a `%` is relative to a base that differs per key:\n  - line widths (`line_width`, `outer_wall_line_width`, `initial_layer_line_width`...): % of nozzle diameter; 0 = use `line_width`.\n  - `small_perimeter_speed`: % of `outer_wall_speed`. `internal_bridge_speed`: % of `bridge_speed`. Overhang speeds `overhang_1_4_speed`...`overhang_4_4_speed`: mm/s or %.\n  - `sparse_infill_acceleration`, `internal_solid_infill_acceleration`: % of `default_acceleration`. `bridge_acceleration`: % of `outer_wall_acceleration`. `initial_layer_travel_jerk`: % of `travel_jerk`.\n  - `wipe_speed`: % of `travel_speed`. `seam_gap`: % of nozzle diameter. `infill_anchor`: % of infill width. `infill_wall_overlap` (percent only): % of inner wall width, 10-15 % recommended.\n- Enum: the internal value below, not the GUI label.\n- Lists: filament keys hold one value per filament; on multi-nozzle printers (H2D, H2C, X2D) many keys hold one value per nozzle or nozzle variant. Keep the entry count; change the entry in use.\n- `nil` in a filament override = use the printer value.\n- Special values: `top_shell_thickness` / `bottom_shell_thickness` 0 = off; `skirt_loops` 0 = no skirt; `adaptive_pressure_advance_bridges` 0 = off; `filament_ramming_volumetric_speed` -1 = use max volumetric speed.\n\n## Enum values (internal)\n| Key (preset) | Values |\n|---|---|\n| `seam_position` (process) | `nearest`, `aligned`, `aligned_back`, `back`, `random` |\n| `seam_slope_type` (process) | `none`, `external`, `all` (scarf seam) |\n| `wall_sequence` (process) | `inner wall/outer wall`, `outer wall/inner wall`, `inner-outer-inner wall` |\n| `wall_generator` (process) | `classic`, `arachne` |\n| `top_surface_pattern`, `bottom_surface_pattern`, `internal_solid_infill_pattern` (process) | `monotonic`, `monotonicline`, `rectilinear`, `alignedrectilinear`, `concentric`, `spiralinset`, `hilbertcurve`, `archimedeanchords`, `octagramspiral` |\n| `sparse_infill_pattern` (process) | `rectilinear`, `alignedrectilinear`, `zigzag`, `crosszag`, `lockedzag`, `line`, `grid`, `triangles`, `tri-hexagon`, `cubic`, `adaptivecubic`, `quartercubic`, `supportcubic`, `lightning`, `honeycomb`, `3dhoneycomb`, `lateral-honeycomb`, `lateral-lattice`, `crosshatch`, `tpmsd`, `tpmsfk`, `gyroid`, `concentric`, `hilbertcurve`, `archimedeanchords`, `octagramspiral` |\n| `support_type` (process) | `normal(auto)`, `tree(auto)`, `normal(manual)`, `tree(manual)` |\n| `support_style` (process) | `default`, `grid`, `snug`, `organic`, `tree_slim`, `tree_strong`, `tree_hybrid` |\n| `brim_type` (process) | `auto_brim`, brim_ears, `painted`, `outer_only`, `inner_only`, `outer_and_inner`, `no_brim`, `leading_edge_only` |\n| `ironing_type` (process) | `no ironing`, `top`, `topmost`, `solid` |\n| `gap_fill_target` (process) | `everywhere`, `topbottom`, `nowhere` |\n| `ensure_vertical_shell_thickness` (process) | `none`, `ensure_critical_only`, `ensure_moderate`, `ensure_all` |\n| `print_sequence` (process) | `by layer`, `by object` |\n| `filament_z_hop_types` (filament) | `Auto Lift`, `Normal Lift`, `Slope Lift`, `Spiral Lift` |\n| `filament_retract_lift_enforce` (filament) | `All Surfaces`, `Top Only`, `Bottom Only`, `Top and Bottom` |\n| `overhang_fan_threshold` (filament) | `0%`, `10%`, `25%`, `50%`, `75%`, `95%` |\n\n## Plate temperature keys (filament)\nChange only the pair for the plate in use (max +10 °C per change, never above 120 °C):\n| Plate (Orca bed type) | Other layers | First layer |\n|---|---|---|\n| Smooth Cool Plate | `cool_plate_temp` | `cool_plate_temp_initial_layer` |\n| Textured Cool Plate | `textured_cool_plate_temp` | `textured_cool_plate_temp_initial_layer` |\n| Smooth High Temp Plate (smooth PEI) | `hot_plate_temp` | `hot_plate_temp_initial_layer` |\n| Textured PEI Plate | `textured_plate_temp` | `textured_plate_temp_initial_layer` |\n| Engineering Plate | `eng_plate_temp` | `eng_plate_temp_initial_layer` |\n| Cool Plate (SuperTack) | `supertack_plate_temp` | `supertack_plate_temp_initial_layer` |\n- Bambu printers and printers with \"Support multi bed types\" let the user pick the plate; others (most Prusa profiles) use the profile default (Textured PEI on Prusa MMU3/INDX). If unsure, ask which plate is selected.\n\n## Filament overrides of printer settings\n`filament_retraction_length`, `filament_retraction_speed`, `filament_deretraction_speed`, `filament_retraction_minimum_travel`, `filament_retract_when_changing_layer`, `filament_retract_before_wipe`, `filament_retract_after_wipe`, `filament_retract_restart_extra` (BY HAND), `filament_wipe`, `filament_wipe_distance`, `filament_z_hop`, `filament_z_hop_types`, `filament_retract_lift_above`, `filament_retract_lift_below`, `filament_retract_lift_enforce`, `filament_long_retractions_when_cut`, `filament_retraction_distances_when_cut`, `filament_retract_length_toolchange`.\nIroning overrides: `filament_ironing_flow`, `filament_ironing_spacing`, `filament_ironing_speed`, `filament_ironing_inset`.\nPlugin limits: length 0..min(8, max(2, 2 × printer value)) mm; (de)retraction speed ≤ max(1.5 × printer value, 30 mm/s); z-hop 0-2 mm.\n\n## Names from other slicers → Orca key\nCura names: for recognition only.\n| PrusaSlicer | Simplify3D | Cura | Orca key (preset) |\n|---|---|---|---|\n| Extrusion multiplier | Extrusion Multiplier | Flow | `filament_flow_ratio` (filament) |\n| Perimeters | - | Wall Line Count | `wall_loops` (process) |\n| Solid layers top / bottom | Top / Bottom Solid Layers | Top / Bottom Layers | `top_shell_layers` / `bottom_shell_layers` (process) |\n| Fill density / Fill pattern | Infill Percentage | Infill Density / Pattern | `sparse_infill_density` / `sparse_infill_pattern` (process) |\n| First layer height | - | Initial Layer Height | `initial_layer_print_height` (process) |\n| Extrusion width | Extrusion Width | Line Width | `line_width` and per-feature widths (process) |\n| Infill/perimeters overlap | Outline Overlap | Infill Overlap | `infill_wall_overlap` (process) |\n| Retraction length | Retraction Distance | Retraction Distance | `filament_retraction_length` (filament) |\n| Retraction speed | Retraction Speed | Retraction Speed | `filament_retraction_speed` (filament) |\n| Lift Z | Retraction Vertical Lift | Z Hop When Retracted | `filament_z_hop` (filament) |\n| Extra length on restart | Extra restart distance | Retraction Extra Prime Amount | `filament_retract_restart_extra` (filament) — BY HAND: Filament → Setting overrides → Retraction |\n| Minimum travel after retraction | Minimum travel for retraction | Retraction Minimum Travel | `filament_retraction_minimum_travel` (filament) |\n| Wipe while retracting | Wipe Nozzle | - | `filament_wipe`, `filament_wipe_distance` (filament) |\n| Only retract when crossing perimeters | Only retract when crossing open spaces | Combing (partly) | `reduce_infill_retraction` (process) |\n| Avoid crossing perimeters | Avoid crossing outline for travel movement | Combing Mode | `reduce_crossing_wall` (process) |\n| - | Coasting | Coasting | none; use PA and retraction |\n| Temperature / First layer | - | Printing Temperature / Initial Layer | `nozzle_temperature` / `nozzle_temperature_initial_layer` (filament) |\n| XY Size Compensation | Horizontal size compensation | Horizontal Expansion | `xy_contour_compensation` (process) |\n| - | - | Hole Horizontal Expansion | `xy_hole_compensation` (process) |\n| Elephant foot compensation | - | Initial Layer Horizontal Expansion (negative) | `elefant_foot_compensation` (process, positive mm) |\n| Seam position (rear = `back`) | - | Z Seam Alignment | `seam_position` (process) |\n| External perimeters first | - | Wall Ordering | `wall_sequence` (process) |\n| Bridge flow ratio | Bridging extrusion multiplier | Bridge Skin Flow | `bridge_flow` (process) — BY HAND: Process → Quality → Bridging → Flow ratio |\n| Slow down if layer print time is below | - | Minimum Layer Time | `slow_down_layer_time` (filament) |\n| Disable fan for the first N layers | - | Initial Fan Speed | `close_fan_the_first_x_layers` (filament) |\n| Contact Z distance | Upper Vertical Separation | Support Top Distance | `support_top_z_distance` (process) |\n| Interface layers | Dense Support | Support Interface | `support_interface_top_layers` (process) |\n| Skirt loops / distance / height | - | Skirt Line Count / Distance | `skirt_loops` / `skirt_distance` / `skirt_height` (process) |\nSpeeds (process): perimeters `inner_wall_speed`, external perimeters `outer_wall_speed`, infill `sparse_infill_speed`, solid infill `internal_solid_infill_speed`, top solid `top_surface_speed`, gap fill `gap_infill_speed`, first layer `initial_layer_speed`, travel / S3D X/Y Axis Movement Speed `travel_speed`.\n\n## Checks the user must do by hand (printer settings, never changed by the plugin)\nPrinter settings tab: `retraction_length`, `retraction_speed`, `z_hop` (override them in the filament instead), `z_offset`, `nozzle_diameter`, `nozzle_type`, layer height limits, machine limits (`machine_max_speed_x`, `machine_max_acceleration_extruding`, `machine_max_jerk_x` ...), input shaping, `resonance_avoidance`, firmware flavour, `extruder_type`. Process speeds/accel/jerk ≤ machine limits.\n\n## Sources\n- https://www.orcaslicer.com/wiki/general_settings/option_type.html\n- https://www.orcaslicer.com/wiki/material_settings/setting%20overrides/material_setting_overrides.html\n- https://www.orcaslicer.com/wiki/material_settings/filament/material_temperatures.html\n- https://www.orcaslicer.com/wiki/printer_settings/basic%20information/printer_basic_information_printable_space.html\n- https://help.prusa3d.com/article/layers-and-perimeters_1748\n- https://help.prusa3d.com/article/stringing-and-oozing_1805\n- https://help.prusa3d.com/article/infill_42\n- https://help.prusa3d.com/article/cooling_127569\n- https://help.prusa3d.com/article/poor-bridging_1802\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/stringing-or-oozing/\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/blobs-and-zits/\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/dimensional-accuracy/\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/poor-surface-above-supports/\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/gaps-between-infill-and-outline/\n- https://www.simplify3d.com/resources/print-quality-troubleshooting/gaps-in-top-layers/\n",
    },
    "printers-bambu": {
        "description": "Bambu Lab printers (X1C, X1E, P1P, P1S, P2S, A1, A1 mini, H2D, H2S, H2C, plus X2D/A2L/H2D Pro profiles) and AMS / AMS 2 Pro / AMS HT / AMS lite - kinematics, enclosure and chamber heating, hotend and bed limits, nozzle options, dual-nozzle rules and Orca profile limits that change print advice. Read when the user has a Bambu Lab printer or AMS, or mentions X1, P1, P2S, A1, H2D, H2S, H2C, Bambu plates, flow dynamics / K value, hardened or high-flow nozzle, left/right nozzle.",
        "content": "# Bambu Lab printers: differences that change advice\n\n## Overview (Orca 2.5.1 profiles, 0.4 mm nozzle, plus Bambu wiki)\n| Model | Motion | Enclosure / chamber | Build volume (mm) | Hotend max | Bed max | Profile limits: XY speed, accel |\n|---|---|---|---|---|---|---|\n| X1C | CoreXY | enclosed, no heater; exhaust fan, filter, aux fan | 256×256×250 | 320 °C | 110 °C | 500 mm/s, 20000 mm/s² |\n| X1E | CoreXY | enclosed, **active heater up to 60 °C**, HEPA + carbon | 256×256×250 | - | - | 500, 20000 |\n| P1P | CoreXY | **open frame**, no aux fan | 256×256×250 | 320 °C | 100 °C | 500, 20000 |\n| P1S | CoreXY | enclosed, no heater; aux fan, filter | 256×256×250 | 320 °C | 100 °C | 500, 20000 |\n| P2S | CoreXY | enclosed, no heater; adaptive airflow (draws outside air for PLA, recirculates through filter for hot materials) | 256×256×256 | 300 °C | 110 °C | 1000, 20000 |\n| A1 | bed-slinger (Cartesian) | **open** | 256×256×256 | - | 100 °C | 500, 12000 |\n| A1 mini | bed-slinger | **open** | 180×180×180 | - | **80 °C** | 500, 20000 |\n| H2D | CoreXY, **two nozzles** (left lifts) | enclosed, **active PTC heater** (H2D Pro: 65 °C max) | 350×320×325 | 350 °C | 120 °C | 1000, 20000 |\n| H2S | CoreXY, one nozzle | enclosed, active PTC heater | 340×320×340 | 350 °C | 120 °C | 1000, 20000 |\n| H2C | CoreXY, left nozzle + right Vortek induction hotend changer (rack of 6) | enclosed, active PTC heater | 330×320×325 | 350 °C | - | 1000, 20000 |\n- All are direct drive. Orca also ships X2D (dual nozzle, second extruder Bowden: printer retraction 2 mm at 20 mm/s), A2L (bed-slinger 330×320×325, 12000 mm/s²) and H2D Pro profiles.\n- Travel acceleration in the profiles is 9000 mm/s² (P2S 10000). Never set process speeds, accelerations or jerk above these machine limits.\n- Printer retraction in profiles: 0.8 mm at 30 mm/s for 0.4 nozzles; 0.2 → 0.4 mm, 0.6 → 1.4 mm, 0.8 → 3 mm (A1 keeps 0.8 mm for every nozzle). Printer z-hop 0.4 mm.\n- Layer height limits in profiles: 0.2 nozzle 0.04-0.14, 0.4: 0.08-0.28, 0.6: 0.12-0.42, 0.8: 0.16-0.56 mm. Keep `layer_height` (process) within the printer maximum even where the plugin's 75 % rule would allow more.\n\n## How the machine type changes advice\n- **Bed-slingers (A1, A1 mini, A2L)**: the bed moves in Y, so tall thin or heavy parts wobble and ring more; prefer lower `outer_wall_acceleration` and `default_acceleration` (process) for tall parts, brim for narrow bases. Open frame: ABS/ASA/PC/PA warp and crack from drafts; suggest `draft_shield` (process) = `enabled` and a brim, but recommend an enclosed printer for large parts.\n- **A1 mini bed max 80 °C**, A1/P1 100 °C: never propose plate temperatures above the printer's bed maximum even if the plugin cap (120 °C) allows it.\n- **Enclosed without heater (X1C, P1S, P2S)**: good for ABS/ASA; for PLA, PETG and TPU heat builds up and causes heat creep and soft, clogging filament. Hardware advice: open the front door and remove or lift the top glass when the bed is at or above the filament's softening point (about 45 °C PLA, 70 °C PETG).\n- **Heated chamber (X1E, H2D, H2S, H2C)**: chamber heating is only for ABS/ASA (optional), PC, PA, PA-CF, PET-CF, PPA, PPS. The plugin never changes chamber settings; if relevant, tell the user. PLA, PETG, TPU, PVA, BVOH, PCTG, PLA-CF and PETG-CF must not see a chamber above about 45 °C. H2C classifies third-party filaments with heat deflection below 80 °C (ISO 75, 1.8 MPa) as low-temperature. High- and low-temperature filaments cannot share one print.\n- **P1P** is open and has no auxiliary fan: same draft advice as bed-slingers for warping materials; for PLA bridges and overhangs rely on `overhang_fan_speed` and `fan_max_speed` (filament).\n\n## Nozzles and hotends\n- Sizes 0.2 / 0.4 / 0.6 / 0.8 mm. Stock: X1C 0.4 hardened steel; P1P/P1S and A series 0.4 stainless steel (hardened optional). Stainless is fine for PLA, PETG, ABS, ASA, TPU, PVA; abrasive filaments (CF, GF, glow-in-the-dark, wood, metal) need hardened steel or tungsten carbide.\n- 0.2 mm nozzles are stainless and not abrasion resistant; avoid CF/GF, glow, sparkle and galaxy filaments (particles clog). Use about 2 mm³/s for `filament_max_volumetric_speed` (filament); layers are weaker than with 0.4/0.6.\n- High-flow hotends (H2 series / P2S / X2D) raise the maximum flow considerably; the E3D High Flow ObXidian hotend for X1C/P1 adds about 60 % flow but is limited to 300 °C. Tungsten carbide nozzles (H2D, H2S, H2C left, P2S, X2D) resist abrasion best, 350 °C max.\n- H2D TPU high-flow hotend: right side only, flexible filaments only (hard filaments damage its coating), no cutter and no AMS feeding on that side.\n- H2C Vortek induction hotends (right side, 0.2-0.8 mm, hardened or stainless) heat in about 8 s, which cuts colour-change time and purge waste.\n- Orca printer variants list the hotend type (Standard, High Flow, E3D High Flow, TPU High Flow): the selected printer preset must match the installed hotend, otherwise flow limits in the filament profiles are wrong.\n\n## Dual-nozzle rules (H2D, H2C; X2D similar)\n- TPU only on the right nozzle (H2D: higher clog risk on the left; H2C left does not support TPU 85A yet).\n- PPS-CF and PPA-CF (H2C also PET-CF) only on the left nozzle: the right filament path bends sharply at homing and brittle filament snaps.\n- H2C: never PVA on one hotend and PETG on the other at the same time (PETG bed heat softens PVA, clogs). PVA with a 0.2 mm standard hotend is not supported.\n- Soft + hard multi-material: hard filament on the left, TPU on the right.\n- For two-colour prints use both nozzles: switching nozzles avoids AMS unload/reload and is faster.\n\n## AMS family\n- AMS (1st gen), AMS 2 Pro (drying), AMS HT (single spool, drying up to 85 °C, needs its own power for drying): X1/P1 need a filament buffer (one unit) or AMS hub (several), up to 4 units; P2S up to 4 AMS 2 Pro + 4 AMS HT; H2 series up to 4 AMS 2 Pro + 8 AMS HT with built-in buffer; A1 up to 4 via the A1 AMS hub.\n- AMS lite: A series only, one unit, 4 slots, single-stage feed; long or sharply bent PTFE tubes cause feed failures (max feed length 1.2 m).\n- Soft TPU cannot be fed automatically by an AMS (Bambu's \"TPU for AMS\" is the exception). AMS HT has a dedicated TPU outlet: feed manually; it still works as a dry box.\n- Purge, prime tower and colour bleed: see defect-multimaterial.\n\n## Plates (Orca bed type → filament keys)\n- Textured PEI (stock): `textured_plate_temp` / `textured_plate_temp_initial_layer`; PLA, PETG, TPU without glue, glue may be needed for PC, PA, ABS, ASA.\n- Smooth PEI / High Temp Plate: `hot_plate_temp` pair; only PLA without glue, use glue for everything else to protect the sheet.\n- Engineering Plate: `eng_plate_temp` pair; always with glue. Cool Plate: `cool_plate_temp` pair. Cool Plate SuperTack: `supertack_plate_temp` pair.\n- Remove parts once the plate is at about 35 °C or less. Second-generation plates are auto-detected only on P2S/X2D.\n\n## Calibration differences\n- Flow Dynamics (K): automatic on X1 (lidar lines), A1, H2 and P2S (eddy sensor at the purge wiper); P1 manual only. H2 series offer Auto / On / Off before each print; Off uses the stored K profile for that slot. With `enable_pressure_advance` (filament) = `1` the Orca filament value overrides the printer. Eddy-sensor auto K reads higher than manual by design; third-party hotends make A1/H2D auto K inaccurate. See calibration-guide.\n- Automatic flow rate (lidar) exists only on X1.\n\n## Checks the user must do by hand (hardware, printer settings)\n- Select the printer preset that matches nozzle size and hotend type; printer settings `nozzle_diameter`, `retraction_length`, `z_hop` and machine limits are changed only by the user. Use filament overrides (`filament_retraction_length`, `filament_z_hop`) for per-material changes.\n- Rerun the printer's automatic calibration (vibration compensation, bed levelling, motor noise) after moving the printer, firmware updates, belt work or part replacement, or when quality suddenly drops.\n- Keep the silicone sock fitted (P2S warns when missing), clean the nozzle wiper and purge chute, check PTFE routing to the AMS, and keep the build plate clean and grease-free.\n\n## Sources\n- https://github.com/OrcaSlicer/OrcaSlicer/tree/v2.5.1/resources/profiles/BBL/machine\n- https://wiki.bambulab.com/en/x1/manual/intro-x1\n- https://wiki.bambulab.com/en/x1/manual/x1e-faq\n- https://wiki.bambulab.com/en/x1/manual/X1E-chamber-temp-guide\n- https://wiki.bambulab.com/en/p1/manual/intro-p1p\n- https://wiki.bambulab.com/en/a1/manual/intro-a1\n- https://wiki.bambulab.com/en/a1-mini/manual/intro-a1-mini\n- https://wiki.bambulab.com/en/h2/manual/h2d-intro\n- https://wiki.bambulab.com/en/h2/manual/h2d-pro-faq\n- https://wiki.bambulab.com/en/h2s/manual/h2s-intro\n- https://wiki.bambulab.com/en/h2c/manual/h2c-intro\n- https://wiki.bambulab.com/en/h2c/manual/induction-hotend-system-workflow\n- https://wiki.bambulab.com/en/p2s/manual/p2s-intro\n- https://wiki.bambulab.com/en/h2/h2d-filament-printing-guide\n- https://wiki.bambulab.com/en/h2c/h2c-filament-printing-guide\n- https://wiki.bambulab.com/en/filament-acc/acc/nozzles\n- https://wiki.bambulab.com/en/filament-acc/acc/plates\n- https://wiki.bambulab.com/en/knowledge-sharing/02-mm-nozzle-FAQ\n- https://wiki.bambulab.com/en/ams/manual/multi-model-AMS-compatibility-guide\n- https://wiki.bambulab.com/en/ams-lite/manual/intro-ams-lite\n- https://wiki.bambulab.com/en/ams-ht/manual/intro-and-connection-guide\n- https://wiki.bambulab.com/en/software/bambu-studio/calibration_pa\n- https://wiki.bambulab.com/en/general/printer-calibration\n",
    },
    "printers-prusa": {
        "description": "Prusa printers (MK4/MK4S, MK3.9, CORE One / CORE One+, CORE One L, XL single and multi-tool, MINI/MINI+, MK3.5/S) and MMU3 / INDX - kinematics, enclosure, extruder type, LoadCell vs Live Z, nozzle system and options, HF profiles and Orca profile limits that change print advice. Read when the user has a Prusa printer or mentions Nextruder, LoadCell, Live Z, CHT or ObXidian nozzle, HF profile, MMU3, INDX, XL toolchanger, CORE One chamber or ventilation grille, Prusa steel sheet.",
        "content": "# Prusa printers: differences that change advice\n\n## Overview (Orca 2.5.1 profiles, 0.4 nozzle; Prusa KB)\n| Model | Motion | Enclosure | Extruder / nozzle system | Build volume (mm) | Profile limits: XY speed, accel (normal / stealth) |\n|---|---|---|---|---|---|\n| MK4 / MK3.9 | Cartesian bed-slinger | open (optional Original Prusa Enclosure) | Nextruder direct drive, LoadCell, Prusa Nozzle | 250×210×220 | 300 / 200 mm/s, 4000 mm/s² |\n| MK4S / MK3.9S | bed-slinger | open (optional enclosure) | Nextruder, LoadCell | 250×210×220 | 300 / 160, 4000 / 2500 |\n| CORE One / CORE One+ | CoreXY | **enclosed**: door, top ventilation grilles, chamber fans, optional HEPA | Nextruder, LoadCell, stock CHT 0.4 nozzle | 250×220×270 | 350 / 160; 10000 (X/Y), 7000 extruding |\n| CORE One L | CoreXY | **enclosed**, chamber temperature item in the menu, integrated accelerometer | Nextruder, LoadCell | 300×300×331 | 350 / 160; 10000, 7000 extruding, 6000 travel |\n| XL (1, 2 or 5 heads) | CoreXY | open (optional enclosure with HEPA) | Nextruder toolchanger heads, LoadCell, integrated accelerometer | 360×360×360 | 400 mm/s; 7000 X/Y, 4000 extruding, 5000 travel |\n| MK3.5 / MK3.5S | bed-slinger | open | direct drive with E3D V6 hotend, no LoadCell | 250×210×210 | 300 mm/s, 4000 |\n| MINI / MINI+ | bed-slinger | open | **Bowden**, E3D V6 hotend, no LoadCell | 180×180×180 | MINI profile 180 mm/s, 1250 extruding; MINI IS profile 400 mm/s, 4000 |\n- None of these has an active chamber heater in the sources read; the CORE One family warms its chamber with the bed and controls it with fans and grilles. The plugin never touches chamber settings.\n- Printer retraction in profiles (0.4 nozzle): MK4S, MK4 MMU3, CORE One family 0.7 mm (MK4S 35 mm/s, CORE One 45 mm/s) with 0.2 mm z-hop (Slope Lift on MK4S and CORE One); MK4, XL, MK3.5 0.8 mm at 30-35 mm/s; MINI 3.2 mm at 70 mm/s (MINI IS 2.5-2.8 mm) because of the Bowden tube; 0.8 nozzles use 0.6 mm and lower retraction speeds on MK4S, CORE One and XL.\n- Layer height limits (0.4 nozzle): 0.07-0.30 mm on MK4S, CORE One/L and XL (MK4 MMU3: 0.25 max), 0.08-0.30 on MK4, MK3.5 and MINI. Keep `layer_height` (process) within the printer maximum.\n- Profile variants matter: \"HF\" printer presets (MK4S HF, CORE One HF, CORE One L HF) are for high-flow nozzles (CHT / E3D High Flow) and allow higher flow; the plain CORE One preset in Orca inherits from CORE One HF, and the CORE One ships with a CHT 0.4 nozzle. MMU3, INDX 4T/8T and XL 5T are separate printer presets.\n\n## How the machine type changes advice\n- **Bed-slingers (MK4/S, MK3.9/S, MK3.5, MINI)**: tall thin or heavy parts wobble and ring; lower `outer_wall_acceleration` / `default_acceleration` (process) for tall parts and add a brim for narrow bases. Open frame: ABS, ASA, PC, PA warp; suggest `draft_shield` (process) = `enabled` plus brim, or an enclosure for large parts.\n- **CORE One family (enclosed)**: open the top ventilation grilles for PLA and PETG; a closed, warm chamber causes heat creep and under-extrusion with PLA. With high-flow nozzles in a closed chamber Prusa suggests opening the grille (or the door on other enclosures). For ABS, ASA and PC keep the chamber closed to hold heat.\n- **Original Prusa Enclosure on MK/MINI**: with the doors closed and room temperature above about 27 °C the inside can get too hot for PLA (under-extrusion, clogs). Advise opening it.\n- **MINI (Bowden)**: needs longer retraction and the Bowden version of the PA test. Soft filament can be hard to push through the PTFE tube on XL and CORE One (see material-tpu).\n- **XL multi-tool**: idle tools ooze; the purge (wipe) tower is on by default when mixing materials. Turning `enable_prime_tower` (process) off works only with well-dried filament. `ooze_prevention` (process) = `1` cools idle tools; its temperature values are blocked by the plugin, so the user sets them BY HAND: `standby_temperature_delta` at Process → Multimaterial → Ooze prevention → Temperature variation, or `idle_temperature` at Filament → Basic information → Idle temperature. After a nozzle change the user must run tool offset calibration.\n- **Pressure advance**: Prusa firmware takes PA from an M572 command (old M900 K values are converted 1:1). PrusaSlicer's default start G-code sets it; the Orca 2.5.1 Prusa machine profiles only reset it, so the value comes from the filament preset (`enable_pressure_advance`, `pressure_advance`); see calibration-guide.\n- **Input shaper** is standard on all current models (crash detection is not used with it). Phase stepping (XL, CORE One/L) reduces VFA but disables crash detection on the XL.\n\n## Nozzles\n- Nextruder printers (MK4/S, MK3.9/S, CORE One/L, XL) use the Prusa Nozzle: heatbreak integrated, cold tool-free swap. MK3.5, MINI and older use E3D V6 nozzles, which must be tightened hot. A Nextruder V6 adapter lets Nextruder printers take V6 nozzles.\n- Options: brass (stock, non-abrasive only); brass CHT and E3D High Flow brass (split melt channels, more flow, can print a bit cooler, need HF profiles); ObXidian (hardened, coated: for CF and other abrasives; no cold pulls, no needles or brass brushes); hardened nickel-plated; High Flow ObXidian; ObXiDian 500 (standard and HF); DiamondBack (diamond tip, most wear resistant).\n- With the MMU3 use the standard Prusa Nozzle, not CHT: CHT holds more material and needs much larger purge volumes, or colours bleed.\n- Diameter rules (Prusa): 0.25 mm: no composites (CF, GF, Kevlar, wood/metal fill), no flexibles, no PVA/BVOH; very long print times. ≥0.6 mm: stronger parts, less detail, more warping for ASA/PC. Metal-filled: hardened nozzle; wood-filled and large-particle composites: at least 0.6 mm.\n\n## Multi-material\n- **MMU3**: one nozzle, up to five filaments, purge tower required. Works with MK3S+, MK3.5/S, MK3.9/S, MK4/S and CORE One (CORE One L as a community mod). Printer and MMU firmware must match; MMU3 G-code for MK4/CORE is not interchangeable with older MMU profiles. Select the MMU3 printer preset in Orca.\n- **INDX** (CORE One toolchanger, 4 or 8 tools) and **XL 5T** are true multi-tool printers: ooze and idle temperature matter more than purge volume. See defect-multimaterial.\n\n## Plates and bed temperature keys\n- Most Prusa Orca profiles do not enable multiple bed types: the filament's bed temperature comes from one global plate type. The MK4 MMU3 and CORE One INDX profiles default to Textured PEI (`textured_plate_temp` pair); otherwise check with the user which plate type Orca shows before changing a plate key (see orca-settings-reference).\n- Prusa steel sheets (smooth, textured, satin, special PA) differ in thickness. On LoadCell printers the first layer is calibrated automatically and Live Z resets after each print; on MK3.5 and MINI every sheet needs its own Live Z value (steel sheet profiles).\n\n## Checks the user must do by hand (hardware, printer settings)\n- In the printer menu (Settings → Hardware) nozzle diameter, \"hardened\", \"high-flow\" and the Nextruder silicone sock option must match the installed parts; G-code checks warn when the sliced profile does not match.\n- Select the Orca printer preset that matches nozzle size, HF nozzle, MMU3 or toolchanger. Printer settings `nozzle_diameter`, `retraction_length`, `retraction_speed`, `z_hop` and machine limits are changed only by the user; per-material retraction goes into filament overrides (`filament_retraction_length`, filament).\n- Before input shaper / phase stepping: tight belts, healthy nozzle, clean rods. A failed phase stepping calibration usually means wrong belt tension. CORE One needs the accessory accelerometer for phase stepping; CORE One L and XL have one built in.\n- MK3.5 / MINI: run first layer calibration and set Live Z per sheet. Fit the silicone sock (and enable it in the menu) for high-temperature filaments and to keep the heater block clean.\n\n## Sources\n- https://github.com/OrcaSlicer/OrcaSlicer/tree/v2.5.1/resources/profiles/Prusa/machine\n- https://help.prusa3d.com/article/types-of-printers-and-their-differences_112464\n- https://help.prusa3d.com/article/core-one-glossary_980046\n- https://help.prusa3d.com/article/lcd-menu-core-one-l_970140\n- https://help.prusa3d.com/article/lcd-menu-core-one_829752\n- https://help.prusa3d.com/article/advanced-filtration-system-for-prusa-core-one_887189\n- https://help.prusa3d.com/article/prusa-printer-upgrades_796284\n- https://help.prusa3d.com/article/core-one-upgrade-paths_1253002\n- https://help.prusa3d.com/article/input-shaper-core-one-mk4-s-mk3-9-s-mk3-5-s-xl-mini_451816\n- https://help.prusa3d.com/article/phase-stepping-core-one-l-core-one_914247\n- https://help.prusa3d.com/article/phase-stepping-xl_681760\n- https://help.prusa3d.com/article/pressure-advance_814986\n- https://help.prusa3d.com/article/prusa-nozzle-types-for-nextruder-printers_928993\n- https://help.prusa3d.com/article/different-nozzle-types_2193\n- https://help.prusa3d.com/article/mmu3-compatibility_470808\n- https://help.prusa3d.com/article/mmu3-prusa-nozzle-vs-cht-nozzle_779168\n- https://help.prusa3d.com/article/printing-without-purge-tower-on-the-xl-multi-tool_649633\n- https://help.prusa3d.com/article/nextruder-silicone-sock-core-one-core-one-l-xl-mk4-s-mk3-9-s_641415\n- https://help.prusa3d.com/article/under-extrusion-nextruder-printers_821253\n- https://help.prusa3d.com/article/clogged-nozzle-core-one-core-one-l-xl-mk4-s-mk3-9-s_411823\n- https://help.prusa3d.com/article/composite-materials-with-metal-or-wood-particles_166863\n- https://help.prusa3d.com/article/mutliple-extruders-settings-interlocking-advanced-bonding_867124\n- https://help.prusa3d.com/article/experimental-printing-with-different-nozzle-diameters_821176\n- https://help.prusa3d.com/article/e3d-v6-nozzles_920168\n- https://help.prusa3d.com/article/flexible-steel-sheets-guidepost_2195\n- https://help.prusa3d.com/article/stringing-and-oozing_1805\n- https://help.prusa3d.com/article/prusament-tpu-95a-material-guide_899653\n",
    },
}
# <<< SKILL INCORPORATE


def parse_skill_text(text, fallback_name):
    name, desc, body = fallback_name, "", text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if m:
        body = m.group(2)
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                k, v = k.strip().lower(), v.strip().strip('"').strip("'")
                if k == "name" and v:
                    name = v
                elif k == "description":
                    desc = v
    if not desc:
        first = next((l.strip("# ").strip() for l in body.splitlines() if l.strip()), "")
        desc = first[:200]
    return name, desc, body


def load_skills(folder):
    skills = {k: dict(v, source="builtin") for k, v in BUILTIN_SKILLS.items()}
    if not folder or not os.path.isdir(folder):
        return skills
    for entry in sorted(os.listdir(folder)):
        if entry.startswith(("_", ".")):          # appunti e file nascosti (es. _fonti.md) non sono skill
            continue
        path = os.path.join(folder, entry)
        target = None
        if os.path.isdir(path) and os.path.isfile(os.path.join(path, "SKILL.md")):
            target = os.path.join(path, "SKILL.md")
        elif entry.lower().endswith(".md") and os.path.isfile(path):
            target = path
        if not target:
            continue
        try:
            with open(target, "r", encoding="utf-8") as fh:
                text = fh.read()
            name, desc, body = parse_skill_text(text, os.path.splitext(entry)[0])
            skills[name] = {"description": desc, "content": body[:60000], "source": target}
        except Exception as exc:
            log("skill non letta", target, repr(exc))
    return skills


# ---------------------------------------------------------------- strumenti --

TOOLS = [
    {
        "name": "get_settings",
        "description": "Read the current values of OrcaSlicer settings by exact key (process, filament or printer preset). Use it before proposing any change. Each key comes with \"changeable\": when it is false the plugin cannot change that setting (never propose it: the user changes it by hand in Orca).",
        "parameters": {"type": "object", "properties": {
            "keys": {"type": "array", "items": {"type": "string"}, "description": "Exact OrcaSlicer keys, e.g. [\"outer_wall_speed\", \"nozzle_temperature\"]"}},
            "required": ["keys"]},
    },
    {
        "name": "search_settings",
        "description": "Find OrcaSlicer setting keys whose name contains the given words (e.g. \"retraction\", \"support top\", \"bridge\"). Returns keys, preset, current values and \"changeable\" (false = the plugin cannot change it: never propose it, the user changes it by hand in Orca).",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "One or more words, matched against key names"}},
            "required": ["query"]},
    },
    {
        "name": "get_plate",
        "description": "List the objects on the build plate with size (mm), copies, scale, triangles and volume.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "read_skill",
        "description": "Read the full text of one of the available skills (troubleshooting guides and references).",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": "Skill name from the list in the instructions"}},
            "required": ["name"]},
    },
    {
        "name": "propose_changes",
        "description": "Propose setting changes to the user. They are shown with an Apply button; nothing changes until the user applies them. Only process and filament settings can be changed. Calling it again replaces the previous proposal.",
        "parameters": {"type": "object", "properties": {
            "summary": {"type": "string", "description": "One sentence: what the changes fix"},
            "changes": {"type": "array", "items": {"type": "object", "properties": {
                "preset": {"type": "string", "enum": ["process", "filament"]},
                "key": {"type": "string", "description": "Exact OrcaSlicer key"},
                "value": {"type": "string", "description": "New value in the same format as the current value"},
                "label": {"type": "string", "description": "Short human name of the setting in the user's language, e.g. \"Nozzle temperature\""},
                "reason": {"type": "string", "description": "Short reason shown to the user, in the user's language"}},
                "required": ["preset", "key", "value", "reason"]}}},
            "required": ["summary", "changes"]},
    },
]


class ToolContext:
    def __init__(self, snap, skills, auto_apply):
        self.snap = snap
        self.skills = skills
        self.auto_apply = auto_apply
        self.proposal = None

    def owner(self, key):
        for ptype in ("process", "filament", "printer"):
            if key in (self.snap["values"].get(ptype) or {}):
                return ptype
        return None

    def all_keys(self):
        keys = []
        for ptype in ("process", "filament", "printer"):
            keys.extend((self.snap["values"].get(ptype) or {}).keys())
        return keys


def run_tool(ctx, name, args):
    args = args or {}
    vals = ctx.snap["values"]
    if name == "get_settings":
        out = {}
        for key in list(args.get("keys") or [])[:60]:
            key = str(key).strip()
            ptype = ctx.owner(key)
            if ptype:
                out[key] = {"preset": ptype, "value": show(vals[ptype][key]),
                            "changeable": key_error(ptype, key) is None}
            else:
                out[key] = {"error": "unknown key",
                            "did_you_mean": difflib.get_close_matches(key, ctx.all_keys(), n=5, cutoff=0.6)}
        return out
    if name == "search_settings":
        words = [w for w in re.split(r"[\s_]+", str(args.get("query", "")).lower()) if w]
        hits = []
        for ptype in ("process", "filament", "printer"):
            for key, v in (vals.get(ptype) or {}).items():
                if key in META_KEYS:
                    continue
                if all(w in key.lower() for w in words):
                    hits.append({"key": key, "preset": ptype, "value": show(v),
                                 "changeable": key_error(ptype, key) is None})
        return {"matches": hits[:50], "total": len(hits)}
    if name == "get_plate":
        return {"objects": ctx.snap.get("plate") or []}
    if name == "read_skill":
        sk = ctx.skills.get(str(args.get("name", "")).strip())
        if not sk:
            return {"error": "unknown skill", "available": sorted(ctx.skills)}
        return {"content": sk["content"]}
    if name == "propose_changes":
        return propose(ctx, args)
    return {"error": "unknown tool %s" % name}


# ------------------------------------------------------------- sicurezza --
# Regole assolute, controllate due volte: quando l'IA propone e di nuovo prima di applicare.
# 1) Le impostazioni della stampante non si toccano mai.
# 2) Niente che possa danneggiare la stampante: G-code personalizzato, script, dati del materiale,
#    limiti di sicurezza; temperature, velocita, accelerazioni e ritrazioni solo entro limiti sicuri.

FORBIDDEN_KEYS = {
    # dati del materiale: se sbagliati la stampante estrude male, si intasa o scalda troppo
    "filament_diameter", "filament_density", "filament_type", "filament_soluble", "filament_is_support",
    "nozzle_temperature_range_low", "nozzle_temperature_range_high", "temperature_vitrification",
    "required_nozzle_HRC", "filament_extruder_variant", "filament_shrink",
    "filament_shrinkage_compensation_z", "pellet_flow_coefficient",
    # camera riscaldata e ventole/filtri della macchina
    "chamber_temperature", "chamber_temperatures", "activate_chamber_temp_control",
    # script eseguiti sul computer dopo lo slicing
    "post_process",
}
FORBIDDEN_WORDS = ("gcode", "post_process")       # qualsiasi G-code personalizzato

# 3) Si cambiano solo le chiavi di questa tabella: tutto il resto e rifiutato (da cambiare a mano).
#    valore = (preset, tipo, minimo, massimo, scelte, nil ammesso)
#    preset: "p" processo, "f" filamento. tipo: "b" si/no, "e" scelta, "i" intero, "f" decimale,
#    "pc" percentuale, "fp" decimale o percentuale. nil = il filamento usa il valore della stampante.
ALLOWED = {
    "adaptive_pressure_advance_bridges": ("f", "f", 0, 1, None, False),
    "adaptive_pressure_advance_overhangs": ("f", "b", None, None, None, False),
    "adaptive_pressure_advance": ("f", "b", None, None, None, False),
    "additional_cooling_fan_speed": ("f", "i", 0, 100, None, False),
    "align_infill_direction_to_model": ("p", "b", None, None, None, False),
    "alternate_extra_wall": ("p", "b", None, None, None, False),
    "bottom_shell_layers": ("p", "i", 0, 30, None, False),
    "bottom_shell_thickness": ("p", "f", 0, 10000, None, False),
    "bottom_surface_pattern": ("p", "e", None, None, ("monotonic", "monotonicline", "rectilinear", "alignedrectilinear", "concentric", "spiralinset", "hilbertcurve", "archimedeanchords", "octagramspiral",), False),
    "bridge_acceleration": ("p", "fp", 0, None, None, False),
    "bridge_angle": ("p", "f", 0, 180, None, False),
    "bridge_density": ("p", "pc", 10, 125, None, False),
    "bridge_no_support": ("p", "b", None, None, None, False),
    "bridge_speed": ("p", "f", 1, 10000, None, False),
    "brim_ears_max_angle": ("p", "f", 0, 180, None, False),
    "brim_ears_outer_only": ("p", "b", None, None, None, False),
    "brim_object_gap": ("p", "f", 0, 2, None, False),
    "brim_type": ("p", "e", None, None, ("auto_brim", "brim_ears", "painted", "outer_only", "inner_only", "outer_and_inner", "no_brim", "leading_edge_only",), False),
    "brim_use_efc_outline": ("p", "b", None, None, None, False),
    "brim_width": ("p", "f", 0, 100, None, False),
    "close_fan_the_first_x_layers": ("f", "i", 0, 20, None, False),
    "cool_plate_temp_initial_layer": ("f", "i", 0, 120, None, False),
    "cool_plate_temp": ("f", "i", 0, 300, None, False),
    "counterbore_hole_bridging": ("p", "e", None, None, ("none", "partiallybridge", "sacrificiallayer",), False),
    "default_acceleration": ("p", "f", 0, None, None, False),
    "default_jerk": ("p", "f", 0, 10000, None, False),
    "default_junction_deviation": ("p", "f", 0, 0.3, None, False),
    "detect_overhang_wall": ("p", "b", None, None, None, False),
    "detect_thin_wall": ("p", "b", None, None, None, False),
    "dont_filter_internal_bridges": ("p", "e", None, None, ("disabled", "limited", "nofilter",), False),
    "dont_slow_down_outer_wall": ("f", "b", None, None, None, False),
    "draft_shield": ("p", "e", None, None, ("disabled", "enabled",), False),
    "elefant_foot_compensation_layers": ("p", "i", 1, 10000, None, False),
    "elefant_foot_compensation": ("p", "f", 0, 1, None, False),
    "enable_extra_bridge_layer": ("p", "e", None, None, ("disabled", "external_bridge_only", "internal_bridge_only", "apply_to_all",), False),
    "enable_overhang_bridge_fan": ("f", "b", None, None, None, False),
    "enable_overhang_speed": ("p", "b", None, None, None, False),
    "enable_pressure_advance": ("f", "b", None, None, None, False),
    "enable_prime_tower": ("p", "b", None, None, None, False),
    "enable_support": ("p", "b", None, None, None, False),
    "eng_plate_temp_initial_layer": ("f", "i", 0, 300, None, False),
    "eng_plate_temp": ("f", "i", 0, 300, None, False),
    "ensure_vertical_shell_thickness": ("p", "e", None, None, ("none", "ensure_critical_only", "ensure_moderate", "ensure_all",), False),
    "extra_perimeters_on_overhangs": ("p", "b", None, None, None, False),
    "extrusion_rate_smoothing_external_perimeter_only": ("p", "b", None, None, None, False),
    "fan_cooling_layer_time": ("f", "f", 0, 1000, None, False),
    "fan_max_speed": ("f", "f", 0, 100, None, False),
    "fan_min_speed": ("f", "f", 0, 100, None, False),
    "filament_deretraction_speed": ("f", "f", 0, 10000, None, True),
    "filament_flow_ratio": ("f", "f", 0.8, 1.2, None, False),
    "filament_ironing_flow": ("f", "pc", 1, 30, None, False),
    "filament_ironing_inset": ("f", "f", 0, 100, None, False),
    "filament_ironing_spacing": ("f", "f", 0, 1, None, False),
    "filament_ironing_speed": ("f", "f", 1, 10000, None, False),
    "filament_max_volumetric_speed": ("f", "f", 0.5, 10000, None, False),
    "filament_minimal_purge_on_wipe_tower": ("f", "f", 0, 10000, None, False),
    "filament_prime_volume_nc": ("f", "f", 1, 10000, None, False),
    "filament_prime_volume": ("f", "f", 1, 10000, None, False),
    "filament_retract_after_wipe": ("f", "pc", 0, 100, None, True),
    "filament_retract_before_wipe": ("f", "pc", 0, 100, None, True),
    "filament_retract_lift_above": ("f", "f", 0, 10000, None, True),
    "filament_retract_lift_below": ("f", "f", 0, 10000, None, True),
    "filament_retract_lift_enforce": ("f", "e", None, None, ("All Surfaces", "Top Only", "Bottom Only", "Top and Bottom",), True),
    "filament_retract_when_changing_layer": ("f", "b", None, None, None, True),
    "filament_retraction_length": ("f", "f", 0, 8, None, True),
    "filament_retraction_minimum_travel": ("f", "f", 0, 10, None, True),
    "filament_retraction_speed": ("f", "f", 0, 10000, None, True),
    "filament_seam_gap": ("f", "fp", 0, 10000, None, True),
    "filament_wipe_distance": ("f", "f", 0, 10, None, True),
    "filament_wipe": ("f", "b", None, None, None, True),
    "filament_z_hop_types": ("f", "e", None, None, ("Auto Lift", "Normal Lift", "Slope Lift", "Spiral Lift",), True),
    "filament_z_hop": ("f", "f", 0, 2, None, True),
    "fill_multiline": ("p", "i", 1, 10, None, False),
    "filter_out_gap_fill": ("p", "f", 0, 50, None, False),
    "flush_into_infill": ("p", "b", None, None, None, False),
    "flush_into_support": ("p", "b", None, None, None, False),
    "fuzzy_skin_first_layer": ("p", "b", None, None, None, False),
    "fuzzy_skin_mode": ("p", "e", None, None, ("displacement", "extrusion", "combined",), False),
    "fuzzy_skin_point_distance": ("p", "f", 0.01, 5, None, False),
    "fuzzy_skin_thickness": ("p", "f", 0, 2, None, False),
    "fuzzy_skin": ("p", "e", None, None, ("none", "external", "hole", "all", "allwalls", "disabled_fuzzy",), False),
    "gap_fill_target": ("p", "e", None, None, ("everywhere", "topbottom", "nowhere",), False),
    "gap_infill_speed": ("p", "f", 1, 10000, None, False),
    "hole_to_polyhole": ("p", "b", None, None, None, False),
    "hot_plate_temp_initial_layer": ("f", "i", 0, 300, None, False),
    "hot_plate_temp": ("f", "i", 0, 300, None, False),
    "independent_support_layer_height": ("p", "b", None, None, None, False),
    "infill_anchor_max": ("p", "fp", 0, 10000, None, False),
    "infill_anchor": ("p", "fp", 0, 10000, None, False),
    "infill_combination_max_layer_height": ("p", "fp", 0, 10000, None, False),
    "infill_combination": ("p", "b", None, None, None, False),
    "infill_direction": ("p", "f", 0, 360, None, False),
    "infill_wall_overlap": ("p", "pc", 0, 100, None, False),
    "initial_layer_acceleration": ("p", "f", 0, None, None, False),
    "initial_layer_infill_speed": ("p", "f", 1, 10000, None, False),
    "initial_layer_line_width": ("p", "fp", 0, 1000, None, False),
    "initial_layer_print_height": ("p", "f", 0.1, 10000, None, False),
    "initial_layer_speed": ("p", "f", 1, 10000, None, False),
    "initial_layer_travel_jerk": ("p", "fp", 0, 10000, None, False),
    "inner_wall_acceleration": ("p", "f", 0, None, None, False),
    "inner_wall_line_width": ("p", "fp", 0, 1000, None, False),
    "inner_wall_speed": ("p", "f", 1, 10000, None, False),
    "interface_shells": ("p", "b", None, None, None, False),
    "interlocking_beam": ("p", "b", None, None, None, False),
    "internal_bridge_fan_speed": ("f", "i", -1, 100, None, False),
    "internal_bridge_speed": ("p", "fp", 1, 10000, None, False),
    "internal_solid_infill_acceleration": ("p", "fp", 0, None, None, False),
    "internal_solid_infill_pattern": ("p", "e", None, None, ("monotonic", "monotonicline", "rectilinear", "alignedrectilinear", "concentric", "spiralinset", "hilbertcurve", "archimedeanchords", "octagramspiral",), False),
    "internal_solid_infill_speed": ("p", "f", 1, 10000, None, False),
    "ironing_angle": ("p", "f", 0, 359, None, False),
    "ironing_fan_speed": ("f", "i", -1, 100, None, False),
    "ironing_flow": ("p", "pc", 1, 30, None, False),
    "ironing_inset": ("p", "f", 0, 100, None, False),
    "ironing_pattern": ("p", "e", None, None, ("rectilinear", "concentric",), False),
    "ironing_spacing": ("p", "f", 0, 1, None, False),
    "ironing_speed": ("p", "f", 1, 10000, None, False),
    "ironing_type": ("p", "e", None, None, ("no ironing", "top", "topmost", "solid",), False),
    "is_infill_first": ("p", "b", None, None, None, False),
    "layer_height": ("p", "f", 0.04, 10000, None, False),
    "line_width": ("p", "fp", 0, 1000, None, False),
    "make_overhang_printable_angle": ("p", "f", 0, 90, None, False),
    "make_overhang_printable": ("p", "b", None, None, None, False),
    "max_bridge_length": ("p", "f", 0, 10000, None, False),
    "max_travel_detour_distance": ("p", "fp", 0, 10000, None, False),
    "max_volumetric_extrusion_rate_slope": ("p", "f", 0, 10000, None, False),
    "min_bead_width": ("p", "pc", 0, 200, None, False),
    "min_feature_size": ("p", "pc", 0, 200, None, False),
    "minimum_sparse_infill_area": ("p", "f", 0, 10000, None, False),
    "mmu_segmented_region_interlocking_depth": ("p", "f", 0, 10000, None, False),
    "mmu_segmented_region_max_width": ("p", "f", 0, 10000, None, False),
    "nozzle_temperature_initial_layer": ("f", "i", 0, 10000, None, False),
    "nozzle_temperature": ("f", "i", 0, 10000, None, False),
    "only_one_wall_top": ("p", "b", None, None, None, False),
    "ooze_prevention": ("p", "b", None, None, None, False),
    "outer_wall_acceleration": ("p", "f", 0, None, None, False),
    "outer_wall_jerk": ("p", "f", 0, 10000, None, False),
    "outer_wall_line_width": ("p", "fp", 0, 1000, None, False),
    "outer_wall_speed": ("p", "f", 1, 10000, None, False),
    "overhang_1_4_speed": ("p", "fp", 0, 10000, None, False),
    "overhang_2_4_speed": ("p", "fp", 0, 10000, None, False),
    "overhang_3_4_speed": ("p", "fp", 0, 10000, None, False),
    "overhang_4_4_speed": ("p", "fp", 0, 10000, None, False),
    "overhang_fan_speed": ("f", "i", 0, 100, None, False),
    "overhang_fan_threshold": ("f", "e", None, None, ("0%", "10%", "25%", "50%", "75%", "95%",), False),
    "overhang_reverse_internal_only": ("p", "b", None, None, None, False),
    "overhang_reverse": ("p", "b", None, None, None, False),
    "precise_outer_wall": ("p", "b", None, None, None, False),
    "precise_z_height": ("p", "b", None, None, None, False),
    "pressure_advance": ("f", "f", 0, 1, None, False),
    "prime_tower_brim_width": ("p", "f", -1, 10000, None, False),
    "prime_tower_enable_framework": ("p", "b", None, None, None, False),
    "prime_tower_infill_gap": ("p", "pc", 100, 500, None, False),
    "prime_tower_width": ("p", "f", 2, 10000, None, False),
    "prime_volume": ("p", "f", 1, 10000, None, False),
    "print_flow_ratio": ("p", "f", 0.8, 1.2, None, False),
    "raft_first_layer_density": ("p", "pc", 10, 100, None, False),
    "raft_first_layer_expansion": ("p", "f", 0, 10000, None, False),
    "raft_layers": ("p", "i", 0, 20, None, False),
    "reduce_crossing_wall": ("p", "b", None, None, None, False),
    "reduce_fan_stop_start_freq": ("f", "b", None, None, None, False),
    "reduce_infill_retraction": ("p", "b", None, None, None, False),
    "role_based_wipe_speed": ("p", "b", None, None, None, False),
    "scarf_angle_threshold": ("p", "i", 0, 180, None, False),
    "scarf_joint_speed": ("p", "fp", 1, 10000, None, False),
    "seam_gap": ("p", "fp", 0, 10000, None, False),
    "seam_position": ("p", "e", None, None, ("nearest", "aligned", "aligned_back", "back", "random",), False),
    "seam_slope_conditional": ("p", "b", None, None, None, False),
    "seam_slope_min_length": ("p", "f", 0, 10000, None, False),
    "seam_slope_type": ("p", "e", None, None, ("none", "external", "all",), False),
    "skirt_distance": ("p", "f", 0, 60, None, False),
    "skirt_height": ("p", "i", 0, 50, None, False),
    "skirt_loops": ("p", "i", 0, 10, None, False),
    "slice_closing_radius": ("p", "f", 0, 10000, None, False),
    "slicing_mode": ("p", "e", None, None, ("regular", "even_odd", "close_holes",), False),
    "slow_down_for_layer_cooling": ("f", "b", None, None, None, False),
    "slow_down_layer_time": ("f", "f", 0, 1000, None, False),
    "slow_down_layers": ("p", "i", 0, 10000, None, False),
    "slow_down_min_speed": ("f", "f", 0, 10000, None, False),
    "slowdown_for_curled_perimeters": ("p", "b", None, None, None, False),
    "small_area_infill_flow_compensation": ("p", "b", None, None, None, False),
    "small_perimeter_speed": ("p", "fp", 1, 10000, None, False),
    "small_perimeter_threshold": ("p", "f", 0, 10000, None, False),
    "solid_infill_direction": ("p", "f", 0, 360, None, False),
    "sparse_infill_acceleration": ("p", "fp", 0, None, None, False),
    "sparse_infill_density": ("p", "pc", 0, 100, None, False),
    "sparse_infill_line_width": ("p", "fp", 0, 1000, None, False),
    "sparse_infill_pattern": ("p", "e", None, None, ("rectilinear", "alignedrectilinear", "zigzag", "crosszag", "lockedzag", "line", "grid", "triangles", "tri-hexagon", "cubic", "adaptivecubic", "quartercubic", "supportcubic", "lightning", "honeycomb", "3dhoneycomb", "lateral-honeycomb", "lateral-lattice", "crosshatch", "tpmsd", "tpmsfk", "gyroid", "concentric", "hilbertcurve", "archimedeanchords", "octagramspiral",), False),
    "sparse_infill_speed": ("p", "f", 1, 10000, None, False),
    "spiral_mode_max_xy_smoothing": ("p", "fp", 0, 1000, None, False),
    "spiral_mode_smooth": ("p", "b", None, None, None, False),
    "spiral_mode": ("p", "b", None, None, None, False),
    "staggered_inner_seams": ("p", "b", None, None, None, False),
    "supertack_plate_temp_initial_layer": ("f", "i", 0, 120, None, False),
    "supertack_plate_temp": ("f", "i", 0, 120, None, False),
    "support_base_pattern_spacing": ("p", "f", 0, 10000, None, False),
    "support_base_pattern": ("p", "e", None, None, ("default", "rectilinear", "rectilinear-grid", "honeycomb", "lightning", "hollow",), False),
    "support_bottom_z_distance": ("p", "f", 0, 2, None, False),
    "support_critical_regions_only": ("p", "b", None, None, None, False),
    "support_filament": ("p", "i", 0, 10000, None, False),
    "support_interface_bottom_layers": ("p", "i", -1, 10000, None, False),
    "support_interface_filament": ("p", "i", 0, 10000, None, False),
    "support_interface_not_for_body": ("p", "b", None, None, None, False),
    "support_interface_pattern": ("p", "e", None, None, ("auto", "rectilinear", "concentric", "spiralinset", "rectilinear_interlaced", "grid",), False),
    "support_interface_spacing": ("p", "f", 0, 10000, None, False),
    "support_interface_speed": ("p", "f", 1, 10000, None, False),
    "support_interface_top_layers": ("p", "i", 0, 10000, None, False),
    "support_ironing_flow": ("p", "pc", 1, 30, None, False),
    "support_ironing": ("p", "b", None, None, None, False),
    "support_material_interface_fan_speed": ("f", "i", -1, 100, None, False),
    "support_object_xy_distance": ("p", "f", 0, 10, None, False),
    "support_on_build_plate_only": ("p", "b", None, None, None, False),
    "support_remove_small_overhang": ("p", "b", None, None, None, False),
    "support_speed": ("p", "f", 1, 10000, None, False),
    "support_style": ("p", "e", None, None, ("default", "grid", "snug", "organic", "tree_slim", "tree_strong", "tree_hybrid",), False),
    "support_threshold_angle": ("p", "i", 0, 90, None, False),
    "support_top_z_distance": ("p", "f", 0, 2, None, False),
    "support_type": ("p", "e", None, None, ("normal(auto)", "tree(auto)", "normal(manual)", "tree(manual)",), False),
    "textured_cool_plate_temp_initial_layer": ("f", "i", 0, 120, None, False),
    "textured_cool_plate_temp": ("f", "i", 0, 300, None, False),
    "textured_plate_temp_initial_layer": ("f", "i", 0, 300, None, False),
    "textured_plate_temp": ("f", "i", 0, 300, None, False),
    "thick_bridges": ("p", "b", None, None, None, False),
    "thick_internal_bridges": ("p", "b", None, None, None, False),
    "top_bottom_infill_wall_overlap": ("p", "pc", 0, 100, None, False),
    "top_shell_layers": ("p", "i", 0, 30, None, False),
    "top_shell_thickness": ("p", "f", 0, 10000, None, False),
    "top_surface_acceleration": ("p", "f", 0, None, None, False),
    "top_surface_expansion_margin": ("p", "f", 0, 10, None, False),
    "top_surface_expansion": ("p", "f", 0, 10000, None, False),
    "top_surface_line_width": ("p", "fp", 0, 1000, None, False),
    "top_surface_pattern": ("p", "e", None, None, ("monotonic", "monotonicline", "rectilinear", "alignedrectilinear", "concentric", "spiralinset", "hilbertcurve", "archimedeanchords", "octagramspiral",), False),
    "top_surface_speed": ("p", "f", 1, 10000, None, False),
    "travel_acceleration": ("p", "f", 0, None, None, False),
    "travel_jerk": ("p", "f", 0, 10000, None, False),
    "travel_speed": ("p", "f", 1, 10000, None, False),
    "tree_support_angle_slow": ("p", "f", 10, 85, None, False),
    "tree_support_auto_brim": ("p", "b", None, None, None, False),
    "tree_support_branch_diameter_angle": ("p", "f", 0, 15, None, False),
    "tree_support_branch_diameter_organic": ("p", "f", 1, 10, None, False),
    "tree_support_branch_diameter": ("p", "f", 1, 10, None, False),
    "tree_support_branch_distance_organic": ("p", "f", 1, 10, None, False),
    "tree_support_branch_distance": ("p", "f", 1, 10, None, False),
    "tree_support_brim_width": ("p", "f", 0, 10000, None, False),
    "tree_support_top_rate": ("p", "pc", 5, 100, None, False),
    "tree_support_wall_count": ("p", "i", 0, 2, None, False),
    "wall_distribution_count": ("p", "i", 1, 10000, None, False),
    "wall_generator": ("p", "e", None, None, ("classic", "arachne",), False),
    "wall_loops": ("p", "i", 1, 20, None, False),
    "wall_sequence": ("p", "e", None, None, ("inner wall/outer wall", "outer wall/inner wall", "inner-outer-inner wall",), False),
    "wall_transition_angle": ("p", "f", 1, 59, None, False),
    "wall_transition_filter_deviation": ("p", "pc", 0, 200, None, False),
    "wipe_before_external_loop": ("p", "b", None, None, None, False),
    "wipe_inward_distance": ("p", "fp", 0, 100, None, False),
    "wipe_inward": ("p", "b", None, None, None, False),
    "wipe_on_loops": ("p", "b", None, None, None, False),
    "wipe_speed": ("p", "fp", 0, 10000, None, False),
    "wipe_tower_filament": ("p", "i", 0, 10000, None, False),
    "wipe_tower_max_purge_speed": ("p", "f", 10, 10000, None, False),
    "wipe_tower_no_sparse_layers": ("p", "b", None, None, None, False),
    "wipe_tower_sparse_layers_combination": ("p", "b", None, None, None, False),
    "wipe_tower_wall_type": ("p", "e", None, None, ("rectangle", "cone", "rib",), False),
    "xy_contour_compensation": ("p", "f", -1, 1, None, False),
    "xy_hole_compensation": ("p", "f", -1, 1, None, False),
}

# Chiavi di cui il plugin non sa verificare un valore sicuro: l'IA spiega come cambiarle a mano.
MANUAL_KEYS = {
    "set_other_flow_ratios", "first_layer_flow_ratio", "outer_wall_flow_ratio", "inner_wall_flow_ratio",
    "top_solid_infill_flow_ratio", "bottom_solid_infill_flow_ratio", "sparse_infill_flow_ratio",
    "internal_solid_infill_flow_ratio", "overhang_flow_ratio", "gap_fill_flow_ratio", "support_flow_ratio",
    "support_interface_flow_ratio", "bridge_flow", "internal_bridge_flow", "filament_retract_restart_extra",
    "filament_retract_restart_extra_toolchange", "activate_air_filtration", "during_print_exhaust_fan_speed",
    "complete_print_exhaust_fan_speed",
}

FLOW_KEYS = {"filament_flow_ratio", "print_flow_ratio"}
NOZZLE_TEMP_KEYS = {"nozzle_temperature", "nozzle_temperature_initial_layer"}
BED_TEMP_MAX = 120.0


def numbers(value):
    """Numeri di un valore testo ("0.2", "15%", "200,200", "nil"); None se non numerico."""
    out = []
    for part in re.split(r"[;,]", str(value)):
        part = part.strip()
        if part in ("", "nil"):
            continue
        try:
            out.append(float(part.rstrip("%")))
        except ValueError:
            return None
    return out


def first_number(vals, ptype, key, default=None, agg=min):
    v = (vals.get(ptype) or {}).get(key)
    if v is None:
        return default
    ns = numbers(";".join(str(x) for x in v) if isinstance(v, list) else v)
    return agg(ns) if ns else default


def machine_limit(vals, key):
    """Limite della macchina in modalita normale. Le chiavi machine_max_* valgono [normale, silenziosa, ...]:
    contano solo i posti pari (0, 2, 4...); i valori mancanti o a zero non contano."""
    v = (vals.get("printer") or {}).get(key)
    items = v if isinstance(v, list) else re.split(r"[;,]", "" if v is None else str(v))
    ns = [n[0] for n in (numbers(x) for x in items[0::2]) if n and n[0] > 0]
    return min(ns) if ns else None


def start_number(base, vals, ptype, key, agg=min):
    """Valore di partenza della sessione per una chiave (base, vedi Assistant.baseline); se manca, quello di adesso."""
    v = (base or {}).get((ptype, key))
    n = first_number({ptype: {key: v}}, ptype, key, agg=agg) if v is not None else None
    return n if n is not None else first_number(vals, ptype, key, agg=agg)


def key_error(ptype, key):
    """Messaggio se la chiave non si puo cambiare affatto (vietata, o da cambiare a mano), altrimenti None."""
    if ptype not in ("process", "filament"):
        return ("FORBIDDEN: printer settings are never changed by this plugin. Explain to the user what to check "
                "or change by hand instead.")
    low = key.lower()
    if key in META_KEYS:
        return "FORBIDDEN: this key describes the preset itself."
    if key in FORBIDDEN_KEYS or any(w in low for w in FORBIDDEN_WORDS):
        return ("FORBIDDEN: custom G-code, scripts, material data, chamber heating and safety limits are never "
                "changed by this plugin, because a wrong value can damage the printer.")
    if "temp" in low and key not in NOZZLE_TEMP_KEYS and "plate_temp" not in low and "bed_temp" not in low:
        return "FORBIDDEN: this temperature setting is not changed by this plugin."
    if key in MANUAL_KEYS or key not in ALLOWED or ALLOWED[key][0] != ptype[0]:
        return ("MANUAL: the plugin cannot verify a safe value for %s, so it must not be proposed. Explain to the "
                "user, step by step, how to change it by hand in OrcaSlicer (which tab and which field)." % key)
    return None


NUMBER = r"-?\d+(?:\.\d+)?"


def spec_error(key, value):
    """Controllo generico del valore con la riga di ALLOWED: None se va bene, altrimenti cosa ci si aspetta.
    Un valore puo avere piu parti separate da , o ; (una per variante): devono andare bene tutte."""
    _preset, kind, lo, hi, enum, nullable = ALLOWED[key]
    parts = [x.strip() for x in re.split(r"[;,]", str(value))]
    if "nil" in parts:
        if not nullable:
            return 'INVALID: %s cannot be "nil": give a real value.' % key
        parts = [x for x in parts if x != "nil"]          # nil = vale il valore della stampante
    span = (" from %g" % lo if lo is not None else "") + (" up to %g" % hi if hi is not None else "")

    def inside(text):
        n = numbers(text)[0]
        return (lo is None or n >= lo) and (hi is None or n <= hi)

    if kind == "b":
        ok, want = all(x in ("1", "0") for x in parts), 'must be "1" (on) or "0" (off)'
    elif kind == "e":
        ok, want = all(x in enum for x in parts), "must be exactly one of: " + ", ".join('"%s"' % x for x in enum)
    elif kind in ("i", "f"):
        ok = all(re.fullmatch(r"-?\d+" if kind == "i" else NUMBER, x) and inside(x) for x in parts)
        want = "must be a %s%s, without the %% sign" % ("whole number" if kind == "i" else "number", span)
    elif kind == "pc":
        ok = all(re.fullmatch(NUMBER + "%", x) and inside(x) for x in parts)
        want = 'must be a percentage%s written with the %% sign (like "15%%")' % span
    else:                                                 # "fp": millimetri (o mm/s...) oppure percentuale
        ok = all((re.fullmatch(NUMBER, x) and inside(x)) or
                 (re.fullmatch(NUMBER + "%", x) and 0 <= numbers(x)[0] <= 1000) for x in parts)
        want = "must be a number%s, or a percentage from 0%% up to 1000%%" % span
    return None if ok else "INVALID: %s %s." % (key, want)


def safety_error(ptype, key, value, vals, base=None):
    """Messaggio d'errore se la modifica e vietata o pericolosa, altrimenti None.
    base = {(ptype, chiave): valore di partenza della sessione}: i limiti "+10 C" e "+10%" si contano da li."""
    err = key_error(ptype, key) or spec_error(key, value)
    if err:
        return err
    low = key.lower()
    ns = numbers(value)
    if ALLOWED[key][1] in ("b", "e") or not ns:           # si/no, scelte, solo "nil": nessun altro limite
        return None
    pct = "%" in str(value)
    fv = vals.get("filament") or {}

    def need_numbers():
        return None if ns else "the value must be a number for this setting"

    if key in NOZZLE_TEMP_KEYS:
        lo = first_number(vals, "filament", "nozzle_temperature_range_low", agg=max)
        hi = first_number(vals, "filament", "nozzle_temperature_range_high", agg=min)
        if need_numbers():
            return need_numbers()
        if lo is None or hi is None:
            return "FORBIDDEN: the filament has no safe temperature range, so the nozzle temperature cannot be changed."
        if any(t < lo or t > hi for t in ns):
            return "UNSAFE: nozzle temperature must stay inside the filament range %g-%g C." % (lo, hi)
        return None
    if "temp" in low:
        if "plate_temp" in low or "bed_temp" in low:
            if need_numbers():
                return need_numbers()
            cur = first_number(vals, ptype, key, agg=max)
            start = start_number(base, vals, ptype, key, agg=max)      # +10 C dal valore di partenza, non a ogni richiesta
            cap = min(BED_TEMP_MAX, max(cur, start + 10) if cur is not None else BED_TEMP_MAX)
            if any(t < 0 or t > cap for t in ns):
                return ("UNSAFE: bed temperature must stay between 0 and %g C (at most +10 C over the original value, "
                        "not per request)." % cap)
            return None
        return "FORBIDDEN: this temperature setting is not changed by this plugin."
    if key in FLOW_KEYS:
        if need_numbers():
            return need_numbers()
        if any(f < 0.8 or f > 1.2 for f in ns):
            return "UNSAFE: flow ratio must stay between 0.8 and 1.2."
        return None
    if key == "filament_max_volumetric_speed":
        cur = first_number(vals, "filament", key)
        if need_numbers():
            return need_numbers()
        start = start_number(base, vals, "filament", key)              # +10% dal valore di partenza, non a ogni richiesta
        if cur is not None and any(f > max(cur, start * 1.1) for f in ns):
            return ("UNSAFE: max volumetric speed can be raised by at most 10%% over the original value (%g mm3/s), "
                    "not per request: more risks clogs and heat creep." % start)
        return None
    nozzle = first_number(vals, "printer", "nozzle_diameter", default=0.4)
    if key == "line_width" or key.endswith("_line_width"):
        for part in re.split(r"[;,]", str(value)):
            w = (numbers(part) or [0])[0]                 # 0 = larghezza predefinita
            if w and ((w < 50 or w > 300) if "%" in part else (w < nozzle * 0.5 or w > nozzle * 3)):
                return ("UNSAFE: line width must be 0 (default), 50%%-300%%, or %g-%g mm with a %g mm nozzle."
                        % (nozzle * 0.5, nozzle * 3, nozzle))
        return None
    if key in ("layer_height", "initial_layer_print_height"):
        if need_numbers() or pct:
            return need_numbers() or "use a value in mm"
        lo = 0.1 if key == "initial_layer_print_height" else 0.04
        if any(h < lo or h > nozzle * 0.75 for h in ns):
            return "UNSAFE: %s must stay between %g and %g mm with a %g mm nozzle." % (key, lo, nozzle * 0.75, nozzle)
        return None
    if key == "filament_retraction_length":
        if not ns:
            return None if str(value).strip().replace(",", "").replace(";", "").replace("nil", "") == "" else need_numbers()
        prn = first_number(vals, "printer", "retraction_length", default=1.0, agg=max)
        cap = min(8.0, max(2.0, prn * 2))
        if any(r < 0 or r > cap for r in ns):
            return "UNSAFE: retraction length must stay between 0 and %g mm on this printer (too much retraction can clog the hotend)." % cap
        return None
    if key in ("filament_retraction_speed", "filament_deretraction_speed"):
        if not ns:
            return None
        prn = first_number(vals, "printer", key.replace("filament_", ""), default=40.0, agg=max)
        if any(v < 0 or (v == 0 and key == "filament_retraction_speed") or v > max(prn * 1.5, 30) for v in ns):   # deretraction 0 = come la ritrazione
            return "UNSAFE: retraction speed must stay between 0 and %g mm/s." % max(prn * 1.5, 30)
        return None
    if key == "filament_z_hop":
        if ns and any(z < 0 or z > 2 for z in ns):
            return "UNSAFE: z hop must stay between 0 and 2 mm."
        return None
    # velocita, accelerazioni e jerk entro i limiti della macchina
    if not pct and ns and "fan" not in low:
        if low.endswith("_acceleration") or low.endswith("acceleration"):
            limits = [machine_limit(vals, k) for k in ("machine_max_acceleration_x", "machine_max_acceleration_y")]
            if "travel" not in low:
                limits.append(machine_limit(vals, "machine_max_acceleration_extruding"))
            limits = [x for x in limits if x]
            if limits and any(a > min(limits) for a in ns):
                return "UNSAFE: acceleration must not exceed the printer limit of %g mm/s2." % min(limits)
        elif low.endswith("_jerk") or low.endswith("jerk"):
            lim = machine_limit(vals, "machine_max_jerk_x")
            if lim and any(j > lim for j in ns):
                return "UNSAFE: jerk must not exceed the printer limit of %g mm/s." % lim
        elif low.endswith("_speed") or low.endswith("speed_z"):
            if "z" in low.split("_")[-1:] or low.endswith("speed_z"):
                lim = machine_limit(vals, "machine_max_speed_z")
            else:
                limits = [machine_limit(vals, k) for k in ("machine_max_speed_x", "machine_max_speed_y")]
                limits = [x for x in limits if x]
                lim = min(limits) if limits else None
            if lim and any(v > lim for v in ns):
                return "UNSAFE: speed must not exceed the printer limit of %g mm/s." % lim
    return None


def propose(ctx, args):
    vals = ctx.snap["values"]
    accepted, errors, blocked = [], [], []
    for ch in list(args.get("changes") or [])[:20]:
        key = str(ch.get("key", "")).strip()
        value = ch.get("value", "")
        value = "" if value is None else str(value).strip()
        ptype = ctx.owner(key)
        if not key or ptype is None:
            errors.append({"key": key, "error": "unknown key",
                           "did_you_mean": difflib.get_close_matches(key, ctx.all_keys(), n=5, cutoff=0.6)})
            continue
        if not value or len(value) > 300:
            errors.append({"key": key, "error": "empty or too long value"})
            continue
        err = safety_error(ptype, key, value, vals, ctx.snap.get("base"))
        if err:
            errors.append({"key": key, "error": err})
            kind = "printer" if ptype == "printer" else next(
                (k for k in ("forbidden", "manual", "invalid") if err.startswith(k.upper())), "unsafe")
            blocked.append({"preset": ptype, "key": key, "new": value, "old": short(vals[ptype].get(key)),
                            "label": str(ch.get("label", ""))[:80], "kind": kind, "error": err})
            continue
        old = vals[ptype][key]
        accepted.append({"preset": ptype, "key": key, "old": short(old), "new": value,
                         "label": str(ch.get("label", ""))[:80], "reason": str(ch.get("reason", ""))[:300]})
    if accepted or blocked:
        ctx.proposal = {"id": secrets.token_hex(6), "summary": str(args.get("summary", ""))[:400],
                        "changes": accepted, "blocked": blocked}
    note = ("Auto-apply is ON: the changes will be applied right away; tell the user to slice again."
            if ctx.auto_apply else
            "The proposal is shown to the user with an Apply button. Nothing is applied yet.")
    return {"accepted": [{"key": a["key"], "old": a["old"], "new": a["new"]} for a in accepted],
            "errors": errors, "note": note if accepted else "Nothing proposed: fix the errors."}


def step_info(name, args, res):
    """Riassunto di un passaggio per il pannello (cosa ha letto o controllato l'IA)."""
    args = args or {}
    info = {"tool": str(name)}
    if name == "get_settings":
        info["keys"] = [str(k) for k in (args.get("keys") or [])][:40]
    elif name == "search_settings":
        info["query"] = str(args.get("query", ""))[:60]
    elif name == "read_skill":
        info["skill"] = str(args.get("name", ""))[:60]
    elif name == "propose_changes" and isinstance(res, dict):
        info["accepted"] = len(res.get("accepted") or [])
        info["blocked"] = sum(1 for e in (res.get("errors") or [])
                              if str(e.get("error", "")).startswith(("FORBIDDEN", "UNSAFE", "MANUAL", "INVALID")))
    return info


# ------------------------------------------------------------- connettori IA --

class ProviderError(Exception):
    def __init__(self, msg, code="", status=0):
        super().__init__(msg)
        self.code, self.status = code, status


_SSL = None


def ssl_context():
    global _SSL
    if _SSL is None:
        _SSL = ssl.create_default_context()
    return _SSL


def extract_error(body):
    try:
        d = json.loads(body)
        e = d.get("error", d)
        if isinstance(e, dict):
            return str(e.get("message") or e.get("type") or e)[:500]
        return str(e)[:500]
    except Exception:
        return body[:500]


def http_json(url, payload=None, headers=None, timeout=HTTP_TIMEOUT):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "PrintDoctor/%s" % VERSION)
    for k, v in (headers or {}).items():
        if v:
            req.add_header(k, v)
    try:
        ctx = ssl_context() if url.startswith("https") else None
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise ProviderError("HTTP %d: %s" % (exc.code, extract_error(body)), status=exc.code)
    except urllib.error.URLError as exc:
        raise ProviderError("connection failed: %s" % (exc.reason,))
    except (http.client.HTTPException, OSError) as exc:
        raise ProviderError("connection failed: %s" % (exc,))


def http_form(url, fields, timeout=60):
    """POST form-encoded (endpoint OAuth). Errori OAuth -> ProviderError con il codice."""
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "PrintDoctor/%s" % VERSION)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as r:
            raw = r.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        code = ""
        try:
            d = json.loads(body)
            code = d.get("error") if isinstance(d.get("error"), str) else (d.get("error") or {}).get("code", "")
        except Exception:
            pass
        raise ProviderError("HTTP %d: %s" % (exc.code, code or extract_error(body)), code=code, status=exc.code)
    except urllib.error.URLError as exc:
        raise ProviderError("connection failed: %s" % (exc.reason,))
    except (http.client.HTTPException, OSError) as exc:
        raise ProviderError("connection failed: %s" % (exc,))


def b64url_decode(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


_JWKS = {}


def verify_id_token(id_token, client_id, nonce):
    """Controlla un ID token OpenID di OpenAI: firma RS256 con le chiavi pubblicate (JWKS),
    emittente, destinatario, scadenza e nonce. Restituisce i dati (claims)."""
    try:
        h64, p64, s64 = id_token.split(".")
        header, claims, sig = json.loads(b64url_decode(h64)), json.loads(b64url_decode(p64)), b64url_decode(s64)
    except Exception:
        raise ProviderError("invalid ID token")
    if header.get("alg") != "RS256":
        raise ProviderError("ID token is not signed with RS256")     # mai un token senza firma controllata
    key = None
    for _attempt in range(2):
        fresh = not _JWKS
        if fresh:
            conf = http_json(CG_AUTH + "/.well-known/openid-configuration", None, timeout=30)
            _JWKS["keys"] = http_json(conf["jwks_uri"], None, timeout=30).get("keys", [])
        key = next((k for k in _JWKS["keys"] if k.get("kid") == header.get("kid")), None)
        if key is not None or fresh:
            break
        _JWKS.clear()                # chiave non tra quelle in memoria: si riscaricano una volta (rotazione)
    if key is None:
        _JWKS.clear()
        raise ProviderError("ID token signed with an unknown key")
    n = int.from_bytes(b64url_decode(key["n"]), "big")
    e = int.from_bytes(b64url_decode(key["e"]), "big")
    k = (n.bit_length() + 7) // 8
    digest_info = bytes.fromhex("3031300d060960864801650304020105000420")
    expected = (b"\x00\x01" + b"\xff" * (k - 3 - len(digest_info) - 32) + b"\x00" + digest_info +
                hashlib.sha256((h64 + "." + p64).encode("ascii")).digest())
    got = pow(int.from_bytes(sig, "big"), e, n).to_bytes(k, "big") if len(sig) == k else b""
    if not hmac.compare_digest(got, expected):
        raise ProviderError("ID token signature is not valid")
    aud = claims.get("aud")
    auds = aud if isinstance(aud, list) else [aud]
    if claims.get("iss") != CG_AUTH:
        raise ProviderError("ID token issuer mismatch")
    if client_id not in auds:
        raise ProviderError("ID token audience mismatch")
    if float(claims.get("exp", 0)) < time.time() - 60:
        raise ProviderError("ID token expired")
    if nonce and claims.get("nonce") != nonce:
        raise ProviderError("ID token nonce mismatch")
    return claims


def http_sse(url, payload, headers, timeout=HTTP_TIMEOUT):
    """POST con risposta in streaming (server-sent events). Restituisce l'evento finale."""
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "text/event-stream")
    req.add_header("User-Agent", "PrintDoctor/%s" % VERSION)
    for k, v in (headers or {}).items():
        if v:
            req.add_header(k, v)
    try:
        r = urllib.request.urlopen(req, timeout=timeout, context=ssl_context())
        with r:
            return read_sse(r)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        code, param = "", ""
        try:
            d = json.loads(body)
            err = d.get("error") if isinstance(d.get("error"), dict) else {}
            code, param = err.get("code") or "", err.get("param") or ""
            if not err and d.get("detail"):
                body = json.dumps({"error": {"message": str(d["detail"])}})
        except Exception:
            pass
        msg = extract_error(body) + (" (%s)" % param if param else "")
        raise ProviderError("HTTP %d: %s" % (exc.code, msg), code=code, status=exc.code)
    except urllib.error.URLError as exc:
        raise ProviderError("connection failed: %s" % (exc.reason,))
    except (http.client.HTTPException, OSError) as exc:
        raise ProviderError("connection failed: %s" % (exc,))


def read_sse(r):
    data_lines = []
    for raw in r:
        line = raw.decode("utf-8", "replace").rstrip("\r\n")
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
            continue
        if line or not data_lines:
            continue
        data, data_lines = "\n".join(data_lines), []
        if data == "[DONE]":
            break
        try:
            ev = json.loads(data)
        except ValueError:
            continue
        t = ev.get("type", "")
        if t in ("response.completed", "response.incomplete"):
            return ev.get("response") or {}
        if t in ("response.failed", "error"):
            err = (ev.get("response") or {}).get("error") or ev.get("error") or ev
            raise ProviderError(str(err.get("message") or err.get("code") or err)[:500], code=err.get("code") or "")
    raise ProviderError("the stream ended before the response was complete")


class ResponsesChat:
    """Responses API con il piano ChatGPT dell'utente (Sign in with ChatGPT).
    Regole dell'anteprima: store=false, stream=true, niente messaggi di sistema (si usa instructions),
    strumenti dentro un namespace, cronologia completa a ogni richiesta."""

    def __init__(self, model, token_fn, effort=None):
        self.url = CG_API + "/responses"
        self.model, self.token_fn, self.effort = model, token_fn, effort
        self.history = []
        self.include_reasoning = True

    def add_user(self, text, images):
        content = [{"type": "input_text", "text": text}]
        for im in images or []:
            content.append({"type": "input_image", "image_url": "data:%s;base64,%s" % (im["mime"], im["data"])})
        self.history.append({"role": "user", "content": content})

    def payload(self, system, tools):
        p = {
            "model": self.model, "instructions": system, "input": self.history, "store": False, "stream": True,
            "tools": [{"type": "namespace", "name": "orca",
                       "description": "Read OrcaSlicer settings, read skills and propose setting changes.",
                       "tools": [{"type": "function", "name": t["name"], "description": t["description"],
                                  "parameters": t["parameters"]} for t in tools]}],
        }
        if self.include_reasoning:
            p["include"] = ["reasoning.encrypted_content"]
        return p

    def step(self, system, tools):
        resp, force = None, False
        for _attempt in range(3):
            try:
                headers = {"Authorization": "Bearer " + self.token_fn(force=force)}
                resp = http_sse(self.url, self.payload(system, tools), headers)
                break
            except ProviderError as exc:
                if exc.status == 401 and not force:
                    force = True             # token scaduto o revocato: lo rinnova e riprova una volta
                    continue
                if exc.status == 400 and self.include_reasoning and "include" in str(exc):
                    self.include_reasoning = False
                    self.history = [h for h in self.history if h.get("type") != "reasoning"]
                    continue
                raise ProviderError(chatgpt_error_text(exc), code=exc.code, status=exc.status)
        if not isinstance(resp, dict):
            raise ProviderError("no response")
        texts, calls = [], []
        for item in resp.get("output") or []:
            t = item.get("type")
            if t == "reasoning":
                if self.include_reasoning and item.get("encrypted_content"):
                    self.history.append(item)
                continue
            keep = {k: v for k, v in item.items() if k not in ("id", "status")}
            if t == "message":
                for c in item.get("content") or []:
                    if c.get("type") == "output_text":
                        texts.append(c.get("text") or "")
                self.history.append(keep)
            elif t == "function_call":
                try:
                    args = json.loads(item.get("arguments") or "{}")
                except ValueError:
                    args = {"_invalid_json": item.get("arguments")}
                calls.append((item.get("call_id"), item.get("name"), args))
                self.history.append(keep)
        status = resp.get("status")
        if status == "incomplete" and not calls:
            reason = (resp.get("incomplete_details") or {}).get("reason", "")
            texts.append("(%s)" % (reason or "incomplete"))
        return "\n".join(x for x in texts if x), calls, status

    def add_tool_results(self, results):
        for cid, _name, content, _err in results:
            self.history.append({"type": "function_call_output", "call_id": cid, "output": content})


def chatgpt_error_text(exc):
    """Messaggi chiari per gli errori del piano ChatGPT (pagina Errors and recovery di OpenAI)."""
    code = getattr(exc, "code", "") or ""
    known = {
        "subscription_sharing_usage_limit_exceeded": "chatgpt_limit",
        "subscription_sharing_user_not_eligible": "chatgpt_not_eligible",
        "subscription_sharing_usage_unavailable": "chatgpt_unavailable",
        "subscription_sharing_user_unavailable": "chatgpt_unavailable",
        "subscription_sharing_invalid_user": "login_expired",
    }
    if code in known:
        return known[code]
    return str(exc)


class OpenAIChat:
    """Chat Completions compatibile OpenAI: OpenRouter, OpenAI, Gemini, Ollama, LM Studio..."""

    def __init__(self, base, key, model, extra_headers=None):
        self.url = base.rstrip("/") + "/chat/completions"
        self.key, self.model = key, model
        self.extra = extra_headers or {}
        self.history = []

    def add_user(self, text, images):
        if images:
            content = [{"type": "text", "text": text}]
            for im in images:
                content.append({"type": "image_url",
                                "image_url": {"url": "data:%s;base64,%s" % (im["mime"], im["data"])}})
        else:
            content = text
        self.history.append({"role": "user", "content": content})

    def step(self, system, tools):
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}] + self.history,
            "tools": [{"type": "function", "function": t} for t in tools],
            "tool_choice": "auto",
        }
        headers = dict(self.extra)
        if self.key:
            headers["Authorization"] = "Bearer " + self.key
        resp = http_json(self.url, payload, headers)
        if resp.get("error"):
            raise ProviderError(extract_error(json.dumps(resp)))
        choices = resp.get("choices") or []
        if not choices:
            raise ProviderError("empty response")
        msg = choices[0].get("message") or {}
        calls = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function") or {}
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except ValueError:
                args = {"_invalid_json": fn.get("arguments")}
            calls.append((tc.get("id") or secrets.token_hex(4), fn.get("name"), args))
        keep = {"role": "assistant", "content": msg.get("content") or ""}
        if msg.get("tool_calls"):
            keep["tool_calls"] = msg["tool_calls"]
        if msg.get("reasoning_details"):
            keep["reasoning_details"] = msg["reasoning_details"]   # OpenRouter: continuita del ragionamento
        self.history.append(keep)
        return (msg.get("content") or ""), calls, choices[0].get("finish_reason")

    def add_tool_results(self, results):
        for cid, name, content, _err in results:
            self.history.append({"role": "tool", "tool_call_id": cid, "name": name, "content": content})


class AnthropicChat:
    """Messages API di Anthropic (chiave API). Chiamata HTTP diretta: niente dipendenze da installare."""

    def __init__(self, base, key, model, effort):
        self.url = base.rstrip("/") + "/messages"
        self.key, self.model, self.effort = key, model, effort or "medium"
        self.history = []

    def add_user(self, text, images):
        content = []
        for im in images or []:
            content.append({"type": "image", "source": {"type": "base64", "media_type": im["mime"], "data": im["data"]}})
        content.append({"type": "text", "text": text})
        self.history.append({"role": "user", "content": content})

    def step(self, system, tools):
        payload = {
            "model": self.model,
            "max_tokens": 16000,
            "system": system,
            "messages": self.history,
            "tools": [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in tools],
            "output_config": {"effort": self.effort},
            "fallbacks": "default",          # se un filtro di sicurezza rifiuta, l'API riprova su un altro modello
        }
        headers = {"x-api-key": self.key, "anthropic-version": ANTHROPIC_VERSION, "anthropic-beta": ANTHROPIC_BETA}
        resp = http_json(self.url, payload, headers)
        content = resp.get("content") or []
        stop = resp.get("stop_reason")
        # un messaggio rifiutato, troncato a meta di una chiamata a uno strumento o vuoto non entra nella cronologia
        if stop == "refusal":
            raise ProviderError("refused")
        if stop == "max_tokens" and any(b.get("type") == "tool_use" for b in content):
            raise ProviderError("truncated")
        if not content:
            raise ProviderError("empty response")
        self.history.append({"role": "assistant", "content": content})   # rimandato com'e (blocchi thinking inclusi)
        text = "\n".join(b.get("text", "") for b in content if b.get("type") == "text")
        calls = [(b["id"], b["name"], b.get("input") or {}) for b in content if b.get("type") == "tool_use"]
        if stop == "max_tokens":
            calls = []
        return text, calls, stop

    def add_tool_results(self, results):
        blocks = [{"type": "tool_result", "tool_use_id": cid, "content": content, "is_error": bool(err)}
                  for cid, _name, content, err in results]
        self.history.append({"role": "user", "content": blocks})


SYSTEM_PROMPT = """You are the print assistant inside OrcaSlicer: an expert in FDM 3D printing and in OrcaSlicer settings.
The user describes print problems or goals. Understand the problem, explain the likely causes briefly, and fix it by changing slicer settings with the propose_changes tool.

How to work:
- Each user message may start with a snapshot of the current Orca state (printer, presets, main values, objects on the plate). Read any other value with get_settings or search_settings: never guess a current value or a key name.
- Before proposing, read the current value of every key you want to change.
- When the problem matches a skill below, read it with read_skill first.
- Ask one short clarifying question only when the answer would change the fix (material, where the defect is, what the part is for). Otherwise act.
- Propose few, targeted changes (usually 1-5), each with a short reason. Prefer the smallest change that fixes the problem.
- Use exact Orca keys and the format of the current value ("15%%", "0.42", "tree(auto)", "1"/"0"). Vector values are applied to every variant.
- ABSOLUTE RULES, enforced by the plugin (forbidden changes are rejected):
  - Never change printer (machine) settings. For hardware causes (bed leveling, Z offset, wet filament, worn or clogged nozzle, belts) or printer settings, tell the user what to check or change by hand.
  - Never change anything that could physically damage the printer: custom G-code, post-processing scripts, material data (diameter, density, type), temperature ranges, chamber heating.
  - Nozzle temperature only inside nozzle_temperature_range_low/high of the filament; flow ratio 0.8-1.2; speeds, accelerations and jerk within the printer's machine limits; moderate retraction. Bed temperature can go up by at most +10 C and max volumetric speed by at most +10%%: both limits are counted from the original value (the one the preset had at the start of the session), not per request, so asking again does not raise them further.
  - Settings the plugin reports as MANUAL, or with "changeable": false in get_settings / search_settings (for example per-feature flow ratios, bridge flow, extra length on restart, air filtration / exhaust fan), must never be put in propose_changes: explain to the user how to change them by hand in Orca (which tab and which field).
- Applied changes go into the presets currently in use as unsaved edits (Orca marks them as modified); the user can undo them or save the preset in Orca.
- After propose_changes, tell the user to press Apply and slice again. Never claim a change is applied unless the tool result says so.
- If the user sends a photo, say what you see that matters for the diagnosis.
- Reply in %(lang)s. Be short and practical. Plain text with simple "- " lists, no tables, no headings.

Skills you can read:
%(skills)s
"""


def build_system(skills, lang):
    lines = ["- %s: %s" % (n, s["description"]) for n, s in sorted(skills.items())]
    return SYSTEM_PROMPT % {"lang": "Italian" if lang == "it" else "the user's language",
                            "skills": "\n".join(lines)}


def make_conversation(settings, token_fn=None):
    pid = settings.get("provider", "openrouter")
    meta = PROVIDERS.get(pid, PROVIDERS["custom"])
    ps = settings.get("providers", {}).get(pid, {})
    if meta["kind"] == "responses":
        if not ps.get("refresh_token") and not ps.get("access_token"):
            raise ProviderError("missing_login")
        if not ps.get("plan"):
            raise ProviderError("chatgpt_no_plan")
        if not (ps.get("model") or "").strip():
            raise ProviderError("missing_model")
        return ResponsesChat(ps["model"].strip(), token_fn)
    base = (ps.get("base") or meta["base"]).strip()
    model = (ps.get("model") or meta["model"]).strip()
    key = (ps.get("key") or "").strip()
    if not base:
        raise ProviderError("missing_base")
    if not model:
        raise ProviderError("missing_model")
    if meta["key"] and not key:
        raise ProviderError("missing_key")
    if meta["kind"] == "anthropic":
        return AnthropicChat(base, key, model, settings.get("effort", "medium"))
    extra = {"X-Title": TITLE} if pid == "openrouter" else {}
    return OpenAIChat(base, key, model, extra)


def list_models(settings, token_fn=None):
    pid = settings.get("provider", "openrouter")
    meta = PROVIDERS.get(pid, PROVIDERS["custom"])
    ps = settings.get("providers", {}).get(pid, {})
    base = (ps.get("base") or meta["base"]).rstrip("/")
    key = (ps.get("key") or "").strip()
    if meta["kind"] == "responses":
        d = http_json(CG_API + "/models", None, {"Authorization": "Bearer " + token_fn()}, timeout=30)
        return [str(m["slug"]) for m in (d.get("models") or [])
                if m.get("slug") and m.get("visibility", "list") == "list"]
    if meta["key"] and not key:
        raise ProviderError("missing_key")
    if pid == "openrouter":
        # verifica la chiave (l'elenco dei modelli di OpenRouter e pubblico)
        http_json(base + "/key", None, {"Authorization": "Bearer " + key}, timeout=30)
    if meta["kind"] == "anthropic":
        headers = {"x-api-key": key, "anthropic-version": ANTHROPIC_VERSION}
        d = http_json(base + "/models?limit=100", None, headers, timeout=30)
        return [m["id"] for m in d.get("data", [])]
    headers = {"Authorization": "Bearer " + key} if key else {}
    d = http_json(base + "/models", None, headers, timeout=30)
    items = d.get("data") or d.get("models") or []
    ids = []
    for m in items:
        if pid == "openrouter" and "tools" not in (m.get("supported_parameters") or []):
            continue
        mid = m.get("id") or m.get("name")
        if mid:
            ids.append(str(mid).replace("models/", "") if pid == "gemini" else str(mid))
    return sorted(set(ids))



# ------------------------------------------------------------------ plugin --

class Assistant(orca.script.ScriptPluginCapabilityBase):
    def __init__(self):
        super().__init__()
        self.panel = None
        self.tab = None
        self.hidden = False
        self.settings = None
        self.lang = "en"
        self.outbox = collections.deque()
        self.lock = threading.Lock()
        self.jobs = queue.Queue()
        self.worker = None
        self.busy = False
        self.conv = None
        self.conv_sig = None
        self.last_context = None
        self.proposals = {}
        self.undo_stack = []       # [(id proposta, gruppi per annullare)], usato solo dal thread di lavoro
        self.baselines = {}        # (ptype, nome preset, chiave) -> primo valore visto in questa sessione
        self.login = {}            # verifier / stato del login OpenRouter in corso
        self.login_cancel = threading.Event()
        self.settings_lock = threading.RLock()    # impostazioni scritte anche dal thread di lavoro (token)
        self._skills = None

    def get_name(self):
        return TITLE

    # ---- apertura pannello ----
    def execute(self):
        # Avviato di nuovo (Plugin, o Speed Dial: Spazio, oppure Alt+1 se fissato) apre o chiude il pannello.
        if self.panel is not None and self.panel.is_open():
            if self.hidden:
                self.reopen()
                return orca.ExecutionResult.success("Shown")
            self.collapse(notify=False)
            return orca.ExecutionResult.success("Hidden")
        self.hidden = False
        self.panel = orca.host.ui.create_dock_panel(
            html=PAGE, title=PANEL_TITLE, width=PANEL_WIDTH, height=720,
            on_message=self.on_message, on_close=self.on_close, dock="right")
        return orca.ExecutionResult.success("Panel opened")

    def on_close(self):
        self.panel = None
        self.hidden = False
        self.close_tab()

    # ---- linguetta sulla destra: il pannello si nasconde senza perdere la chat ----
    # Orca esegue show/hide/close dei pannelli piu tardi, nell'ordine in cui li chiediamo; close() rimuove il
    # pannello ancora piu tardi. Il pannello che sparisce va quindi nascosto PRIMA di mostrare l'altro, mai
    # chiuso: altrimenti i due stanno insieme per un attimo nella stessa colonna e il pannello grande si
    # apre largo quanto la linguetta.
    def reopen(self):
        if self.tab is not None:
            try:
                self.tab.hide()
            except Exception:
                self.tab = None
        if self.panel is not None:
            self.panel.show()
            self.hidden = False
        return True

    def collapse(self, notify=True):
        if self.panel is None:
            return
        self.panel.hide()
        self.hidden = True
        if self.tab is not None and self.tab.is_open():
            self.tab.show()                      # la linguetta esiste gia (nascosta): si riusa
            return
        try:
            self.tab = orca.host.ui.create_dock_panel(
                html=TAB_PAGE, title=TAB_TITLE, width=TAB_WIDTH, height=320,
                on_message=self.on_tab_message, on_close=self.on_tab_close, dock="right")
        except Exception as exc:
            log("linguetta", repr(exc))
            self.tab = None
            self.reopen()                        # senza linguetta non si nasconde: meglio non perderlo

    def on_tab_message(self, data):
        if (data or {}).get("type") == "expand":
            self.reopen()

    def on_tab_close(self):
        self.tab = None                          # chiusa con la X: si riapre da Spazio → «Assistente»

    def close_tab(self):
        tab, self.tab = self.tab, None
        if tab is not None:
            try:
                tab.close()
            except Exception:
                pass

    def on_unload(self):
        self.close_tab()
        self.login_cancel.set()
        self.jobs.put(None)
        if self.panel is not None:
            try:
                self.panel.close()
            except Exception:
                pass

    # ---- cartelle e impostazioni ----
    def storage(self):
        d = None
        try:
            d = orca.host.plugin.storage()
        except Exception:
            d = None
        if not d:
            base = data_dir() or os.path.expanduser("~")
            d = os.path.join(base, "orca_plugins", ".print_doctor")
        d = str(d)
        os.makedirs(d, exist_ok=True)
        return d

    def skills_dir(self):
        d = os.path.join(self.storage(), "skills")
        os.makedirs(d, exist_ok=True)
        return d

    def skills(self, reload=False):
        if self._skills is None or reload:
            self._skills = load_skills(self.skills_dir())
        return self._skills

    def load_settings(self):
        if self.settings is not None:
            return self.settings
        s = {"provider": "chatgpt", "providers": {}, "auto_apply": False, "effort": "medium"}
        try:
            with open(os.path.join(self.storage(), SETTINGS_FILE), "r", encoding="utf-8") as fh:
                s.update(json.load(fh))
        except FileNotFoundError:
            pass
        except Exception as exc:
            log("impostazioni non lette", repr(exc))
        self.settings = s
        return s

    def save_settings(self):
        with self.settings_lock:
            path = os.path.join(self.storage(), SETTINGS_FILE)
            tmp = path + ".tmp"
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)   # contiene chiavi e token
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self.settings, fh, indent=2)
            os.replace(tmp, path)
            try:
                os.chmod(path, 0o600)
            except Exception:
                pass

    def provider_settings(self, pid):
        with self.settings_lock:
            return self.load_settings().setdefault("providers", {}).setdefault(pid, {})

    def settings_copy(self):
        with self.settings_lock:
            return json.loads(json.dumps(self.load_settings()))

    # ---- ChatGPT: token di accesso sempre valido (thread di lavoro) ----
    def chatgpt_token(self, force=False):
        with self.settings_lock:
            cg = self.provider_settings("chatgpt")
            if not cg.get("refresh_token") and not cg.get("access_token"):
                raise ProviderError("missing_login")
            if not force and cg.get("access_token") and time.time() < float(cg.get("expires_at", 0)) - 120:
                return cg["access_token"]
            if not cg.get("refresh_token"):
                raise ProviderError("login_expired")
            try:
                d = http_form(CG_TOKEN, {"grant_type": "refresh_token", "client_id": cg["client_id"],
                                         "refresh_token": cg["refresh_token"], "resource": CG_RESOURCE})
            except ProviderError as exc:
                if exc.code in ("invalid_grant", "invalid_refresh_token", "token_expired", "refresh_token_expired",
                                "refresh_token_invalidated", "refresh_token_reused") or exc.status in (400, 401):
                    for k in ("access_token", "refresh_token", "expires_at"):
                        cg.pop(k, None)
                    self.save_settings()
                    raise ProviderError("login_expired")
                raise
            cg["access_token"] = d["access_token"]
            if d.get("refresh_token"):
                cg["refresh_token"] = d["refresh_token"]
            cg["expires_at"] = time.time() + float(d.get("expires_in", 3600))
            if d.get("scope"):
                cg["scopes"] = d["scope"].split()
                cg["plan"] = CG_PLAN_SCOPE in cg["scopes"]
            self.save_settings()
            return cg["access_token"]

    def public_settings(self):
        s = self.load_settings()
        provs = {}
        for pid, meta in PROVIDERS.items():
            ps = s.get("providers", {}).get(pid, {})
            key = ps.get("key") or ""
            provs[pid] = {"label": meta["label"], "kind": meta["kind"], "needs_key": meta["key"],
                          "login": bool(meta.get("login")) or pid == "openrouter", "key_page": KEY_PAGES.get(pid, ""),
                          "base": ps.get("base") or "", "default_base": meta["base"],
                          "model": ps.get("model") or "", "default_model": meta["model"],
                          "has_key": bool(key), "key_hint": ("..." + key[-4:]) if len(key) > 8 else ""}
            if pid == "chatgpt":
                provs[pid].update(signed_in=bool(ps.get("refresh_token") or ps.get("access_token")),
                                  email=ps.get("email", ""), plan=bool(ps.get("plan")),
                                  welcomed=bool(ps.get("welcomed")), usage_url=CG_USAGE_URL,
                                  known=bool(ps.get("client_id")))
        return {"provider": s.get("provider"), "providers": provs, "auto_apply": bool(s.get("auto_apply")),
                "effort": s.get("effort", "medium")}

    # ---- thread di lavoro (uno solo) ----
    def emit(self, kind, **data):
        data["kind"] = kind
        with self.lock:
            self.outbox.append(data)

    def ensure_worker(self):
        if self.worker is not None and self.worker.is_alive():
            return
        self.worker = threading.Thread(target=self._work, name="print-doctor", daemon=True)
        self.worker.start()

    def submit(self, fn, *args):
        self.ensure_worker()
        self.busy = True
        self.jobs.put((fn, args))

    def _work(self):
        while True:
            job = self.jobs.get()
            if job is None:
                return
            fn, args = job
            try:
                fn(*args)
            except Exception:
                self.emit("error", text=traceback.format_exc(limit=3))
            finally:
                if self.jobs.empty():
                    self.busy = False
                    self.emit("idle")

    # ---- chat (thread di lavoro: niente accesso al modello di Orca qui) ----
    def chat_job(self, text, images, snap, settings, skills, lang):
        ps = settings.get("providers", {}).get(settings.get("provider"), {})
        sig = json.dumps([settings.get("provider"), {k: ps.get(k) for k in ("model", "base", "key", "client_id", "plan")},
                          settings.get("effort")], sort_keys=True)          # i token che si rinnovano non contano
        if self.conv is None or self.conv_sig != sig:
            try:
                self.conv = make_conversation(settings, self.chatgpt_token)
            except ProviderError as exc:
                self.emit("error", text=str(exc))
                return
            self.conv_sig = sig
            self.last_context = None
        conv = self.conv
        start = len(conv.history)
        context = context_text(snap)
        prefix = "" if context == self.last_context else context + "\n\n"
        if settings.get("auto_apply"):
            prefix += "[Auto-apply is ON]\n\n"
        try:
            conv.add_user(prefix + "[User]\n" + (text or "(see the photo)"), images)
            ctx = ToolContext(snap, skills, bool(settings.get("auto_apply")))
            system = build_system(skills, lang)
            for _ in range(MAX_STEPS):
                self.emit("status", text="thinking")
                out_text, calls, _stop = conv.step(system, TOOLS)
                if out_text.strip():
                    self.emit("assistant", text=out_text.strip())
                if not calls:
                    break
                results = []
                for cid, name, args in calls:
                    tool = str(name or "").split(".")[-1]      # alcune API antepongono il namespace ("orca.")
                    self.emit("status", text="tool:" + tool)
                    try:
                        res = run_tool(ctx, tool, args)
                        results.append((cid, name, json.dumps(res, ensure_ascii=False), "error" in res))
                        self.emit("step", **step_info(tool, args, res))
                    except Exception as exc:
                        results.append((cid, name, json.dumps({"error": repr(exc)}), True))
                conv.add_tool_results(results)
            else:
                self.emit("assistant", text="(step limit reached)")
        except Exception as exc:
            del conv.history[start:]          # il turno fallito (per qualsiasi errore) non resta nella conversazione
            if isinstance(exc, ProviderError):
                self.emit("error", text=str(exc))
            else:
                log("chat", traceback.format_exc())
                self.emit("error", text="%s: %s" % (type(exc).__name__, exc))
            return
        self.last_context = context
        if ctx.proposal:
            self.emit("proposal", proposal=ctx.proposal)

    def models_job(self, settings):
        pid = settings.get("provider")
        try:
            models = list_models(settings, self.chatgpt_token)
            with self.settings_lock:
                ps = self.provider_settings(pid)
                if pid == "chatgpt" and models and ps.get("model") not in models:
                    ps["model"] = models[0]
                    self.save_settings()
            self.emit("models", provider=pid, models=models)
        except ProviderError as exc:
            self.emit("models_error", provider=pid, text=str(exc))

    def open_url_job(self, url):
        try:
            webbrowser.open(url)
        except Exception as exc:
            self.emit("error", text="browser: %r" % (exc,))

    # ---- login OpenRouter (OAuth PKCE con ritorno su localhost) ----
    def login_job(self, provider="openrouter"):
        if provider == "chatgpt":
            return self.chatgpt_login_job()
        verifier = b64url(secrets.token_bytes(48))
        challenge = b64url(hashlib.sha256(verifier.encode("ascii")).digest())
        state = secrets.token_urlsafe(16)
        got = {}

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                u = urllib.parse.urlparse(self.path)
                q = urllib.parse.parse_qs(u.query)
                if u.path != "/callback":
                    self.send_response(404)
                    self.end_headers()
                    return
                got["code"] = (q.get("code") or [None])[0]
                got["state"] = (q.get("state") or [None])[0]
                body = ("<html><body style='font-family:sans-serif;padding:40px'>"
                        "<h2>OK</h2><p>Torna in OrcaSlicer. / Go back to OrcaSlicer.</p></body></html>").encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        srv.timeout = 0.5
        port = srv.server_address[1]
        params = {"callback_url": "http://localhost:%d/callback" % port, "code_challenge": challenge,
                  "code_challenge_method": "S256", "key_label": "%s (OrcaSlicer)" % TITLE, "state": state}
        url = "https://openrouter.ai/auth?" + urllib.parse.urlencode(params)
        self.login = {"verifier": verifier}
        self.login_cancel.clear()
        self.emit("login_url", url=url)
        try:
            webbrowser.open(url)
        except Exception:
            pass
        deadline = time.time() + 600
        try:
            while time.time() < deadline and not got.get("code") and not self.login_cancel.is_set():
                srv.handle_request()
        finally:
            srv.server_close()
        if self.login_cancel.is_set() and not got.get("code"):
            if not self.login.get("manual"):
                self.emit("login_done", ok=False, text="cancelled")
            return
        if not got.get("code"):
            self.emit("login_done", ok=False, text="timeout")
            return
        if got.get("state") != state:
            self.emit("login_done", ok=False, text="state mismatch")
            return
        self.exchange_code(got["code"], verifier)

    def exchange_code(self, code, verifier):
        try:
            d = http_json("https://openrouter.ai/api/v1/auth/keys",
                          {"code": code, "code_verifier": verifier, "code_challenge_method": "S256"}, timeout=30)
            key = d.get("key")
            if not key:
                raise ProviderError("no key in the response")
            with self.settings_lock:
                self.provider_settings("openrouter")["key"] = key
                self.settings["provider"] = "openrouter"
                self.save_settings()
            self.emit("login_done", ok=True, provider="openrouter")
        except ProviderError as exc:
            self.emit("login_done", ok=False, provider="openrouter", text=str(exc))

    # ---- Sign in with ChatGPT (OAuth PKCE + registrazione dinamica, ritorno su 127.0.0.1) ----
    def chatgpt_login_job(self):
        cg = self.provider_settings("chatgpt")
        with self.settings_lock:
            host_id = self.settings.get("host_id")
            if not host_id:
                host_id = self.settings["host_id"] = "urn:uuid:" + str(uuid.uuid4())   # prima del primo accesso
                self.save_settings()
        client_id = cg.get("client_id") or ""
        verifier = b64url(secrets.token_bytes(48))
        challenge = b64url(hashlib.sha256(verifier.encode("ascii")).digest())
        state, nonce = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
        got = {}

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                u = urllib.parse.urlparse(self.path)
                if u.path != "/auth/callback":
                    self.send_response(404)
                    self.end_headers()
                    return
                q = urllib.parse.parse_qs(u.query)
                for k in ("code", "state", "client_id", "error", "error_description", "scope"):
                    got[k] = (q.get(k) or [None])[0]
                ok = bool(got.get("code"))
                body = ("<html><head><meta charset='utf-8'></head><body style='font-family:system-ui,sans-serif;"
                        "background:#1e1f22;color:#e8e8ea;padding:48px;text-align:center'><h2>%s</h2>"
                        "<p>Torna in OrcaSlicer. / Go back to OrcaSlicer.</p></body></html>"
                        % ("Accesso completato ✔" if ok else "Accesso non completato")).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        try:
            srv = http.server.HTTPServer(("127.0.0.1", 1455), Handler)
        except OSError:
            srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)   # porta occupata: solo la porta puo cambiare
        srv.timeout = 0.5
        redirect = "http://127.0.0.1:%d/auth/callback" % srv.server_address[1]
        params = {"response_type": "code", "redirect_uri": redirect, "scope": CG_SCOPES, "resource": CG_RESOURCE,
                  "state": state, "nonce": nonce, "code_challenge": challenge, "code_challenge_method": "S256",
                  "ext_agent_host_id": host_id}
        if client_id:
            params["client_id"] = client_id
            if cg.get("sub") and not cg.get("plan"):
                params["prompt"] = "consent"           # aveva rifiutato l'uso del piano: lo richiede di nuovo
            if cg.get("id_token"):
                params["id_token_hint"] = cg["id_token"]
            if cg.get("email"):
                params["login_hint"] = cg["email"]
        else:
            params["client_id"] = "dynamic_agent_client"
            params["agent_name_hint"] = CG_AGENT_NAME
        url = CG_AUTHORIZE + "?" + urllib.parse.urlencode(params)
        # se il browser non si apre il pannello copia negli appunti questo indirizzo (mai mostrato): come url,
        # ma senza id_token_hint e login_hint
        copy = CG_AUTHORIZE + "?" + urllib.parse.urlencode(
            {k: v for k, v in params.items() if k not in ("id_token_hint", "login_hint")})
        self.login_cancel.clear()
        self.emit("login_url", provider="chatgpt", url=CG_AUTHORIZE, copy=copy)   # niente token nell'indirizzo mostrato
        try:
            webbrowser.open(url)
        except Exception:
            pass
        deadline = time.time() + 600
        try:
            while time.time() < deadline and not got and not self.login_cancel.is_set():
                srv.handle_request()
        finally:
            srv.server_close()
        fail = lambda text: self.emit("login_done", ok=False, provider="chatgpt", text=text)
        if not got:
            return fail("cancelled" if self.login_cancel.is_set() else "timeout")
        if got.get("state") != state:
            return fail("state mismatch")
        if got.get("error"):
            return fail("chatgpt_denied" if got["error"] == "access_denied" else
                        "%s %s" % (got["error"], got.get("error_description") or ""))
        issued = got.get("client_id") or client_id
        if not issued or issued == "dynamic_agent_client":
            return fail("registration incomplete: no client_id")
        if client_id and got.get("client_id") and got["client_id"] != client_id:
            return fail("chatgpt_other_account")
        if not client_id:
            with self.settings_lock:                 # registrazione riuscita: il client_id va conservato
                cg["client_id"] = issued
                self.save_settings()
        try:
            d = http_form(CG_TOKEN, {"grant_type": "authorization_code", "client_id": issued, "code": got["code"],
                                     "code_verifier": verifier, "redirect_uri": redirect, "resource": CG_RESOURCE})
            claims = verify_id_token(d.get("id_token", ""), issued, nonce)
        except Exception as exc:
            return fail(str(exc) if isinstance(exc, ProviderError) else "%s: %s" % (type(exc).__name__, exc))
        scopes = (d.get("scope") or got.get("scope") or "").split()
        with self.settings_lock:
            if cg.get("sub") and cg["sub"] != claims.get("sub") and client_id:
                return fail("chatgpt_other_account")
            cg.update(client_id=issued, sub=claims.get("sub"), email=claims.get("email", ""),
                      id_token=d.get("id_token"), access_token=d.get("access_token"),
                      refresh_token=d.get("refresh_token"), scopes=scopes, plan=CG_PLAN_SCOPE in scopes,
                      expires_at=time.time() + float(d.get("expires_in", 3600)))
            self.settings["provider"] = "chatgpt"
            self.save_settings()
        models = []
        if cg.get("plan"):
            try:
                models = list_models(self.settings_copy(), self.chatgpt_token)
                with self.settings_lock:
                    if models and cg.get("model") not in models:
                        cg["model"] = models[0]
                        self.save_settings()
            except ProviderError as exc:
                log("modelli ChatGPT", str(exc))
        self.emit("login_done", ok=True, provider="chatgpt", plan=bool(cg.get("plan")), models=models)

    def chatgpt_logout_job(self, forget=False):
        cg = self.provider_settings("chatgpt")
        note = ""
        if cg.get("refresh_token") and cg.get("client_id"):
            try:
                conf = http_json(CG_AUTH + "/.well-known/openid-configuration", None, timeout=30)
                http_form(conf["revocation_endpoint"], {"token": cg["refresh_token"],
                                                        "token_type_hint": "refresh_token", "client_id": cg["client_id"]})
            except Exception as exc:
                note = "revoke_unconfirmed"
                log("revoca ChatGPT", repr(exc))
        keys = ("access_token", "refresh_token", "id_token", "expires_at")
        if forget:
            keys += ("client_id", "sub", "email", "scopes", "plan", "model", "welcomed")
        with self.settings_lock:
            for k in keys:
                cg.pop(k, None)              # client_id resta per il prossimo accesso (non con forget); host_id sempre
            self.save_settings()
        self.emit("logged_out", provider="chatgpt", note=note)

    def chatgpt_forget_job(self):
        """Dimentica l'account ChatGPT per poter accedere con un altro: stessa revoca dell'uscita, poi via
        anche la registrazione (client_id) e i dati dell'account. settings["host_id"] resta."""
        self.chatgpt_logout_job(forget=True)

    # ---- valori di partenza (thread UI) ----
    def baseline(self, snap):
        """Ricorda, la prima volta che li vede, portata volumetrica massima e temperature del piatto del
        filamento in uso: i limiti "+10%" e "+10 C" si contano da questi valori, non a ogni richiesta.
        Restituisce {(ptype, chiave): valore di partenza} per i preset della fotografia."""
        out = {}
        name = (snap["presets"].get("filament") or {}).get("name")
        for key, v in (snap["values"].get("filament") or {}).items():
            if key == "filament_max_volumetric_speed" or "plate_temp" in key or "bed_temp" in key:
                out[("filament", key)] = self.baselines.setdefault(("filament", name, key), v)
        return out

    # ---- applicazione delle modifiche ----
    # Orca 2.5.1: orca.host.preset.<tipo>.begin_update() / set() / commit() modifica il preset in uso
    # come se l'utente cambiasse i campi a mano (modifiche non salvate). Va chiamato da un thread di
    # lavoro, mai dal thread UI: il piano si prepara sul thread UI, il commit sul thread di lavoro.
    def build_plan(self, proposal):
        b = orca.host.preset_bundle()
        snap = take_snapshot()
        vals, base = snap["values"], self.baseline(snap)   # valori di adesso, per ricontrollare la sicurezza
        groups = collections.OrderedDict()
        blocked = []
        for ch in proposal["changes"]:
            ptype = ch["preset"]
            err = safety_error(ptype, ch["key"], ch["new"], vals, base)
            if err:
                blocked.append({"preset": ptype, "name": ch["key"], "ok": False, "text": "%s: %s" % (ch["key"], err)})
                continue
            g = groups.get(ptype)
            if g is None:
                if ptype == "filament":
                    cur, slot = filament_target(b)
                else:
                    cur, slot = current_preset(b, ptype), None
                if cur is None:
                    raise RuntimeError("no current %s preset" % ptype)
                g = groups[ptype] = {"ptype": ptype, "slot": slot, "name": cur.name, "set": [], "undo": [], "_p": cur}
            raw = g["_p"].config_value(ch["key"])
            g["set"].append((ch["key"],) + serialized(raw, ch["new"]))
            g["undo"].append((ch["key"],) + serialized(raw))
        plan = list(groups.values())
        for g in plan:
            g.pop("_p", None)
        return plan, blocked

    @staticmethod
    def commit_group(g):
        if g["ptype"] not in ("process", "filament"):
            raise RuntimeError("printer settings are never changed by this plugin")
        editor = getattr(orca.host.preset, g["ptype"], None)
        if editor is None or not hasattr(editor, "begin_update"):
            raise RuntimeError("this OrcaSlicer version cannot change presets from plugins (2.5.1 or newer needed)")

        def run(items):
            tx = editor.begin_update(g["slot"]) if g["ptype"] == "filament" else editor.begin_update()
            for key, value in items:
                tx.set(key, value)
            return tx.commit()
        try:
            return run([(k, v) for k, v, _a in g["set"]]), []
        except ValueError as first:
            # Orca ha rifiutato il blocco: riprova chiave per chiave, anche con l'altro separatore di lista
            res, failed = None, []
            for key, value, alt in g["set"]:
                err = None
                for cand in (value, alt):
                    if cand is None:
                        continue
                    try:
                        res = run([(key, cand)])
                        err = None
                        break
                    except ValueError as exc:
                        err = exc
                if err is not None:
                    failed.append("%s: %s" % (key, err))
            if res is None:
                raise first
            return res, failed

    def apply_job(self, pid, plan, blocked=()):
        results, undo = list(blocked), []
        for g in plan:
            r = {"preset": g["ptype"], "name": g["name"], "slot": g["slot"]}
            try:
                res, failed = self.commit_group(g)
                r.update(ok=True, name=str(getattr(res, "target_name", g["name"]) or g["name"]),
                         dirty=bool(getattr(res, "dirty", True)))
                if failed:
                    r["text"] = "; ".join(failed)
                undo.append({"ptype": g["ptype"], "slot": g["slot"], "name": r["name"], "set": g["undo"]})
            except Exception as exc:
                log("applica", g["ptype"], traceback.format_exc())
                r.update(ok=False, text="%s: %s" % (type(exc).__name__, exc))
            results.append(r)
        if undo:
            self.undo_stack.append((pid, undo))
        self.emit("applied", id=pid, result={"results": results})

    def undo_job(self, pid=None):
        # annulla la proposta indicata (la scheda premuta); senza id, l'ultima applicata
        idx = next((i for i in range(len(self.undo_stack) - 1, -1, -1)
                    if pid is None or self.undo_stack[i][0] == pid), None)
        if idx is None:
            self.emit("undone", id=pid, result={"results": [], "text": "nothing to undo"})
            return
        pid, groups = self.undo_stack.pop(idx)
        results = []
        for g in groups:
            r = {"preset": g["ptype"], "name": g["name"]}
            try:
                _res, failed = self.commit_group(g)
                r["ok"] = not failed
                if failed:
                    r["text"] = "; ".join(failed)
            except Exception as exc:
                log("annulla", g["ptype"], traceback.format_exc())
                r.update(ok=False, text="%s: %s" % (type(exc).__name__, exc))
            results.append(r)
        self.emit("undone", id=pid, result={"results": results})

    def context_info(self):
        """Stampante, processo e filamento in uso, per la striscia in alto nel pannello."""
        out = {"type": "context"}
        try:
            b = orca.host.preset_bundle()
            for ptype in ("printer", "process"):
                p = current_preset(b, ptype)
                out[ptype] = p.name if p is not None else ""
                out[ptype + "_dirty"] = bool(getattr(p, "is_dirty", False))
            p, slot = filament_target(b)
            out["filament"] = p.name if p is not None else ""
            out["filament_dirty"] = bool(getattr(p, "is_dirty", False))
            out["slot"] = slot
            try:
                out["slots"] = len(list(b.current_filament_preset_names() or []))
            except Exception:
                out["slots"] = 1
            try:
                col = to_plain(p.config_value("filament_colour"))
                col = col[0] if isinstance(col, list) and col else col
                if isinstance(col, str) and re.match(r"^#[0-9A-Fa-f]{6}", col):
                    out["color"] = col[:7]
            except Exception:
                pass
        except Exception as exc:
            out["error"] = repr(exc)
        return out

    # ---- diagnostica (per i test) ----
    def diagnostics(self):
        def pub(o):
            try:
                return [n for n in dir(o) if not n.startswith("_")]
            except Exception as exc:
                return repr(exc)
        b = orca.host.preset_bundle()
        out = {"version": VERSION, "orca": pub(orca), "orca.host": pub(orca.host), "orca.host.ui": pub(orca.host.ui)}
        for label, fn in (("orca.host.preset", lambda: orca.host.preset),
                          ("orca.host.preset.bundles", lambda: orca.host.preset.bundles),
                          ("Plater", lambda: orca.host.plater())):
            try:
                out[label] = pub(fn())
            except Exception as exc:
                out[label] = repr(exc)
        out["PresetBundle"] = pub(b)
        out["PresetCollection"] = pub(b.prints)
        try:
            out["Preset"] = pub(current_preset(b, "process"))
        except Exception as exc:
            out["Preset"] = repr(exc)
        try:
            out["bundle_ids"] = list(orca.host.preset.bundles.list_ids())
        except Exception as exc:
            out["bundle_ids"] = repr(exc)
        try:
            out["write_api"] = {t: hasattr(getattr(orca.host.preset, t, None), "begin_update")
                                for t in ("process", "filament", "printer")}
        except Exception as exc:
            out["write_api"] = repr(exc)
        try:
            out["filament_slots"] = list(b.current_filament_preset_names())
            out["filament_target"] = filament_target(b)[1]
        except Exception as exc:
            out["filament_slots"] = repr(exc)
        for label, fn in (("app_info", lambda: orca.host.app_info()), ("orca.host.plugin", lambda: pub(orca.host.plugin))):
            try:
                v = fn()
                out[label] = v if isinstance(v, (list, dict, str, int, float, bool)) else {n: repr(getattr(v, n, None))[:120] for n in pub(v)}
            except Exception as exc:
                out[label] = repr(exc)
        out["lang"] = self.lang
        out["storage"] = self.storage()
        try:
            snap = take_snapshot()
            out["snapshot"] = {"presets": snap["presets"], "errors": snap["errors"], "plate": snap["plate"][:5],
                               "n_values": {k: len(v) for k, v in snap["values"].items()}}
        except Exception:
            out["snapshot"] = traceback.format_exc()
        return out

    # ---- messaggi dal pannello (thread UI) ----
    def post(self, data):
        if self.panel is not None:
            try:
                self.panel.post(data)
            except Exception as exc:
                log("post", repr(exc))

    def on_message(self, data):
        data = data or {}
        kind = data.get("type")
        try:
            self.handle(kind, data)
        except Exception as exc:
            log("errore", kind, traceback.format_exc())
            self.post({"type": "events", "busy": self.busy,
                       "events": [{"kind": "error", "text": "%s: %s" % (type(exc).__name__, exc)}]})

    def handle(self, kind, data):
        s = self.load_settings()
        if kind == "ready":
            lang = ""
            fn = getattr(orca.host, "app_language", None)
            if fn is not None:
                try:
                    lang = str(fn() or "")
                except Exception:
                    lang = ""
            if not lang:
                lang = str(data.get("lang") or "")      # lingua della pagina (sistema)
            self.lang = "it" if lang.lower().startswith("it") else "en"
            with self.lock:
                pending = bool(self.outbox)
            if not self.busy and not pending and self.conv is not None:
                self.conv = None                 # pagina nuova e vuota, niente in arrivo: come "new_chat"
                self.last_context = None
                self.proposals.clear()
            self.post({"type": "state", "lang": self.lang, "version": VERSION, "settings": self.public_settings(),
                       "donate": DONATE_URL, "meshdab": MESHDAB_URL, "skills_dir": self.skills_dir(),
                       "skills": sorted(self.skills()), "busy": self.busy})
        elif kind == "poll":
            events = []
            with self.lock:
                while self.outbox:
                    events.append(self.outbox.popleft())
            for ev in events:
                if ev["kind"] in ("login_done", "logged_out", "models"):
                    ev["settings"] = self.public_settings()
                if ev["kind"] == "proposal":
                    self.proposals[ev["proposal"]["id"]] = ev["proposal"]
            self.post({"type": "events", "events": events, "busy": self.busy})
        elif kind == "send":
            text = str(data.get("text") or "").strip()
            images = [im for im in (data.get("images") or []) if im.get("data")][:3]
            if not text and not images:
                return
            snap = take_snapshot()
            snap["base"] = self.baseline(snap)
            self.submit(self.chat_job, text, images, snap, self.settings_copy(), self.skills(), self.lang)
            self.post({"type": "events", "events": [], "busy": True})
        elif kind == "apply":
            prop = self.proposals.get(data.get("id"))
            if not prop:
                raise RuntimeError("proposal not found")
            keys = data.get("keys")
            if isinstance(keys, list):
                prop = dict(prop, changes=[c for c in prop["changes"] if c["key"] in keys])
            if not prop["changes"]:
                raise RuntimeError("no change selected")
            plan, blocked = self.build_plan(prop)
            self.submit(self.apply_job, prop["id"], plan, blocked)
            self.post({"type": "events", "events": [], "busy": True})
        elif kind == "undo":
            self.submit(self.undo_job, str(data["id"]) if data.get("id") else None)
            self.post({"type": "events", "events": [], "busy": True})
        elif kind == "new_chat":
            self.conv = None
            self.last_context = None
            self.proposals.clear()
            self.post({"type": "cleared"})
        elif kind == "save_settings":
            pid = data.get("provider")
            if pid in PROVIDERS:
                s["provider"] = pid
                ps = s.setdefault("providers", {}).setdefault(pid, {})
                for field in ("model", "base"):
                    if field in data:
                        ps[field] = str(data.get(field) or "").strip()
                if data.get("key"):
                    ps["key"] = str(data["key"]).strip()
                if data.get("clear_key"):
                    ps.pop("key", None)
            if "auto_apply" in data:
                s["auto_apply"] = bool(data["auto_apply"])
            if data.get("effort") in ("low", "medium", "high", "xhigh", "max"):
                s["effort"] = data["effort"]
            self.save_settings()
            self.post({"type": "settings", "settings": self.public_settings()})
        elif kind == "models":
            self.submit(self.models_job, self.settings_copy())
            self.post({"type": "events", "events": [], "busy": True})
        elif kind == "login_start":
            self.submit(self.login_job, "chatgpt" if data.get("provider") == "chatgpt" else "openrouter")
            self.post({"type": "events", "events": [], "busy": True})
        elif kind == "login_cancel":
            self.login_cancel.set()
        elif kind == "login_code":
            raw = str(data.get("code") or "").strip()
            m = re.search(r"[?&]code=([^&#]+)", raw)
            code = urllib.parse.unquote(m.group(1)) if m else raw
            verifier = self.login.get("verifier")
            if not code or not verifier:
                raise RuntimeError("start the login first")
            self.login["manual"] = True
            self.login_cancel.set()
            self.submit(self.exchange_code, code, verifier)
            self.post({"type": "events", "events": [], "busy": True})
        elif kind == "logout":
            self.submit(self.chatgpt_logout_job)
            self.post({"type": "events", "events": [], "busy": True})
        elif kind == "forget_account":
            self.submit(self.chatgpt_forget_job)
            self.post({"type": "events", "events": [], "busy": True})
        elif kind == "welcomed":
            with self.settings_lock:
                self.provider_settings("chatgpt")["welcomed"] = True
                self.save_settings()
        elif kind == "open_key_page":
            url = KEY_PAGES.get(str(data.get("provider")), "")
            if url:
                self.submit(self.open_url_job, url)
        elif kind == "open_usage":
            self.submit(self.open_url_job, CG_USAGE_URL)
        elif kind == "open_url":
            url = str(data.get("url") or "")
            if url.startswith("https://"):
                self.submit(self.open_url_job, url)
        elif kind == "reload_skills":
            self.post({"type": "skills", "skills": sorted(self.skills(reload=True)), "skills_dir": self.skills_dir()})
        elif kind == "collapse":
            self.collapse()
        elif kind == "context":
            self.post(self.context_info())
        elif kind == "diagnostics":
            self.post({"type": "diagnostics", "result": self.diagnostics()})
        else:
            raise RuntimeError("unknown message %r" % (kind,))


@orca.plugin
class AssistantPlugin(orca.base):
    def register_capabilities(self):
        orca.request_permissions(
            network_http=[
                "https://auth.openai.com/api/accounts/oauth/token",
                "https://auth.openai.com/.well-known/openid-configuration",
                "https://api.openai.com/v1/responses",
                "https://api.openai.com/v1/models",
                "https://api.openai.com/v1/chat/completions",
                "https://openrouter.ai/api/v1/chat/completions",
                "https://openrouter.ai/api/v1/auth/keys",
                "https://openrouter.ai/api/v1/models",
                "https://openrouter.ai/api/v1/key",
                "https://api.anthropic.com/v1/messages",
                "https://api.anthropic.com/v1/models",
                "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                "https://generativelanguage.googleapis.com/v1beta/openai/models",
            ],
            threading=True,
        )
        orca.register_capability(Assistant)


TAB_PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}html,body{height:100%;margin:0}
body{background:#2a2b2f;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;overflow:hidden}
button{all:unset;box-sizing:border-box;cursor:pointer;width:100%;height:100%;display:flex;flex-direction:column;align-items:center;
 justify-content:flex-start;gap:12px;padding:12px 0;color:#e8e8ea;background:#2a2b2f;border-left:3px solid #6cc4e0;transition:background .15s}
button:hover{background:#34353a}button:focus-visible{outline:2px solid #6cc4e0;outline-offset:-3px}
.ic{width:28px;height:28px;border-radius:8px;background:rgba(108,196,224,.16);color:#6cc4e0;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.tx{writing-mode:vertical-rl;font-size:13px;font-weight:650;letter-spacing:.04em;white-space:nowrap}
.tx b{color:#6cc4e0;font-weight:700}
.ar{margin-top:auto;color:#a9abb1;display:flex}
</style></head><body>
<button id="b" type="button" aria-label="Print Doctor" title="Print Doctor">
 <span class="ic"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M18 6l-2.5 2.5M8.5 15.5L6 18"></path></svg></span>
 <span class="tx">Print <b>Doctor</b></span>
 <span class="ar"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 17l-5-5 5-5M18 17l-5-5 5-5"></path></svg></span>
</button>
<script>document.getElementById("b").onclick=function(){if(window.orca&&orca.postMessage)orca.postMessage({type:"expand"})};</script>
</body></html>"""


PAGE = r"""<!doctype html><html><head><meta charset="utf-8">
<style>
:root{--bg:#1e1f22;--panel:#26272b;--bar:#2a2b2f;--raised:#2d2e33;--control:#34353a;--hover:#3f4046;--active:#46474d;--line:#3a3b40;--line-s:#4d4e54;--text:#e8e8ea;--soft:#c9cbd0;--muted:#a9abb1;--ok:#7fd1a0;--ok-bg:#1f3a2b;--warn:#e0a84f;--warn-bg:#3d3220;--acc:#6cc4e0;--acc-hi:#9bd8ec;--acc-bg:rgba(108,196,224,.16);--acc-ink:#10242c}
*{box-sizing:border-box}
[hidden]{display:none!important}
html,body{height:100%}
body{margin:0;background:var(--panel);color:var(--text);font:13px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;display:flex;flex-direction:column;overflow:hidden;-webkit-font-smoothing:antialiased}
button{font:inherit;color:inherit;cursor:pointer;border:0;background:none}
button:disabled{cursor:default;opacity:.4}
:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
svg{flex-shrink:0}
.ib{width:32px;height:32px;display:flex;align-items:center;justify-content:center;border-radius:6px;color:var(--soft)}
.ib:hover{background:var(--hover);color:var(--text)}
.lbl{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.btn{height:32px;padding:0 12px;border:1px solid var(--line);border-radius:6px;color:var(--soft);font-size:12.5px;display:inline-flex;align-items:center;gap:6px}
.btn:hover:not(:disabled){background:var(--hover);color:var(--text)}
.btn.sm{height:26px;padding:0 9px;font-size:11.5px}
.btn.pri{background:var(--acc);border-color:var(--acc);color:var(--acc-ink);font-weight:650}
.btn.pri:hover:not(:disabled){background:var(--acc-hi);border-color:var(--acc-hi);color:var(--acc-ink)}
.dots{display:inline-flex;gap:3px;align-items:center}
.dots i{width:5px;height:5px;border-radius:50%;background:var(--acc);animation:dot 1.1s infinite}
.dots i:nth-child(2){animation-delay:.15s}.dots i:nth-child(3){animation-delay:.3s}
@keyframes dot{0%,80%,100%{opacity:.25;transform:none}40%{opacity:1;transform:translateY(-2px)}}
@keyframes rise{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.rise{animation:rise .22s ease both}
/* intestazione */
header{display:flex;align-items:center;gap:2px;padding:4px 4px 4px 8px;background:var(--bar);border-bottom:1px solid var(--line);min-height:38px}
header .sp{flex:1}
#mdab{display:flex;align-items:center;gap:7px;width:100%;height:30px;padding:0 10px;background:var(--acc-bg);color:var(--acc);border-bottom:1px solid var(--line);font-size:12px;font-weight:600;text-align:left;transition:background .15s,color .15s}
#mdab span{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#mdab .go{flex:0 0 auto;transition:transform .15s}
#mdab:hover{background:rgba(108,196,224,.26);color:var(--acc-hi)}
#mdab:hover .go{transform:translateX(3px)}
#bmc{display:flex;align-items:center;gap:5px;height:26px;padding:0 10px 0 8px;margin-right:2px;border-radius:999px;background:#ffdd00;color:#0d0c22;font-size:11.5px;font-weight:700;white-space:nowrap;flex-shrink:0;box-shadow:0 1px 0 rgba(0,0,0,.25);transition:transform .15s,background .15s}
#bmc:hover{background:#ffe433;transform:translateY(-1px)}
#bmc svg{width:15px;height:15px}
header .ib{width:28px;height:28px}
.logo{width:26px;height:26px;border-radius:7px;background:var(--acc-bg);color:var(--acc);display:flex;align-items:center;justify-content:center}
.ttl{display:flex;flex-direction:column;flex:1;min-width:0}
.ttl b{font-size:13px;font-weight:600}
#prov{display:flex;align-items:center;gap:5px;height:28px;padding:0 5px;border-radius:6px;color:var(--soft);font-size:11.5px;min-width:0;overflow:hidden}
#prov:hover{background:var(--hover)}
#prov:hover{color:var(--text)}
#prov span.t{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pdot{width:6px;height:6px;border-radius:50%;background:var(--warn);flex-shrink:0}
.pdot.ok{background:var(--ok)}
/* contesto */
#ctx{display:flex;gap:6px;padding:7px 10px;border-bottom:1px solid var(--line);overflow:hidden;min-height:35px}
.cx{display:flex;align-items:center;gap:5px;padding:3px 8px;border-radius:999px;background:var(--control);color:var(--soft);font-size:11px;white-space:nowrap;min-width:0;overflow:hidden}
.cx span{overflow:hidden;text-overflow:ellipsis}
.cx .sw{width:9px;height:9px;border-radius:50%;box-shadow:0 0 0 1px rgba(0,0,0,.35);flex-shrink:0}
.cx .dirty{width:6px;height:6px;border-radius:50%;background:var(--warn);flex-shrink:0}
/* chat */
#log{flex:1;min-height:0;overflow-y:auto;padding:12px 10px 8px;display:flex;flex-direction:column;gap:10px}
#log>*{flex-shrink:0}
#log::-webkit-scrollbar{width:8px}#log::-webkit-scrollbar-thumb{background:var(--line-s);border-radius:4px}
#welcome{display:flex;flex-direction:column;gap:12px;padding-top:6px}
#welcome h1{margin:0;font-size:15px;line-height:1.25;font-weight:650}
#welcome p{margin:4px 0 0;color:var(--muted);font-size:11.5px}
.probs{display:flex;flex-wrap:wrap;gap:6px}
.prob{padding:5px 10px;border:1px solid var(--line);border-radius:999px;background:var(--raised);font-size:12px;color:var(--soft);transition:background .15s,border-color .15s,color .15s}
.prob:hover{background:var(--hover);border-color:var(--line-s);color:var(--text)}
.dropz{display:flex;align-items:center;justify-content:center;gap:8px;height:54px;border:1px dashed var(--line-s);border-radius:8px;color:var(--muted);font-size:12px}
.dropz:hover{background:var(--raised);color:var(--text)}
.u{align-self:flex-end;max-width:84%;padding:8px 11px;border-radius:12px 12px 4px 12px;background:var(--active);white-space:pre-wrap;word-wrap:break-word}
.u img{display:block;max-width:150px;max-height:110px;border-radius:6px;margin-top:6px}
.a{color:var(--soft);word-wrap:break-word}
.a p{margin:0 0 6px}.a p:last-child{margin:0}
.a b{color:var(--text)}
.a ul{margin:4px 0 6px;padding-left:18px}.a li{margin:2px 0}
code{font:11.5px ui-monospace,Menlo,monospace;background:var(--control);padding:1px 4px;border-radius:4px;color:var(--text)}
.err{display:flex;gap:8px;padding:9px 11px;border-radius:8px;background:var(--warn-bg);color:var(--warn);font-size:12px}
.err span{color:var(--text)}
.act{align-self:flex-start;display:flex;flex-direction:column;gap:6px;max-width:100%}
.pill{display:flex;align-items:center;gap:6px;padding:4px 9px;border:1px solid var(--line);border-radius:999px;color:var(--muted);font-size:11px;text-align:left;max-width:100%}
.pill:hover{background:var(--raised)}
.pill .t{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pill .ck{color:var(--ok);display:flex}
.pill .cv{transition:transform .15s;display:flex}
.act.open .pill .cv{transform:rotate(180deg)}
.steps{display:none;margin:0;padding:8px 10px 8px 26px;border-radius:8px;background:var(--bar);color:var(--muted);font-size:11px}
.act.open .steps{display:block}
.steps li{margin:2px 0}
/* scheda modifiche */
.card{border:1px solid var(--line-s);border-radius:10px;background:var(--bar);overflow:hidden}
.card.done{border-color:var(--ok)}
.card .hd{display:flex;align-items:center;gap:8px;padding:9px 10px 7px}
.card .hd .lbl{flex:1}
.cnt{padding:1px 7px;border-radius:999px;background:var(--acc-bg);color:var(--acc);font-size:11px;font-weight:600}
.card .sum{padding:0 10px 9px;color:var(--soft);font-size:12px;border-bottom:1px solid var(--line)}
.chg{display:grid;grid-template-columns:20px minmax(0,1fr);gap:2px 6px;padding:8px 10px;border-bottom:1px solid var(--line);cursor:pointer;transition:opacity .15s,background .15s}
.chg:hover{background:var(--raised)}
.chg.off{opacity:.5}
.chg input{width:15px;height:15px;margin:2px 0 0;accent-color:var(--acc);cursor:pointer}
.chg .t{display:flex;align-items:baseline;gap:6px;min-width:0;flex-wrap:wrap}
.chg .t b{font-size:12.5px;font-weight:600}
.tag{font-size:10px;padding:0 5px;border-radius:4px;background:var(--control);color:var(--muted)}
.vv{display:flex;align-items:center;gap:6px;flex-wrap:wrap;font-variant-numeric:tabular-nums}
.vv s{color:var(--muted);text-decoration-color:var(--line-s)}
.vv .ar{color:var(--muted)}
.vv b{font-weight:600}
.vv .dl{font-size:11px;color:var(--acc)}
.rs{font-size:11px;color:var(--muted)}
.ky{font:10px ui-monospace,Menlo,monospace;color:var(--muted)}
.blk{display:grid;grid-template-columns:20px minmax(0,1fr);gap:2px 6px;padding:8px 10px;background:var(--warn-bg);border-bottom:1px solid var(--line)}
.blk .ic{color:var(--warn);display:flex;padding-top:2px}
.blk .w{font-size:11px;color:var(--warn)}
.card .ft{display:flex;gap:6px;padding:8px 10px}
.card .ft .pri{flex:1;justify-content:center;height:32px;font-size:12.5px}
.card .ft .btn:not(.pri){height:32px}
.card .busy{display:flex;align-items:center;gap:8px;padding:12px;color:var(--muted);font-size:12px}
.card .okb{display:flex;flex-direction:column;gap:8px;padding:9px 10px;background:var(--ok-bg)}
.card .okb .m{display:flex;gap:8px;color:var(--ok);font-size:12px}
.card .okb .m span{color:var(--text)}
.card .okb .ko{color:var(--warn);font-size:11px}
.card .note{padding:9px 10px;color:var(--muted);font-size:12px}
@media (max-width:380px){#kHint{display:none}.ky{display:none}.u{max-width:90%}}
/* composer */
footer{padding:6px 8px 8px;border-top:1px solid var(--line);background:var(--panel)}
.box{border:1px solid var(--line-s);border-radius:10px;background:var(--control);transition:border-color .15s}
.box:focus-within{border-color:var(--acc)}
#thumbs{display:flex;gap:6px;padding:8px 8px 0;flex-wrap:wrap}
#thumbs:empty{display:none}
.th{position:relative;width:52px;height:52px;border-radius:6px;overflow:hidden;border:1px solid var(--line-s)}
.th img{width:100%;height:100%;object-fit:cover;display:block}
.th button{position:absolute;top:2px;right:2px;width:18px;height:18px;border-radius:50%;background:rgba(0,0,0,.65);color:#fff;display:flex;align-items:center;justify-content:center}
#inp{display:block;width:100%;resize:none;border:0;background:transparent;color:var(--text);font:inherit;font-size:13px;padding:8px 10px 2px;outline:none;max-height:140px;min-height:34px}
#inp::placeholder{color:var(--muted)}
.tools{display:flex;align-items:center;gap:4px;padding:4px 6px 6px}
.tools .sp{flex:1}
.hint{font-size:10.5px;color:var(--muted)}
#auto{display:flex;align-items:center;gap:6px;height:26px;padding:0 8px;border:1px solid var(--line);border-radius:999px;color:var(--muted);font-size:11px}
#auto:hover{background:var(--hover);color:var(--text)}
#auto.on{border-color:var(--acc);background:var(--acc-bg);color:var(--acc)}
.mini{position:relative;width:22px;height:12px;border-radius:999px;background:var(--hover);transition:background .15s}
.mini i{position:absolute;top:2px;left:2px;width:8px;height:8px;border-radius:50%;background:var(--text);transition:left .15s}
.on .mini{background:var(--acc)}.on .mini i{left:12px}
#bSend{width:30px;height:30px;border-radius:8px;background:var(--acc);color:var(--acc-ink);display:flex;align-items:center;justify-content:center}
#bSend:hover:not(:disabled){background:var(--acc-hi)}
/* impostazioni */
#scrim{position:fixed;inset:0;background:rgba(0,0,0,.45);display:none;flex-direction:column;justify-content:flex-end;z-index:5}
#scrim.show{display:flex}
.sheet{max-height:94%;overflow-y:auto;background:var(--panel);border-top:1px solid var(--line-s);border-radius:14px 14px 0 0;animation:sheet .22s ease both}
@keyframes sheet{from{transform:translateY(16px);opacity:0}to{transform:none;opacity:1}}
.sh{display:flex;align-items:center;padding:12px 8px 6px 16px;position:sticky;top:0;background:var(--panel);z-index:1}
.sh b{flex:1;font-size:15px;font-weight:650}
.sb{display:flex;flex-direction:column;gap:16px;padding:4px 16px 16px}
.grp{display:flex;flex-direction:column;gap:6px}
.provs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}
.pv{display:flex;flex-direction:column;align-items:flex-start;gap:1px;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--raised);text-align:left}
.pv:hover{border-color:var(--line-s)}
.pv.sel{border-color:var(--acc);background:var(--acc-bg)}
.pv b{font-size:12.5px;font-weight:600}
.pv span{font-size:11px;color:var(--muted)}
.conn{display:flex;flex-direction:column;gap:10px;padding:12px;border:1px solid var(--line);border-radius:10px;background:var(--bar)}
.cst{display:flex;align-items:center;gap:8px;font-size:12px}
#cTxt{flex:1}
.fld{display:flex;flex-direction:column;gap:4px;font-size:11px;color:var(--muted)}
.fld .in{display:flex;gap:6px}
.fld input{flex:1;min-width:0;height:32px;padding:0 10px;border:1px solid var(--line);border-radius:6px;background:var(--control);color:var(--text);font:inherit;font-size:12.5px;outline:none}
.fld input:focus{border-color:var(--acc)}
.fld input::placeholder{color:var(--muted)}
.fld .h{font-size:11px;color:var(--muted)}
.seg{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));padding:3px;gap:3px;border-radius:8px;background:var(--control)}
.seg button{height:28px;border-radius:6px;color:var(--muted);font-size:12px}
.seg button.sel{background:var(--active);color:var(--text);font-weight:600}
.sw2{display:flex;align-items:flex-start;gap:10px;padding:12px;border:1px solid var(--line);border-radius:10px}
.sw2 .tx{display:flex;flex-direction:column;gap:2px;flex:1}
.sw2 .tx b{font-size:12.5px;font-weight:600}
.sw2 .tx span{font-size:11px;color:var(--muted)}
.tg{flex-shrink:0;position:relative;width:38px;height:22px;border-radius:999px;background:var(--hover);transition:background .15s}
.tg i{position:absolute;top:3px;left:3px;width:16px;height:16px;border-radius:50%;background:var(--text);transition:left .15s}
.tg.on{background:var(--acc)}.tg.on i{left:19px}
.safe{display:flex;gap:8px;padding:10px 12px;border-radius:8px;background:var(--bar);font-size:11px;color:var(--soft)}
.cinfo{font-size:11.5px;color:var(--soft)}
.cerr{font-size:11.5px;color:var(--warn);background:var(--warn-bg);padding:7px 9px;border-radius:6px;word-break:break-word}
.lnk{align-self:flex-start;padding:0;color:var(--acc);font-size:11.5px}
.lnk:hover{color:var(--acc-hi);text-decoration:underline}
.btn.gpt{background:var(--text);border-color:var(--text);color:#111;font-weight:650;height:36px;padding:0 16px}
.btn.gpt:hover:not(:disabled){background:#fff;color:#000}
#kHint.plan{color:var(--soft);cursor:pointer}
#kHint.plan:hover{color:var(--acc)}
#modal{position:fixed;inset:0;background:rgba(0,0,0,.55);display:none;align-items:center;justify-content:center;z-index:10;padding:20px}
#modal.show{display:flex}
#modal .box2{background:var(--panel);border:1px solid var(--line-s);border-radius:12px;padding:18px;display:flex;flex-direction:column;gap:10px;max-width:340px;animation:rise .2s ease both}
#modal b{font-size:15px}
#modal p{margin:0;color:var(--soft);font-size:12.5px}
.safe .ic{color:var(--warn);display:flex;padding-top:1px}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{padding:3px 8px;border-radius:999px;background:var(--acc-bg);color:var(--acc);font-size:11px}
.path{display:flex;align-items:center;gap:6px;font:10.5px ui-monospace,Menlo,monospace;color:var(--muted);word-break:break-all}
.sfoot{display:flex;align-items:center;gap:6px;flex-wrap:wrap;padding-top:10px;border-top:1px solid var(--line);font-size:11px;color:var(--muted)}
.sfoot .v{flex:1}
#diag{display:none;margin:0;font:10.5px/1.35 ui-monospace,Menlo,monospace;white-space:pre-wrap;max-height:220px;overflow:auto;background:var(--bar);border:1px solid var(--line);border-radius:8px;padding:8px;color:var(--soft)}
#toast{position:fixed;left:50%;bottom:86px;transform:translate(-50%,8px);padding:6px 12px;border-radius:999px;background:var(--active);color:var(--text);font-size:12px;opacity:0;pointer-events:none;transition:opacity .2s,transform .2s;z-index:9;white-space:nowrap}
#toast.show{opacity:1;transform:translate(-50%,0)}
#drop{position:fixed;inset:6px;border:2px dashed var(--acc);border-radius:12px;background:rgba(30,31,34,.85);display:none;align-items:center;justify-content:center;gap:8px;color:var(--acc);font-size:13px;z-index:8;pointer-events:none}
#drop.show{display:flex}
</style></head><body>
<header>
 <button id="bmc" type="button"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 8h13v5a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5V8z"></path><path d="M17 10h1.5a2.5 2.5 0 0 1 0 5H17"></path><path d="M8 3v2M12 3v2"></path></svg><span id="bmcT"></span></button>
 <button id="prov" type="button"><span class="pdot" id="pdot"></span><span class="t" id="provT"></span></button>
 <span class="sp"></span>
 <button class="ib" id="bNew" type="button"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"></path></svg></button>
 <button class="ib" id="bSet" type="button"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"></path></svg></button>
 <button class="ib" id="bHide" type="button"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M13 7l5 5-5 5M6 7l5 5-5 5"></path></svg></button>
</header>
<button id="mdab" type="button"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z"></path><path d="M12 12l8-4.5M12 12v9M12 12L4 7.5"></path></svg><span id="mdabT"></span><span class="go">→</span></button>
<main id="log">
 <section id="welcome">
  <div><h1 id="wH"></h1><p id="wP"></p></div>
  <div class="grp"><span class="lbl" id="wL"></span><div class="probs" id="probs"></div></div>
 </section>
</main>
<footer>
 <div class="box">
  <div id="thumbs"></div>
  <textarea id="inp" rows="1"></textarea>
  <div class="tools">
   <button class="ib" id="bImg" type="button" style="width:30px;height:30px"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"></rect><circle cx="9" cy="10" r="1.6"></circle><path d="M21 16l-5-5-8 8"></path></svg></button>
   <button id="auto" type="button" aria-pressed="false"><span class="mini"><i></i></span><span id="autoT"></span></button>
   <span class="sp"></span><button class="hint" id="kHint" type="button" tabindex="-1"></button>
   <button id="bSend" type="button" disabled><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5M6 11l6-6 6 6"></path></svg></button>
  </div>
 </div>
 <input type="file" id="file" accept="image/*" multiple hidden>
</footer>
<div id="scrim"><div class="sheet" role="dialog" aria-modal="true" aria-labelledby="sT">
 <div class="sh"><b id="sT"></b><button class="ib" id="sClose" type="button"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"></path></svg></button></div>
 <div class="sb">
  <div class="grp"><span class="lbl" id="lProv"></span><div class="provs" id="provs"></div></div>
  <div class="conn">
   <div class="cst"><span class="pdot" id="cDot"></span><span id="cTxt"></span><button class="btn sm" id="bUsage" type="button" hidden></button><button class="btn sm" id="bClear" type="button"></button></div>
   <div class="cinfo" id="cInfo" hidden></div>
   <div class="cerr" id="cErr" hidden></div>
   <div id="orBox" class="grp">
    <div style="display:flex;gap:6px;flex-wrap:wrap"><button class="btn pri" id="bLogin" type="button"></button><button class="btn" id="bLoginX" type="button" hidden></button><button class="btn" id="bCopyLink" type="button" hidden></button></div>
    <div class="fld" id="loginInfo"></div>
    <div class="fld" id="codeBox" hidden><span id="lCode"></span><div class="in"><input id="code" type="text"><button class="btn" id="bCode" type="button"></button></div></div>
    <button class="lnk" id="bForget" type="button" hidden></button>
   </div>
   <label class="fld" id="keyBox"><span id="lKey"></span><div class="in"><input id="key" type="password" autocomplete="off"><button class="btn" id="bKey" type="button"></button></div><button class="lnk" id="bKeyPage" type="button"></button></label>
   <label class="fld" id="baseBox"><span id="lBase"></span><input id="base" type="text"><span class="h" id="baseHint"></span></label>
   <label class="fld"><span id="lModel"></span><div class="in"><input id="model" type="text" list="models"><button class="btn" id="bModels" type="button"></button></div><span class="h" id="modelHint"></span></label>
   <datalist id="models"></datalist>
  </div>
  <div class="grp" id="effBox"><span class="lbl" id="lEff"></span><div class="seg" id="effs"></div><span class="hint" id="effHint"></span></div>
  <div class="sw2"><div class="tx"><b id="lAuto"></b><span id="autoHint"></span></div><button class="tg" id="tgAuto" type="button" role="switch" aria-checked="false"><i></i></button></div>
  <div class="grp"><span class="lbl" id="lSafe"></span><div class="safe"><span class="ic"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2"></rect><path d="M8 11V8a4 4 0 0 1 8 0v3"></path></svg></span><span id="safeT"></span></div></div>
  <div class="grp"><span class="lbl" id="lSkills"></span><div class="chips" id="skills"></div><div class="path"><span id="skDir"></span></div><div><button class="btn sm" id="bSkills" type="button"></button></div><span class="hint" id="skHint"></span></div>
  <div class="sfoot"><span class="v" id="ver"></span><button class="btn sm" id="bDiag" type="button"></button><button class="btn sm" id="bDon2" type="button"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 8h13v5a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5V8z"></path><path d="M17 10h1.5a2.5 2.5 0 0 1 0 5H17"></path><path d="M8 3v2M12 3v2"></path></svg><span id="donT"></span></button></div>
  <div style="display:flex;flex-direction:column;gap:6px"><pre id="diag"></pre><div><button class="btn sm" id="bDiagCopy" type="button" hidden><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2"></rect><path d="M5 15V5a2 2 0 0 1 2-2h8"></path></svg><span id="copyT"></span></button></div></div>
 </div>
</div></div>
<div id="toast"></div>
<div id="modal" role="dialog" aria-modal="true" aria-labelledby="mT"><div class="box2"><b id="mT"></b><p id="mP"></p><button class="btn pri" id="mOk" type="button" style="justify-content:center"></button></div></div>
<div id="drop"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"></rect><circle cx="9" cy="10" r="1.6"></circle><path d="M21 16l-5-5-8 8"></path></svg><span id="dropT"></span></div>
<script>
var ICON={check:'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"></path></svg>',undo:'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 14L4 9l5-5"></path><path d="M4 9h10a6 6 0 0 1 0 12h-3"></path></svg>',lock:'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2"></rect><path d="M8 11V8a4 4 0 0 1 8 0v3"></path></svg>',warn:'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l10 18H2L12 3z"></path><path d="M12 10v5M12 18v.5"></path></svg>',chev:'<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"></path></svg>',printer:'<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="2"></rect><path d="M3 15h18M8 8h8"></path></svg>',layers:'<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l9 5-9 5-9-5 9-5z"></path><path d="M3 13l9 5 9-5"></path></svg>'};
var L={
 it:{title:"Assistente stampa",bmc:"Offrimi un caffè",mdab:"Unisciti all'anteprima di MeshDab",hide:"Nascondi a destra",newc:"Nuova chat",don:"Sostieni il progetto",set:"Impostazioni",
  wH:"Cosa non va nella stampa?",wP:"Descrivi il difetto o allega una foto: leggo i parametri di Orca e ti propongo le modifiche.",
  wL:"Problemi frequenti",wDrop:"Trascina qui una foto della stampa, o incollala",drop:"Rilascia per allegare la foto",
  probs:[["Fili","tra le parti, «ragnatele»","La stampa fa molti fili tra le parti"],["Angoli sollevati","warping sul piatto","Gli angoli si sollevano dal piatto (warping)"],["Primo strato","non attacca o è irregolare","Il primo strato non attacca bene o è irregolare"],["Supporti","difficili da staccare","I supporti sono difficili da staccare e rovinano la superficie"],["Strati separati","crepe tra gli strati","Gli strati si separano o si crepano"],["Sbavature","puntini e bolle sulle pareti","Ci sono puntini, bolle e sbavature sulle pareti"],["Sporgenze","cadenti o arricciate","Le sporgenze cadono o si arricciano"],["Superficie superiore","buchi o righe","La superficie superiore ha buchi o righe"]],
  ph:"Descrivi il problema…",kHint:"Invio per inviare",img:"Allega una foto",send:"Invia",auto:"Autonomia",autoTip:"Autonomia: applica le modifiche senza chiedere",
  thinking:"Sto pensando…",tools:{get_settings:"Leggo i parametri di Orca…",search_settings:"Cerco tra le impostazioni…",get_plate:"Guardo gli oggetti sul piatto…",read_skill:"Consulto le skill…",propose_changes:"Controllo i limiti di sicurezza…"},
  stRead:"Letti: %s",stMore:" e altri %s",stSearch:"Cercato «%s»",stPlate:"Letti gli oggetti sul piatto",stSkill:"Skill «%s»",stProp:"Controllo sicurezza: %s ok, %s bloccate",
  sumKeys:"Letti %s parametri",sumSkill:"skill «%s»",sumSafe:"controllo sicurezza",sumDone:"Fatto",
  prop:"Modifiche proposte",of:"%s di %s",process:"Processo",filament:"Filamento",printer:"Stampante",
  apply1:"Applica 1 modifica",applyN:"Applica %s modifiche",apply0:"Scegli almeno una modifica",discard:"Scarta",applying:"Applico in Orca…",
  okMsg:"Applicate a %s. Non sono salvate: rifai lo slicing e, se il risultato ti piace, salva i preset in Orca.",koMsg:"Non applicata: ",undo:"Annulla",
  undone:"Annullate: i valori sono tornati come prima.",undoKo:"Annullamento non riuscito: ",discarded:"Proposta scartata. Dimmi cosa preferisci cambiare.",
  blocked:"Bloccata",bPrinter:"Le impostazioni della stampante non si toccano: se serve, cambiala tu a mano.",bForbidden:"Vietata: può danneggiare la stampante.",bUnsafe:"Fuori dai limiti sicuri.",bManual:"Da cambiare a mano in Orca",bInvalid:"Valore non valido",
  sT:"Impostazioni",lProv:"Servizio IA",provNote:{chatgpt:"il tuo abbonamento",openrouter:"accesso dal browser",anthropic:"chiave API",openai:"chiave API",gemini:"chiave API",ollama:"sul tuo computer",lmstudio:"sul tuo computer",custom:"compatibile OpenAI"},
  cOk:"Collegato · chiave %s",cOkLocal:"Modello sul tuo computer",cNo:"Non collegato: serve una chiave",clear:"Rimuovi chiave",
  notConn:"non collegato",gptBtn:"Continua con ChatGPT",gptInfo:"Usa il tuo piano ChatGPT (Plus, Pro, Business…): niente chiavi API, niente costi in più. Si apre il browser per l'accesso.",
  gptAs:"Collegato come %s",gptNoPlan:"Hai fatto l'accesso, ma non hai autorizzato l'uso del piano ChatGPT. Premi Continua con ChatGPT e accetta, oppure scegli un altro servizio.",
  gptWait:"Completa l'accesso nella finestra del browser che si è aperta…",logout:"Esci",usage:"Gestisci utilizzo",planHint:"Piano ChatGPT · Gestisci utilizzo",
  gwT:"Stai usando il tuo piano ChatGPT",gwP:"Le richieste di questo plugin usano il tuo piano ChatGPT. Puoi controllare e gestire l'utilizzo nelle impostazioni di ChatGPT.",gwOk:"Ho capito",
  keyPage:"Crea una chiave ↗",verified:"Collegamento OK · %s modelli",loggedOut:"Disconnesso da ChatGPT",localInfo:"Avvia %s sul computer e carica un modello, poi premi Elenco per verificare.",
  login:"Accedi con OpenRouter",loginX:"Annulla accesso",copyLink:"Copia il link di accesso",forget:"Usa un altro account",loginWait:"Completa l'accesso nel browser. Se non si è aperto, apri questo link:",loginOk:"Accesso riuscito: chiave salvata su questo computer.",loginKo:"Accesso non riuscito: ",
  lCode:"Oppure incolla il codice o l'indirizzo di ritorno",useCode:"Usa",lKey:"Chiave API",keySave:"Salva",keyPh:"Incolla la chiave",
  lBase:"Indirizzo del servizio",baseHint:"Predefinito: %s",lModel:"Modello",models:"Elenco",modelHint:"Predefinito: %s",nModels:"%s modelli disponibili",
  lEff:"Ragionamento",effs:[["low","Basso"],["medium","Medio"],["high","Alto"]],effHint:"Più ragionamento: risposte più accurate, ma più lente e costose.",
  lAuto:"Autonomia",autoHint:"L'IA applica subito le modifiche che propone, sempre entro i limiti di sicurezza. Annulla resta disponibile.",
  lSafe:"Sicurezza",safe:"Mai toccati: impostazioni della stampante, G-code, script, dati del materiale. Temperature, velocità e ritrazioni solo entro limiti sicuri.",
  lSkills:"Skill",skBtn:"Ricarica skill",skHint:"Aggiungi le tue skill (file .md o cartelle con SKILL.md) nella cartella qui sopra, poi premi Ricarica.",
  ver:"Versione %s · gratuito",diag:"Diagnostica",copy:"Copia",copied:"Copiato",donate:"Offrimi un caffè",saved:"Salvato",
  e_missing_key:"Manca la chiave API: aprila nelle impostazioni.",e_missing_model:"Scegli un modello nelle impostazioni.",e_missing_base:"Manca l'indirizzo del servizio nelle impostazioni.",err:"Errore: ",
  e_missing_login:"Accedi con ChatGPT nelle impostazioni.",e_login_expired:"L'accesso a ChatGPT è scaduto: premi Continua con ChatGPT nelle impostazioni.",e_chatgpt_no_plan:"Non hai autorizzato l'uso del piano ChatGPT: ripeti l'accesso nelle impostazioni.",
  e_chatgpt_limit:"Hai raggiunto il limite di utilizzo del piano ChatGPT. Controlla in ChatGPT → Impostazioni → Utilizzo.",e_chatgpt_not_eligible:"Il tuo account o spazio di lavoro ChatGPT non può usare il piano in app esterne.",e_chatgpt_unavailable:"Il servizio ChatGPT non è disponibile in questo momento: riprova tra poco.",e_chatgpt_denied:"Accesso annullato nel browser.",
  e_refused:"Il modello ha rifiutato questa richiesta.",e_truncated:"La risposta è stata troncata: riprova o scegli un impegno più basso.",
  e_chatgpt_other_account:"Hai fatto l'accesso con un account ChatGPT diverso da quello collegato. Premi «Usa un altro account» e riprova.",
  e_cancelled:"Accesso annullato.",e_timeout:"Tempo scaduto: riprova l'accesso.",slot:"slot %s",unsaved:"Modifiche non salvate"},
 en:{title:"Print assistant",bmc:"Buy me a coffee",mdab:"Join the MeshDab preview",hide:"Hide to the right",newc:"New chat",don:"Support the project",set:"Settings",
  wH:"What's wrong with the print?",wP:"Describe the defect or attach a photo: I read the Orca settings and propose changes.",
  wL:"Common problems",wDrop:"Drop a photo of the print here, or paste it",drop:"Drop to attach the photo",
  probs:[["Stringing","hairs and cobwebs between parts","The print has a lot of stringing between parts"],["Corners lifting","warping on the bed","The corners lift off the bed (warping)"],["First layer","not sticking or uneven","The first layer does not stick well or is uneven"],["Supports","hard to remove","Supports are hard to remove and damage the surface"],["Layer splitting","cracks between layers","Layers split or crack"],["Blobs","zits and blobs on the walls","There are zits, blobs and bumps on the walls"],["Overhangs","drooping or curling","Overhangs droop or curl up"],["Top surface","holes or lines","The top surface has holes or lines"]],
  ph:"Describe the problem…",kHint:"Enter to send",img:"Attach a photo",send:"Send",auto:"Autonomy",autoTip:"Autonomy: apply changes without asking",
  thinking:"Thinking…",tools:{get_settings:"Reading Orca settings…",search_settings:"Searching the settings…",get_plate:"Looking at the plate…",read_skill:"Reading the skills…",propose_changes:"Checking safety limits…"},
  stRead:"Read: %s",stMore:" and %s more",stSearch:"Searched \"%s\"",stPlate:"Read the objects on the plate",stSkill:"Skill \"%s\"",stProp:"Safety check: %s ok, %s blocked",
  sumKeys:"Read %s settings",sumSkill:"skill \"%s\"",sumSafe:"safety check",sumDone:"Done",
  prop:"Proposed changes",of:"%s of %s",process:"Process",filament:"Filament",printer:"Printer",
  apply1:"Apply 1 change",applyN:"Apply %s changes",apply0:"Pick at least one change",discard:"Discard",applying:"Applying in Orca…",
  okMsg:"Applied to %s. Not saved yet: slice again and, if you like the result, save the presets in Orca.",koMsg:"Not applied: ",undo:"Undo",
  undone:"Undone: the values are back as before.",undoKo:"Undo failed: ",discarded:"Proposal discarded. Tell me what you would rather change.",
  blocked:"Blocked",bPrinter:"Printer settings are never changed: change it by hand if needed.",bForbidden:"Forbidden: it could damage the printer.",bUnsafe:"Outside the safe limits.",bManual:"Change it by hand in Orca",bInvalid:"Invalid value",
  sT:"Settings",lProv:"AI service",provNote:{chatgpt:"your subscription",openrouter:"sign in from the browser",anthropic:"API key",openai:"API key",gemini:"API key",ollama:"on your computer",lmstudio:"on your computer",custom:"OpenAI compatible"},
  cOk:"Connected · key %s",cOkLocal:"Model on your computer",cNo:"Not connected: a key is needed",clear:"Remove key",
  notConn:"not connected",gptBtn:"Continue with ChatGPT",gptInfo:"Use your ChatGPT plan (Plus, Pro, Business…): no API keys, no extra cost. The browser opens to sign in.",
  gptAs:"Connected as %s",gptNoPlan:"You signed in but did not allow use of your ChatGPT plan. Press Continue with ChatGPT and accept, or choose another service.",
  gptWait:"Finish signing in in the browser window that opened…",logout:"Sign out",usage:"Manage usage",planHint:"ChatGPT plan · Manage usage",
  gwT:"You're using your ChatGPT plan",gwP:"Requests from this plugin use your ChatGPT plan. You can review and manage usage in ChatGPT settings.",gwOk:"Got it",
  keyPage:"Create a key ↗",verified:"Connection OK · %s models",loggedOut:"Signed out of ChatGPT",localInfo:"Start %s on this computer and load a model, then press List to check.",
  login:"Sign in with OpenRouter",loginX:"Cancel sign-in",copyLink:"Copy the sign-in link",forget:"Use another account",loginWait:"Finish signing in in the browser. If it did not open, open this link:",loginOk:"Signed in: key saved on this computer.",loginKo:"Sign-in failed: ",
  lCode:"Or paste the code or the return address",useCode:"Use",lKey:"API key",keySave:"Save",keyPh:"Paste the key",
  lBase:"Service address",baseHint:"Default: %s",lModel:"Model",models:"List",modelHint:"Default: %s",nModels:"%s models available",
  lEff:"Reasoning",effs:[["low","Low"],["medium","Medium"],["high","High"]],effHint:"More reasoning: more accurate answers, but slower and more expensive.",
  lAuto:"Autonomy",autoHint:"The AI applies the changes it proposes right away, always within the safety limits. Undo stays available.",
  lSafe:"Safety",safe:"Never touched: printer settings, G-code, scripts, material data. Temperatures, speeds and retraction only within safe limits.",
  lSkills:"Skills",skBtn:"Reload skills",skHint:"Add your own skills (.md files or folders with SKILL.md) to the folder above, then press Reload.",
  ver:"Version %s · free",diag:"Diagnostics",copy:"Copy",copied:"Copied",donate:"Buy me a coffee",saved:"Saved",
  e_missing_key:"API key missing: open the settings.",e_missing_model:"Choose a model in the settings.",e_missing_base:"Service address missing in the settings.",err:"Error: ",
  e_missing_login:"Sign in with ChatGPT in the settings.",e_login_expired:"Your ChatGPT sign-in expired: press Continue with ChatGPT in the settings.",e_chatgpt_no_plan:"You did not allow use of your ChatGPT plan: sign in again in the settings.",
  e_chatgpt_limit:"You reached your ChatGPT plan usage limit. Check ChatGPT → Settings → Usage.",e_chatgpt_not_eligible:"Your ChatGPT account or workspace cannot use the plan in external apps.",e_chatgpt_unavailable:"ChatGPT is unavailable right now: try again shortly.",e_chatgpt_denied:"Sign-in cancelled in the browser.",
  e_refused:"The model declined this request.",e_truncated:"The answer was cut off: try again or pick a lower effort.",
  e_chatgpt_other_account:"You signed in with a different ChatGPT account. Press \"Use another account\" and try again.",
  e_cancelled:"Sign-in cancelled.",e_timeout:"Timed out: try signing in again.",slot:"slot %s",unsaved:"Unsaved changes"}
};
var T=L.en,S=null,busy=false,imgs=[],donate="",meshdab="",pollT=null,cards={},turn=null,lastCard=null,loginCopy="",version="",WEL=document.getElementById("welcome");
function $(id){return document.getElementById(id)}
function fmt(s){var a=arguments,i=1;return s.replace(/%s/g,function(){return a[i++]})}
function send(o){if(window.orca&&orca.postMessage)orca.postMessage(o)}
function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]})}
function el(tag,cls,html){var e=document.createElement(tag);if(cls)e.className=cls;if(html!=null)e.innerHTML=html;return e}
function toast(t){var x=$("toast");x.textContent=t;x.classList.add("show");clearTimeout(x._t);x._t=setTimeout(function(){x.classList.remove("show")},1800)}
function scrollEnd(){var l=$("log");l.scrollTop=l.scrollHeight;requestAnimationFrame(function(){l.scrollTop=l.scrollHeight})}
function md(s){
 var out=[],list=null;
 esc(s).split(/\n/).forEach(function(line){
  var t=line.replace(/\*\*([^*]+)\*\*/g,"<b>$1</b>").replace(/\x60([^\x60]+)\x60/g,"<code>$1</code>").replace(/^#{1,4}\s+(.*)$/,"<b>$1</b>");
  var m=/^\s*(?:[-*•]|\d+[.)])\s+(.*)$/.exec(t);
  if(m){if(!list){list=[];}list.push("<li>"+m[1]+"</li>");return}
  if(list){out.push("<ul>"+list.join("")+"</ul>");list=null}
  if(t.trim())out.push("<p>"+t+"</p>");
 });
 if(list)out.push("<ul>"+list.join("")+"</ul>");
 return out.join("");
}
function shortName(n){return String(n||"").replace(/\s*@.*$/,"").replace(/^Bambu Lab\s+/,"").replace(/\s+nozzle$/i,"")}
/* ---------- testo dell'interfaccia ---------- */
function ui(){
 $("bNew").title=T.newc;$("bNew").setAttribute("aria-label",T.newc);
 $("bmcT").textContent=T.bmc;$("bmc").title=T.don;$("mdabT").textContent=T.mdab;$("mdab").title="meshdab.com";
 $("bSet").title=T.set;$("bSet").setAttribute("aria-label",T.set);$("bHide").title=T.hide;$("bHide").setAttribute("aria-label",T.hide);
 $("wH").textContent=T.wH;$("wP").textContent=T.wP;$("wL").textContent=T.wL;$("dropT").textContent=T.drop;
 var pr=$("probs");pr.innerHTML="";T.probs.forEach(function(p){var b=el("button","prob");b.textContent=p[0];b.title=p[1];b.type="button";b.onclick=function(){if(!busy)ask(p[2],[])};pr.appendChild(b)});
 $("inp").placeholder=T.ph;$("kHint").textContent=T.kHint;$("bImg").title=T.img;$("bImg").setAttribute("aria-label",T.img);$("bSend").setAttribute("aria-label",T.send);
 $("autoT").textContent=T.auto;$("auto").title=T.autoTip;
 $("sT").textContent=T.sT;$("sClose").setAttribute("aria-label",T.sT);$("lProv").textContent=T.lProv;$("bClear").textContent=T.clear;
 $("bLogin").textContent=T.login;$("bLoginX").textContent=T.loginX;$("bCopyLink").textContent=T.copyLink;$("bForget").textContent=T.forget;$("lCode").textContent=T.lCode;$("bCode").textContent=T.useCode;
 $("lKey").textContent=T.lKey;$("bKey").textContent=T.keySave;$("key").placeholder=T.keyPh;$("lBase").textContent=T.lBase;$("lModel").textContent=T.lModel;$("bModels").textContent=T.models;
 $("lEff").textContent=T.lEff;$("effHint").textContent=T.effHint;$("lAuto").textContent=T.lAuto;$("autoHint").textContent=T.autoHint;$("tgAuto").setAttribute("aria-label",T.lAuto);
 $("lSafe").textContent=T.lSafe;$("safeT").textContent=T.safe;$("lSkills").textContent=T.lSkills;$("bSkills").textContent=T.skBtn;$("skHint").textContent=T.skHint;
 $("bDiag").textContent=T.diag;$("donT").textContent=T.donate;$("copyT").textContent=T.copy;$("ver").textContent=fmt(T.ver,version);
}
/* ---------- stato del servizio IA ---------- */
function prov(){return S?S.providers[S.provider]:null}
function connected(p){if(!p)return false;if(S.provider=="chatgpt"&&p.kind=="responses")return p.signed_in&&p.plan;return !p.needs_key||p.has_key}
function header(){
 var p=prov();if(!p)return;
 var mdl=connected(p)?(p.model||p.default_model||"?"):T.notConn;$("provT").textContent=p.label;$("prov").title=p.label+" · "+mdl;
 $("pdot").className="pdot"+(connected(p)?" ok":"");
 var on=!!S.auto_apply;$("auto").classList.toggle("on",on);$("auto").setAttribute("aria-pressed",on);$("tgAuto").classList.toggle("on",on);$("tgAuto").setAttribute("aria-checked",on);
}
function fillSettings(){
 if(!S)return; var p=prov(), k=S.provider;
 var g=$("provs");g.innerHTML="";
 Object.keys(S.providers).forEach(function(id){var q=S.providers[id];var b=el("button","pv"+(id==k?" sel":""),"<b>"+esc(q.label)+"</b><span>"+esc(T.provNote[id]||"")+"</span>");b.type="button";b.setAttribute("aria-pressed",id==k);
  b.onclick=function(){if(id!=S.provider)save({provider:id})};g.appendChild(b)});
 var gpt=k=="chatgpt";
 $("cDot").className="pdot"+(connected(p)?" ok":"");
 if(gpt)$("cTxt").textContent=p.signed_in?fmt(T.gptAs,p.email||"ChatGPT"):T.gptInfo;
 else $("cTxt").textContent=!p.needs_key?T.cOkLocal:(p.has_key?fmt(T.cOk,p.key_hint||"…"):T.cNo);
 $("cDot").hidden=gpt&&!p.signed_in;
 $("bClear").textContent=gpt?T.logout:T.clear;
 $("bClear").hidden=gpt?!p.signed_in:!(p.needs_key&&p.has_key);
 $("bUsage").hidden=!(gpt&&p.signed_in);$("bUsage").textContent=T.usage;
 var info=gpt&&p.signed_in&&!p.plan?T.gptNoPlan:(!p.needs_key&&!gpt?fmt(T.localInfo,p.label):"");
 $("cInfo").hidden=!info;$("cInfo").textContent=info;$("cErr").hidden=true;
 $("orBox").hidden=!(k=="openrouter"||(gpt&&(!p.signed_in||!p.plan)));
 $("bLogin").textContent=gpt?T.gptBtn:T.login;$("bLogin").className="btn "+(gpt?"gpt":"pri");
 $("bForget").hidden=!(gpt&&!p.signed_in&&p.known);
 $("keyBox").hidden=!p.needs_key;$("key").value="";
 $("bKeyPage").hidden=!p.key_page;$("bKeyPage").textContent=T.keyPage;
 $("baseBox").hidden=!(k=="custom"||k=="ollama"||k=="lmstudio");$("base").value=p.base||"";$("base").placeholder=p.default_base||"https://…/v1";$("baseHint").textContent=p.default_base?fmt(T.baseHint,p.default_base):"";
 $("model").value=p.model||"";$("model").placeholder=p.default_model||"";$("modelHint").textContent=p.default_model?fmt(T.modelHint,p.default_model):"";
 $("model").closest(".fld").hidden=gpt&&!(p.signed_in&&p.plan);
 var kh=$("kHint");if(gpt&&p.signed_in){kh.className="hint plan";kh.textContent=T.planHint;kh.tabIndex=0}else{kh.className="hint";kh.textContent=T.kHint;kh.tabIndex=-1}
 $("effBox").hidden=p.kind!="anthropic";
 var e=$("effs");e.innerHTML="";T.effs.forEach(function(x){var b=el("button",(S.effort||"medium")==x[0]?"sel":"",esc(x[1]));b.type="button";b.onclick=function(){save({effort:x[0]})};e.appendChild(b)});
 header();
}
function save(o){o.type="save_settings";o.provider=o.provider||S.provider;send(o)}
/* ---------- contesto (stampante, processo, filamento) ---------- */
function context(d){
 var c=$("ctx");if(!c||d.error)return;c.innerHTML="";
 function chip(icon,label,full,dirty){var x=el("span","cx",icon+"<span>"+esc(label)+"</span>"+(dirty?"<i class='dirty' title='"+esc(T.unsaved)+"'></i>":""));x.title=full;c.appendChild(x)}
 if(d.printer)chip(ICON.printer,shortName(d.printer),d.printer,d.printer_dirty);
 if(d.process)chip(ICON.layers,shortName(d.process),d.process,d.process_dirty);
 if(d.filament)chip("<i class='sw' style='background:"+esc(d.color||"#9a9ca2")+"'></i>",(d.slots>1?d.slot+" · ":"")+shortName(d.filament),d.filament+(d.slots>1?" ("+fmt(T.slot,d.slot)+")":""),d.filament_dirty);
}
/* ---------- conversazione ---------- */
function hideWelcome(){var w=$("welcome");if(w)w.remove()}
function ask(text,images){
 hideWelcome();
 var u=el("div","u rise");u.textContent=text||"";images.forEach(function(im){var i=el("img");i.src="data:"+im.mime+";base64,"+im.data;i.alt="";u.appendChild(i)});
 $("log").appendChild(u);
 startTurn();
 send({type:"send",text:text,images:images});setBusy(true);
}
function startTurn(){
 var a=el("div","act rise");var b=el("button","pill","<span class='dots'><i></i><i></i><i></i></span><span class='t'></span>");b.type="button";
 var ol=el("ol","steps");a.appendChild(b);a.appendChild(ol);b.onclick=function(){if(ol.children.length)a.classList.toggle("open")};
 $("log").appendChild(a);turn={el:a,pill:b,steps:ol,keys:0,skills:[],safety:false,after:a};
 b.querySelector(".t").textContent=T.thinking;scrollEnd();
}
function stepText(ev){
 if(ev.tool=="get_settings"){var k=ev.keys||[];turn&&(turn.keys+=k.length);return fmt(T.stRead,k.slice(0,4).join(", "))+(k.length>4?fmt(T.stMore,k.length-4):"")}
 if(ev.tool=="search_settings")return fmt(T.stSearch,ev.query||"");
 if(ev.tool=="get_plate")return T.stPlate;
 if(ev.tool=="read_skill"){turn&&turn.skills.push(ev.skill);return fmt(T.stSkill,ev.skill||"")}
 if(ev.tool=="propose_changes"){turn&&(turn.safety=true);return fmt(T.stProp,ev.accepted||0,ev.blocked||0)}
 return ev.tool;
}
function endTurn(){
 if(!turn)return;var t=turn;turn=null;
 if(!t.steps.children.length){t.el.remove();return}
 var parts=[];if(t.keys)parts.push(fmt(T.sumKeys,t.keys));t.skills.forEach(function(s){parts.push(fmt(T.sumSkill,s))});if(t.safety)parts.push(T.sumSafe);
 t.pill.innerHTML="<span class='ck'>"+ICON.check+"</span><span class='t'></span><span class='cv'>"+ICON.chev+"</span>";
 t.pill.querySelector(".t").textContent=parts.join(" · ")||T.sumDone;
}
function place(node){
 if(turn){turn.after.insertAdjacentElement("afterend",node);turn.after=node}else $("log").appendChild(node);
 scrollEnd();
}
function errText(t){t=String(t||"");return T["e_"+t]||T.err+t}
function addError(t){var e=el("div","err rise",ICON.warn+"<span></span>");e.querySelector("span").textContent=errText(t);place(e)}
function presetName(p){return T[p]||p}
function delta(o,n){var a=parseFloat(o),b=parseFloat(n);if(isNaN(a)||isNaN(b)||!/^-?[\d.]+%?$/.test(String(o).trim())||!/^-?[\d.]+%?$/.test(String(n).trim()))return "";var d=Math.round((b-a)*1000)/1000;return d==0?"":(d>0?"+":"−")+Math.abs(d)}
function card(p){
 var c=el("section","card rise");c.setAttribute("aria-label",T.prop);
 var n=p.changes.length;
 c.innerHTML="<div class='hd'><span class='lbl'></span>"+(n?"<span class='cnt'></span>":"")+"</div>"+(p.summary?"<div class='sum'></div>":"");
 c.querySelector(".lbl").textContent=T.prop;if(p.summary)c.querySelector(".sum").textContent=p.summary;
 var rows=[];
 p.changes.forEach(function(ch){
  var r=el("label","chg");
  r.innerHTML="<input type='checkbox' checked><span class='t'><b></b><span class='tag'></span></span><span></span><span class='vv'><s></s><span class='ar'>→</span><b></b><span class='dl'></span></span>"+(ch.reason?"<span></span><span class='rs'></span>":"")+"<span></span><span class='ky'></span>";
  r.querySelector(".t b").textContent=ch.label||ch.key;r.querySelector(".tag").textContent=presetName(ch.preset);
  r.querySelector(".vv s").textContent=ch.old;r.querySelector(".vv b").textContent=ch.new;r.querySelector(".dl").textContent=delta(ch.old,ch.new);
  if(ch.reason)r.querySelector(".rs").textContent=ch.reason;r.querySelector(".ky").textContent=ch.key;
  var cb=r.querySelector("input");cb.onchange=function(){r.classList.toggle("off",!cb.checked);count()};
  rows.push({ch:ch,cb:cb});c.appendChild(r);
 });
 (p.blocked||[]).forEach(function(b){
  var r=el("div","blk","<span class='ic'>"+ICON.lock+"</span><span><b></b> <span class='lb'></span></span><span></span><span class='w'></span><span></span><span class='ky'></span>");
  r.querySelector("b").textContent=T.blocked+":";
  r.querySelector(".lb").textContent=(b.label||b.key)+(b.old?" "+b.old+" → "+b.new:" → "+b.new);
  r.querySelector(".w").textContent=T["b"+b.kind.charAt(0).toUpperCase()+b.kind.slice(1)]||b.error;
  r.querySelector(".ky").textContent=b.key+" · "+String(b.error).replace(/^(FORBIDDEN|UNSAFE|MANUAL|INVALID):\s*/,"");
  c.appendChild(r);
 });
 var ft=el("div","ft");c.appendChild(ft);
 var res=el("div");c.appendChild(res);
 var st={id:p.id,el:c,rows:rows,ft:ft,res:res};
 function count(){var k=rows.filter(function(x){return x.cb.checked}).length;var cnt=c.querySelector(".cnt");if(cnt)cnt.textContent=fmt(T.of,k,n);
  if(st.bApply){st.bApply.disabled=!k;st.bApply.textContent=k==0?T.apply0:(k==1?T.apply1:fmt(T.applyN,k))}}
 if(n){
  var a=el("button","btn pri");a.type="button";var d=el("button","btn",esc(T.discard));d.type="button";ft.appendChild(a);ft.appendChild(d);st.bApply=a;
  a.onclick=function(){doApply(st)};
  d.onclick=function(){ft.remove();lock(st);res.className="note";res.textContent=T.discarded};
 } else ft.remove();
 count();cards[p.id]=st;place(c);
 if(n&&S&&S.auto_apply)doApply(st);
}
function lock(st){st.rows.forEach(function(x){x.cb.disabled=true})}
function doApply(st){
 var keys=st.rows.filter(function(x){return x.cb.checked}).map(function(x){return x.ch.key});if(!keys.length)return;
 lock(st);st.ft.innerHTML="<div class='busy' style='padding:2px 0'><span class='dots'><i></i><i></i><i></i></span>"+esc(T.applying)+"</div>";
 send({type:"apply",id:st.id,keys:keys});setBusy(true);
}
function applied(id,res){
 var st=cards[id];if(!st){return}
 st.ft.remove();var ok=[],ko=[];(res.results||[]).forEach(function(r){if(r.ok){ok.push(shortName(r.name));if(r.text)ko.push(r.text)}else ko.push((r.name?r.name+": ":"")+(r.text||"?"))});
 st.res.className="okb";st.res.innerHTML="";
 if(ok.length){st.el.classList.add("done");var m=el("div","m","<span style='display:flex;padding-top:1px'>"+ICON.check+"</span><span></span>");m.lastChild.textContent=fmt(T.okMsg,ok.join(", "));st.res.appendChild(m)}
 ko.forEach(function(t){var k=el("div","ko");k.textContent=T.koMsg+t;st.res.appendChild(k)});
 if(ok.length){var u=el("button","btn sm",ICON.undo+"<span></span>");u.type="button";u.lastChild.textContent=T.undo;u.style.alignSelf="flex-start";
  u.onclick=function(){u.disabled=true;lastCard=st;send({type:"undo",id:st.id});setBusy(true)};st.res.appendChild(u)}
 else st.res.className="note";
 scrollEnd();send({type:"context"});
}
function undone(id,res){
 var st=(id&&cards[id])||lastCard;var fail=(res.results||[]).filter(function(r){return !r.ok});
 var t=fail.length?T.undoKo+fail.map(function(r){return r.text}).join("; "):(res.text&&!(res.results||[]).length?res.text:T.undone);
 if(st){st.el.classList.remove("done");st.res.className="note";st.res.textContent=t}else{var n=el("div","a");n.textContent=t;place(n)}
 send({type:"context"});
}
function onEvent(ev){
 if(ev.kind=="assistant"){var a=el("div","a rise",md(ev.text));place(a)}
 else if(ev.kind=="status"){if(turn){var k=ev.text.indexOf("tool:")==0?ev.text.slice(5):"";var t=turn.pill.querySelector(".t");if(t)t.textContent=k?(T.tools[k]||T.thinking):T.thinking}}
 else if(ev.kind=="step"){if(turn){var li=el("li");li.textContent=stepText(ev);turn.steps.appendChild(li)}}
 else if(ev.kind=="error")addError(ev.text);
 else if(ev.kind=="proposal")card(ev.proposal);
 else if(ev.kind=="applied")applied(ev.id,ev.result);
 else if(ev.kind=="undone")undone(ev.id,ev.result);
 else if(ev.kind=="idle"){endTurn();send({type:"context"})}
 else if(ev.kind=="models"){if(ev.settings){S=ev.settings;fillSettings()}fillModels(ev.models);toast(fmt(T.verified,(ev.models||[]).length))}
 else if(ev.kind=="models_error"){var ce=$("cErr");ce.hidden=false;ce.textContent=errText(ev.text)}
 else if(ev.kind=="login_url"){$("bLoginX").hidden=false;loginCopy=ev.provider=="chatgpt"?String(ev.copy||""):"";$("bCopyLink").hidden=!loginCopy;
  if(ev.provider=="chatgpt"){$("loginInfo").textContent=T.gptWait;$("codeBox").hidden=true}
  else{$("loginInfo").innerHTML=esc(T.loginWait)+"<br><code style='word-break:break-all'>"+esc(ev.url)+"</code>";$("codeBox").hidden=false}}
 else if(ev.kind=="login_done"){$("bLoginX").hidden=true;$("codeBox").hidden=true;$("bCopyLink").hidden=true;loginCopy="";
  if(ev.settings)S=ev.settings;
  if(ev.ok){$("loginInfo").textContent=ev.provider=="chatgpt"?"":T.loginOk;fillSettings();fillModels(ev.models);
   var g=S.providers.chatgpt;if(ev.provider=="chatgpt"&&ev.plan&&g&&!g.welcomed)welcome()}
  else{$("loginInfo").textContent="";var ce=$("cErr");ce.hidden=false;ce.textContent=T.loginKo+errText(ev.text).replace(T.err,"")}}
 else if(ev.kind=="logged_out"){if(ev.settings){S=ev.settings;fillSettings()}toast(T.loggedOut)}
}
function setBusy(b){busy=b;sendState();
 if(b&&!pollT)pollT=setInterval(function(){send({type:"poll"})},400);
 if(!b&&pollT){clearInterval(pollT);pollT=null;send({type:"poll"})}}
function sendState(){$("bSend").disabled=busy||(!$("inp").value.trim()&&!imgs.length)}
function onMsg(d){
 if(d.type=="state"){T=L[d.lang]||L.en;S=d.settings;donate=d.donate;meshdab=d.meshdab||"";version=d.version;ui();fillSettings();skills(d.skills,d.skills_dir);setBusy(!!d.busy);send({type:"context"});send({type:"poll"})}
 else if(d.type=="events"){(d.events||[]).forEach(onEvent);setBusy(!!d.busy)}
 else if(d.type=="context")context(d);
 else if(d.type=="cleared"){$("log").innerHTML="";$("log").appendChild(WEL);cards={};turn=null;lastCard=null}
 else if(d.type=="settings"){S=d.settings;fillSettings();toast(T.saved)}
 else if(d.type=="skills"){skills(d.skills,d.skills_dir);toast(T.saved)}
 else if(d.type=="diagnostics"){$("diag").style.display="block";$("diag").textContent=JSON.stringify(d.result,null,1);$("bDiagCopy").hidden=false}
}
function fillModels(list){if(!list||!list.length)return;var dl=$("models");dl.innerHTML="";list.forEach(function(m){var o=el("option");o.value=m;dl.appendChild(o)});$("modelHint").textContent=fmt(T.nModels,list.length)}
function welcome(){$("mT").textContent=T.gwT;$("mP").textContent=T.gwP;$("mOk").textContent=T.gwOk;$("modal").classList.add("show");$("mOk").focus()}
$("mOk").onclick=function(){$("modal").classList.remove("show");send({type:"welcomed"})};
function skills(list,dir){var c=$("skills");c.innerHTML="";(list||[]).forEach(function(n){var x=el("span","chip");x.textContent=n;c.appendChild(x)});$("skDir").textContent=dir||""}
/* ---------- invio e foto ---------- */
function doSend(){if(busy)return;var t=$("inp").value.trim();if(!t&&!imgs.length)return;var im=imgs;imgs=[];$("thumbs").innerHTML="";$("inp").value="";grow();ask(t,im)}
function grow(){var i=$("inp");i.style.height="auto";i.style.height=Math.min(i.scrollHeight,140)+"px";sendState()}
function addImage(file){
 if(!file||!/^image\//.test(file.type)||imgs.length>=3)return;
 var r=new FileReader();r.onload=function(){var im=new Image();im.onload=function(){
  var s=Math.min(1,1024/Math.max(im.width,im.height));var c=document.createElement("canvas");c.width=Math.round(im.width*s);c.height=Math.round(im.height*s);
  c.getContext("2d").drawImage(im,0,0,c.width,c.height);var data=c.toDataURL("image/jpeg",0.82).split(",")[1];var item={mime:"image/jpeg",data:data};imgs.push(item);
  var th=el("div","th","<img alt=''><button type='button' aria-label='×'>×</button>");th.firstChild.src="data:image/jpeg;base64,"+data;
  th.lastChild.onclick=function(){imgs.splice(imgs.indexOf(item),1);th.remove();sendState()};$("thumbs").appendChild(th);sendState()};im.src=r.result};r.readAsDataURL(file);
}
$("inp").oninput=grow;
$("inp").onkeydown=function(e){if(e.key=="Enter"&&!e.shiftKey&&!e.isComposing){e.preventDefault();doSend()}};
document.addEventListener("paste",function(e){var it=(e.clipboardData||{}).items||[];for(var i=0;i<it.length;i++)if(it[i].kind=="file")addImage(it[i].getAsFile())});
var dragN=0;
document.addEventListener("dragenter",function(e){e.preventDefault();dragN++;$("drop").classList.add("show")});
document.addEventListener("dragleave",function(e){dragN=Math.max(0,dragN-1);if(!dragN)$("drop").classList.remove("show")});
document.addEventListener("dragover",function(e){e.preventDefault()});
document.addEventListener("drop",function(e){e.preventDefault();dragN=0;$("drop").classList.remove("show");Array.prototype.forEach.call((e.dataTransfer||{}).files||[],addImage)});
$("bSend").onclick=doSend;
$("bImg").onclick=function(){$("file").click()};
$("bHide").onclick=function(){send({type:"collapse"})};
$("file").onchange=function(){Array.prototype.forEach.call(this.files,addImage);this.value=""};
$("auto").onclick=function(){save({auto_apply:!S.auto_apply})};
$("tgAuto").onclick=function(){save({auto_apply:!S.auto_apply})};
$("bNew").onclick=function(){if(!busy)send({type:"new_chat"})};
$("bDon2").onclick=$("bmc").onclick=function(){if(donate)send({type:"open_url",url:donate})};
$("mdab").onclick=function(){if(meshdab)send({type:"open_url",url:meshdab})};
function openSet(){$("scrim").classList.add("show");fillSettings()}
function closeSet(){$("scrim").classList.remove("show")}
$("bSet").onclick=openSet;$("prov").onclick=openSet;$("sClose").onclick=closeSet;
$("scrim").onclick=function(e){if(e.target===this)closeSet()};
document.addEventListener("keydown",function(e){if(e.key=="Escape")closeSet()});
$("bKey").onclick=function(){var k=$("key").value.trim();if(k)save({key:k})};
$("key").onkeydown=function(e){if(e.key=="Enter"){e.preventDefault();$("bKey").click()}};
$("bClear").onclick=function(){if(S.provider=="chatgpt"){send({type:"logout"});setBusy(true)}else save({clear_key:true})};
$("bUsage").onclick=function(){send({type:"open_usage"})};
$("kHint").onclick=function(){if(this.classList.contains("plan"))send({type:"open_usage"})};
$("bKeyPage").onclick=function(e){e.preventDefault();send({type:"open_key_page",provider:S.provider})};
$("base").onchange=function(){save({base:$("base").value})};
$("model").onchange=function(){save({model:$("model").value})};
$("bModels").onclick=function(){$("cErr").hidden=true;send({type:"models"});setBusy(true)};
$("bLogin").onclick=function(){$("cErr").hidden=true;send({type:"login_start",provider:S.provider=="chatgpt"?"chatgpt":"openrouter"});setBusy(true)};
$("bLoginX").onclick=function(){send({type:"login_cancel"})};
$("bCopyLink").onclick=function(){var t=loginCopy;if(!t)return;var a=document.createElement("textarea");a.value=t;document.body.appendChild(a);a.select();try{document.execCommand("copy")}catch(e){}a.remove();if(navigator.clipboard)navigator.clipboard.writeText(t).catch(function(){});toast(T.copied)};
$("bForget").onclick=function(){$("cErr").hidden=true;send({type:"forget_account"});setBusy(true)};
$("bCode").onclick=function(){var c=$("code").value.trim();if(c){send({type:"login_code",code:c});setBusy(true)}};
$("bSkills").onclick=function(){send({type:"reload_skills"})};
$("bDiag").onclick=function(){send({type:"diagnostics"})};
$("bDiagCopy").onclick=function(){var t=$("diag").textContent;var a=document.createElement("textarea");a.value=t;document.body.appendChild(a);a.select();try{document.execCommand("copy")}catch(e){}a.remove();if(navigator.clipboard)navigator.clipboard.writeText(t).catch(function(){});toast(T.copied)};
if(window.orca&&orca.onMessage)orca.onMessage(onMsg);
ui();send({type:"ready",lang:navigator.language||""});
</script></body></html>"""
