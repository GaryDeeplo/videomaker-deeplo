"""COMPOSITION HyperFrames -> <job>/index.html   (base reel-cut, étendue)

- Vidéo dérushée + caméra (doctrine reel-cut : drifts imperceptibles de 3 %, punch-in +7,5 % rare).
- Texte selon text.mode : "captions" (sous-titres complets, styles pop | karaoke | minimal | boite | impact | duo | mono | bulle | souligne,
  emoji automatique sur les mots-clés avec text.captionEmoji ou --emoji),
  "overlays" (phrases rares verbatim de reel-cut), ou "both".
- SFX réels de la banque sounds/ (real-sfx) : whoosh calé par son pic sur chaque punch, tick sur les jointures.
- Charte : police, couleurs, cadrage horizontal (visual.focusX) depuis config / brand.json.
Rien n'est gravé : tout reste modifiable dans le Studio HyperFrames.

- Sous-titres qui évitent le visage (face.py, vertical) : sous le menton, sinon au-dessus de la tête, sinon en bas
  sur fond sombre, dans la zone sûre de la plateforme (text.platform : tous | reels | tiktok | shorts) ;
  --no-visage (ou text.captionFace: false) garde la hauteur fixe captionTopPct.
- work/<slug>_calques.json : où et quand chaque calque est posé (contrôle « visage couvert » de face.py / qa.py).

  python build_composition.py <job> <slug> [--no-cam] [--no-sfx] [--mode captions|overlays|both] [--style pop]
"""
import argparse
import html
import json
import math
import shutil
from pathlib import Path

import re

from zooms import strong_words, zoom_js
import sound_design
from common import (REAL_SFX_INDEX, ROOT, SOUNDS, add_credit, block_file, brand_info, config, fail, job_dir, motion_nodes,
                    mount, out, probe, read_json, size_of, word_hit, write_json)

S_MIN, S_MAX = 1.0, 1.13
PUNCH_JUMP, PUNCH_SETTLE, PUNCH_DUR = 0.075, 0.055, 3.0
DRIFT_SPREAD, DRIFT_TARGET = 0.03, 10.0
SHADOW = "0 2px 5px rgba(0,0,0,0.9), 0 6px 18px rgba(0,0,0,0.75), 0 14px 40px rgba(0,0,0,0.55)"


def esc(s):
    return html.escape(s, quote=True)


def clamp(v):
    return round(max(S_MIN, min(S_MAX, v)), 4)


def build_cam(dur, punches):
    """[t, from, to, durée, ease] ; les drifts s'enchaînent (from == to précédent)."""
    cam, cur, up = [], 1.03, True
    bounds = sorted({0.0, *[p for p in punches if 0 < p < dur], dur})
    for i in range(len(bounds) - 1):
        t0, t1 = bounds[i], bounds[i + 1]
        span = t1 - t0
        if span <= 0.05:
            continue
        if i > 0 and any(abs(t0 - p) < 1e-6 for p in punches):
            pd = min(PUNCH_DUR, span)
            a, b = clamp(cur + PUNCH_JUMP), clamp(cur + PUNCH_SETTLE)
            cam.append([round(t0, 3), a, b, round(pd, 3), "power2.out"])
            cur, t0, span = b, t0 + pd, span - pd
            if span <= 0.05:
                continue
        n = max(1, round(span / DRIFT_TARGET))
        seg = span / n
        for k in range(n):
            nxt = clamp(cur + (DRIFT_SPREAD if up else -DRIFT_SPREAD))
            if nxt == clamp(cur):
                up = not up
                nxt = clamp(cur + (DRIFT_SPREAD if up else -DRIFT_SPREAD))
            cam.append([round(t0 + k * seg, 3), clamp(cur), nxt, round(seg, 3), "power1.inOut"])
            cur, up = nxt, not up
    return cam


def sfx_asset(job, rel):
    """Copie un son de la banque dans assets/sfx et renvoie (chemin relatif, instant du pic)."""
    src = SOUNDS / rel
    if not src.exists():
        return None, 0.0, 0.0
    (job / "assets" / "sfx").mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, job / "assets" / "sfx" / src.name)
    peak = 0.06
    if REAL_SFX_INDEX.exists():
        for s in read_json(REAL_SFX_INDEX).get("sounds", []):
            if Path(s["path"]).name == src.name:
                peak = float(s.get("peak_time") or peak)
    return f"assets/sfx/{src.name}", peak, round(probe(src)["duration"], 3)


def broll_nodes(job, items, words, dur, W, H, T0, whoosh=None):
    """Plans de coupe (work/<slug>_broll.json) posés sur un mot dit, jusqu'au mot "until" ou pendant "dur" secondes.
    Image ou vidéo du client (inbox/) ou image libre (broll.py get). Sous les sous-titres, au-dessus du rush."""
    nodes, js, sfx, rep, prev_end = [], [], [], [], 0.0
    credits = read_json(job / "work" / "broll_credits.json") if (job / "work" / "broll_credits.json").exists() else {}
    for k, b in enumerate(items or []):
        hit = word_hit(words, b.get("word", ""), b.get("occurrence", 1))
        if not hit or not b.get("image"):
            rep.append({"mot": b.get("word"), "pose": False, "raison": "mot introuvable" if not hit else "pas d'image"})
            continue
        st = max(prev_end + 0.05, hit["start"] - 0.1)
        end_w = word_hit(words, b["until"], 1, lo=hit["start"], hi=hit["start"] + 12) if b.get("until") else None
        en = min(dur - 0.1, end_w["end"] + 0.2 if end_w else st + float(b.get("dur", 2.5)), st + 8.0)
        if en - st < 0.8:
            rep.append({"mot": b.get("word"), "pose": False, "raison": "trop court"})
            continue
        src = Path(b["image"])
        if not (job / src).exists() or src.parts[0] != "assets":
            for base in (job / "inbox", job, ROOT):
                if not src.is_absolute() and (base / src).exists():
                    src = base / src
                    break
            if not src.exists():
                rep.append({"mot": b.get("word"), "pose": False, "raison": f"introuvable : {b['image']}"})
                continue
            (job / "assets" / "broll").mkdir(parents=True, exist_ok=True)
            if src.resolve() != (job / "assets" / "broll" / src.name).resolve():
                shutil.copy2(src, job / "assets" / "broll" / src.name)
            rel = f"assets/broll/{src.name}"
        else:
            rel = str(src).replace("\\", "/")
        if credits.get(rel):
            add_credit(job, credits[rel])
        mode = b.get("mode", "full")
        is_vid = rel.lower().endswith((".mp4", ".mov", ".webm"))
        S0, D = round(st + T0, 3), round(en - st, 3)
        cls = "carte" if mode == "carte" else "full"
        if is_vid:  # la vidéo porte elle-même le minutage (une vidéo minutée ne s'imbrique pas dans un élément minuté)
            nodes.append(f'      <div class="broll {cls}" id="br-{k}"><div class="bw"><video id="brv-{k}" class="bri clip" src="{esc(rel)}" '
                         f'data-start="{S0}" data-duration="{D}" data-track-index="{40 + k}" muted playsinline></video></div></div>')
        else:
            nodes.append(f'      <div class="clip broll {cls}" id="br-{k}" data-start="{S0}" data-duration="{D}" '
                         f'data-track-index="{2 + k % 2}"><div class="bw"><img class="bri" src="{esc(rel)}" alt=""></div></div>')
        t0, t1 = round(st, 3), round(en, 3)
        if mode == "carte":
            js.append(f'  tl.fromTo("#br-{k} .bw", {{ opacity: 0, y: 80, scale: 0.82, rotation: -5 }}, {{ opacity: 1, y: 0, scale: 1, rotation: -2, '
                      f'duration: 0.45, ease: "back.out(1.6)", immediateRender: false }}, {t0});')
        else:
            js.append(f'  tl.fromTo("#br-{k} .bw", {{ opacity: 0, scale: 1.06 }}, {{ opacity: 1, scale: 1, duration: 0.22, ease: "power2.out", '
                      f'immediateRender: false }}, {t0});')
        if not is_vid:  # léger travelling (Ken Burns) pendant le plan
            js.append(f'  tl.fromTo("#br-{k} .bri", {{ scale: 1.0, xPercent: 0 }}, {{ scale: 1.1, xPercent: {(-2, 2)[k % 2]}, duration: {round(t1 - t0, 3)}, '
                      f'ease: "none", immediateRender: false }}, {t0});')
        js.append(f'  tl.to("#br-{k} .bw", {{ opacity: 0, duration: 0.18, ease: "power1.in" }}, {round(t1 - 0.18, 3)});')
        if whoosh and whoosh[0]:
            ws = round(max(0.0, st - whoosh[1]) + T0, 3)
            sfx.append(f'      <audio id="sfx-br{k}" class="clip" src="{whoosh[0]}" data-start="{ws}" '
                       f'data-duration="{min(whoosh[2], dur + T0 - ws)}" data-track-index="13" data-volume="{whoosh[3]}"></audio>')
        rep.append({"mot": b.get("word"), "pose": True, "a": t0, "duree": D, "image": rel, "mode": mode})
        prev_end = en
    return nodes, js, sfx, rep


def text_box(text, size, x0, width, top, line_h, max_lines=None, center=True, pad=0.0):
    """Boîte estimée d'un texte à l'écran [x0, y0, x1, y1] (≈ 0,6 em par caractère gras) : pour placer les
    sous-titres et repérer un visage couvert (face.py). center : centré dans la largeur, sinon calé à gauche."""
    tw = len(text) * 0.6 * size + 2 * pad * size
    lines = max(1, math.ceil(tw / max(1.0, width)))
    if max_lines:
        lines = min(lines, max_lines)
    w = min(width, tw)
    xa = x0 + (width - w) / 2 if center else x0
    return [round(xa), round(top), round(xa + w), round(top + lines * line_h * size + 2 * pad * size)]


EMOJI_CHAR = {"valide": "✅", "coeur": "❤️", "etoile": "⭐", "pouce": "👍", "fusee": "🚀", "cadeau": "🎁", "idee": "💡",
              "regard": "👀", "waouh": "🤩", "adore": "😍", "cent": "💯", "bravo": "🙌", "applaudir": "👏", "eclat": "✨",
              "cloche": "🔔", "alarme": "🚨", "trophee": "🏆", "force": "💪", "reflexion": "🤔", "rire": "😂", "doigt": "👉",
              "cible": "🎯", "feu": "🔥", "fete": "🎉"}
NBSP = chr(160)  # espace insécable
EDITORIAL_INK = "#F4EAD5"  # ivoire du mot fort (style « editorial ») ; text.editorialColor pour une autre teinte
STYLES = ["pop", "karaoke", "minimal", "boite", "impact", "duo", "seam", "mono", "bulle", "souligne", "geant", "editorial"]


def emoji_for(word):
    """Emoji d'un mot-clé (même dictionnaire que la suggestion de motions), sinon None."""
    from suggest_motions import EMOJI, keys
    for k in keys(word):
        if k in EMOJI:
            return EMOJI_CHAR.get(EMOJI[k])
    return None


def key_word(words):
    """Style duo : les nombres, sinon le mot le plus long du groupe (6 lettres et plus), passent en couleur."""
    nums = {j for j, w in enumerate(words) if re.search(r"\d|€|%", w["w"])}
    if nums:
        return nums
    j = max(range(len(words)), key=lambda j: len(words[j]["w"]))
    return {j} if len(re.sub(r"\W", "", words[j]["w"])) >= 6 else set()


VOY = "aeiouyàâäéèêëîïôöùûüœæ"
INSEP = {"bl", "br", "cl", "cr", "dr", "fl", "fr", "gl", "gr", "pl", "pr", "tr", "vr", "ch", "ph", "gn", "th", "qu", "gu"}


