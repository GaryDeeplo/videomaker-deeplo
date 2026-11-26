"""SOUND DESIGN AUTOMATIQUE : un petit bruitage sur ce qui apparaît à l'écran (whoosh sur un changement de plan, pop sur
un élément de liste, tap sur un bouton, impact sur un chiffre, verre sur une notification…), calé sur l'instant
exact de l'animation, lu dans la composition elle-même. Marche avec tous les monteurs (rush, scènes, explainer,
punch, infographie, montage) ; les monteurs l'appellent d'eux-mêmes (config "sfx": {"design": true}, par défaut).

  python sound_design.py <job> [--off] [--densite 0.45]

- Instants : début de chaque plan / scène / temps fort / bloc (data-start) et chaque entrée animée à l'intérieur
  (tl.fromTo(... opacity: 0 ...)), décalage des timelines imbriquées compris. Jamais un timecode écrit à la main.
  Le PIC du son (index real-sfx) tombe sur l'instant : impact / tampon / prix à 70 % de l'animation d'entrée.
- Sons : banque locale sounds/openverse (real-sfx), ordre mélangé par job (graine = nom du job) sans répétition
  immédiate, hauteur ±1 demi-ton et gain ±1,5 dB ; pops en cascade sur une échelle montante. Niveau mesuré une fois
  pour toutes (max du volume momentané, ebur128) puis gain fixe + limiteur, cible par famille (impacts -16, souffles /
  pops / clics -20, ticks / scintillements -24) ; rien sur les sous-titres.
- Couches : riser qui monte jusqu'au pic d'un gros chiffre, boom sous l'impact de l'accroche (-6 dB), sub-drop sous
  une révélation, applaudissements sur la fin d'un événement ("sfx": {"applause": true} pour forcer).
- Retenue : au moins 0,45 s entre deux bruitages (les changements de plan passent en priorité), 1,2 s entre deux sons
  de la même famille (sauf cascade de 3 pops), rien à moins de 0,3 s d'un son déjà posé par le monteur, et au plus
  un son par changement de plan + 0,5 son par seconde ; au-delà, on retire les sons les plus serrés (pas ceux de la fin).
Relancer remplace le bloc précédent (balise <!-- sound-design -->).
"""
import argparse
import random
import re
import subprocess
from pathlib import Path

import numpy as np

from common import REAL_SFX_INDEX, SOUNDS, config, job_dir, out, probe, read_json

BANK = SOUNDS / "openverse"
MARK_A, MARK_B = "<!-- sound-design -->", "<!-- /sound-design -->"
# niveau visé : max du volume momentané (LUFS, fenêtre 0,4 s), mesuré sur le son allongé de 1 s de silence
TARGET = {"hit": -16, "boom": -16, "cash": -16, "subdrop": -16,
          "whoosh": -20, "swoosh": -20, "swoosh_soft": -20, "pop": -20, "click": -20, "tap": -20, "glitch": -20,
          "shutter": -20, "ding": -20, "chime": -20, "glass": -20, "paper": -22, "pageflip": -22, "swell": -22,
          "riser": -22, "applause": -22, "typing": -24, "tick": -24, "sparkle": -24}
# réglage fin une fois le niveau mis à la cible
VOL = {"whoosh": 0.8, "swoosh": 0.8, "swoosh_soft": 0.75, "pop": 0.8, "click": 0.85, "tap": 0.85, "tick": 0.8, "ding": 0.75,
       "glass": 0.75, "hit": 0.8, "sparkle": 0.8, "chime": 0.7, "swell": 0.7, "typing": 0.7, "cash": 0.75, "paper": 0.8,
       "pageflip": 0.8, "boom": 0.5, "subdrop": 0.5, "riser": 0.75, "glitch": 0.7, "shutter": 0.8, "applause": 0.6}
