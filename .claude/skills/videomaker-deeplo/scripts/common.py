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


def _rate(s):
    """« 30000/1001 » -> 29.97 ; « 0/0 » ou vide -> None."""
    try:
        n, _, d = str(s or "").partition("/")
        v = float(n) / float(d or 1)
        return v if v > 0 else None
    except (ValueError, ZeroDivisionError):
        return None


def rotation_of(stream):
    """Rotation d'affichage d'un flux vidéo ffprobe (0, 90, 180, 270) : tag « rotate » des anciens ffmpeg, sinon matrice
    d'affichage (side_data_list, seul endroit où ffmpeg 6+ la met : un rush de téléphone en portrait)."""
    rot = 0
    for sd in stream.get("side_data_list") or []:
        if "rotation" in sd:
            try:
                rot = int(round(float(sd["rotation"])))
            except (TypeError, ValueError):
                pass
    tag = (stream.get("tags") or {}).get("rotate")
    if tag not in (None, ""):
        try:
            rot = int(tag)
        except ValueError:
            pass
    return rot % 360


STD_FPS = (23.976, 24, 25, 29.97, 30, 48, 50, 59.94, 60)


def round_fps(fps, nominal=None):
    """Cadence ramenée à la cadence standard la plus proche (à 3 % près) : un rush VFR à 29,6 i/s de moyenne est un 30.
    Trop loin de tout standard (téléphone qui a perdu des images) : cadence nominale du fichier si elle est standard, sinon 30."""
    def snap(x):
        best = min(STD_FPS, key=lambda r: abs(r - x)) if x else None
        return best if best and abs(best - x) / best < 0.03 else None
    r = snap(fps) or snap(nominal) or 30
    return {23.976: "24000/1001", 29.97: "30000/1001", 59.94: "60000/1001"}.get(r, f"{r:g}")


def probe(src):
    """Mesure d'un média. Clés historiques : duration, width, height (taille affichée, rotation comprise), has_audio.
    En plus, pour les rushs de téléphone : fps (moyenne), fps_nominal, vfr (cadence variable), rotation, hdr (PQ, HLG ou Dolby Vision),
    hdr_format, pix_fmt, codec, color (tags), video_duration, audio (codec, sample_rate, channels, duration) ou None.
    vfr, rotation et hdr d'après ffmpeg-skill (MIT), scripts/_common/probe.py."""
    d = json.loads(sh(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(src)], "ffprobe"))
    streams = d.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"
              and not (s.get("disposition") or {}).get("attached_pic")), {})
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    w, h = v.get("width"), v.get("height")
    rot = rotation_of(v) if v else 0
    if rot in (90, 270):
        w, h = h, w
    r_rate, avg = _rate(v.get("r_frame_rate")), _rate(v.get("avg_frame_rate"))
    fps = avg or r_rate
    trc = v.get("color_transfer") or ""
    dovi = any("dv_profile" in sd or "DOVI" in str(sd.get("side_data_type", "")) for sd in v.get("side_data_list") or [])
    num = lambda x: float(x) if x not in (None, "", "N/A") else None
    return {"duration": float(d.get("format", {}).get("duration") or 0), "width": w, "height": h,
            "has_audio": a is not None,
            "fps": round(fps, 3) if fps else None, "fps_nominal": round(r_rate, 3) if r_rate else None,
            # cadence variable : cadence nominale ≠ cadence moyenne (téléphones, enregistrements d'écran)
            "vfr": bool(r_rate and avg and abs(r_rate - avg) > 0.01),
            "rotation": rot,
            "hdr": trc in ("smpte2084", "arib-std-b67") or dovi,
            "hdr_format": "Dolby Vision" if dovi else "HDR10/PQ" if trc == "smpte2084" else "HLG" if trc == "arib-std-b67" else None,
            "pix_fmt": v.get("pix_fmt"), "codec": v.get("codec_name"),
            "color": {"primaries": v.get("color_primaries"), "transfer": v.get("color_transfer"),
                      "space": v.get("color_space"), "range": v.get("color_range")},
            "video_duration": num(v.get("duration")),
            "audio": {"codec": a.get("codec_name"), "sample_rate": int(a.get("sample_rate") or 0),
                      "channels": a.get("channels"), "duration": num(a.get("duration"))} if a else None}


_FILTERS = {}


def ffmpeg_has(name):
    """Le ffmpeg installé a-t-il ce filtre (zscale manque aux builds « essentials ») ?"""
    if name not in _FILTERS:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        _FILTERS[name] = bool(re.search(rf"^\s*\S+\s+{re.escape(name)}\s", r.stdout, re.M))
    return _FILTERS[name]