def syllabes(mot):
    """Découpe orale approximative d'un mot français (« incroyable » -> in, cro, ya, ble) pour l'affichage en escalier."""
    m, out, cur, i = mot, [], "", 0
    low = mot.lower()
    while i < len(m):
        cur += m[i]
        if low[i] in VOY and i + 2 < len(m) and low[i + 1] == "y" and low[i + 2] in VOY:  # « croyable » : cro-yable
            out.append(cur)
            cur, i = "", i + 1
            continue
        if low[i] in VOY and i + 1 < len(m):
            j = i + 1
            while j < len(m) and low[j] not in VOY and low[j].isalpha():
                j += 1
            cons = low[i + 1:j]
            if j >= len(m) or not cons:  # fin du mot, ou deux voyelles qui se suivent : on continue
                i += 1
                continue
            cut = i + 1 if len(cons) == 1 or cons[-2:] in INSEP and len(cons) == 2 else i + 1 + (len(cons) - (2 if cons[-2:] in INSEP else 1))
            cur += m[i + 1:cut]
            out.append(cur)
            cur, i = "", cut
            continue
        i += 1
    if cur:
        if out and not any(ch in VOY for ch in cur.lower()):
            out[-1] += cur
        else:
            out.append(cur)
    if len(out) > 1 and re.fullmatch(rf"[^{VOY}]*es?", out[-1].lower()):  # e muet final : « mon-tage », « in-cro-yable »
        last = out.pop()
        out[-1] += last
    return out if len(out) > 1 else [mot]


def join_numbers(words):
    """« 50 » + « 000 » -> « 50 000 » (espace insécable) : un nombre ne se coupe jamais entre deux mots ou deux lignes."""
    out = []
    for w in words:
        if out and re.fullmatch(r"\d{3}[.,!?…]*", w["w"]) and re.search(r"\d$", out[-1]["w"]):
            out[-1] = {**out[-1], "w": out[-1]["w"] + " " + w["w"], "end": w["end"]}
        else:
            out.append(dict(w))
    return out


def glue_flags(words, skip=()):
    """glue[j] : le mot j reste collé au suivant en fin de ligne (« de la », « 20 % », « 4 à 7 ») ; skip : indices jamais
    collés (mot fort du style editorial, sur sa propre ligne). Une chaîne collée ne dépasse pas 18 caractères."""
    from build_text import HARD, NUMW, UNITS, deac

    def core(w):
        return re.sub(r"[^\w%€'’]", "", w.lower())

    def num(w):
        return bool(re.search(r"\d", w)) or deac(core(w)) in NUMW
    g = [False] * len(words)
    for j in range(len(words) - 1):
        if j in skip or j + 1 in skip or re.search(r"[,;:.!?]$", words[j]["w"]):
            continue
        a, b = words[j]["w"], words[j + 1]["w"]
        ca, cb = core(a), core(b)
        if (ca in HARD or deac(ca) in HARD) and len(ca) <= 4:
            g[j] = True
        elif num(a) and (cb in UNITS or deac(cb) in UNITS or b.startswith(("%", "€"))):
            g[j] = True
        elif num(a) and deac(cb) in ("a", "et", "ou") and j + 2 < len(words) and num(words[j + 2]["w"]):
            g[j] = g[j + 1] = True
    n = 0
    for j in range(len(words)):  # chaîne trop longue : coupée
        n += len(words[j]["w"]) + 1
        if n > 18 and j and g[j - 1]:
            g[j - 1], n = False, len(words[j]["w"]) + 1
        if not g[j]:
            n = 0
    return g


def caption_spans(words, style, use_emoji, st, last_emo, syl=(), fit=None):
    """HTML des mots d'un groupe selon le style (+ emoji collé à son mot). -> (html, instant de l'emoji ou None, last_emo)
    syl : mots (minuscules, sans ponctuation) affichés en escalier de syllabes par le style « geant » (IN- / CRO- / YABLE).
    fit : liste où ajouter le texte de mesure de la taille (blocs insécables séparés par une espace, « ¦ » = mot fort
    editorial, sur sa ligne)."""
    if style == "geant":  # un seul mot géant à la fois ; les mots déjà dits du groupe en petit au-dessus
        small = " ".join(f'<span class="s">{esc(w["w"])}</span>' for w in words)

        def big_of(w):
            core = re.sub(r"[^\w'-]", "", w["w"].lower())
            if core in syl:
                sy = syllabes(re.sub(r"[^\w'-]", "", w["w"]))
                lines = "".join(f'<i>{esc(x.upper())}{"-" if k + 1 < len(sy) else ""}</i>' for k, x in enumerate(sy))
                return f'<span class="b sy" style="--n:{len(sy)}">{lines}</span>'
            return f'<span class="b">{esc(w["w"])}</span>'
        big = "".join(big_of(w) for w in words)
        if fit is not None:
            fit.append(max((w["w"] for w in words), key=len))
        return f'<span class="gs">{small}</span><span class="gb">{big}</span>', None, last_emo
    keyw = key_word(words) if style in ("duo", "seam", "bulle", "souligne") else set()
    if style == "editorial" and words:  # un mot fort par groupe, toujours : chiffre > mot fort > mot plein le plus long
        from build_text import STRONG_WORDS, WEAK

        def _score(j):
            raw = words[j]["w"].lower()
            core = re.sub(r"^(?:[a-z]{1,3}['’])", "", re.sub(r"[^\w'’-]", "", raw))  # « c'est » -> « est », « l'offre » -> « offre »
            weak = core in WEAK or raw.rstrip(".,!?") in WEAK or core in ("est", "sont", "suis", "ai", "as", "va", "vont", "fait") or core.endswith("ment")
            return (bool(re.search(r"\d", raw)), core in STRONG_WORDS, not weak, len(core))
        keyw = {max(range(len(words)), key=_score)}
    parts, emo, units = [], None, []
    edito = style == "editorial"
    for j, w in enumerate(words):
        txt = esc(w["w"])
        if edito and j in keyw and EDITORIAL_INK == "degrade":  # dégradé clair -> accent sur un <em> intérieur
            txt = f"<em>{txt}</em>"
        inner = ('<i class="bx"></i>' if style == "boite" else "") + txt
        parts.append(f'<span class="w{" k" if j in keyw else ""}">{inner}</span>')
        units.append("¦" if edito and j in keyw else w["w"])
        ch = emoji_for(w["w"]) if use_emoji and emo is None and w["start"] - last_emo > 4 else None
        if ch:  # un emoji au plus par groupe, et pas plus d'un toutes les 4 s ; collé à son mot (même ligne)
            parts[-1] = f'<span class="wn">{parts[-1]}<span class="em">{ch}</span></span>'
            units[-1] += NBSP + "MM"
            emo, last_emo = round(max(st, w["start"]), 3), w["start"]
    glue = glue_flags(words, skip=keyw if edito else ())  # « de | la », « 20 | % » : jamais coupés en fin de ligne
    html_, fit_, run, urun = [], [], [], []
    for j, p_ in enumerate(parts):
        run.append(p_)
        urun.append(units[j])
        if not glue[j] or j == len(parts) - 1:
            html_.append(run[0] if len(run) == 1 else '<span class="wn">' + " ".join(run) + "</span>")
            fit_.append(NBSP.join(urun))
            run, urun = [], []
    if fit is not None:
        fit.append(" ".join(fit_))
    return " ".join(html_), emo, last_emo


def emoji_tween(gid, emo):
    return (f'  tl.fromTo("#{gid} .em", {{ opacity: 0, scale: 0.2, rotation: -25 }}, {{ opacity: 1, scale: 1, rotation: 0, '
            f'duration: 0.35, ease: "back.out(3)", immediateRender: false }}, {emo});')


def bubble_ink(accent):
    """Accent lisible sur une bulle blanche : un accent clair (jaune, citron) est assombri."""
    import panel as pn
    return pn._mix(accent, "#111111", 0.45) if pn._lum(accent) > 165 else accent


def _mix(a, b, t):
    import panel as pn
    return pn._mix(a, b, t)


def _readable(color, bg, target=4.5, to=None):
    """Couleur assez contrastée sur bg (WCAG 4,5:1, ou ce que permet le blanc / le noir) : éclaircie sur fond sombre,
    assombrie sur fond clair (to : forcer le sens)."""
    import panel as pn
    to = to or ("#ffffff" if pn._lum(bg) < 128 else "#111111")
    target, c = min(target, 0.85 * pn._contrast(to, bg)), color
    for t in (0.15, 0.3, 0.45, 0.6, 0.75, 0.9):
        if pn._contrast(c, bg) >= target:
            break
        c = pn._mix(color, to, t)
    return c


def band_luma(video, W, H, focus, contain, bands):
    """Luminosité moyenne (0-255) de la bande de chaque sous-titre, sur la vidéo cadrée comme à l'écran (ffmpeg, 3 images/s
    au 1/8) ; bands : [(t0, t1, x0, y0, x1, y1)] en temps du contenu -> [lum | None]."""
    import subprocess
    import numpy as np
    w, h = max(16, W // 8) // 2 * 2, max(16, H // 8) // 2 * 2
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2" if contain else
          f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}:(iw-{w})*{float(focus) / 100:.3f}:(ih-{h})/2")
    try:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"fps=3,{vf},format=gray", "-f", "rawvideo", "-"],
                             capture_output=True, timeout=600).stdout
    except Exception:  # noqa: BLE001 — mesure impossible : sous-titres sur fond sombre par défaut
        return [None] * len(bands)
    n = len(raw) // (w * h)
    if not n:
        return [None] * len(bands)
    fr = np.frombuffer(raw[:n * w * h], np.uint8).reshape(n, h, w)
    res = []
    for t0, t1, x0, y0, x1, y1 in bands:
        a, b = max(0, int(t0 * 3)), min(n, max(int(t0 * 3) + 1, int(t1 * 3) + 1))
        ya, yb = max(0, int(y0 * h / H)), min(h, max(int(y0 * h / H) + 1, int(y1 * h / H)))
        xa, xb = max(0, int(x0 * w / W)), min(w, max(int(x0 * w / W) + 1, int(x1 * w / W)))
        sub = fr[a:b, ya:yb, xa:xb]
        res.append(round(float(sub.mean()), 1) if sub.size else None)
    return res


def cli_args(ap, a, skip=("job", "slug", "size", "lang")):
    """Options effectives de la ligne de commande (sans le job, le slug, --size ni --lang), prêtes à repasser au script :
    deliver.py reconstruit la vidéo validée à l'identique dans chaque format."""
    res = []
    for act in ap._actions:
        if not act.option_strings or act.dest in skip or act.dest == "help":
            continue
        v = getattr(a, act.dest, None)
        if v is None or v == act.default or v is False:
            continue
        flag = max(act.option_strings, key=len)
        res += [flag] if v is True else [flag, str(v)]
    return res


def fit_settings(style, family, W, cap_size, split=False):
    """Réglages de mesure de la taille des sous-titres (police, graisse, majuscules, marges des mots en em, lignes)."""
    upper = style not in ("minimal", "geant", "editorial", "souligne", "bulle") and (not split or style == "mono")
    weight = {"minimal": 700, "souligne": 700, "editorial": 400, "bulle": 800, "mono": 500}.get(style, 800 if split else 900)
    fam = "'IBM Plex Mono', monospace" if style == "mono" else f"'{family}', 'Inter', sans-serif"
    ls = {"geant": -0.035, "editorial": -0.005, "mono": 0, "souligne": -0.005, "minimal": 0}.get(style, -0.01)
    pad = {"impact": 0.54, "mono": 0.7, "geant": 0}.get(style, 0.14)  # marges (et boîtes) des mots
    width = W * (0.86 if style == "geant" else 0.84 * (0.8 if style == "bulle" else 1))
    load = [f"{weight} 50px '{family}'"] + (["italic 700 50px 'Bodoni Moda'"] if style == "editorial" else []) \
        + (["500 50px 'IBM Plex Mono'"] if style == "mono" else [])
    return {"upper": upper, "weight": weight, "family": fam, "ls": ls, "pad": pad, "width": round(width),
            "inset": 1.2 if style == "bulle" else 0, "scale": {"impact": 1.08, "karaoke": 1.08, "geant": 1.0, "editorial": 1.0}.get(style, 1.04),
            "lines": 1 if (split or style == "geant") else (3 if style == "editorial" else 2), "uniform": style != "geant",
            "base": cap_size, "min": round(cap_size * 0.55), "floor": round(cap_size * 0.8), "load": load}