PRIO = {"whoosh": 3, "swoosh": 3, "glitch": 3, "shutter": 3, "hit": 2, "boom": 2, "ding": 2, "glass": 2, "chime": 2, "cash": 2, "subdrop": 2}
MAXLEN = {"swell": 2.5, "chime": 2.0, "sparkle": 2.0, "glass": 2.0, "typing": 8.0, "boom": 5.0, "riser": 6.0, "applause": 6.0,
          "subdrop": 3.0}
CUT = {"typing", "boom", "riser", "applause", "subdrop"}  # sons longs : coupés à la longueur utile + fondu
FALLBACK = {"glass": "ding", "swoosh_soft": "swoosh", "tap": "click", "subdrop": "boom", "boom": "subdrop", "pageflip": "paper",
            "shutter": "click", "glitch": "whoosh"}
VARY = {"whoosh", "swoosh", "swoosh_soft", "pop", "click", "tap", "tick", "hit", "ding", "glass", "sparkle", "shutter", "paper",
        "pageflip", "cash", "chime"}  # familles dont la hauteur varie (±1 demi-ton)
SAME_FAM, CASC_GAP, SCALE = 1.2, 0.8, [0, 4, 7]  # pops en cascade : arpège montant (do, mi, sol)
RISER_LEN = 1.6

# blocs de la bibliothèque (data-composition-src) -> famille
BLOCKS = {"compteur": "tick", "note-etoiles": "sparkle", "sticker": "pop", "notification": "glass", "bouton-cta": "tap",
          "confetti": "sparkle", "compte-rebours": "tick", "jauge": "swell", "barres": "swell", "tarif": "cash", "suivre": "tap",
          "fleche": "swoosh", "surligneur": "swoosh_soft", "frise": "swoosh", "machine-a-ecrire": "typing", "intro-marque": "whoosh",
          "outro-marque": "chime", "bandeau-nom": "swoosh_soft", "marquee": "swoosh_soft", "mot-tournant": "pop", "lottie": "pop",
          "recherche-verre": "click", "lieu-photo": "pop", "cartes-3d": "swoosh", "chiffre-verre": "hit", "fin-logo": "chime"}
TWEEN_BLOCKS = ("chiffre-verre", "tarif")  # impact calé sur la 1re animation du bloc
# classes de clip -> famille (None = silence)
CLIPS = [("cap", None), ("hd", None), ("ser", None), ("shade", None), ("lab", "tick"), ("hook", "hit"), ("k-photo", "shutter"),
         ("k-stat", "hit"), ("shotv", "whoosh"), ("shot", "whoosh"), ("scene", "whoosh"), ("cmp", "swoosh"), ("pwrap", "pop"),
         ("ttls", "hit"), ("beat", "swoosh"), ("card", "pop"), ("br", "whoosh")]
# classes de l'élément animé à l'intérieur -> famille
INNER = [(r"\b(eur|ivc)\b", "cash"), (r"\b(big|num|stat|price|pct|count|cnt)\b", "hit"), (r"\b(btn|button|cta)\b", "tap"),
         (r"\b(cur|cursor|done)\b", "click"), (r"\b(notif|toast)\b", "glass"), (r"\b(msg|bubble)\b", "ding"),
         (r"\b(stamp|stampx|tag|tagp)\b", "hit"), (r"\b(chart|line|bar|bars|gauge|curve)\b", "swell"),
         (r"\b(pill|chip|item|row|stp|p\d+|r\d+|it\d*|li|card|tile|dbx|x\d+)\b", "pop")]
BIG = r"\b(big|num|stat|cnt|count)\b"  # gros chiffre : riser avant, sub-drop dessous
EVENT = r"evenement|événement|event|soiree|soirée|gala|salon|inauguration|concert|mariage|fete|fête|anniversaire|conference|conférence|seminaire|séminaire|lancement"
_IDX = None