def hdr_to_sdr(info):
    """Chaîne PQ / HLG / Dolby Vision -> SDR BT.709 (tonemap hable). Linéarisé à 100 nits par unité (blanc SDR = 1,0),
    crête de la source : 1000 nits (HLG décodé par zimg pour un écran de 1000 nits). Passage en 8 bits tramé
    (error_diffusion), plage limitée (tv) balisée sur chaque image. D'après ffmpeg-skill (MIT),
    scripts/_common/color.py hdr_to_sdr_chain."""
    c = info.get("color") or {}
    trc, prim, space = c.get("transfer") or "smpte2084", c.get("primaries") or "bt2020", c.get("space") or "bt2020nc"
    if trc not in ("smpte2084", "arib-std-b67"):  # Dolby Vision sans tag de transfert : base PQ
        trc = "smpte2084"
    label = [] if (c.get("transfer") and c.get("primaries") and c.get("space")) else \
        [f"setparams=color_primaries={prim}:color_trc={trc}:colorspace={space}"]  # zscale exige des tags
    return ",".join(label + [
        f"zscale=tin={trc}:pin={prim}:min={space}:rin={c.get('range') or 'tv'}:t=linear:npl=100",
        "format=gbrpf32le", "zscale=p=bt709", "tonemap=tonemap=hable:desat=0:peak=10",
        "zscale=t=bt709:m=bt709:r=tv:d=error_diffusion", "format=yuv420p",  # tramage : pas de bandes dans les ciels
        "setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709"])  # + -color_range tv à l'encodage


FORMATS = {"9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350), "16:9": (1920, 1080)}


def size_of(arg, vis):
    """--size 1:1 | 1080x1080 | None -> (W, H)."""
    if not arg:
        return vis["width"], vis["height"]
    if arg in FORMATS:
        return FORMATS[arg]
    w, h = arg.lower().split("x")
    return int(w), int(h)


def scale_of(W, H):
    """Échelle des textes et marges, pensée pour le 1080 × 1920 : 1 en vertical, ~0,95 en carré et en paysage (la hauteur
    commande, sinon tout grossit de 1,78 en 16:9 et déborde)."""
    return min(W / 1080, H / 1080 * 0.95)


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


def serif_fonts(job):
    """Bodoni Moda (OFL, vendor/fonts) copiée dans le job -> règles @font-face (serif Didone des styles éditoriaux)."""
    import shutil
    (job / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    css = []
    for f, w, st in (("BodoniModa-700-normal.woff2", 700, "normal"), ("BodoniModa-700-italic.woff2", 700, "italic"),
                     ("BodoniModa-400-italic.woff2", 400, "italic")):
        shutil.copy2(SKILL / "vendor" / "fonts" / f, job / "assets" / "fonts" / f)
        css.append(f"@font-face {{ font-family: 'Bodoni Moda'; src: url('assets/fonts/{f}') format('woff2'); font-weight: {w}; font-style: {st}; }}")
    return " ".join(css)


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


def music_beats(job, slug):
    """Temps de la musique du slug (librosa, en secondes depuis le début de la piste), gardés dans work/<slug>_beats.json."""
    mj = job / "work" / f"{slug}_music.json"
    if not mj.exists():
        return []
    src = job / read_json(mj)["file"]
    if not src.exists():
        return []
    cache = job / "work" / f"{slug}_beats.json"
    if cache.exists():
        c = read_json(cache)
        if c.get("file") == str(src) and c.get("mtime") == src.stat().st_mtime:
            return c["beats"]
    try:
        import librosa
        y, sr = librosa.load(str(src), sr=22050, mono=True)
        _, frames = librosa.beat.beat_track(y=y, sr=sr)
        beats = [round(float(t), 3) for t in librosa.frames_to_time(frames, sr=sr)]
    except Exception:  # noqa: BLE001 — pas d'analyse possible : on coupe sans caler
        beats = []
    write_json(cache, {"file": str(src), "mtime": src.stat().st_mtime, "beats": beats})
    return beats


def snap_beat(t, beats, tol=0.3, lo=None):
    """Instant t recalé sur le temps de musique le plus proche (à tol près), sans passer avant lo."""
    best = min(beats, key=lambda b: abs(b - t)) if beats else None
    if best is None or abs(best - t) > tol or (lo is not None and best < lo):
        return t
    return best
