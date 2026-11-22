"""COMPOSITION HyperFrames -> <job>/index.html   (base reel-cut, étendue)

- Vidéo dérushée + caméra (doctrine reel-cut : drifts imperceptibles de 3 %, punch-in +7,5 % rare).
- Texte selon text.mode : "captions" (sous-titres complets, styles pop | karaoke | minimal | boite | impact | duo,
  emoji automatique sur les mots-clés avec text.captionEmoji ou --emoji),
  "overlays" (phrases rares verbatim de reel-cut), ou "both".
- SFX réels de la banque sounds/ (real-sfx) : whoosh calé par son pic sur chaque punch, tick sur les jointures.
- Charte : police, couleurs, cadrage horizontal (visual.focusX) depuis config / brand.json.
Rien n'est gravé : tout reste modifiable dans le Studio HyperFrames.

  python build_composition.py <job> <slug> [--no-cam] [--no-sfx] [--mode captions|overlays|both] [--style pop]
"""
import argparse
import html
import json
import shutil
from pathlib import Path

import re

from common import (REAL_SFX_INDEX, ROOT, SOUNDS, add_credit, block_file, brand_info, config, fail, job_dir, motion_nodes,
                    mount, out, probe, read_json, size_of, word_hit)

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


EMOJI_CHAR = {"valide": "✅", "coeur": "❤️", "etoile": "⭐", "pouce": "👍", "fusee": "🚀", "cadeau": "🎁", "idee": "💡",
              "regard": "👀", "waouh": "🤩", "adore": "😍", "cent": "💯", "bravo": "🙌", "applaudir": "👏", "eclat": "✨",
              "cloche": "🔔", "alarme": "🚨", "trophee": "🏆", "force": "💪", "reflexion": "🤔", "rire": "😂", "doigt": "👉",
              "cible": "🎯", "feu": "🔥", "fete": "🎉"}
STYLES = ["pop", "karaoke", "minimal", "boite", "impact", "duo", "seam", "mono"]


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


def caption_spans(words, style, use_emoji, st, last_emo):
    """HTML des mots d'un groupe selon le style (+ emoji collé à son mot). -> (html, instant de l'emoji ou None, last_emo)"""
    keyw = key_word(words) if style in ("duo", "seam") else set()
    parts, emo = [], None
    for j, w in enumerate(words):
        inner = ('<i class="bx"></i>' if style == "boite" else "") + esc(w["w"])
        parts.append(f'<span class="w{" k" if j in keyw else ""}">{inner}</span>')
        ch = emoji_for(w["w"]) if use_emoji and emo is None and w["start"] - last_emo > 4 else None
        if ch:  # un emoji au plus par groupe, et pas plus d'un toutes les 4 s ; collé à son mot (même ligne)
            parts[-1] = f'<span class="wn">{parts[-1]}<span class="em">{ch}</span></span>'
            emo, last_emo = round(max(st, w["start"]), 3), w["start"]
    return " ".join(parts), emo, last_emo