def peak_of(f):
    """Instant du pic (s) : index real-sfx, sinon maximum de l'enveloppe."""
    global _IDX
    if _IDX is None:
        _IDX = {}
        if REAL_SFX_INDEX.exists():
            for s in read_json(REAL_SFX_INDEX).get("sounds", []):
                _IDX[Path(s["path"]).name] = float(s.get("peak_time") or 0.0)
    if f.name in _IDX:
        return _IDX[f.name]
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-ac", "1", "-ar", "8000", "-f", "f32le", "-"], capture_output=True)
    a = np.abs(np.frombuffer(p.stdout, dtype=np.float32))
    _IDX[f.name] = round(float(np.argmax(a)) / 8000, 3) if len(a) else 0.0
    return _IDX[f.name]


def files(cat):
    """[(fichier, durée, pic)] de la famille : sons courts (ponctuation), ou longs coupés à la longueur utile."""
    d = BANK / cat
    res = []
    for f in sorted(d.glob("*.mp3")) + sorted(d.glob("*.wav")):
        try:
            du = float(probe(f)["duration"])
        except Exception:  # noqa: BLE001
            continue
        if du <= MAXLEN.get(cat, 1.6) * (2.5 if cat in CUT else 1):
            res.append((f, du, min(peak_of(f), du)))
    if cat == "riser":  # un riser monte : pic tardif
        res = [x for x in res if x[2] >= 1.2]
    if cat == "boom":  # sous un impact : pic tout de suite
        res = [x for x in res if x[2] <= 0.4] or res
    return res


def mmax(chain, src):
    """Max du volume momentané (LUFS) d'un son, allongé de 1 s de silence (fenêtre de 0,4 s pleine)."""
    log = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af", chain + ",apad=pad_dur=1,ebur128",
                          "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    ms = [float(x) for x in re.findall(r"\bM:\s*(-?[\d.]+)", log)]
    return max(ms) if ms else -120.0


def prepared(job, f, fam, peak, start=0.0, cut=None, semis=0.0, fade_in=0.0, fade_out=None):
    """Copie mise à niveau dans assets/sfx/ (cache) ; renvoie (src relatif, durée, pic dans la copie)."""
    d = job / "assets" / "sfx"
    d.mkdir(parents=True, exist_ok=True)
    tag = (f"_s{int(start * 1000)}" if start else "") + (f"_c{int(cut * 1000)}" if cut else "") + \
          (f"_p{'u' if semis > 0 else 'd'}{int(abs(semis) * 10)}" if semis else "")
    dst = d / f"sd2_{f.stem}{tag}.wav"
    if not dst.exists():
        seg = ["aresample=48000", "aformat=sample_fmts=fltp:channel_layouts=stereo"]  # mesuré en stéréo, comme la copie
        if start or cut:
            seg.append(f"atrim=start={start:.3f}" + (f":end={start + cut:.3f}" if cut else "") + ",asetpts=PTS-STARTPTS")
        if fade_in:
            seg.append(f"afade=t=in:d={fade_in:.3f}")
        if cut:
            fo = fade_out if fade_out is not None else min(1.5, cut * 0.25)
            seg.append(f"afade=t=out:st={max(0.0, cut - fo):.3f}:d={fo:.3f}")
        m = mmax(",".join(seg), f)
        gain = 0.0 if m < -70 else max(-30.0, min(30.0, TARGET.get(fam, -20) - m))
        pitch = [f"asetrate={48000 * 2 ** (semis / 12):.0f}", "aresample=48000"] if semis else []
        af = ",".join(seg + pitch + [f"volume={gain:.2f}dB", "alimiter=limit=0.89:level=false:latency=true"])
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(f), "-af", af, "-ar", "48000", "-ac", "2", str(dst)], check=True)
    pk = max(0.0, peak - start) / 2 ** (semis / 12)
    return f"assets/sfx/{dst.name}", round(float(probe(dst)["duration"]), 3), round(pk, 3)