FIT_JS = r"""
  /* taille des sous-titres mesurée (police chargée, graisse, majuscules, marges des mots) : 2 lignes au plus (1 en
     écran partagé), une seule taille pour la vidéo, bornée : un groupe trop long garde sa taille, plus petite */
  function fitCaps() {
    const cv = document.createElement("canvas").getContext("2d");
    const wid = function (t, font) { cv.font = font; return cv.measureText(t).width; };
    const els = Array.prototype.slice.call(document.querySelectorAll(".cap .in[data-fit]"));
    const f100 = FIT.weight + " 100px " + FIT.family;
    const sp = wid(" ", f100);
    const own = els.map(function (el) {
      let t = el.dataset.fit;
      if (FIT.upper) t = t.toUpperCase();
      const segs = t.split("¦").map(function (x) { return x.split(" ").filter(Boolean); }).filter(function (x) { return x.length; });
      const ws = segs.map(function (u) { return u.map(function (x) { return wid(x, f100) + 100 * (FIT.ls * x.length + FIT.pad * x.split(" ").length); }); });
      const key = el.querySelector(".w.k");
      const kw = FIT.lines === 3 && key ? wid(FIT.upper ? key.textContent.toUpperCase() : key.textContent, "italic 700 100px 'Bodoni Moda'") * 1.9 : 0;
      const box = el.parentNode.classList.contains("fond") || el.parentNode.classList.contains("clair") ? 0.7 : 0;
      for (let s = FIT.base; s > FIT.min; s -= 1) {
        const lw = FIT.width - (FIT.inset + box) * s, k = s / 100;
        if (kw * k > lw) continue;
        let lines = 0, ok = true;
        ws.forEach(function (seg) {
          let cur = 0;
          lines += 1;
          seg.forEach(function (w) {
            const ww = w * k * FIT.scale;
            if (ww > lw) ok = false;
            if (cur && cur + sp * k + ww > lw) { lines += 1; cur = ww; } else cur += (cur ? sp * k : 0) + ww;
          });
        });
        if (ok && lines <= FIT.lines) return s;
      }
      return FIT.min;
    });
    const S = FIT.uniform && own.length ? Math.max(FIT.floor, Math.min.apply(null, own)) : FIT.base;
    els.forEach(function (el, i) { el.style.fontSize = Math.min(S, own[i]) + "px"; });
  }
  fitCaps();
  if (document.fonts && document.fonts.load) {
    Promise.all(FIT.load.map(function (f) { return document.fonts.load(f); })).then(fitCaps, fitCaps);
    document.fonts.ready.then(fitCaps);
  }"""


def caption_css(style, accent, shadow=SHADOW):
    """CSS commun aux styles boîte / impact / duo et aux emojis (rush et vidéos sans rush)."""
    css = f"""
  .cap .em {{ display: inline-block; margin-left: 0.12em; opacity: 0; text-shadow: none; -webkit-text-stroke: 0; }}  /* police emoji du système */
  .cap .wn {{ display: inline-block; white-space: nowrap; }}
  .cap .w.k {{ color: {accent}; font-size: 1.12em; }}
  .cap .w {{ position: relative; z-index: 0; }}
  .cap .bx {{ position: absolute; left: -0.1em; right: -0.1em; top: 0.02em; bottom: -0.04em; z-index: -1; border-radius: 0.14em;
             background: {accent}; opacity: 0; transform-origin: 50% 50%; box-shadow: 0 0.08em 0.3em rgba(0,0,0,.35); }}"""
    if style == "impact":
        css += f"""
  .cap .in {{ -webkit-text-stroke: 0.09em #000; paint-order: stroke fill; text-shadow: 0 0.07em 0 #000, {shadow}; }}
  .cap .w {{ margin: 0 0.2em; }}  /* le mot dit grossit de 8 % : de la place pour ne pas toucher ses voisins */"""
    if style == "geant":  # mot géant en casse normale, petits mots déjà dits au-dessus (tutos tech TikTok)
        css += """
  .cap .in { text-transform: none; letter-spacing: -0.035em; line-height: 1; white-space: nowrap; }
  .cap .gs { display: block; font-size: 0.26em; font-weight: 700; letter-spacing: 0; line-height: 1.2; margin-bottom: 0.08em; opacity: .9; }
  .cap .gs .s { opacity: 0; }
  .cap .gb { display: grid; justify-items: center; }
  .cap .gb .b { grid-area: 1 / 1; opacity: 0; }
  .cap .gb .sy { display: flex; flex-direction: column; align-items: center; font-size: .82em; line-height: .86; letter-spacing: -0.02em;
                 margin-top: calc((1 - var(--n)) * .86em); }  /* l'escalier monte : la dernière ligne reste à la place du mot */
  .cap .gb .sy i { font-style: normal; opacity: 0; }"""
    if style == "editorial":  # petits mots en sans fine, le mot fort en serif Didone italique ivoire, empilés (immobilier, luxe)
        css += f"""
  .cap .in {{ text-transform: none; font-weight: 400; letter-spacing: -0.005em; line-height: 1.02; text-shadow: 0 2px 18px rgba(0,0,0,.45); }}
  .cap .w {{ opacity: 0; }}
  .cap .w.k {{ display: block; font-family: 'Bodoni Moda', Georgia, serif; font-style: italic; font-weight: 700; font-size: 1.9em; line-height: .92;
              letter-spacing: -0.01em; color: {EDITORIAL_INK if EDITORIAL_INK != "degrade" else "#fff"}; margin: .02em 0 .04em; }}
  .cap .w.k em {{ font-style: inherit; display: inline-block; padding: .08em .06em .14em; margin: -.08em -.06em -.14em;
                 background: linear-gradient(180deg, {_mix(accent, "#ffffff", 0.55)} 0%, {accent} 100%); -webkit-background-clip: text; background-clip: text;
                 color: transparent; }}  /* text.editorialColor: "degrade" */
  .cap.clair .in {{ color: #1c1a17; text-shadow: 0 1px 16px rgba(255,255,255,.4); }}  /* fond clair : encre sombre */
  .cap.clair .w.k {{ color: {_readable(accent, "#e6e6e6")}; }}
  .cap.clair .w.k em {{ background-image: linear-gradient(180deg, {_mix(accent, "#000000", 0.2)} 0%, {_mix(accent, "#000000", 0.55)} 100%); }}"""
    if style == "mono":  # majuscules machine à écrire, chaque mot dans sa boîte noire, le mot dit en couleur d'accent
        css += """
  .cap .in { font-family: 'IBM Plex Mono', monospace; font-weight: 500; text-transform: uppercase; letter-spacing: 0; text-shadow: none; }
  .cap .w { background: #111; color: #fff; padding: 0.02em 0.26em; margin: 0 0.02em; box-decoration-break: clone; -webkit-box-decoration-break: clone; }"""
    if style == "souligne":  # éditorial : petits, casse normale, mots à venir en gris, le mot dit en blanc, le mot fort souligné
        css += f"""
  .cap .in {{ text-transform: none; font-weight: 700; letter-spacing: -0.005em; }}
  .cap .w {{ color: rgba(255,255,255,.42); }}
  .cap .w.k {{ color: rgba(255,255,255,.42); font-size: 1em; }}
  .cap .w.k::after {{ content: ""; position: absolute; left: 0; right: 0; bottom: -0.04em; height: 0.08em; border-radius: 0.04em; background: {accent};
                     transform: scaleX(var(--u, 0)); transform-origin: 0 50%; }}"""
    if style == "bulle":  # bulle blanche arrondie (message), le mot-clé en couleur d'accent, pas de majuscules
        kc = bubble_ink(accent)
        css += f"""
  .cap {{ text-align: center; }}
  .cap .in {{ display: inline-block; position: relative; max-width: 80%; margin: 0 auto; padding: 0.3em 0.6em 0.36em; border-radius: 0.55em;
             background: #fff; color: #111; text-transform: none; letter-spacing: -0.01em; font-weight: 800; line-height: 1.12;
             text-shadow: none; -webkit-text-stroke: 0; box-shadow: 0 0.12em 0.5em rgba(0,0,0,.35); transform-origin: 18% 100%; white-space: normal; }}
  .cap .in::after {{ content: ""; position: absolute; left: 14%; bottom: -0.3em; width: 0.7em; height: 0.7em; background: #fff;
                    border-radius: 0 0 0.5em 0; transform: skewX(-28deg); z-index: -1; }}
  .cap .w {{ opacity: 1; }}
  .cap .w.k {{ color: {kc}; font-size: 1em; background: none; padding: 0; }}"""
    return css


