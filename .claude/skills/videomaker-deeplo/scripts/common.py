"""Outils partagés : chemins, config, lecture/écriture JSON en UTF-8 (Windows), appels ffmpeg."""
import json
import re
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
ROOT = SKILL.parents[2]  # dossier « Deeplo video maker »
SOUNDS = ROOT / "sounds"
REAL_SFX_INDEX = Path.home() / ".claude" / "skills" / "real-sfx" / "library_index.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def read_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_json(p, data):
    Path(p).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def out(**kw):
    """Chaque script répond en une ligne JSON."""
    print(json.dumps(kw, ensure_ascii=False))


def fail(msg, **kw):
    raise SystemExit(json.dumps({"error": msg, **kw}, ensure_ascii=False))


def deep_merge(a, b):
    r = dict(a)
    for k, v in b.items():
        r[k] = deep_merge(r[k], v) if isinstance(v, dict) and isinstance(r.get(k), dict) else v
    return r


def job_dir(arg):
    """Accepte un chemin de job ou son nom dans jobs/."""
    p = Path(arg)
    if not p.is_absolute() and not p.exists():
        p = ROOT / "jobs" / arg
    p = p.resolve()
    if not (p / "job.json").exists():
        fail(f"job introuvable : {p} (crée-le avec new_job.py)")
    return p


def config(job):
    """config par défaut du skill, écrasée par la marque (brands/<client>/brand.json), puis par le job."""
    c = read_json(SKILL / "config.default.json")
    meta = read_json(job / "job.json")
    brand = ROOT / "brands" / meta.get("brand", "") / "brand.json"
    if meta.get("brand") and brand.exists():
        c = deep_merge(c, read_json(brand).get("video", {}))
    if (job / "config.json").exists():
        c = deep_merge(c, read_json(job / "config.json"))
    return c


def sh(cmd, what=None):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        fail(f"{what or Path(cmd[0]).name} a échoué", stderr=r.stderr[-1500:])
    return r.stdout


def probe(src):
    d = json.loads(sh(["ffprobe", "-v", "error", "-show_entries",
                       "stream=codec_type,width,height:stream_tags=rotate:format=duration",
                       "-of", "json", str(src)], "ffprobe"))
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    w, h = v.get("width"), v.get("height")
    if str((v.get("tags") or {}).get("rotate", "0")) in ("90", "270", "-90"):
        w, h = h, w
    return {"duration": float(d["format"].get("duration") or 0), "width": w, "height": h,
            "has_audio": any(s.get("codec_type") == "audio" for s in d.get("streams", []))}