def block_hit(job, src_rel):
    """Instant de l'impact dans un bloc : 70 % de sa première animation (position et durée écrites en clair)."""
    p = job / src_rel
    if not p.exists():
        return None
    m = re.search(r"fromTo\([^;]*?\{[^}]*\}\s*,\s*\{([^}]*)\}\s*,\s*([\d.]+)\s*\)", p.read_text(encoding="utf-8"))
    du = re.search(r"duration:\s*([\d.]+)", m.group(1)) if m else None
    return float(m.group(2)) + 0.7 * float(du.group(1)) if du else None


def events(html_, job=None, luxe=False, punch=False):
    """[(t, famille, quoi, info)] lus dans la composition ; t = instant où le pic du son doit tomber."""
    ev, kinds, n_shot = [], {}, 0
    # clips (class="clip …") et blocs montés (data-composition-src, sans classe : common.mount)
    for m in re.finditer(r"<(div|video|img|section)\b([^>]*)>", html_):
        tagn, attrs = m.group(1), m.group(2)
        if not re.search(r'\bclass="clip\b|data-composition-src="', attrs):
            continue
        cm = re.search(r'class="([^"]*)"', attrs)
        cls = cm.group(1).split() if cm else []
        st = re.search(r'data-start="([\d.]+)"', attrs)
        if not st:
            continue
        t = float(st.group(1))
        idm = re.search(r'\bid="([^"]+)"', attrs)
        src = re.search(r'data-composition-src="([^"]*?([\w-]+)\.html)"', attrs)
        du = re.search(r'data-duration="([\d.]+)"', attrs)
        du = float(du.group(1)) if du else 0.0
        if src:
            name = src.group(2)
            if name.startswith("accroche-"):
                ev.append((t + 0.15, "hit", name, {"kind": "hook"}))
                if du:
                    ev.append((t + du - 0.45, "whoosh", name + " (sortie)", {}))
                continue
            fam = next((v for k, v in BLOCKS.items() if name.startswith(k)), "pop")
            if fam == "cash" and luxe:
                fam = "glass"  # tarif haut de gamme : verre plutôt que caisse
            info = {"dur": du}
            th = t + 0.05
            if name.startswith(TWEEN_BLOCKS) and job is not None:
                bh = block_hit(job, src.group(1))
                th = t + bh if bh is not None else th
            if name.startswith("chiffre-verre"):
                info["kind"] = "big"
            if name.startswith(("fin-logo", "outro-marque")):
                info["kind"] = "outro"
            if fam == "typing":
                th = t + 0.05
            ev.append((th, fam, name, info))
            continue
        fam, info = "skip", {}
        for k, v in CLIPS:
            if k in cls or (idm and k == "br" and idm.group(1).startswith("br-")):
                fam = v
                break
        photo = tagn == "img" or bool(re.match(r"\s*(<div[^>]*>\s*)*<img\b", html_[m.end():m.end() + 300]))
        if fam in ("whoosh", "swoosh") and photo and "vid" not in cls:
            fam = "shutter"  # plan photo : déclencheur d'appareil
        elif fam == "whoosh" and punch and "shot" in cls and t > 0.05:
            n_shot += 1
            if n_shot % 2 == 0:
                fam = "glitch"  # pack punch : un changement de plan vidéo sur deux en glitch
        if "hook" in cls:
            info, t = {"kind": "hook"}, t + 0.15
        if "k-stat" in cls:
            info = {"kind": "big"}
        if idm:
            kinds[idm.group(1)] = fam
        if fam not in ("skip", None) and t > 0.05:
            ev.append((t, fam, " ".join(cls[1:]) or (idm.group(1) if idm else ""), info))
    # décalage des timelines imbriquées (master.add(tl, T0), tl.add(ct, T0))
    off = {}
    for m in re.finditer(r"(\w+)\.add\((\w+),\s*([\d.]+)\)", html_):
        off[m.group(2)] = off.get(m.group(1), 0.0) + float(m.group(3))
    # entrées animées à l'intérieur d'un clip qui fait du bruit (élément de liste, chiffre, bouton…)
    for m in re.finditer(r"(\w+)\.fromTo\(\"#([\w-]+) ([^\"]+)\",\s*\{([^}]*)\}\s*,\s*\{([^}]*)\}\s*,\s*([\d.]+)\s*\)", html_):
        var, cid, sel, frm, to, t = m.groups()
        if "opacity: 0" not in frm or kinds.get(cid) in (None, "skip"):
            continue
        fam = next((v for pat, v in INNER if re.search(pat, sel)), None)
        if not fam:
            continue
        if fam == "cash" and luxe:
            fam = "glass"
        t = float(t) + off.get(var, 0.0)
        tw = re.search(r"duration:\s*([\d.]+)", to)
        if fam in ("hit", "cash") and tw:  # impact / tampon / prix : quand l'élément se pose (70 % de l'entrée)
            t += 0.7 * float(tw.group(1))
        info = {"grp": cid}  # éléments d'un même clip : une cascade possible
        if fam == "hit" and re.search(BIG, sel):
            info["kind"] = "big"
        ev.append((t, fam, f"#{cid} {sel}", info))
    return sorted(ev, key=lambda e: e[0])