def caption_js(style):
    """Animation d'un groupe de sous-titres selon le style."""
    if style == "boite":  # le mot dit passe dans une boîte de la couleur d'accent (style CapCut)
        return """
  function cap(id, st, en, ws) {
    const g = "#" + id, spans = document.querySelectorAll(g + " .w");
    tl.fromTo(g + " .in", { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.14, ease: "power2.out", immediateRender: false }, st);
    ws.forEach(function (t, i) {
      const bx = spans[i].querySelector(".bx"), on = Math.max(st, t[0] - 0.03);
      const off = Math.max(on + 0.1, i + 1 < ws.length ? ws[i + 1][0] - 0.03 : en - 0.1);
      tl.fromTo(bx, { opacity: 0, scaleX: 0.6 }, { opacity: 1, scaleX: 1, duration: 0.1, ease: "power2.out", immediateRender: false }, on);
      tl.to(spans[i], { color: BOXINK, duration: 0.06 }, on);
      if (i + 1 < ws.length) {
        tl.to(bx, { opacity: 0, duration: 0.06 }, off);
        tl.to(spans[i], { color: INK, duration: 0.06 }, off);
      }
    });
    tl.to(g + " .in", { opacity: 0, duration: 0.1, ease: "power2.in" }, en - 0.1);
    tl.set(g + " .in", { opacity: 0 }, en);
  }"""
    if style == "impact":  # gros, contour noir, le mot dit grossit en couleur d'accent (style Hormozi)
        return """
  function cap(id, st, en, ws) {
    const g = "#" + id, spans = document.querySelectorAll(g + " .w");
    tl.fromTo(g + " .in", { opacity: 0, scale: 0.7 }, { opacity: 1, scale: 1, duration: 0.18, ease: "back.out(2.2)", immediateRender: false }, st);
    ws.forEach(function (t, i) {
      const on = Math.max(st, t[0] - 0.02);
      tl.to(spans[i], { color: ACCENT, scale: 1.08, duration: 0.07, ease: "power2.out" }, on);
      if (i + 1 < ws.length) tl.to(spans[i], { color: INK, scale: 1, duration: 0.07, ease: "power2.in" }, Math.max(on + 0.08, ws[i + 1][0] - 0.02));
    });
    tl.to(g + " .in", { opacity: 0, scale: 0.94, duration: 0.1, ease: "power2.in" }, en - 0.1);
    tl.set(g + " .in", { opacity: 0 }, en);
  }"""
    if style == "geant":  # chaque mot dit remplace le précédent, en grand ; les mots déjà dits restent en petit au-dessus
        return """
  function cap(id, st, en, ws) {
    const g = "#" + id, bs = document.querySelectorAll(g + " .gb .b"), ss = document.querySelectorAll(g + " .gs .s");
    tl.set(g + " .in", { opacity: 1 }, st);
    ws.forEach(function (t, i) {
      const on = i ? Math.max(st, t[0] - 0.02) : st;
      tl.fromTo(bs[i], { opacity: 0, scale: 1.12, filter: "blur(6px)" }, { opacity: 1, scale: 1, filter: "blur(0px)", duration: 0.12, ease: "power3.out", immediateRender: false }, on);
      if (i) { tl.set(bs[i - 1], { opacity: 0 }, on); tl.to(ss[i - 1], { opacity: 1, duration: 0.1 }, on); }
      const ls = bs[i].querySelectorAll("i");  // mot en escalier : une syllabe après l'autre, sur la durée du mot
      if (ls.length) {  // seul à l'écran : les petits mots s'effacent le temps de l'escalier
        tl.to(g + " .gs", { opacity: 0, duration: 0.06 }, on);
        if (i + 1 < ws.length) tl.to(g + " .gs", { opacity: 0.9, duration: 0.1 }, Math.max(on + 0.1, ws[i + 1][0] - 0.02));
        const step = Math.max(0.08, (Math.max(t[1], on + 0.3) - on) / ls.length);
        ls.forEach(function (l, k) {
          tl.fromTo(l, { opacity: 0, y: 30, scale: 1.2 }, { opacity: 1, y: 0, scale: 1, duration: 0.1, ease: "back.out(2)", immediateRender: false }, on + k * step);
        });
      }
    });
    tl.to(g + " .in", { opacity: 0, duration: 0.08, ease: "power2.in" }, en - 0.08);
    tl.set(g + " .in", { opacity: 0 }, en);
  }"""
    if style == "editorial":  # chaque mot arrive quand il est dit (montée + flou) ; le mot fort grossit depuis le flou
        return """
  function cap(id, st, en, ws) {
    const g = "#" + id, spans = document.querySelectorAll(g + " .w");
    tl.set(g + " .in", { opacity: 1, filter: "blur(0px)" }, st);
    ws.forEach(function (t, i) {
      const on = i ? Math.max(st, t[0] - 0.03) : st, k = spans[i].classList.contains("k");
      tl.fromTo(spans[i], k ? { opacity: 0, scale: 1.25, filter: "blur(10px)" } : { opacity: 0, y: 14, filter: "blur(6px)" },
        { opacity: 1, scale: 1, y: 0, filter: "blur(0px)", duration: k ? 0.35 : 0.2, ease: k ? "power3.out" : "power2.out", immediateRender: false }, on);
    });
    tl.to(g + " .in", { opacity: 0, filter: "blur(8px)", duration: 0.15, ease: "power2.in" }, en - 0.15);
    tl.set(g + " .in", { opacity: 0 }, en);
  }"""
    if style == "karaoke":
        return """
  function cap(id, st, en, ws) {
    const g = "#" + id, spans = document.querySelectorAll(g + " .w");
    tl.fromTo(g + " .in", { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.14, ease: "power2.out", immediateRender: false }, st);
    ws.forEach(function (t, i) {
      tl.to(spans[i], { color: ACCENT, scale: 1.08, duration: 0.08, ease: "power2.out" }, t[0]);
      tl.to(spans[i], { color: INK, scale: 1, duration: 0.12, ease: "power2.in" }, Math.max(t[0] + 0.08, t[1]));
    });
    tl.to(g + " .in", { opacity: 0, duration: 0.1, ease: "power2.in" }, en - 0.1);
    tl.set(g + " .in", { opacity: 0 }, en);
  }"""
    if style == "mono":
        return """
  function cap(id, st, en, ws) {
    const g = "#" + id, spans = document.querySelectorAll(g + " .w");
    tl.set(g + " .in", { opacity: 1 }, st);
    ws.forEach(function (t, i) {
      const on = Math.max(st, t[0] - 0.03);
      tl.fromTo(spans[i], { opacity: 0 }, { opacity: 1, duration: 0.04, immediateRender: false }, on);
      tl.fromTo(spans[i], { backgroundColor: "#111111", color: "#ffffff" }, { backgroundColor: ACCENT, color: BOXINK, duration: 0.05, immediateRender: false }, on);
      if (i + 1 < ws.length) tl.to(spans[i], { backgroundColor: "#111111", color: "#ffffff", duration: 0.05 }, Math.max(on + 0.06, ws[i + 1][0] - 0.03));
    });
    tl.to(g + " .in", { opacity: 0, duration: 0.08 }, en - 0.08);
    tl.set(g + " .in", { opacity: 0 }, en);
  }"""
    if style == "souligne":
        return """
  function cap(id, st, en, ws) {
    const g = "#" + id, spans = document.querySelectorAll(g + " .w");
    tl.fromTo(g + " .in", { opacity: 0, y: 8 }, { opacity: 1, y: 0, duration: 0.14, ease: "power2.out", immediateRender: false }, st);
    ws.forEach(function (t, i) {
      const on = Math.max(st, t[0] - 0.03), k = spans[i].classList.contains("k");
      tl.to(spans[i], { color: k ? ACCENT : "#ffffff", duration: 0.08 }, on);
      if (k) tl.fromTo(spans[i], { "--u": 0 }, { "--u": 1, duration: 0.25, ease: "power2.out", immediateRender: false }, on);
    });
    tl.to(g + " .in", { opacity: 0, duration: 0.1, ease: "power2.in" }, en - 0.1);
    tl.set(g + " .in", { opacity: 0 }, en);
  }"""
    if style == "bulle":  # la bulle arrive comme un message reçu, d'un coup, et repart
        return """
  function cap(id, st, en, ws) {
    const g = "#" + id;
    tl.fromTo(g + " .in", { opacity: 0, scale: 0.55, y: 18 }, { opacity: 1, scale: 1, y: 0, duration: 0.24, ease: "back.out(2.2)", immediateRender: false }, st);
    tl.to(g + " .in", { opacity: 0, scale: 0.92, duration: 0.1, ease: "power2.in" }, en - 0.1);
    tl.set(g + " .in", { opacity: 0 }, en);
  }"""
    if style == "minimal":
        return """
  function cap(id, st, en, ws) {
    const g = "#" + id;
    tl.fromTo(g + " .in", { opacity: 0 }, { opacity: 1, duration: 0.15, ease: "power1.out", immediateRender: false }, st);
    tl.to(g + " .in", { opacity: 0, duration: 0.12, ease: "power1.in" }, en - 0.12);
    tl.set(g + " .in", { opacity: 0 }, en);
  }"""
    return """
  function cap(id, st, en, ws) {
    const g = "#" + id, spans = document.querySelectorAll(g + " .w");
    ws.forEach(function (t, i) {
      tl.fromTo(spans[i], { opacity: 0, scale: 0.6, y: 18 },
        { opacity: 1, scale: 1, y: 0, duration: 0.22, ease: "back.out(2.6)", immediateRender: false }, Math.max(st, t[0] - 0.06));
    });
    tl.to(g + " .in", { opacity: 0, scale: 0.94, duration: 0.1, ease: "power2.in" }, en - 0.1);
    tl.set(g + " .in", { opacity: 0 }, en);
  }"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--no-cam", action="store_true")
    ap.add_argument("--no-sfx", action="store_true")
    ap.add_argument("--derriere", help="titre géant DERRIÈRE la personne détourée (cutout.py), 2,6 s ; ou config behind.text")
    ap.add_argument("--derriere-mot", help="mot dit où le titre derrière apparaît (sinon au début)")
    ap.add_argument("--mots", action="store_true", help="mots dynamiques : mot géant derrière la personne + satellites + carte de verre (mots.py)")
    ap.add_argument("--zooms", action="store_true", help="zooms sur les mots appuyés (zooms.py ; ou camera.zooms dans la config)")
    ap.add_argument("--size", help="9:16 | 1:1 | 4:5 | 16:9 | LxH (défaut : config)")
    ap.add_argument("--layout", choices=["full", "split", "cards"],
                    help="split : animation en haut, visage en bas ; cards : visage plein écran, cartes en haut (visual.layout)")
    ap.add_argument("--accroche", help="accroche animée de 3 s en ouverture : papier, plan, pate, neon, aquarelle, pixel, isometrique, mosaique, encre, relief")
    ap.add_argument("--accroche-texte", help="titre de l'accroche (sinon config hook.text ou l'accroche du short)")
    ap.add_argument("--panel-theme", choices=["dark", "light", "glass"],
                    help="écran partagé : panneau sombre ou clair ; cartes : glass = cartes en verre dépoli (visual.panelTheme)")
    ap.add_argument("--mode", choices=["captions", "overlays", "both", "none"])
    ap.add_argument("--no-captions", action="store_true", help="= --mode none (couverture)")
    ap.add_argument("--style", choices=STYLES)
    ap.add_argument("--emoji", action="store_true", help="emoji après les mots-clés (bravo 👏, idée 💡…)")
    ap.add_argument("--no-branding", action="store_true", help="sans intro / outro / bandeau nom")
    ap.add_argument("--lang", help="sous-titres traduits (translate.py) : nl, en…")
    ap.add_argument("--plateforme", choices=["tous", "reels", "tiktok", "shorts"],
                    help="zones sûres pour les sous-titres (text.platform ; défaut : tous)")
    ap.add_argument("--no-visage", action="store_true", help="sous-titres à hauteur fixe (captionTopPct), sans éviter le visage")
    a = ap.parse_args()
    job = job_dir(a.job)
    c = config(job)
    vis, txt, sfxc = c["visual"], c["text"], c["sfx"]
    W, H = size_of(a.size, vis)
    mode = "none" if a.no_captions else ("captions" if a.lang else (a.mode or txt["mode"]))
    mots_on = bool(a.mots or (job / "work" / f"{a.slug}_mots.json").exists() or c.get("mots"))
    if mots_on and not a.mode and not a.lang:
        mode = "none"  # le mot géant et la carte de verre remplacent les sous-titres (--mode captions pour garder les deux)
    sfx_lang = f"_{a.lang}" if a.lang else ""
    style = a.style or txt["captionStyle"]
    family, ink, accent = vis["fontFamily"], vis["textColor"], vis["accentColor"]

    mj, tj = job / "work" / f"{a.slug}_map.json", job / "work" / f"{a.slug}_text{sfx_lang}.json"
    for p in (mj, tj):
        if not p.exists():
            fail(f"{p} absent")
    m, t = read_json(mj), read_json(tj)
    dur = float(m["out_duration"])
    cut = Path(m["cut"]).name
    src = probe(m["cut"])
    ratio = (src["width"] / src["height"]) / (W / H) if src.get("width") else 1.0
    fit = vis.get("fit", "auto")  # auto | cover (recadre serré, face caméra simple) | fill (image entière + fond flouté) | track
    rf = job / "work" / f"{a.slug}_reframe.json"  # reframe.py : la fenêtre suit le visage (source plus large que le format)
    track = read_json(rf) if fit in ("auto", "track") and rf.exists() else None
    if track and track.get("size") != [W, H]:  # autre format (livraison 1:1, 16:9) : trajet recalculé pour cette fenêtre
        from reframe import camera_path
        sw, sh = track["src_size"]
        cw = (sh * W / H) / sw
        if cw >= 0.98:
            track = None  # le format montre déjà toute la largeur
        else:
            track["start"], track["moves"] = camera_path([tuple(x) for x in track["samples"]], cw, track.get("zone", 0.18))
    fill = not track and (fit == "fill" or (fit == "auto" and (ratio < 0.75 or ratio > 1.33)))
    layout = a.layout or vis.get("layout", "full")
    split = layout == "split" and H > W  # écran partagé : vertical seulement
    cards = layout == "cards" and H > W  # visage plein écran, temps forts en cartes blanches en haut
    ptheme = a.panel_theme or vis.get("panelTheme", "dark")
    PH = round(H * (0.44 if cards else 0.5))
    if split:
        track, fill = None, False
        style = "seam" if style in ("pop", "duo", "seam") else style
        mode = "captions" if mode != "none" else mode
    cap_top = (txt["captionTopPct"] if not fill else 70) if H > W else 82  # fond flouté : sous l'image

    from fonts import brand_faces, title_stack, title_weight
    font_face = brand_faces(job, vis)  # fonts + fontFile + titleFont de la charte
    mcfg0 = c.get("mots") if isinstance(c.get("mots"), dict) else {}
    if style == "editorial" or mcfg0.get("police") == "serif":  # serif Didone (Bodoni Moda, OFL) des styles éditoriaux
        from common import serif_fonts
        font_face += " " + serif_fonts(job)
    global EDITORIAL_INK
    EDITORIAL_INK = txt.get("editorialColor", EDITORIAL_INK)

    r = W / 1920.0
    k = float(vis.get("sizeScale") or (1.5 if H > W else 1.0))
    SZ = {"side": round(88 * r * k), "center": round(97 * r * k), "topline": round(110 * r * k)}
    hook_size = round(84 * 0.82 * (W / 1080 if H > W else H / 1080))  # accroche : même taille quel que soit le style
    cap_bottom = round(H * 0.08) if H <= W else None  # 1:1 / 16:9 : sous-titres ancrés par le bas (2 lignes restent dans l'image)
    cap_size = round({"minimal": 58, "impact": 96, "seam": 62, "mono": 52, "souligne": 56, "geant": 150, "editorial": 64}.get(style, 84) * (W / 1080 if H > W else H / 1080))
    use_emoji = a.emoji or txt.get("captionEmoji", False)
    syl_words = {str(x).lower() for x in txt.get("syllabes", [])}  # style « geant » : mots en escalier de syllabes

    cap_words = [w for g in t.get("captions", []) for w in g["words"]]
    if not cap_words:
        from build_text import remap
        cap_words = remap(read_json(job / "work" / f"{a.slug}_words.json")["words"], m["segments"])
    # catalogue « N trucs que X sait faire » (effets.py) : pas de sous-titres ni d'accroche pendant qu'il est à l'écran
    cat_f, fx_f = job / "work" / f"{a.slug}_catalogue.json", job / "work" / f"{a.slug}_effets.json"
    fx_ok = layout == "full" and not (track or fill)
    cat_win = None
    if cat_f.exists() and fx_ok:
        import effets as fx
        cat_win = fx.catalogue_window(read_json(cat_f), cap_words, dur)

    nodes, tw = [], []
    cap_blocks, calques = [], []  # groupes de sous-titres à placer ; calques posés (work/<slug>_calques.json)
    overlays = sorted((o for o in t["overlays"] if o.get("keep") and o["start"] < dur), key=lambda o: o["start"])
    punches = sorted(float(o["start"]) for o in t["overlays"] if o.get("punch") and o["start"] < dur)

    if mode in ("captions", "both"):
        caps = t["captions"]
        last_emo = -99.0
        for i, g in enumerate(caps):
            st = round(max(0.1, g["words"][0]["start"] - 0.05), 3)
            nxt = caps[i + 1]["words"][0]["start"] - 0.05 if i + 1 < len(caps) else dur
            en = round(min(dur, max(g["end"] + 0.25, st + 0.4), nxt if split else max(nxt, g["end"])), 3)  # écran partagé : une ligne, jamais deux groupes à la fois
            if en - st <= 0.1 or (cat_win and st < cat_win[1] and en > cat_win[0]):
                continue
            gid = f"cap-{g['id']}"
            words = join_numbers(g["words"])
            text = " ".join(w["w"] for w in words)
            fl = []
            spans, emo, last_emo = caption_spans(words, style, use_emoji, st, last_emo, syl_words, fit=fl)
            fit_text = text + (" MM" if emo is not None else "")  # place de l'emoji dans le calcul de taille (estimation)
            fs_ = ""
            if style == "geant":  # un mot à la fois : c'est le plus long qui doit tenir (réduit s'il dépasse)
                fit_text = max((w["w"] for w in words), key=len)
                k_ = W * 0.86 / max(1.0, len(fit_text) * 0.56 * cap_size)
                fs_ = f' style="font-size:{round(cap_size * k_)}px"' if k_ < 1 else ""
            nodes.append(f'      <div class="clip cap" id="{gid}" data-start="{st}" data-duration="{round(en - st, 3)}" '
                         f'data-track-index="4"><div class="in" data-fit="{esc(fl[0])}"{fs_}>{spans}</div></div>')
            bx = text_box(fit_text, cap_size, W * 0.08, W * 0.84, 0, 1.08, max_lines=2, pad=0.3 if style == "bulle" else 0)
            if style == "editorial":  # mot fort sur sa propre ligne, 1,9 fois plus grand : bloc plus haut
                bx = (bx[0], bx[1], bx[2], bx[1] + round((bx[3] - bx[1]) * 1.9))
            cap_blocks.append({"id": gid, "t0": st, "t1": en, "h": bx[3], "x0": bx[0], "x1": bx[2]})
            times = [[round(max(st, w["start"]), 3), round(w["end"], 3)] for w in words]
            tw.append(f'  cap("{gid}", {st}, {en}, {json.dumps(times)});')
            if emo is not None:
                tw.append(emoji_tween(gid, emo))

    hook = job / "work" / f"{a.slug}_hook{sfx_lang}.json"
    if a.lang and not hook.exists():
        hook = job / "work" / f"{a.slug}_hook.json"
    if cat_win:  # le titre du catalogue tient lieu d'accroche
        hook = job / "work" / f"{a.slug}_hook_absent.json"
    hook_end = 0.15 + min(3.2, dur - 0.3) + 0.2 if hook.exists() else 0
    if mode in ("overlays", "both"):
        rot = ["nL", "nR"]
        overlays = [o for o in overlays if o["start"] >= hook_end]  # pas de texte sous l'accroche
        for i, o in enumerate(overlays):
            place = ("topline" if i % 2 == 0 else "nC") if o.get("punch") else rot[i % 2]
            if mode == "both":
                place = "topline"
            st = round(max(0.0, o["start"] - 0.12), 3)
            en = min(float(o["end"]) + 0.45, dur)
            if en - st <= 0.1:
                continue
            oid = f"ov-{o['id']}"
            spans = " ".join(f'<span class="w">{esc(w["w"])}</span>' for w in o["words"])
            nodes.append(f'      <div class="clip note {place}" id="{oid}" data-start="{st}" '
                         f'data-duration="{round(en - st, 3)}" data-track-index="5">{spans}</div>')
            otext = " ".join(w["w"] for w in o["words"])
            obox = {"nL": (otext, SZ["side"], 90 * r, W * 0.58, H * 0.40, False),
                    "nR": (otext, SZ["side"], W - 90 * r - W * 0.58, W * 0.58, H * 0.46, False),
                    "nC": (otext, SZ["center"], 70 * r, W - 140 * r, H * 0.52, True),
                    "topline": (otext.upper(), SZ["topline"], 70 * r, W - 140 * r, H * 0.16, True)}[place]
            bx = text_box(*obox[:5], 1.1, center=obox[5])
            if place == "nR":  # calé à droite
                bx = [round(W - 90 * r - (bx[2] - bx[0])), bx[1], round(W - 90 * r), bx[3]]
            calques.append({"type": "texte", "nom": oid, "t0": st, "t1": round(en, 3), "box": bx})
            times, prev = [], None
            for w in o["words"]:
                tt = max(st, float(w["start"]))
                if prev is not None and tt < prev + 0.02:
                    tt = prev + 0.02
                times.append(round(tt, 3))
                prev = tt
            tw.append(f'  wIn("#{oid}", {json.dumps(times)});')
            tw.append(f'  noteOut("#{oid}", {round(min(en - 0.3, dur), 3)});')
            tw.append(f'  tl.set("#{oid}", {{ opacity: 0 }}, {round(en, 3)});')

    low_res = float(m.get("upscale", 1)) > 1.001  # petite source agrandie (build_cut) : pas de punch ni de zoom, ils la rendraient floue
    cam = [] if (a.no_cam or not c["camera"]["enabled"] or low_res) else build_cam(dur, punches)  # petite source : pas de dérive non plus
    zooms = []
    if (a.zooms or c["camera"].get("zooms")) and not a.no_cam and not low_res:  # resserrements sur les mots appuyés, mesurés (zooms.py)
        zooms = [z for z in strong_words(job, a.slug, float(c["camera"].get("zoomsPerMinute", 8)))
                 if not any(abs(z["t"] - p) < 1.5 for p in punches)]  # pas sur un punch-in déjà posé

    sfx_nodes, n_whoosh, n_tick = [], 0, 0
    if not a.no_sfx and sfxc["enabled"]:
        wsrc, wpeak, wdur = sfx_asset(job, sfxc["whoosh"])
        if wsrc and cam:
            for i, p in enumerate(punches):
                st = round(max(0.0, p - wpeak), 3)
                sfx_nodes.append(f'      <audio id="sfx-w{i}" class="clip" src="{wsrc}" data-start="{st}" '
                                 f'data-duration="{min(wdur, dur - st)}" data-track-index="11" data-volume="{sfxc["whooshVolume"]}"></audio>')
                n_whoosh += 1
        tsrc, tpeak, tdur = sfx_asset(job, sfxc["tick"])
        if tsrc:
            for i, sg in enumerate(m["segments"][1:]):
                st = round(float(sg["out_start"]) - tpeak, 3)
                if 0.05 < st < dur - 0.2:
                    sfx_nodes.append(f'      <audio id="sfx-t{i}" class="clip" src="{tsrc}" data-start="{st}" '
                                     f'data-duration="{min(tdur, dur - st)}" data-track-index="12" data-volume="{sfxc["tickVolume"]}"></audio>')
                    n_tick += 1

    rgb = [int(accent.lstrip("#")[k:k + 2], 16) for k in (0, 2, 4)] if len(accent.lstrip("#")) == 6 else [0, 0, 0]
    hook_ink = "#111111" if (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) > 160 else "#ffffff"
    if hook.exists() and not (split or cards):  # accroche en titre les 3 premières secondes (shorts) ; en écran partagé : dans le panneau
        hd = round(min(3.2, dur - 0.3), 3)
        nodes.append(f'      <div class="clip hook" id="hook" data-start="0.15" data-duration="{hd}" data-track-index="7">'
                     f'<div class="hk">{esc(read_json(hook)["text"])}</div></div>')
        tw.append(f'  tl.fromTo("#hook .hk", {{ opacity: 0, y: -30, scale: 0.92 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.45, '
                  f'ease: "back.out(2)", immediateRender: false }}, 0.15);')
        tw.append(f'  tl.to("#hook .hk", {{ opacity: 0, y: -20, duration: 0.3, ease: "power2.in" }}, {round(0.15 + hd - 0.35, 3)});')
        calques.append({"type": "accroche", "nom": "hook", "t0": 0.15, "t1": round(0.15 + hd, 3),
                        "box": text_box(read_json(hook)["text"], hook_size, W * 0.08, W * 0.84, H * (0.11 if H > W else 0.08), 1.12, pad=0.3)})

    music = job / "work" / f"{a.slug}_music.json"
    if music.exists():
        mu = read_json(music)
        sfx_nodes.insert(0, f'      <audio id="music" class="clip" src="{mu["file"]}" data-start="0" '
                            f'data-duration="{dur}" data-track-index="9" data-volume="1"></audio>')

    # habillage de marque (config "branding") : intro avant, outro après, bandeau nom à la première prise de parole
    br = {} if a.no_branding else c.get("branding", {})
    brand = brand_info(job)
    logo_rel = ""
    if vis.get("logo") and (br.get("intro") or br.get("outro")):
        lp = ROOT / vis["logo"]
        (job / "assets" / "img").mkdir(parents=True, exist_ok=True)
        shutil.copy2(lp, job / "assets" / "img" / lp.name)
        logo_rel = f"assets/img/{lp.name}"
    common_vals = {"logo": logo_rel, "bg": vis.get("bgColor", "#f6f4f0"), "ink": vis.get("inkColor", "#1a1a1a"),
                   "accent": accent, "font": family, "blend": vis.get("logoBlend", "normal")}
    T0, blocks = 0.0, []
    if br.get("intro"):
        block_file(job, br["intro"])
        idur = float(br.get("introDuration", 1.6))
        T0 = round(idur - 0.45, 3)  # la vidéo démarre sous le volet de sortie de l'intro (pas d'écran noir)
        blocks.append(mount(br["intro"], "brand-intro", 0, idur, W, H, 20, common_vals, z=200))
    hk = dict(c.get("hook") or {})
    if a.accroche:
        hk["style"] = a.accroche
    if a.accroche_texte:
        hk["text"] = a.accroche_texte
    if hk.get("style"):  # accroche animée par style (library/block/accroche-<style>) : remplace l'intro de marque
        hname = f"accroche-{hk['style']}"
        block_file(job, hname)
        hdur = float(hk.get("dur", 3.0))
        text = hk.get("text") or (read_json(hook)["text"] if hook.exists() else "")
        hv = {"text": text, "sub": hk.get("sub", ""), "accent": hk.get("accent") or accent,
              "font": (vis.get("titleFont") or {}).get("family") or family}  # titre de la paire choisie (polices.py)
        hv.update({k: hk[k] for k in ("bg", "ink") if hk.get(k)})
        if hk.get("art") and (job / hk["art"]).exists():  # dessin du sujet (SVG) : references/accroches-dessin.md
            hv["art"] = (job / hk["art"]).read_text(encoding="utf-8")
        blocks = [mount(hname, "hook-anim", 0, hdur, W, H, 20, hv, z=200)]
        T0 = round(hdur - 0.45, 3)  # la vidéo démarre sous le volet de sortie

    def shift(node):
        return re.sub(r'data-start="([\d.]+)"', lambda mm: f'data-start="{round(float(mm.group(1)) + T0, 3)}"', node)

    nodes = [shift(n) for n in nodes]
    sfx_nodes = [shift(n) for n in sfx_nodes]
    lt = dict(br.get("lowerThird") or {})
    role_tr = job / "work" / f"{a.slug}_role{sfx_lang}.json"
    if a.lang and role_tr.exists():
        lt["role"] = read_json(role_tr)["role"]
    if lt.get("name"):
        block_file(job, "bandeau-nom")
        first = t["captions"][0]["words"][0]["start"] if t.get("captions") else 0.3
        lt_start = max(first + 0.3, hook_end)
        blocks.append(mount("bandeau-nom", "brand-lt", T0 + lt_start, min(4.0, dur - lt_start), W, H, 21,
                            {"name": lt["name"], "role": lt.get("role", ""), "accent": accent, "font": family,
                             "top": lt.get("top", (80 if fill else 50) if H > W else 64)}, z=150))  # fond flouté : sous l'image
    outro_d = 0.0
    if br.get("outro"):
        block_file(job, br["outro"])
        outro_d = float(br.get("outroDuration", 3.4))
        blocks.append(mount(br["outro"], "brand-outro", T0 + dur, outro_d, W, H, 22,
                            {**common_vals, "tagline": brand.get("tagline", ""),
                             "info": (brand.get("contact") or {}).get("site", "")}, z=200))
    total = round(T0 + dur + outro_d, 3)
    mj_ = job / "work" / f"{a.slug}_motions.json"
    motion_rep = []
    # titre géant derrière la personne : vidéo détourée (cutout.py) posée par-dessus le titre, dans la même caméra
    behind_html, behind_rep, btop = "", None, 0
    bh = dict(c.get("behind") or {})
    if a.derriere:
        bh["text"] = a.derriere
    if a.derriere_mot:
        bh["word"] = a.derriere_mot
    if bh.get("text") and not (track or fill or split or cards):
        hit = word_hit(cap_words, bh["word"], bh.get("occurrence", 1)) if bh.get("word") else None
        b0 = max(0.0, (hit["start"] - 0.1) if hit else max(0.0, hook_end))
        bd = round(min(float(bh.get("dur", 2.6)), dur - b0 - 0.1), 3)
        if bd >= 1.0:
            from cutout import head_top, person_matte
            rel = person_matte(job, job / "assets" / cut, b0, bd, model=bh.get("model", "u2net_human_seg"))
            words_ = esc(str(bh["text"])).split()
            half = (len(words_) + 1) // 2
            lines = [" ".join(words_[:half]), " ".join(words_[half:])] if len(words_) > 1 else words_
            longest = max(len(x) for x in lines)
            bfs = round(min(H * 0.15, W * 1.2 / max(4, longest)))  # le plus gros possible sur la largeur
            st_ = round(T0 + b0, 3)
            # hauteur du titre : centré sur le haut de la tête (mesuré sur le détourage) : la tête passe devant
            head = head_top(job, rel)
            btop = max(round(H * 0.04), round(head * H - 0.95 * bfs))
            behind_html = (f'        <div class="clip bh" id="bh" data-start="{st_}" data-duration="{bd}" data-track-index="3" '
                           f'style="font-size:{bfs}px">' + "".join(f'<span class="bl">{x}</span>' for x in lines if x) + '</div>' + chr(10) +
                           f'        <video id="a-cut" class="clip" src="{rel}" data-start="{st_}" data-duration="{bd}" data-track-index="4" muted playsinline></video>')
            tw.append(f'  tl.fromTo("#bh .bl", {{ opacity: 0, scale: 1.25, y: 40 }}, {{ opacity: 1, scale: 1, y: 0, duration: 0.45, stagger: 0.12, '
                      f'ease: "power3.out", immediateRender: false }}, {round(b0, 3)});')
            tw.append(f'  tl.to("#bh .bl", {{ opacity: 0, y: -30, duration: 0.25, stagger: 0.05, ease: "power2.in" }}, {round(b0 + bd - 0.3, 3)});')
            behind_rep = {"texte": bh["text"], "a": round(b0, 2), "duree": bd, "detourage": rel}
    mots_css, mots_rep, macc = "", None, None
    if mots_on and not (track or fill or split or cards):  # mots dynamiques derrière la personne (mots.py)
        import mots as mo
        import panel as pn_m
        mf = job / "work" / f"{a.slug}_mots.json"
        if not mf.exists():
            write_json(mf, mo.suggest(cap_words))
        mcfg = c.get("mots") if isinstance(c.get("mots"), dict) else {}
        default_acc = read_json(Path(__file__).resolve().parent.parent / "config.default.json")["visual"]["accentColor"]
        # couleur des mots : imposée (mots.couleur) > accent de la charte > tirée de l'image
        macc = mcfg.get("couleur") or (accent if accent.lower() != default_acc.lower() else mo.scene_color(job / "assets" / cut))
        mh_, mo_over, mjs, mots_css, mots_rep = mo.nodes(job, read_json(mf), cap_words, dur, W, H, T0, job / "assets" / cut, macc, family,
                                                         segments=m["segments"], icon=pn_m.icon, mix=pn_m._mix,
                                                         serif=mcfg.get("police") == "serif")
        behind_html += "\n" + mh_
        mots_css += f"\n  .acut {{ object-position: {vis['focusX']}% 50%; }}"  # même recadrage que la vidéo
        nodes += mo_over
        tw += mjs
        for r_ in mots_rep:  # mot géant posé devant (plan serré) : il peut couvrir le visage ; derrière, la personne passe devant
            if r_.get("place", "").startswith("devant"):
                calques.append({"type": "texte", "nom": f'mot géant « {r_["geant"]} »', "t0": r_["a"], "t1": round(r_["a"] + r_["duree"], 3),
                                "box": r_.pop("box"), "estime": True})
            else:
                r_.pop("box", None)
    bj = job / "work" / f"{a.slug}_broll.json"
    broll_rep = []
    if bj.exists():  # plans de coupe : photos / vidéos du client ou images libres, calés sur des mots dits
        wh = None
        if not a.no_sfx and sfxc["enabled"]:
            wsrc, wpeak, wdur = sfx_asset(job, sfxc["whoosh"])
            wh = (wsrc, wpeak, wdur, round(float(sfxc["whooshVolume"]) * 0.5, 3))
        bn, bjs, bsfx, broll_rep = broll_nodes(job, read_json(bj), cap_words, dur, W, H, T0, wh)
        nodes += bn
        tw += bjs
        sfx_nodes += bsfx
    # catalogue et effets sur le rush (effets.py) : vertigo, cadre (frame break), contour (doodle boil), traverse (zoom-through)
    fx_css, fx_svg, cat_rep, fx_rep = "", "", None, None
    if (cat_f.exists() or fx_f.exists()) and not fx_ok:
        cat_rep = {"pose": False, "raison": "catalogue et effets : plein écran recadré seulement (pas d'écran partagé, de fond flouté ni de suivi du visage)"}
    if fx_ok and fx_f.exists():
        import effets as fx
        fh_, fjs, fcss, fx_svg, fwh, fx_rep = fx.effets(job, read_json(fx_f), cap_words, m["segments"], dur, W, H, T0, cut,
                                                        (src["width"], src["height"]), vis["focusX"], accent, avoid=cat_win)
        behind_html += chr(10) + fh_
        tw += fjs
        fx_css += fcss
        if fwh and not a.no_sfx and sfxc["enabled"]:
            wsrc, wpeak, wdur = sfx_asset(job, sfxc["whoosh"])
            for i, t_ in enumerate(fwh):
                st = round(T0 + max(0.0, t_ - wpeak), 3)
                if wsrc:
                    sfx_nodes.append(f'      <audio id="sfx-fx{i}" class="clip" src="{wsrc}" data-start="{st}" '
                                     f'data-duration="{min(wdur, T0 + dur - st)}" data-track-index="13" data-volume="{sfxc["whooshVolume"]}"></audio>')
    if cat_win:
        import effets as fx
        from fonts import title_stack as tstack
        cn_, cjs, ccss, ccal, cat_rep = fx.catalogue(job, read_json(cat_f), cap_words, dur, W, H, T0, accent, tstack(vis), family)
        nodes += cn_
        tw += cjs
        fx_css += ccss
        calques += ccal
    # piles de cartes d'outils (work/<slug>_outils.json) : captures de sites étiquetées sur la vidéo floutée
    ts_css, stack_rep = "", None
    if (job / "work" / f"{a.slug}_outils.json").exists():
        import panel as pn_
        from common import music_beats
        from tools_stack import stack_nodes
        tn, tjs, stack_rep = stack_nodes(job, a.slug, cap_words, dur, W, H, T0, beats=music_beats(job, a.slug), logo_fn=pn_.logo)
        nodes += tn
        tw += tjs
        ts_css = (stack_rep or {}).pop("css", "")
        if stack_rep and stack_rep.get("pose"):  # sous-titres descendus sous la pile pendant qu'elle est là
            cap0 = PH - round(cap_size * 0.62) if split else (H - cap_bottom - round(cap_size * 2.2) if cap_bottom else H * cap_top / 100)
            dy = round(H * (stack_rep["bas_libre"] + 0.06) - cap0)
            if cap_bottom and not split:  # ancrés en bas : jamais sortis de l'image
                dy = min(dy, cap_bottom - round(H * 0.025))
            if dy > 0:
                tw.append(f'  tl.set(".cap", {{ y: {dy} }}, {stack_rep["t0"]});')
                tw.append(f'  tl.set(".cap", {{ y: 0 }}, {stack_rep["t1"]});')
    if mj_.exists() and split:  # écran partagé : pas de bloc par-dessus le panneau, ce qu'ils disent va dans les temps forts
        motion_rep = [{"block": m_.get("block"), "pose": False, "raison": "écran partagé : à mettre dans le panneau"} for m_ in read_json(mj_)]
    elif mj_.exists():  # blocs de motion design calés sur des mots prononcés
        mvals = {"accent": accent, "font": family, "top": (12 if fill else 22) if H > W else 18,  # fond flouté : bande du haut
                 "icon": logo_rel, "avatar": logo_rel}
        mn, motion_rep = motion_nodes(job, read_json(mj_), cap_words, W, H, offset=T0, base_vals=mvals)
        blocks += mn

    # carte : sur fond flouté, dans la bande du haut (l'image du rush reste visible) ; sinon en haut de l'écran
    band = (H - W * src["height"] / src["width"]) / 2 if (fill and H > W and src.get("width")) else 0
    if band > H * 0.25:
        card_top, card_h = round(H * 0.035), round(band - H * 0.06)
    else:
        card_top, card_h = round(H * (0.13 if H > W else 0.1)), round(H * (0.4 if H > W else 0.55))
    # suivi du visage : la vidéo garde toute sa largeur (VW) et glisse en x (transform) pour centrer la personne
    VW = round(H * src["width"] / src["height"]) if track else W
    off = lambda cx: round(min(0, max(W - VW, W / 2 - cx * VW)), 1)
    track_js = ""
    if track:
        track_js = f'  gsap.set("#a-roll", {{ x: {off(track["start"])} }});\n' + "".join(
            f'  tl.to("#a-roll", {{ x: {off(cx)}, duration: {d}, ease: "power2.inOut" }}, {t});\n' for t, cx, d in track["moves"])
    panel_html, panel_rep, split_css = "", [], ""
    if split or cards:  # panneau d'animation (panel.py) : temps forts posés sur des mots dits
        import panel as pn
        pj = job / "work" / f"{a.slug}_panels.json"
        beats = read_json(pj) if pj.exists() else pn.default_beats(t)
        if not pj.exists() and hook.exists():
            beats = [{"type": "title", "_t": 0.0, "text": read_json(hook)["text"], "mark": True}] + beats
        cw = [w for g in t.get("captions", []) for w in g["words"]] or cap_words
        theme = ("glass" if ptheme == "glass" else "cards") if cards else ("light" if ptheme == "light" else "dark")
        blur_off = round(H * 0.15) if cards and vis.get("cardsBlur") else 0  # cartes au milieu : les calques vidéo suivent
        if blur_off:  # vidéo floutée : une carte ne reste pas plus de cardsMax s, puis retour au visage (net) jusqu'au temps fort suivant
            mx = float(vis.get("cardsMax", 4.0))
            rep0 = pn.nodes(job, beats, cw, dur, T0, W, PH, vis, theme=theme, origin=(0, blur_off))[2]
            beats = list(beats) + [{"type": "face", "_t": r_["a"] + mx, "_auto": True} for r_ in rep0
                                   if r_.get("a") is not None and r_["type"] != "face" and r_["duree"] > mx + 1.0]
        panel_html, pjs, panel_rep, layers = pn.nodes(job, beats, cw, dur, T0, W, PH, vis, theme=theme, origin=(0, blur_off))
        panel_html += "\n" + "\n".join(layers)
        tw += pjs
        font_face += " " + pn.fonts(job)
        seam_h = round(cap_size * 2.1)
        base_css = (pn.css_glass(W, PH, family, vis) if theme == "glass" else
                    pn.css_light(W, PH, family, vis, cards=cards) if theme != "dark" else pn.css(W, PH, family, vis))
        kbox = "" if style in ("bulle", "souligne") else f".cap .w.k {{ background: {accent}; color: {hook_ink}; padding: 0 .2em; border-radius: .14em; font-size: 1em; }}"
        split_css = base_css if cards else base_css + f"""
  .zw {{ inset: auto; left: 0; top: {PH}px; width: {W}px; height: {H - PH}px; }}
  #a-roll {{ height: {H - PH}px; object-fit: cover; object-position: {vis["focusX"]}% 32%; }}
  .seam {{ position: absolute; left: 0; right: 0; top: {PH - seam_h // 2}px; height: {seam_h}px; z-index: 40;
          background: linear-gradient(180deg, transparent 0%, rgba(0,0,0,.9) 28%, rgba(0,0,0,.9) 72%, transparent 100%); }}
  .cap {{ top: {PH - round(cap_size * 0.62)}px; }}
  .cap .in {{ {"" if style == "mono" else "text-transform: none; font-weight: 800; letter-spacing: -0.01em; "}{"" if style == "bulle" else "text-shadow: 0 2px 10px rgba(0,0,0,.6); "}white-space: nowrap; }}
  {kbox}
  .broll {{ inset: auto; left: 0; top: 0; width: {W}px; height: {PH}px; }}"""
        faces = [r_ for r_ in panel_rep if r_.get("type") == "face" and r_.get("pose", True)]
        if split and faces:  # alternance : temps forts « face » -> visage plein écran (coupe franche), le panneau revient au suivant
            cap_split, cap_full = PH - round(cap_size * 0.62), round(H * cap_top / 100)
            for f_ in faces:
                for t_, full in ((f_["a"], True), (round(f_["a"] + f_["duree"], 3), False)):
                    if not full and t_ >= dur - 0.05:
                        continue
                    tw.append(f'  tl.set("#panel, .seam", {{ autoAlpha: {0 if full else 1} }}, {t_});')
                    tw.append(f'  tl.set(".zw", {{ top: {0 if full else PH}, height: {H if full else H - PH} }}, {t_});')
                    tw.append(f'  tl.set("#a-roll", {{ height: {H if full else H - PH}, objectPosition: "{vis["focusX"]}% {50 if full else 32}%" }}, {t_});')
                    tw.append(f'  tl.set(".cap", {{ top: {cap_full if full else cap_split} }}, {t_});')
        if split and stack_rep and stack_rep.get("pose"):  # pile d'outils plein écran : le panneau s'efface dessous (pas de texte caché)
            s0_, s1_ = stack_rep["t0"], stack_rep["t1"]
            tw.append(f'  tl.set("#panel, .seam", {{ autoAlpha: 0 }}, {s0_});')
            if not any(f_["a"] <= s1_ < f_["a"] + f_["duree"] for f_ in faces):
                tw.append(f'  tl.set("#panel, .seam", {{ autoAlpha: 1 }}, {s1_});')
        if cards and vis.get("cardsBlur"):  # cartes au milieu, vidéo floutée et assombrie derrière (tutos TikTok) ; « face » la rend nette
            split_css += f"\n  #panel.paper.light.cards {{ top: {blur_off}px; }}"
            for r_ in sorted((r_ for r_ in panel_rep if r_.get("a") is not None), key=lambda r_: r_["a"]):
                face_ = r_["type"] == "face"
                tw.append(f'  tl.to("#a-roll", {{ filter: "{"blur(0px) brightness(1)" if face_ else "blur(16px) brightness(.6)"}", '
                          f'duration: 0.22, ease: "power2.out" }}, {r_["a"]});')
                tw.append(f'  tl.set("#panel", {{ autoAlpha: {0 if face_ else 1} }}, {r_["a"]});')
    # géométrie de la vidéo à l'écran (face.py la rejoue pour situer le visage)
    geo = None
    if src.get("width") and not cards:
        geo = {"W": W, "H": H, "src": [src["width"], src["height"]], "focusX": vis["focusX"],
               "fit": "track" if track else ("contain" if fill else "cover"), "cam": cam,
               "zooms": [[z["t"], z["fin"], 1.12 if z["kind"] == "sec" else 1.09] for z in zooms]}
        if track:
            geo.update(VW=VW, track={"start": track["start"], "moves": track["moves"]})
        if split:
            geo.update(zone=[0, PH, W, H - PH], posY=32, cam=[], zooms=[])
        if cat_rep and cat_rep.get("decal"):  # catalogue : personne décalée à gauche (#fxv), pour situer le visage
            geo["fxv"] = [cat_rep.pop("decal")]
    for b_ in broll_rep:  # plans de coupe : plein écran (le visage est remplacé, voulu) ou carte en haut
        if b_.get("pose"):
            full = b_.get("mode", "full") != "carte"
            calques.append({"type": "plein-ecran" if full else "carte", "nom": f'plan de coupe {b_["image"]}', "t0": b_["a"],
                            "t1": round(b_["a"] + b_["duree"], 3),
                            "box": [0, 0, W, H] if full else [round(W * 0.1), card_top, round(W * 0.9), card_top + card_h]})
    if stack_rep and stack_rep.get("pose"):  # pile d'outils : vidéo floutée derrière, voulu
        calques.append({"type": "plein-ecran", "nom": "pile d'outils", "t0": stack_rep["t0"], "t1": stack_rep["t1"], "box": [0, 0, W, H]})
    if mj_.exists() and not (split or cards):  # blocs de motion : hauteur connue (var top), taille estimée
        for mo_, rp in zip(read_json(mj_), motion_rep):
            if not rp.get("pose"):
                continue
            v_ = {**mvals, **mo_.get("vars", {})}
            t0_ = rp["a"]
            if mo_.get("block") == "lottie":
                sz = float(v_.get("size", 34)) / 100 * min(W, H)
                cx_, cy_ = float(v_.get("x", 50)) / 100 * W, float(v_.get("y", 30)) / 100 * H
                bx = [round(cx_ - sz / 2), round(cy_ - sz / 2), round(cx_ + sz / 2), round(cy_ + sz / 2)]
            else:
                y_ = float(v_.get("top", 40)) / 100 * H
                hb = {"chiffre-verre": 0.3, "cartes-3d": 0.3, "lieu-photo": 0.3, "recherche-verre": 0.15, "suivre": 0.12}.get(mo_.get("block"))
                bx = [round(W * 0.1), round(y_), round(W * 0.9), round(y_ + (hb * H if hb else 0.35 * min(W, H)))]
            calques.append({"type": "bloc", "nom": mo_.get("block"), "t0": t0_, "t1": round(t0_ + float(mo_.get("dur", 3)), 3), "box": bx, "estime": True})
    if lt.get("name"):  # bandeau nom (position estimée)
        y_ = float(lt.get("top", (80 if fill else 50) if H > W else 64)) / 100 * H
        calques.append({"type": "bandeau", "nom": "bandeau-nom", "t0": round(lt_start, 3), "t1": round(lt_start + min(4.0, dur - lt_start), 3),
                        "box": [round(W * 0.05), round(y_), round(W * 0.75), round(y_ + 0.12 * min(W, H))], "estime": True})
    # sous-titres qui évitent le visage : vertical, plein cadre (l'écran partagé a sa propre couture)
    plat = a.plateforme or txt.get("platform", "tous")
    face_rep, cap_y = None, {}
    if cap_blocks and geo and H > W and not split and not a.no_visage and txt.get("captionFace", True):
        import face as fc
        try:
            vis_f = fc.face_samples(job / "assets" / cut)
        except Exception as e:  # détection indisponible : hauteur fixe, la composition se construit quand même
            vis_f = {"samples": [], "erreur": str(e)[:200]}
        pct = fc.part_visages(vis_f)
        if pct >= 15:
            masques = [(c_["t0"], c_["t1"]) for c_ in calques if c_["type"] == "plein-ecran"]
            pile = (stack_rep["t0"], stack_rep["t1"]) if stack_rep and stack_rep.get("pose") else None
            blocs = [b_ for b_ in cap_blocks if not (pile and b_["t0"] < pile[1] and b_["t1"] > pile[0])]  # pile : sous-titres déjà descendus
            occ = [{"t0": c_["t0"], "t1": c_["t1"], "y0": c_["box"][1], "y1": c_["box"][3]} for c_ in calques
                   if c_["type"] in ("accroche", "carte", "texte", "bloc")]  # les sous-titres contournent aussi les blocs posés
            pl = fc.placer_sous_titres(blocs, vis_f, geo, plat, ideal=round(H * cap_top / 100), occupes=occ, masques=masques)
            for p_ in pl:
                cap_y[p_["id"]] = p_["y"]
                cls = "clip cap fond" if p_["fond"] and style not in ("bulle", "mono") else "clip cap"
                for i_, n_ in enumerate(nodes):
                    if f'id="{p_["id"]}"' in n_:
                        nodes[i_] = n_.replace('class="clip cap"', f'class="{cls}" style="top:{p_["y"]}px"', 1)
                        break
            modes = {}
            for p_ in pl:
                modes[p_["mode"]] = modes.get(p_["mode"], 0) + 1
            face_rep = {"plateforme": plat, "visages_pct": pct, "zones": modes}
        else:
            face_rep = {"visages_pct": pct, "zones": "hauteur fixe (pas assez de visage)"}
    bands = []
    for b_ in cap_blocks:
        y_ = cap_y.get(b_["id"], round(H * cap_top / 100) if not split else PH - round(cap_size * 0.62))
        if cap_bottom is not None and not split:
            y_ = H - cap_bottom - b_["h"]
        calques.append({"type": "sous-titre", "nom": b_["id"], "t0": b_["t0"], "t1": b_["t1"], "box": [b_["x0"], y_, b_["x1"], y_ + b_["h"]]})
        bands.append((b_["t0"], b_["t1"], b_["x0"], y_, b_["x1"], y_ + b_["h"]))
    # fond clair sous un groupe (mur blanc, ciel) : voile sombre derrière le texte, ou encre sombre (editorial)
    cap_acc, clairs, lums = accent, 0, []
    if bands and not split and not track and style not in ("bulle", "mono") and txt.get("captionLight", True):
        lums = band_luma(job / "assets" / cut, W, H, vis["focusX"], fill, bands)
        for b_, l_ in zip(cap_blocks, lums):
            if l_ is not None and l_ > float(txt.get("captionLightAt", 170)):
                clairs += 1
                for i_, n_ in enumerate(nodes):
                    if f'id="{b_["id"]}"' in n_ and 'cap fond' not in n_:  # déjà sur fond sombre (gros plan) : rien à faire
                        nodes[i_] = n_.replace('class="clip cap', 'class="clip cap clair', 1)
                        break
    dark = sorted(l_ for l_ in lums if l_ is not None and l_ <= 170)
    if style not in ("boite", "mono", "bulle", "editorial"):  # accent sombre sur vidéo sombre : éclairci (contraste 4,5:1)
        g_ = round(dark[len(dark) // 2]) if dark else 60
        if g_ < 110:  # vidéo sombre seulement : sur un fond moyen, l'ombre portée du texte suffit
            cap_acc = _readable(accent, f"#{g_:02x}{g_:02x}{g_:02x}", to="#ffffff")  # texte clair sur la vidéo : l'accent s'éclaircit
    if style == "mono" and not (split or cards):  # police machine à écrire du style « mono »
        import panel as pn
        font_face += " " + pn.fonts(job)
    doc = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<title>{esc(a.slug)}</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
<style>
  {font_face}
  html, body {{ margin: 0; padding: 0; background: #000; width: {W}px; height: {H}px; overflow: hidden; }}
  #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; }}
  #bg {{ position: absolute; inset: 0; background: #000; }}
  .zw {{ position: absolute; inset: 0; overflow: hidden; }}
  #cam {{ position: absolute; inset: 0; transform-origin: {vis["focusX"]}% 42%; will-change: transform; }}
  #zm {{ position: absolute; inset: 0; transform-origin: {vis["focusX"]}% 38%; }}
  #fxv {{ position: absolute; inset: 0; }}  /* calque de la vidéo pour les effets (effets.py) : un clip vidéo ignore les transform */
  #a-roll {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; object-fit: {"contain" if fill else "cover"};
             object-position: {vis["focusX"]}% 50%; display: block; }}
  #a-cut {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; object-fit: cover; object-position: {vis["focusX"]}% 50%; }}
  .bh {{ position: absolute; left: 0; right: 0; top: {btop}px; text-align: center; font-family: '{family}', 'Inter', sans-serif;
        font-weight: 900; line-height: .92; letter-spacing: -.02em; text-transform: uppercase; color: #fff; }}
  .bh .bl {{ display: block; text-shadow: 0 .04em .12em rgba(0,0,0,.35); }}
  .bh .bl:nth-child(2) {{ color: {accent}; }}
  #a-fill {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; object-fit: cover;
             filter: blur(40px) brightness(.55); transform: scale(1.15); }}
  .cap {{ position: absolute; left: 0; right: 0; top: {round(H * cap_top / 100)}px; overflow: visible; z-index: 50; }}
  #pbar {{ position: absolute; left: 6%; right: 6%; bottom: {round(H * 0.035)}px; height: {max(4, round(H * 0.0032))}px; border-radius: 99px;
          background: rgba(255,255,255,.42); overflow: hidden; z-index: 400; }}  /* barre de progression (visual.progressBar) */
  #pbar i {{ display: block; height: 100%; background: {accent}; transform-origin: 0 50%; transform: scaleX(0); }}
  .cap .in {{ margin: 0 {round(W * 0.08)}px; text-align: center; font-family: '{family}'; font-weight: 900;
             font-size: {cap_size}px; line-height: 1.08; color: {ink}; text-shadow: {SHADOW}; text-wrap: balance;
             {"text-transform: uppercase; letter-spacing: -0.01em;" if style != "minimal" else "font-weight: 700;"} }}
  .cap.fond .in {{ width: fit-content; max-width: {round(W * 0.84)}px; margin: 0 auto; padding: .1em .35em .14em; border-radius: .22em;
                  background: rgba(0,0,0,.58); box-sizing: border-box; }}  /* gros plan : sous la bouche, sur fond sombre */
  .cap .w {{ display: inline-block; margin: 0 0.07em; transform-origin: 50% 70%; {"opacity: 0;" if style in ("pop", "duo", "seam", "mono") else ""} }}
  {"" if style in ("editorial", "bulle", "mono") else f".cap.clair .in {{ width: fit-content; max-width: {round(W * 0.84)}px; margin: 0 auto; padding: .1em .35em .14em; border-radius: .22em; background: rgba(0,0,0,.5); box-sizing: border-box; }}  /* fond clair : voile sombre */"}
  {f".cap {{ top: auto; bottom: {cap_bottom}px; }}" if cap_bottom is not None and not split else ""}
{caption_css(style, cap_acc)}
{ts_css}
{mots_css}
{fx_css}
  .broll {{ position: absolute; inset: 0; z-index: 30; overflow: hidden; }}
  .broll .bw {{ position: absolute; inset: 0; overflow: hidden; opacity: 0; }}
  .broll .bri {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
  .broll.carte .bw {{ inset: auto; left: {round(W * 0.1)}px; width: {round(W * 0.8)}px; top: {card_top}px; height: {card_h}px; border-radius: {round(min(W, H) * 0.03)}px;
                     border: {round(min(W, H) * 0.012)}px solid #fff; box-shadow: 0 {round(H * 0.012)}px {round(H * 0.04)}px rgba(0,0,0,.45); }}
  .note {{ position: absolute; z-index: 55; font-family: '{family}'; font-weight: 900; color: {ink}; line-height: 1.1;
           letter-spacing: -0.01em; text-shadow: {SHADOW}; text-wrap: balance; }}
  .note .w {{ display: inline-block; opacity: 0; }}  /* chaque mot attend son tween : sinon visible avant d'être dit */
  .nL {{ left: {round(90 * r)}px; width: {round(W * 0.58)}px; text-align: left; top: {round(H * 0.40)}px; font-size: {SZ['side']}px; }}
  .nR {{ right: {round(90 * r)}px; width: {round(W * 0.58)}px; text-align: right; top: {round(H * 0.46)}px; font-size: {SZ['side']}px; }}
  .nC {{ left: {round(70 * r)}px; right: {round(70 * r)}px; text-align: center; top: {round(H * 0.52)}px; font-size: {SZ['center']}px; }}
  .hook {{ position: absolute; left: 0; right: 0; top: {round(H * (0.11 if H > W else 0.08))}px; text-align: center; z-index: 60; }}
  .hook .hk {{ display: inline-block; max-width: 84%; padding: .28em .6em; border-radius: .22em; background: {accent};
              color: {hook_ink}; font-family: {title_stack(vis)}; font-weight: {title_weight(vis, 900)}; font-size: {hook_size}px; line-height: 1.12;
              text-wrap: balance; opacity: 0; box-shadow: 0 10px 30px rgba(0,0,0,.35); }}
  .topline {{ left: {round(70 * r)}px; right: {round(70 * r)}px; text-align: center; top: {round(H * 0.16)}px;
              font-size: {SZ['topline']}px; text-transform: uppercase; color: {accent}; }}
{split_css}
</style>
</head>
<body>
  <div id="root" data-composition-id="reel" data-start="0" data-width="{W}" data-height="{H}" data-duration="{total}">
    <div id="bg"></div>
{fx_svg}
    <div class="zw">
      <div id="zm"><div id="cam"><div id="fxv">
        {f'<video id="a-fill" class="clip" src="assets/{esc(cut)}" data-start="{T0}" data-duration="{dur}" data-track-index="1" muted playsinline></video>' if fill else ""}
        <video id="a-roll" class="clip" src="assets/{esc(cut)}" data-start="{T0}" data-duration="{dur}"
               data-track-index="0" playsinline data-has-audio="true" data-volume="1"{' style="width: ' + str(VW) + 'px; max-width: none; object-fit: fill;"' if track else ''}></video>
        </div>
{behind_html}
      </div></div>
    </div>
{panel_html}
{'    <div class="seam"></div>' if split else ''}
{chr(10).join(sfx_nodes)}
{chr(10).join(nodes)}
{chr(10).join(blocks)}
{'    <div id="pbar"><i></i></div>' if vis.get("progressBar") else ""}
  </div>
<script>
  window.__timelines = window.__timelines || {{}};
  /* contenu dans sa propre timeline, décalée de la durée de l'intro dans la timeline principale */
  const master = gsap.timeline({{ paused: true }});
  const tl = gsap.timeline();
  master.add(tl, {T0});
{"  master.fromTo('#pbar i', { scaleX: 0 }, { scaleX: 1, duration: " + str(total) + ", ease: 'none' }, 0);" if vis.get("progressBar") else ""}
  const INK = {json.dumps(ink)}, ACCENT = {json.dumps(cap_acc)}, BOXINK = {json.dumps(hook_ink)};
  const FIT = {json.dumps(fit_settings(style, family, W, cap_size, split))};
{FIT_JS}
{caption_js(style)}

  /* overlays reel-cut : chaque mot apparaît 0,12 s avant d'être dit */
  function wIn(sel, times) {{
    const spans = document.querySelectorAll(sel + " .w");
    times.forEach(function (t, i) {{
      if (spans[i]) tl.fromTo(spans[i], {{ opacity: 0, y: 16 }},
        {{ opacity: 1, y: 0, duration: 0.24, ease: "power2.out", immediateRender: false }}, Math.max(0, t - 0.12));
    }});
  }}
  function noteOut(sel, t) {{ tl.to(sel + " .w", {{ opacity: 0, y: -14, duration: 0.3, ease: "power2.in" }}, t); }}

{track_js}
  /* caméra : [t, from, to, durée, ease] */
  var CAM = {json.dumps(cam)};
  CAM.forEach(function (c) {{
    tl.fromTo("#cam", {{ scale: c[1] }}, {{ scale: c[2], duration: c[3], ease: c[4], immediateRender: false }}, c[0]);
  }});
{chr(10).join(zoom_js(zooms))}

{chr(10).join(tw)}

  window.__timelines["reel"] = master;
</script>
</body>
</html>
"""
    (job / "index.html").write_text(doc, encoding="utf-8")
    write_json(job / "work" / f"{a.slug}_build.json", {"script": "build_composition.py", "args": cli_args(ap, a)})
    write_json(job / "work" / f"{a.slug}_calques.json",
               {"slug": a.slug, "T0": T0, "duree": dur, "video": f"assets/{cut}", "ideal": round(H * cap_top / 100), "plateforme": plat,
                "geo": geo, "calques": sorted(calques, key=lambda c_: c_["t0"])})
    if not getattr(a, "no_sfx", False):  # bruitages sur ce qui apparaît (sound_design.py ; "sfx": {"design": false} pour s'en passer)
        sound_design.auto(job)
    drifts = sum(1 for x in cam if x[4] == "power1.inOut")
    out(ok=True, format=f"{W}x{H}", duree=total, contenu=dur, intro=T0, outro=outro_d, bandeau=bool(lt.get("name")),
        motions=motion_rep, plans_de_coupe=broll_rep, mode=mode, style=style,
        cadrage="écran partagé" if split else ("suit le visage" if track else ("image entière, fond flouté" if fill else "recadré")),
        panneau=panel_rep or None,
        captions=sum(1 for n in nodes if 'class="clip cap' in n), overlays=sum(1 for n in nodes if "note" in n),
        drifts=drifts, punchs=len(cam) - drifts,
        sous_titres_fond_clair=clairs or None, fond_sous_titres=[round(l_) for l_ in lums if l_ is not None][:60] or None, accent_sous_titres=cap_acc if cap_acc != accent else None, sous_titres_visage=face_rep, titre_derriere=behind_rep, catalogue=cat_rep, effets=fx_rep, mots=mots_rep, couleur_mots=macc if mots_rep is not None else None, outils=stack_rep, zooms=[f"{z['t']} s {z['mot']} ({z['kind']})" for z in zooms], sfx_whoosh=n_whoosh, sfx_tick=n_tick,
        suite="npx hyperframes check, puis snapshot / preview")


if __name__ == "__main__":
    main()