FORMATS = {"9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350), "16:9": (1920, 1080)}


def size_of(arg, vis):
    """--size 1:1 | 1080x1080 | None -> (W, H)."""
    if not arg:
        return vis["width"], vis["height"]
    if arg in FORMATS:
        return FORMATS[arg]
    w, h = arg.lower().split("x")
    return int(w), int(h)


def block_file(job, name):
    """Copie le bloc <name> de library/ dans <job>/compositions/ s'il n'y est pas ; renvoie le chemin relatif."""
    import shutil
    dst = job / "compositions" / f"{name}.html"
    found = sorted((ROOT / "library").glob(f"*/{name}/{name}.html"))
    if found and (not dst.exists() or found[0].stat().st_mtime > dst.stat().st_mtime):  # copie à jour de la bibliothèque
        dst.parent.mkdir(exist_ok=True)
        shutil.copy2(found[0], dst)
    elif not dst.exists():
        fail(f"bloc introuvable : {name} (ni compositions/ ni library/)")
    return f"compositions/{name}.html"


def brand_info(job):
    meta = read_json(job / "job.json")
    p = ROOT / "brands" / meta.get("brand", "") / "brand.json"
    return read_json(p) if meta.get("brand") and p.exists() else {}


def mount(name, sid, start, dur, W, H, track, values, z=None):
    """Hôte HyperFrames d'un bloc (sous-composition) avec ses variables."""
    import html as _h
    st = f' style="z-index:{z}"' if z is not None else ""
    values = {"dur": round(dur, 3), **values}  # le bloc cale ses animations sur sa durée réelle
    vals = _h.escape(json.dumps(values, ensure_ascii=False))
    return (f'    <div id="{sid}" data-composition-id="{name}" data-composition-src="compositions/{name}.html" '
            f'data-start="{round(start, 3)}" data-duration="{round(dur, 3)}" data-width="{W}" data-height="{H}" '
            f"data-track-index=\"{track}\" data-variable-values='{vals}'{st}></div>")


def _norm_word(s):
    import unicodedata
    s = unicodedata.normalize("NFD", str(s).lower())
    return "".join(c for c in s if c.isalnum() and unicodedata.category(c) != "Mn")


# hésitations pures (jamais de sens) et tics de langage (parfois utiles : Claude tranche au cas par cas)
HESITATIONS = {"euh", "euhh", "euhhh", "heu", "heuu", "hum", "humm", "hmm", "hm", "mmh", "mmm", "mm", "eh", "em", "bah", "beh"}
TICS = [("du", "coup"), ("en", "fait"), ("tu", "vois"), ("vous", "voyez"), ("en", "gros"), ("genre",), ("voila",),
        ("ben",), ("bon",), ("quoi",), ("enfin",), ("bref",)]
NO_REPEAT = {"nous", "vous", "tres", "si"}  # « nous nous sommes », « très très » : répétitions voulues


def env_key(name):
    """Clé d'API : variable d'environnement, sinon ligne NAME= du fichier .env (jamais affichée)."""
    import os
    v = os.environ.get(name, "")
    f = ROOT / ".env"
    if not v and f.exists():
        for raw in f.read_text(encoding="utf-8").splitlines():
            if raw.startswith(name + "="):
                v = raw.split("=", 1)[1].strip()
    return v


def word_hit(words, word, occurrence=1, lo=0.0, hi=1e9):
    """Le mot prononcé n° `occurrence` entre lo et hi (« l'aventure » trouvé par « aventure »), sinon None."""
    key, seen = _norm_word(word), 0
    for w in words:
        parts = {_norm_word(w["w"])} | {_norm_word(x) for x in re.split(r"[’'\-]", w["w"])}
        if lo <= w["start"] <= hi and key in parts:
            seen += 1
            if seen == int(occurrence):
                return w
    return None


def add_credit(job, line):
    cred = job / "renders" / "credits.txt"
    old = cred.read_text(encoding="utf-8") if cred.exists() else ""
    if line not in old:
        cred.parent.mkdir(exist_ok=True)
        cred.write_text(old + line + "\n", encoding="utf-8")


def motion_nodes(job, motions, words, W, H, offset=0.0, lo=0.0, hi=1e9, base_vals=None, track=30, z=120):
    """Blocs de motion design posés sur un MOT prononcé (jamais sur un timecode écrit à la main).
    motions : [{"block": "compteur", "word": "250", "occurrence": 1, "dur": 3, "vars": {…}}]
    words : mots horodatés de la vidéo (temps de la composition avant décalage) ; offset : décalage (intro).
    Renvoie (noeuds HTML, rapport). Un mot introuvable = bloc ignoré et signalé."""
    nodes, rep = [], []
    for k, mo in enumerate(motions or []):
        hit = word_hit(words, mo.get("word", ""), mo.get("occurrence", 1), lo, hi)
        at = hit["start"] if hit else None
        if at is None:
            rep.append({"block": mo.get("block"), "mot": mo.get("word"), "pose": False, "raison": "mot introuvable"})
            continue
        start = max(0.0, at - float(mo.get("lead", 0.15)))
        if mo["block"] == "lottie":  # animation Lottie rendue (library/lottie/<nom>/<nom>.webm), répétée si besoin
            import math
            import shutil
            lm = ROOT / "library" / "lottie" / mo.get("name", "") / "lottie.json"
            if not lm.exists() or "webm" not in read_json(lm):
                rep.append({"block": "lottie", "nom": mo.get("name"), "pose": False, "raison": "non rendue (lottie.py render)"})
                continue
            meta = read_json(lm)
            (job / "assets" / "lottie").mkdir(parents=True, exist_ok=True)
            shutil.copy2(lm.parent / meta["webm"], job / "assets" / "lottie" / meta["webm"])
            v = mo.get("vars", {})
            x, y, size = float(v.get("x", 50)), float(v.get("y", 30)), float(v.get("size", 34))
            one = float(meta.get("rendered_duration") or meta.get("duration") or 1.5)
            total = float(mo.get("dur", one))
            n = max(1, math.ceil(total / one - 0.05)) if v.get("loop", True) else 1
            style = (f"position:absolute;left:calc({x}% - {size / 2}vmin);top:calc({y}% - {size / 2}vmin);"
                     f"width:{size}vmin;height:{size}vmin;z-index:{z + k}")
            for r_ in range(n):
                nodes.append(f'    <video id="mo-{k}-{r_}" class="clip" src="assets/lottie/{meta["webm"]}" data-start="{round(start + offset + r_ * one, 3)}" '
                             f'data-duration="{round(one, 3)}" data-track-index="{track + k}" muted playsinline style="{style}"></video>')
            add_credit(job, meta["credit"])
            rep.append({"block": "lottie", "nom": mo.get("name"), "mot": mo.get("word"), "pose": True, "a": round(start, 2), "fois": n})
            continue
        block_file(job, mo["block"])
        vals = {**(base_vals or {}), **mo.get("vars", {})}
        nodes.append(mount(mo["block"], f"mo-{k}", start + offset, float(mo.get("dur", 3)), W, H, track + k, vals, z=z + k))
        rep.append({"block": mo["block"], "mot": mo.get("word"), "pose": True, "a": round(start, 2)})
    return nodes, rep