def existing(html_):
    """Instants des sons déjà posés par le monteur (hors voix et musique)."""
    res = []
    for m in re.finditer(r"<audio\b([^>]*)>", html_):
        a = m.group(1)
        if 'id="voice"' in a or 'id="music"' in a or "sd-" in a:
            continue
        st = re.search(r'data-start="([\d.]+)"', a)
        if st:
            res.append(float(st.group(1)))
    return res


def select(ev, taken, total, gap=0.45):
    """Sons gardés : priorité aux changements de plan, écarts, même famille espacée, puis budget."""
    casc, cid, prev = {}, 0, None
    for i, e in enumerate(ev):  # cascades : pops successifs du même clip (1,5 s au plus), ou à moins de 0,8 s
        if e[1] == "pop":
            g, pg = e[3].get("grp"), ev[prev][3].get("grp") if prev is not None else None
            if prev is None or e[0] - ev[prev][0] > (1.5 if g and g == pg else CASC_GAP):
                cid += 1
            casc[i], prev = cid, i
    kept = []
    for prio in (3, 2, 1):
        for i, (t, fam, what, info) in enumerate(ev):
            if PRIO.get(fam, 1) != prio or any(abs(t - x) < 0.3 for x in taken):
                continue
            c = casc.get(i)
            same = lambda k: c is not None and casc.get(k[4]) == c  # noqa: E731
            if any(abs(t - k[0]) < (0.2 if same(k) else 0.3 if {prio, PRIO.get(k[1], 1)} == {2, 3} else gap) for k in kept):
                continue
            if any(k[1] == fam and abs(t - k[0]) < SAME_FAM and not same(k) for k in kept):
                continue
            if c is not None and sum(1 for k in kept if same(k)) >= len(SCALE):
                continue
            kept.append((t, fam, what, info, i, c))
    kept.sort(key=lambda k: k[0])
    budget = max(3, sum(1 for k in kept if PRIO.get(k[1], 1) == 3) + int(0.5 * total))
    while len(kept) > budget:  # on retire le son le plus serré parmi les moins prioritaires (début, milieu ou fin)
        lo = min(PRIO.get(k[1], 1) for k in kept)

        def crowd(j):
            ns = [abs(kept[j][0] - kept[x][0]) for x in (j - 1, j + 1) if 0 <= x < len(kept)]
            return min(ns) if ns else 1e9
        kept.pop(min((j for j in range(len(kept)) if PRIO.get(kept[j][1], 1) == lo), key=crowd))
    return kept