def emoji_tween(gid, emo):
    return (f'  tl.fromTo("#{gid} .em", {{ opacity: 0, scale: 0.2, rotation: -25 }}, {{ opacity: 1, scale: 1, rotation: 0, '
            f'duration: 0.35, ease: "back.out(3)", immediateRender: false }}, {emo});')


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
  .cap .in {{ -webkit-text-stroke: 0.09em #000; paint-order: stroke fill; text-shadow: 0 0.07em 0 #000, {shadow}; }}"""
    if style == "mono":  # majuscules machine à écrire, chaque mot dans sa boîte noire, le mot dit en couleur d'accent
        css += """
  .cap .in { font-family: 'IBM Plex Mono', monospace; font-weight: 500; text-transform: uppercase; letter-spacing: 0; text-shadow: none; }
  .cap .w { background: #111; color: #fff; padding: 0.02em 0.26em; margin: 0 0.02em; box-decoration-break: clone; -webkit-box-decoration-break: clone; }"""
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
      tl.to(spans[i], { color: ACCENT, scale: 1.14, duration: 0.07, ease: "power2.out" }, on);
      if (i + 1 < ws.length) tl.to(spans[i], { color: INK, scale: 1, duration: 0.07, ease: "power2.in" }, Math.max(on + 0.08, ws[i + 1][0] - 0.02));
    });
    tl.to(g + " .in", { opacity: 0, scale: 0.94, duration: 0.1, ease: "power2.in" }, en - 0.1);
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
    ap.add_argument("--size", help="9:16 | 1:1 | 4:5 | 16:9 | LxH (défaut : config)")
    ap.add_argument("--layout", choices=["full", "split", "cards"],
                    help="split : animation en haut, visage en bas ; cards : visage plein écran, cartes en haut (visual.layout)")
    ap.add_argument("--accroche", help="accroche animée de 3 s en ouverture : papier, plan, pate, neon, aquarelle, pixel, isometrique, mosaique, encre, relief")
    ap.add_argument("--accroche-texte", help="titre de l'accroche (sinon config hook.text ou l'accroche du short)")
    ap.add_argument("--panel-theme", choices=["dark", "light"], help="écran partagé : panneau sombre ou clair (visual.panelTheme)")
    ap.add_argument("--mode", choices=["captions", "overlays", "both", "none"])
    ap.add_argument("--no-captions", action="store_true", help="= --mode none (couverture)")
    ap.add_argument("--style", choices=STYLES)
    ap.add_argument("--emoji", action="store_true", help="emoji après les mots-clés (bravo 👏, idée 💡…)")
    ap.add_argument("--no-branding", action="store_true", help="sans intro / outro / bandeau nom")
    ap.add_argument("--lang", help="sous-titres traduits (translate.py) : nl, en…")
    a = ap.parse_args()
    job = job_dir(a.job)
    c = config(job)
    vis, txt, sfxc = c["visual"], c["text"], c["sfx"]
    W, H = size_of(a.size, vis)
    mode = "none" if a.no_captions else ("captions" if a.lang else (a.mode or txt["mode"]))
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

    font_face = ""
    for f in vis.get("fonts", []):
        ff = ROOT / f["file"] if not Path(f["file"]).is_absolute() else Path(f["file"])
        (job / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
        shutil.copy2(ff, job / "assets" / "fonts" / ff.name)
        font_face += (f"@font-face {{ font-family: '{family}'; src: url('assets/fonts/{ff.name}') format('{f.get('format', 'woff2')}'); "
                      f"font-weight: {f.get('weight', 400)}; }} ")
    if vis.get("fontFile"):
        ff = Path(vis["fontFile"])
        (job / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
        shutil.copy2(ff, job / "assets" / "fonts" / ff.name)
        font_face = f"@font-face {{ font-family: '{family}'; src: url('assets/fonts/{ff.name}'); font-weight: 100 900; }}"

    r = W / 1920.0
    k = float(vis.get("sizeScale") or (1.5 if H > W else 1.0))
    SZ = {"side": round(88 * r * k), "center": round(97 * r * k), "topline": round(110 * r * k)}
    cap_size = round({"minimal": 58, "impact": 96, "seam": 62, "mono": 52}.get(style, 84) * (W / 1080 if H > W else H / 1080))
    use_emoji = a.emoji or txt.get("captionEmoji", False)

    nodes, tw = [], []
    overlays = sorted((o for o in t["overlays"] if o.get("keep") and o["start"] < dur), key=lambda o: o["start"])
    punches = sorted(float(o["start"]) for o in t["overlays"] if o.get("punch") and o["start"] < dur)

    if mode in ("captions", "both"):
        caps = t["captions"]
        last_emo = -99.0
        for i, g in enumerate(caps):
            st = round(max(0.1, g["words"][0]["start"] - 0.05), 3)
            nxt = caps[i + 1]["words"][0]["start"] - 0.05 if i + 1 < len(caps) else dur
            en = round(min(dur, max(g["end"] + 0.25, st + 0.4), nxt if split else max(nxt, g["end"])), 3)  # écran partagé : une ligne, jamais deux groupes à la fois
            if en - st <= 0.1:
                continue
            gid = f"cap-{g['id']}"
            words = g["words"]
            text = " ".join(w["w"] for w in words)
            spans, emo, last_emo = caption_spans(words, style, use_emoji, st, last_emo)
            fit_text = text + (" MM" if emo is not None else "")  # place de l'emoji dans le calcul de taille
            nodes.append(f'      <div class="clip cap" id="{gid}" data-start="{st}" data-duration="{round(en - st, 3)}" '
                         f'data-track-index="4"><div class="in" data-fit="{esc(fit_text)}">{spans}</div></div>')
            times = [[round(max(st, w["start"]), 3), round(w["end"], 3)] for w in words]
            tw.append(f'  cap("{gid}", {st}, {en}, {json.dumps(times)});')
            if emo is not None:
                tw.append(emoji_tween(gid, emo))

    hook = job / "work" / f"{a.slug}_hook{sfx_lang}.json"
    if a.lang and not hook.exists():
        hook = job / "work" / f"{a.slug}_hook.json"
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

    cam = [] if (a.no_cam or not c["camera"]["enabled"]) else build_cam(dur, punches)

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
        hv = {"text": text, "sub": hk.get("sub", ""), "accent": hk.get("accent") or accent, "font": family}
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
    cap_words = [w for g in t.get("captions", []) for w in g["words"]]
    if not cap_words:
        from build_text import remap
        cap_words = remap(read_json(job / "work" / f"{a.slug}_words.json")["words"], m["segments"])
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
    if mj_.exists() and (split or cards):  # écran partagé : pas de bloc par-dessus le panneau, ce qu'ils disent va dans les temps forts
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
        theme = "cards" if cards else ("light" if ptheme == "light" else "dark")
        panel_html, pjs, panel_rep, layers = pn.nodes(job, beats, cw, dur, T0, W, PH, vis, theme=theme)
        panel_html += "\n" + "\n".join(layers)
        tw += pjs
        font_face += " " + pn.fonts(job)
        seam_h = round(cap_size * 2.1)
        base_css = pn.css_light(W, PH, family, vis, cards=cards) if theme != "dark" else pn.css(W, PH, family, vis)
        split_css = base_css if cards else base_css + f"""
  .zw {{ inset: auto; left: 0; top: {PH}px; width: {W}px; height: {H - PH}px; }}
  #a-roll {{ height: {H - PH}px; object-fit: cover; object-position: {vis["focusX"]}% 32%; }}
  .seam {{ position: absolute; left: 0; right: 0; top: {PH - seam_h // 2}px; height: {seam_h}px; z-index: 40;
          background: linear-gradient(180deg, transparent 0%, rgba(0,0,0,.9) 28%, rgba(0,0,0,.9) 72%, transparent 100%); }}
  .cap {{ top: {PH - round(cap_size * 0.62)}px; }}
  .cap .in {{ {"" if style == "mono" else "text-transform: none; font-weight: 800; letter-spacing: -0.01em; "}text-shadow: 0 2px 10px rgba(0,0,0,.6); white-space: nowrap; }}
  .cap .w.k {{ background: {accent}; color: {hook_ink}; padding: 0 .2em; border-radius: .14em; font-size: 1em; }}
  .broll {{ inset: auto; left: 0; top: 0; width: {W}px; height: {PH}px; }}"""
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
  #a-roll {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; object-fit: {"contain" if fill else "cover"};
             object-position: {vis["focusX"]}% 50%; display: block; }}
  #a-fill {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; object-fit: cover;
             filter: blur(40px) brightness(.55); transform: scale(1.15); }}
  .cap {{ position: absolute; left: 0; right: 0; top: {round(H * cap_top / 100)}px; overflow: visible; z-index: 50; }}
  .cap .in {{ margin: 0 {round(W * 0.08)}px; text-align: center; font-family: '{family}'; font-weight: 900;
             font-size: {cap_size}px; line-height: 1.08; color: {ink}; text-shadow: {SHADOW}; text-wrap: balance;
             {"text-transform: uppercase; letter-spacing: -0.01em;" if style != "minimal" else "font-weight: 700;"} }}
  .cap .w {{ display: inline-block; margin: 0 0.07em; transform-origin: 50% 70%; {"opacity: 0;" if style in ("pop", "duo", "mono") else ""} }}
{caption_css(style, accent)}
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
              color: {hook_ink}; font-family: '{family}'; font-weight: 900; font-size: {round(cap_size * 0.82)}px; line-height: 1.12;
              text-wrap: balance; opacity: 0; box-shadow: 0 10px 30px rgba(0,0,0,.35); }}
  .topline {{ left: {round(70 * r)}px; right: {round(70 * r)}px; text-align: center; top: {round(H * 0.16)}px;
              font-size: {SZ['topline']}px; text-transform: uppercase; color: {accent}; }}
{split_css}
</style>
</head>
<body>
  <div id="root" data-composition-id="reel" data-start="0" data-width="{W}" data-height="{H}" data-duration="{total}">
    <div id="bg"></div>
    <div class="zw">
      <div id="cam">
        {f'<video id="a-fill" class="clip" src="assets/{esc(cut)}" data-start="{T0}" data-duration="{dur}" data-track-index="1" muted playsinline></video>' if fill else ""}
        <video id="a-roll" class="clip" src="assets/{esc(cut)}" data-start="{T0}" data-duration="{dur}"
               data-track-index="0" playsinline data-has-audio="true" data-volume="1"{' style="width: ' + str(VW) + 'px; max-width: none; object-fit: fill;"' if track else ''}></video>
      </div>
    </div>
{panel_html}
{'    <div class="seam"></div>' if split else ''}
{chr(10).join(sfx_nodes)}
{chr(10).join(nodes)}
{chr(10).join(blocks)}
  </div>