class Picker:
    """Fichiers d'une famille dans un ordre mélangé (graine = job), sans répétition immédiate."""

    def __init__(self, rng):
        self.rng, self.queue, self.last, self.pool = rng, {}, {}, {}

    def fam(self, fam):
        """Famille servie (repli si la banque est vide) -> (nom, fichiers)."""
        for f in (fam, FALLBACK.get(fam)):
            if f and f not in self.pool:
                self.pool[f] = files(f)
            if f and self.pool[f]:
                return f, self.pool[f]
        return fam, []

    def pick(self, fam):
        fam, fs = self.fam(fam)
        if not fs:
            return fam, None
        q = self.queue.get(fam)
        if not q:
            q = list(range(len(fs)))
            self.rng.shuffle(q)
            if len(q) > 1 and q[0] == self.last.get(fam):
                q.append(q.pop(0))
            self.queue[fam] = q
        i = q.pop(0)
        self.last[fam] = i
        return fam, fs[i]


def apply(job, gap=0.45, off=False):
    p = job / "index.html"
    h = p.read_text(encoding="utf-8")
    h = re.sub(re.escape(MARK_A) + r".*?" + re.escape(MARK_B) + r"\n?", "", h, flags=re.S)
    if off:
        p.write_text(h, encoding="utf-8")
        return {"sons": 0}
    c = config(job)
    sf = c.get("sfx", {})
    rng = random.Random(job.name)
    luxe = c.get("text", {}).get("captionStyle") == "editorial"
    punch = 'class="clip ttls' in h
    meta = read_json(job / "job.json") if (job / "job.json").exists() else {}
    event = sf.get("applause")
    if event is None:
        event = bool(re.search(EVENT, f"{job.name} {meta.get('sujet', '')}", re.I))
    dur_m = re.search(r'data-composition-id="[^"]+"[^>]*data-duration="([\d.]+)"', h)
    total = float(dur_m.group(1)) if dur_m else 1e9
    ev = [e for e in events(h, job, luxe, punch) if 0.1 < e[0] < total - 0.2]
    kept = select(ev, existing(h), total, gap)
    pk = Picker(rng)
    plan, casc_file, casc_n, layers, risers = [], {}, {}, [], []

    def place(t, fam, layer=False, length=None, semis=None):
        """Pose un son dont le pic tombe à t -> entrée du plan (ou None)."""
        fam_, item = pk.pick(fam)
        if not item:
            return None
        f, du, peak = item
        start, cut, fi, fo = 0.0, None, 0.0, None
        if fam_ == "riser":  # coupé pour finir sur son pic, qui tombe sur l'impact
            start = max(0.0, peak - RISER_LEN)
            cut, fi, fo = round(peak - start + 0.06, 3), 0.25, 0.05
        elif fam_ in CUT:
            cut = round(min(MAXLEN.get(fam_, du), du, length or du), 2)
            cut = None if cut >= du - 0.01 else cut
        if semis is None:
            semis = rng.choice([-1, -0.5, 0, 0, 0.5, 1]) if fam_ in VARY and not layer else 0
        src, d2, pk2 = prepared(job, f, fam_, peak, start, cut, semis, fi, fo)
        st = round(max(0.0, t - (0.0 if fam_ in ("typing", "applause") else pk2)), 3)  # nappes : dès l'instant
        if st >= total - 0.1:
            return None
        g = 0.0 if layer else rng.uniform(-1.5, 1.5)
        return {"st": st, "fam": fam_, "src": src, "dur": round(min(d2, total - st), 3),
                "vol": round(VOL.get(fam_, 0.7) * 10 ** (g / 20), 3), "t": t, "item": item}

    for t, fam, what, info, i, cc in kept:
        semis = None
        if cc is not None:  # cascade : même fichier, arpège montant
            k = casc_n.get(cc, 0)
            casc_n[cc] = k + 1
            if k:
                semis = SCALE[min(k, len(SCALE) - 1)]
                fam_, (f, du, peak) = casc_file[cc]
                src, d2, pk2 = prepared(job, f, fam_, peak, semis=semis)
                st = round(max(0.0, t - pk2), 3)
                plan.append({"st": st, "fam": fam_, "src": src, "dur": round(min(d2, total - st), 3),
                             "vol": round(VOL.get(fam_, 0.7), 3), "t": t})
                continue
            semis = 0
        e = place(t, fam, length=info.get("dur", 0) - 0.3 if fam == "typing" and info.get("dur") else None, semis=semis)
        if not e:
            continue
        if cc is not None:
            casc_file[cc] = (e["fam"], e["item"])
        plan.append(e)
        kind = info.get("kind")
        # couches : riser avant un gros chiffre, boom sous l'accroche, sub-drop sous une révélation, applaudissements
        if len(layers) >= 4 and kind != "outro":
            continue
        if kind == "hook":
            lay = place(t, "boom", layer=True, length=2.5)  # VOL boom = 0,5 : -6 dB sous l'impact
            if lay:
                layers.append(lay)
        if kind in ("hook", "big") and t >= RISER_LEN + 0.4 and len(risers) < 2 and all(t - r > 8 for r in risers) \
                and not any(PRIO.get(k[1], 1) >= 2 and t - 1.4 < k[0] < t - 0.1 for k in kept):
            lay = place(t, "riser", layer=True)
            if lay:
                layers.append(lay)
                risers.append(t)
        if kind == "big" and sum(1 for x in layers if x["fam"] == "subdrop") < 2:
            lay = place(t, "subdrop", layer=True, length=2.2)
            if lay:
                layers.append(lay)
        if kind == "outro" and event:
            lay = place(t - 0.1, "applause", layer=True, length=min(MAXLEN["applause"], total - t))
            if lay:
                layers.append(lay)
    plan = sorted(plan + layers, key=lambda e: e["st"])
    nodes = [f'    <audio id="sd-{i}" class="clip" src="{e["src"]}" data-start="{e["st"]}" data-duration="{e["dur"]}" '
             f'data-track-index="{80 + i % 10}" data-volume="{e["vol"]}"></audio>' for i, e in enumerate(plan)]
    block = MARK_A + "\n" + "\n".join(nodes) + "\n    " + MARK_B + "\n"
    # juste avant la fermeture de la racine (dernier </div> avant le premier <script> du corps)
    body = h.index("<body")
    sc = h.index("<script", body)
    cut = h.rindex("</div>", body, sc)
    h = h[:cut] + block + "  " + h[cut:]
    p.write_text(h, encoding="utf-8")
    fams = {}
    for e in plan:
        fams[e["fam"]] = fams.get(e["fam"], 0) + 1
    return {"sons": len(nodes), "couches": len(layers), "familles": fams}


def auto(job):
    """Appelé par les monteurs après l'écriture de index.html : bruitages, puis baisse de la musique (mix.py)."""
    c = config(job)
    sf = c.get("sfx", {})
    rep = None
    if sf.get("enabled", True) and sf.get("design", True):
        try:
            rep = apply(job)
        except Exception as e:  # noqa: BLE001  (le bruitage ne doit jamais bloquer un montage)
            rep = {"erreur": str(e)[:200]}
    import mix
    p = job / "index.html"
    h, mrep = mix.auto(job, p.read_text(encoding="utf-8"))
    p.write_text(h, encoding="utf-8")
    return {"bruitages": rep, "musique": mrep}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--off", action="store_true", help="retire les bruitages posés")
    ap.add_argument("--densite", type=float, default=0.45, help="écart minimal entre deux bruitages (s)")
    a = ap.parse_args()
    r = apply(job_dir(a.job), a.densite, a.off)
    out(ok=True, **r, suite="npx hyperframes check, puis aperçu avec le son")


if __name__ == "__main__":
    main()