<script>
  window.__timelines = window.__timelines || {{}};
  /* contenu dans sa propre timeline, décalée de la durée de l'intro dans la timeline principale */
  const master = gsap.timeline({{ paused: true }});
  const tl = gsap.timeline();
  master.add(tl, {T0});
  const INK = {json.dumps(ink)}, ACCENT = {json.dumps(accent)}, BOXINK = {json.dumps(hook_ink)};

  /* taille ajustée à la largeur, pour que chaque groupe tienne sur 2 lignes max */
  document.querySelectorAll(".cap .in").forEach(function (el) {{
    const f = window.__hyperframes && window.__hyperframes.fitTextFontSize;
    if (!f) return;
    const r = f(el.dataset.fit, {{ fontFamily: {json.dumps(family)}, fontWeight: 900, maxWidth: {round(W * 0.84 / 1.12)}, baseFontSize: {cap_size}, minFontSize: 42 }});
    if (r && r.fontSize) el.style.fontSize = r.fontSize + "px";
  }});
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

{chr(10).join(tw)}

  window.__timelines["reel"] = master;
</script>
</body>
</html>
"""
    (job / "index.html").write_text(doc, encoding="utf-8")
    drifts = sum(1 for x in cam if x[4] == "power1.inOut")
    out(ok=True, format=f"{W}x{H}", duree=total, contenu=dur, intro=T0, outro=outro_d, bandeau=bool(lt.get("name")),
        motions=motion_rep, plans_de_coupe=broll_rep, mode=mode, style=style,
        cadrage="écran partagé" if split else ("suit le visage" if track else ("image entière, fond flouté" if fill else "recadré")),
        panneau=panel_rep or None,
        captions=sum(1 for n in nodes if 'class="clip cap"' in n), overlays=sum(1 for n in nodes if "note" in n),
        drifts=drifts, punchs=len(cam) - drifts, sfx_whoosh=n_whoosh, sfx_tick=n_tick,
        suite="npx hyperframes check, puis snapshot / preview")


if __name__ == "__main__":
    main()
