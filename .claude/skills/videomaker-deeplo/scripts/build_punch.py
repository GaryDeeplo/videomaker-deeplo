"""PACK « ACTU / PUNCH » -> <job>/index.html : images plein cadre coupées vite, gros titres condensés qui claquent,
objets qui collent aux mots (notification, prix, étiquette, document, date, chiffre, picto, emoji animé).

  python build_punch.py <job> <slug> [--size 9:16] [--no-captions]
  python build_punch.py fetch <job> <slug>          # temps forts avec "query" sans "media" : Pixabay + planche
  python build_punch.py pick <job> <slug> <n> <a-f|none>

Voix : voice.py (storyboard, Gemini / Fish / --file) -> build_text.py -> add_music.py. Puis work/<slug>_punch.json,
une liste de temps forts posés sur des MOTS dits (jamais un timecode) :
  {"word": "C'est", "media": "inbox/clip.mp4 | photo.jpg" (ou "query": "1-2 mots anglais"),
   "title": ["MARTIN", {"text": "*RÉSERVATIONS*", "word": "réservations"}, {"text": "OUVERTES", "word": "ouvertes"}],
   "prop": {"type": "price", "word": "soixante", "value": "60 €", "sub": "1 H DE SOIN"}}
Un média reste à l'écran jusqu'au temps fort suivant qui en a un (visez une coupe toutes les 1,5 à 3 s). Les lignes de
titre s'empilent en haut (*mot* = couleur d'accent) ; chaque ligne peut attendre son mot. Objets ("prop") :
  notif  {"app": "…", "title": "…", "text": "…", "icon": "bell"}      — illustration, jamais une fausse vraie notification
  price  {"value": "60 €", "sub": "…"}          tag   {"text": "…"}          date  {"month": "NOV.", "day": "19"}
  doc    {"title": "…", "lines": ["Classe : …", "…"]}                       stat  {"value": "2,8", "unit": "µg", "label": "…"}
  icon   {"icon": "calendar-check", "label": "…"}                           lottie {"name": "valide"}
  "y": hauteur en % (défaut 52). Toutes les infos sont réelles ; les objets illustrent ce qui est dit.
Accent : visual.punchAccent (sinon l'accent de la charte s'il est vif, sinon jaune) ; police des titres : Anton (OFL).
"""
import argparse
import html
import json
import math
import re
import shutil
import sys
from pathlib import Path

import panel as pn
from build_composition import SHADOW, caption_css, caption_js, caption_spans
import sound_design
from common import ROOT, add_credit, config, fail, job_dir, music_beats, out, probe, read_json, scale_of, size_of, snap_beat, word_hit, write_json

esc = lambda s: html.escape(str(s), quote=True)
VENDOR = ROOT / ".claude" / "skills" / "videomaker-deeplo" / "vendor" / "fonts"


def vivid(c):
    r, g, b = [x / 255 for x in pn._hex(c)]
    mx, mn = max(r, g, b), min(r, g, b)
    return (mx - mn) / (mx or 1) > 0.45 and mx > 0.5


def title_html(text, acc_cls="a"):
    return re.sub(r"\*([^*]+)\*", lambda m: f'<span class="{acc_cls}">{esc(m.group(1))}</span>', esc(text).replace("&#x27;", "'"))


def media_src(job, src):
    p = Path(src)
    if (job / p).exists():
        return str(p).replace("\\", "/")
    for base in (job / "inbox", ROOT):
        if (base / p).exists():
            (job / "assets" / "media").mkdir(parents=True, exist_ok=True)
            if (base / p).resolve() != (job / "assets" / "media" / p.name).resolve():
                shutil.copy2(base / p, job / "assets" / "media" / p.name)
            return f"assets/media/{p.name}"
    return None


def prop_html(pid, pr, u, acc):
    t = pr.get("type")
    if t == "notif":
        ic = pn.icon(pr.get("icon", "bell"))
        return (f'<div class="pp notif" id="{pid}"><div class="nh"><span class="ni">{ic}</span><b>{esc(pr.get("app", ""))}</b>'
                f'<em>maintenant</em></div><div class="nt">{esc(pr.get("title", ""))}</div><div class="nx">{esc(pr.get("text", ""))}</div></div>')
    if t == "price":
        return f'<div class="pp price" id="{pid}"><i></i><b>{esc(pr.get("value", ""))}</b><span>{esc(pr.get("sub", ""))}</span></div>'
    if t == "tag":
        return f'<div class="pp tagp" id="{pid}"><i></i><b>{esc(pr.get("text", ""))}</b></div>'
    if t == "date":
        return f'<div class="pp date" id="{pid}"><span>{esc(pr.get("month", ""))}</span><b>{esc(pr.get("day", ""))}</b></div>'
    if t == "doc":
        lines = "".join(f'<div class="dl l{j}" data-t="{esc(x)}"></div>' for j, x in enumerate(pr.get("lines", [])[:5]))
        return f'<div class="pp doc" id="{pid}"><div class="dh">{esc(pr.get("head", "NOTICE"))}</div><div class="dt">{esc(pr.get("title", ""))}</div>{lines}</div>'
    if t == "stat":
        return (f'<div class="pp stat" id="{pid}"><b>{esc(pr.get("value", ""))}</b><em>{esc(pr.get("unit", ""))}</em>'
                f'<span>{esc(pr.get("label", ""))}</span></div>')
    if t == "icon":
        return f'<div class="pp ico" id="{pid}"><div class="ci">{pn.icon(pr.get("icon", "star"))}</div><span>{esc(pr.get("label", ""))}</span></div>'
    return ""


def prop_js(pid, pr, t0, t1):
    t = pr.get("type")
    js = []
    if t == "notif":
        js.append(f'  tl.fromTo("#{pid}", {{ opacity: 0, y: -260 }}, {{ opacity: 1, y: 0, duration: 0.55, ease: "back.out(1.5)", immediateRender: false }}, {t0});')
    elif t in ("price", "tag", "date", "stat"):
        rot = {"price": -6, "tag": 4, "date": -5, "stat": 0}[t]
        js.append(f'  tl.fromTo("#{pid}", {{ opacity: 0, scale: 2.1, rotation: {rot * 3} }}, {{ opacity: 1, scale: 1, rotation: {rot}, duration: 0.32, '
                  f'ease: "back.out(2.2)", immediateRender: false }}, {t0});')
        js.append(f'  tl.fromTo("#flash", {{ opacity: 0.55 }}, {{ opacity: 0, duration: 0.18, immediateRender: false }}, {t0 + 0.05});')
    elif t == "doc":
        js.append(f'  tl.fromTo("#{pid}", {{ opacity: 0, scaleY: 0.05, transformOrigin: "50% 0%" }}, {{ opacity: 1, scaleY: 1, duration: 0.4, '
                  f'ease: "power3.out", immediateRender: false }}, {t0});')
        js.append(f'  (function () {{ document.querySelectorAll("#{pid} .dl").forEach(function (el, j) {{ const s = el.dataset.t, o = {{ n: 0 }};'
                  f' tl.fromTo(o, {{ n: 0 }}, {{ n: s.length, duration: Math.min(1.0, s.length * 0.035), ease: "none", immediateRender: false,'
                  f' onUpdate: function () {{ el.textContent = s.slice(0, Math.round(o.n)); }} }}, {t0 + 0.45} + j * 0.75); }}); }})();')
    elif t == "icon":
        js.append(f'  tl.fromTo("#{pid}", {{ opacity: 0, scale: 0.2, rotation: -30 }}, {{ opacity: 1, scale: 1, rotation: 0, duration: 0.55, '
                  f'ease: "back.out(2.6)", immediateRender: false }}, {t0});')
    js.append(f'  tl.to("#{pid}", {{ opacity: 0, scale: 0.9, duration: 0.2, ease: "power2.in" }}, {round(t1 - 0.2, 3)});')
    return js


def build(a):
    job = job_dir(a.job)
    c = config(job)
    vis = c["visual"]
    W, H = size_of(a.size, vis)
    u = scale_of(W, H)
    wide = W / H > 1.2  # paysage : titres à gauche, objets (notification, date, prix…) à droite
    PW = W * 0.46 if wide else W  # largeur de la zone des objets
    mj, tj, pj = job / "work" / f"{a.slug}_map.json", job / "work" / f"{a.slug}_text.json", job / "work" / f"{a.slug}_punch.json"
    for p in (mj, tj, pj):
        if not p.exists():
            fail(f"{p} absent")
    m, t, beats = read_json(mj), read_json(tj), read_json(pj)
    dur = float(m["out_duration"])
    voice = Path(m["cut"]).name
    acc = vis.get("punchAccent") or (vis["accentColor"] if vivid(vis["accentColor"]) else "#FFD60A")
    on_acc = "#111111" if pn._lum(acc) > 160 else "#ffffff"
    fam = vis["fontFamily"]
    words = [w for g in t.get("captions", []) for w in g["words"]]
    (job / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(VENDOR / "Anton-Regular.ttf", job / "assets" / "fonts" / "Anton-Regular.ttf")
    faces = ["@font-face { font-family: 'Anton'; src: url('assets/fonts/Anton-Regular.ttf'); }", pn.fonts(job)]
    if vis.get("fontFile"):
        ff = ROOT / vis["fontFile"]
        shutil.copy2(ff, job / "assets" / "fonts" / ff.name)
        faces.append(f"@font-face {{ font-family: '{fam}'; src: url('assets/fonts/{ff.name}'); font-weight: 100 900; }}")
    for f in vis.get("fonts", []):
        ff = ROOT / f["file"]
        shutil.copy2(ff, job / "assets" / "fonts" / ff.name)
        faces.append(f"@font-face {{ font-family: '{fam}'; src: url('assets/fonts/{ff.name}'); font-weight: {f.get('weight', 400)}; }}")

    def at(word, occ=1, default=None):
        h = word_hit(words, word, occ) if word else None
        return max(0.0, h["start"] - 0.08) if h else default

    placed = sorted(((at(b.get("word"), b.get("occurrence", 1)), b) for b in beats), key=lambda x: (x[0] is None, x[0] or 0))
    placed = [(tt, b) for tt, b in placed if tt is not None]
    if not placed:
        fail("aucun temps fort placé (mots introuvables)")
    placed[0] = (0.0, placed[0][1])
    shots, layers, titles, props, js, rep = [], [], [], [], [], []
    media_starts = []
    for tt, b in placed:  # un plan dure au moins 1,2 s : un média trop proche du précédent n'est pas montré
        if not b.get("media"):
            continue
        if media_starts and tt - media_starts[-1][0] < 1.2:
            rep.append({"media": b["media"], "pose": False, "raison": "trop près du plan précédent (moins de 1,2 s)"})
            continue
        media_starts.append((tt, b))
    if len(media_starts) > 1 and dur - media_starts[-1][0] < 1.2:
        rep.append({"media": media_starts.pop()[1]["media"], "pose": False, "raison": "dernier plan trop court"})
    beats = music_beats(job, a.slug)  # l'image change sur le temps de musique le plus proche (0,2 s au plus : les titres restent sur leurs mots)
    if beats:
        ms = [media_starts[0]]
        for tt_, b_ in media_starts[1:]:
            ms.append((round(snap_beat(tt_, beats, 0.2, lo=ms[-1][0] + 1.2), 3), b_))
        media_starts = ms
    for i, (tt, b) in enumerate(media_starts):
        t1 = media_starts[i + 1][0] if i + 1 < len(media_starts) else dur
        src = media_src(job, b["media"])
        if not src:
            rep.append({"media": b["media"], "pose": False, "raison": "introuvable"})
            continue
        d = round(t1 - tt, 3)
        sid = f"sh{i}"
        if src.lower().endswith((".mp4", ".mov", ".webm")):
            vd = probe(job / src).get("duration") or d
            if vd + 0.05 < d:
                rep.append({"media": src, "attention": f"vidéo de {vd:.1f} s pour un plan de {d:.1f} s : image figée à la fin"})
            shots.append(f'    <video id="{sid}" class="clip shot" src="{esc(src)}" data-start="{round(tt, 3)}" data-duration="{d}" '
                         f'data-track-index="{1 + i % 2}" muted playsinline></video>')
        else:
            shots.append(f'    <div id="{sid}" class="clip shot" data-start="{round(tt, 3)}" data-duration="{d}" data-track-index="{1 + i % 2}">'
                         f'<img src="{esc(src)}" alt=""></div>')
            js.append(f'  tl.fromTo("#{sid} img", {{ scale: 1.04, xPercent: {(-2, 2)[i % 2]} }}, {{ scale: 1.16, xPercent: {(2, -2)[i % 2]}, duration: {d}, ease: "none", immediateRender: false }}, {tt});')
        js.append(f'  tl.fromTo("#{sid}", {{ scale: 1.12 }}, {{ scale: 1, duration: 0.45, ease: "power3.out", immediateRender: false }}, {tt});')
        if i:
            js.append(f'  tl.fromTo("#flash", {{ opacity: 0.45 }}, {{ opacity: 0, duration: 0.14, immediateRender: false }}, {tt});')
        rep.append({"plan": i, "a": round(tt, 2), "duree": d, "media": src})

    for k, (tt, b) in enumerate(placed):
        t_next = placed[k + 1][0] if k + 1 < len(placed) else dur
        lines = b.get("title") or []
        if lines:
            tid = f"tt{k}"
            spans = []
            for j, ln in enumerate(lines):
                txt = ln if isinstance(ln, str) else ln.get("text", "")
                spans.append(f'<span class="ln l{j}">{title_html(txt)}</span>')
                lt = at(ln.get("word"), ln.get("occurrence", 1), None) if isinstance(ln, dict) else None
                lt = max(tt, lt) if lt is not None else tt + 0.12 * j
                js.append(f'  tl.fromTo("#{tid} .l{j}", {{ opacity: 0, scale: 1.7, y: -10 }}, {{ opacity: 1, scale: 1, y: 0, duration: 0.24, '
                          f'ease: "power4.out", immediateRender: false }}, {round(lt, 3)});')
                if "*" in txt:
                    js.append(f'  tl.fromTo("#burst", {{ opacity: 0.85, scale: 0.4 }}, {{ opacity: 0, scale: 1.5, duration: 0.4, ease: "power2.out", immediateRender: false }}, {round(lt + 0.04, 3)});')
            titles.append(f'    <div id="{tid}" class="clip ttls" data-start="{round(tt, 3)}" data-duration="{round(t_next - tt, 3)}" '
                          f'data-track-index="20">{"".join(spans)}</div>')
            js.append(f'  tl.to("#{tid} .ln", {{ opacity: 0, duration: 0.12 }}, {round(t_next - 0.12, 3)});')
        pr = b.get("prop")
        if pr:
            p0 = at(pr.get("word"), pr.get("occurrence", 1), None)
            p0 = max(tt, p0) if p0 is not None else tt + 0.3
            pid = f"pp{k}"
            y = float(pr.get("y", 52))
            if pr.get("type") == "lottie":
                lm = ROOT / "library" / "lottie" / str(pr.get("name", "")) / "lottie.json"
                if lm.exists() and "webm" in read_json(lm):
                    meta = read_json(lm)
                    (job / "assets" / "lottie").mkdir(parents=True, exist_ok=True)
                    shutil.copy2(lm.parent / meta["webm"], job / "assets" / "lottie" / meta["webm"])
                    add_credit(job, meta["credit"])
                    size = round(min(PW, H * 0.56) * float(pr.get("size", 40)) / 100 * (1.6 if wide else 1))
                    one = float(meta.get("rendered_duration") or meta.get("duration") or 1.5)
                    for r_ in range(max(1, math.ceil((t_next - p0) / one - 0.05))):
                        layers.append(f'    <video id="lo{k}_{r_}" class="clip" src="assets/lottie/{meta["webm"]}" data-start="{round(p0 + r_ * one, 3)}" '
                                      f'data-duration="{round(min(one, t_next - p0 - r_ * one), 3)}" data-track-index="{40 + k}" muted playsinline '
                                      f'style="position:absolute;left:{round(W * 0.73 - size / 2) if wide else (W - size) // 2}px;top:{round(H * (46 if wide else y) / 100) - size // 2}px;width:{size}px;height:{size}px;z-index:35"></video>')
                continue
            h = prop_html(pid, pr, u, acc)
            if h:
                props.append(f'    <div class="clip pwrap" data-start="{round(p0, 3)}" data-duration="{round(t_next - p0, 3)}" data-track-index="{30 + k % 3}" '
                             f'style="top:{round(H * (46 if wide else y) / 100)}px">{h}</div>')
                js += prop_js(pid, pr, round(p0, 3), t_next)

    caps, capjs, last = [], [], -99.0
    if not a.no_captions:
        tl_ = t
        if a.lang and (job / "work" / f"{a.slug}_text_{a.lang}.json").exists():
            tl_ = read_json(job / "work" / f"{a.slug}_text_{a.lang}.json")
        groups = tl_.get("captions", [])
        for i, g in enumerate(groups):
            st = round(max(0.05, g["words"][0]["start"] - 0.05), 3)
            nxt = groups[i + 1]["words"][0]["start"] - 0.05 if i + 1 < len(groups) else dur
            en = round(min(dur, max(g["end"] + 0.25, st + 0.4), nxt), 3)
            if en - st <= 0.1:
                continue
            spans, _, last = caption_spans(g["words"], "impact", False, st, last)
            caps.append(f'    <div class="clip cap" id="cap-{g["id"]}" data-start="{st}" data-duration="{round(en - st, 3)}" data-track-index="6"><div class="in">{spans}</div></div>')
            capjs.append(f'  cap("cap-{g["id"]}", {st}, {en}, {json.dumps([[round(max(st, w["start"]), 3), round(w["end"], 3)] for w in g["words"]])});')

    audio = [f'    <audio id="voice" class="clip" src="assets/{esc(voice)}" data-start="0" data-duration="{dur}" data-track-index="8" data-volume="1"></audio>']
    mu = job / "work" / f"{a.slug}_music.json"
    if mu.exists():
        audio.append(f'    <audio id="music" class="clip" src="{read_json(mu)["file"]}" data-start="0" data-duration="{dur}" data-track-index="9" data-volume="1"></audio>')
    cap_size = round(80 * u)
    wide_css = ""
    if wide:
        wide_css = (f"  .ttls {{ left: {round(W*0.05)}px; right: {round(W*0.5)}px; top: {round(H*0.1)}px; text-align: left; }}"
                    f"  .ttls .ln {{ font-size: {round(165*u)}px; }} .ttls .ln:first-child {{ font-size: {round(118*u)}px; }}"
                    f"  .pwrap {{ left: {round(W*0.5)}px; right: {round(W*0.04)}px; }}"
                    f"  #burst {{ left: 27%; }}"
                    f"  .cap {{ top: {round(H*0.8)}px; }} .cap .in {{ margin: 0 {round(W*0.12)}px; }}")
    doc = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<title>{esc(a.slug)}</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
<style>
  {' '.join(faces)}
  html, body {{ margin: 0; width: {W}px; height: {H}px; overflow: hidden; background: #000; }}
  #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; font-family: '{fam}', 'Inter', sans-serif; }}
  .shot {{ position: absolute; inset: 0; width: {W}px; height: {H}px; object-fit: cover; overflow: hidden; }}
  .shot img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
  .grad {{ position: absolute; inset: 0; z-index: 10; background: linear-gradient(180deg, rgba(0,0,0,.62) 0%, rgba(0,0,0,0) 34%, rgba(0,0,0,0) 62%, rgba(0,0,0,.55) 100%); }}
  #flash {{ position: absolute; inset: 0; background: #fff; opacity: 0; z-index: 60; }}
  #burst {{ position: absolute; left: 50%; top: {round(H*0.12)}px; width: {round(900*u)}px; height: {round(500*u)}px; margin-left: -{round(450*u)}px;
           background: radial-gradient(ellipse, rgba(255,255,255,.95) 0%, {acc}66 30%, transparent 65%); opacity: 0; z-index: 21; }}
  .ttls {{ position: absolute; left: {round(50*u)}px; right: {round(50*u)}px; top: {round(H*0.055)}px; z-index: 22; text-align: center;
          font-family: 'Anton', sans-serif; text-transform: uppercase; color: #fff; line-height: 1.04; }}
  .ttls .ln {{ display: block; line-height: 1.04; margin-bottom: {round(6*u)}px; font-size: {round(150*u)}px; opacity: 0; text-shadow: 0 {round(6*u)}px {round(30*u)}px rgba(0,0,0,.6); letter-spacing: .005em; }}
  .ttls .ln:first-child {{ font-size: {round(110*u)}px; }}
  .ttls .a {{ color: {acc}; }}
  .pwrap {{ position: absolute; left: 0; right: 0; z-index: 30; display: flex; justify-content: center; transform: translateY(-50%); }}
  .pp {{ opacity: 0; }}
  .notif {{ width: {round(PW*0.86 if wide else W*0.86)}px; background: rgba(246,246,248,.94); border-radius: {round(38*u)}px; padding: {round(26*u)}px {round(30*u)}px;
           box-shadow: 0 {round(20*u)}px {round(60*u)}px rgba(0,0,0,.45); color: #111; font-family: 'Inter', system-ui, sans-serif; }}
  .notif .nh {{ display: flex; align-items: center; gap: {round(16*u)}px; font-size: {round(30*u)}px; color: #555; }}
  .notif .nh b {{ color: #333; font-weight: 600; letter-spacing: .02em; text-transform: uppercase; font-size: {round(26*u)}px; }}
  .notif .nh em {{ margin-left: auto; font-style: normal; font-size: {round(26*u)}px; color: #888; }}
  .notif .ni {{ width: {round(58*u)}px; height: {round(58*u)}px; border-radius: {round(14*u)}px; background: {acc}; color: {on_acc}; display: flex;
              align-items: center; justify-content: center; }}
  .notif .ni svg {{ width: 60%; height: 60%; }}
  .notif .nt {{ margin-top: {round(14*u)}px; font-size: {round(42*u)}px; font-weight: 700; }}
  .notif .nx {{ margin-top: {round(4*u)}px; font-size: {round(36*u)}px; color: #333; }}
  .price {{ position: relative; background: {acc}; color: {on_acc}; padding: {round(34*u)}px {round(60*u)}px {round(30*u)}px {round(90*u)}px;
           border-radius: {round(26*u)}px; box-shadow: 0 {round(18*u)}px {round(50*u)}px rgba(0,0,0,.45); text-align: center; }}
  .price i {{ position: absolute; left: {round(30*u)}px; top: 50%; width: {round(30*u)}px; height: {round(30*u)}px; margin-top: -{round(15*u)}px;
             border-radius: 50%; background: rgba(0,0,0,.35); }}
  .price b {{ display: block; font-family: 'Anton', sans-serif; font-weight: 400; font-size: {round(190*u)}px; line-height: 1; }}
  .price span {{ display: block; font: 500 {round(32*u)}px 'IBM Plex Mono', monospace; letter-spacing: .12em; margin-top: {round(8*u)}px; }}
  .tagp {{ display: flex; align-items: center; gap: {round(24*u)}px; background: #fff; color: #111; border: {round(5*u)}px solid #111;
          padding: {round(22*u)}px {round(34*u)}px; border-radius: {round(12*u)}px; box-shadow: 0 {round(16*u)}px {round(40*u)}px rgba(0,0,0,.4); }}
  .tagp i {{ width: {round(70*u)}px; height: {round(80*u)}px; background: repeating-linear-gradient(90deg, #111 0 {round(4*u)}px, transparent {round(4*u)}px {round(8*u)}px); }}
  .tagp b {{ font-family: 'Anton', sans-serif; font-weight: 400; font-size: {round(76*u)}px; letter-spacing: .01em; text-transform: uppercase; }}
  .date {{ width: {round(300*u)}px; background: #fff; border-radius: {round(40*u)}px; overflow: hidden; text-align: center; color: #111;
          box-shadow: 0 {round(18*u)}px {round(50*u)}px rgba(0,0,0,.45); font-family: 'Inter', system-ui, sans-serif; }}
  .date span {{ display: block; background: #e53935; color: #fff; font-weight: 700; font-size: {round(46*u)}px; padding: {round(12*u)}px 0; }}
  .date b {{ display: block; font-weight: 300; font-size: {round(170*u)}px; line-height: 1.15; }}
  .doc {{ width: {round(PW*0.84 if wide else W*0.84)}px; background: #fbfbf8; color: #111; padding: {round(30*u)}px {round(36*u)}px; border-radius: {round(8*u)}px;
         box-shadow: 0 {round(18*u)}px {round(50*u)}px rgba(0,0,0,.45); font-family: 'Inter', system-ui, sans-serif; }}
  .doc .dh {{ font: 500 {round(22*u)}px 'IBM Plex Mono', monospace; letter-spacing: .12em; color: #666; border-bottom: 2px solid #111;
             padding-bottom: {round(10*u)}px; }}
  .doc .dt {{ font-size: {round(52*u)}px; font-weight: 800; margin: {round(14*u)}px 0 {round(6*u)}px; }}
  .doc .dl {{ font-size: {round(38*u)}px; font-weight: 600; min-height: 1.3em; }}
  .stat {{ text-align: center; color: #fff; text-shadow: 0 {round(8*u)}px {round(30*u)}px rgba(0,0,0,.6); }}
  .stat b {{ font-family: 'Anton', sans-serif; font-weight: 400; font-size: {round(260*u)}px; line-height: 1; }}
  .stat em {{ font-family: 'Anton', sans-serif; font-style: normal; font-size: {round(120*u)}px; color: {acc}; margin-left: {round(10*u)}px; }}
  .stat span {{ display: block; font: 500 {round(34*u)}px 'IBM Plex Mono', monospace; letter-spacing: .1em; text-transform: uppercase; }}
  .ico {{ text-align: center; color: #fff; }}
  .ico .ci {{ width: {round(260*u)}px; height: {round(260*u)}px; border-radius: 50%; margin: 0 auto; background: {acc}; color: {on_acc}; display: flex;
             align-items: center; justify-content: center; box-shadow: 0 {round(18*u)}px {round(60*u)}px rgba(0,0,0,.45); }}
  .ico .ci svg {{ width: 52%; height: 52%; }}
  .ico span {{ display: block; margin-top: {round(20*u)}px; font-family: 'Anton', sans-serif; font-size: {round(70*u)}px; text-transform: uppercase;
              text-shadow: 0 {round(6*u)}px {round(20*u)}px rgba(0,0,0,.6); }}
  .cap {{ position: absolute; left: 0; right: 0; top: {round(H*0.79)}px; z-index: 50; }}
  .cap .in {{ margin: 0 {round(W*0.08)}px; text-align: center; font-family: '{fam}', 'Inter', sans-serif; font-weight: 900; font-size: {cap_size}px;
             line-height: 1.08; color: #fff; text-shadow: {SHADOW}; text-transform: uppercase; }}
  .cap .w {{ display: inline-block; margin: 0 .07em; transform-origin: 50% 70%; }}
{caption_css("impact", acc)}
{wide_css}
</style>
</head>
<body>
  <div id="root" data-composition-id="punch" data-start="0" data-width="{W}" data-height="{H}" data-duration="{dur}">
{chr(10).join(shots)}
    <div class="grad"></div>
    <div id="burst"></div>
{chr(10).join(titles)}
{chr(10).join(props)}
{chr(10).join(layers)}
{chr(10).join(caps)}
    <div id="flash"></div>
{chr(10).join(audio)}
  </div>
<script>
  window.__timelines = window.__timelines || {{}};
  const tl = gsap.timeline({{ paused: true }});
  const INK = "#ffffff", ACCENT = {json.dumps(acc)}, BOXINK = {json.dumps(on_acc)};
{caption_js("impact")}
{chr(10).join(capjs)}
{chr(10).join(js)}
  window.__timelines["punch"] = tl;
</script>
</body>
</html>
"""
    (job / "index.html").write_text(doc, encoding="utf-8")
    if not getattr(a, "no_sfx", False):  # bruitages sur ce qui apparaît (sound_design.py ; "sfx": {"design": false} pour s'en passer)
        sound_design.auto(job)
    out(ok=True, format=f"{W}x{H}", duree=dur, plans=rep, titres=len(titles), objets=len(props) + len(layers), sous_titres=len(caps),
        suite="npx hyperframes check, puis snapshot")


def fetch(job_name, slug):
    import argparse as _a

    from broll import candidates, download, planche
    job = job_dir(job_name)
    pj = job / "work" / f"{slug}_punch.json"
    beats = read_json(pj)
    items, rep = [], []
    for i, b in enumerate(beats):
        if b.get("media") or not b.get("query"):
            continue
        alts = [x for x in candidates(job, b["query"], True, None, "tall") if float(x.get("duree") or 0) >= 3][:3]
        alts += candidates(job, b["query"], False, None, "tall")[:3]
        if not alts:
            rep.append({"temps_fort": i, "query": b["query"], "raison": "aucun résultat"})
            continue
        b["media"], _ = download(job, _a.Namespace(id=alts[0]["id"]))
        items.append({"beat": i, "query": b["query"], "phrase": " / ".join(x if isinstance(x, str) else x.get("text", "") for x in b.get("title", []))
                      or b.get("word", ""), "alts": [x["id"] for x in alts], "_alts": alts})
        rep.append({"temps_fort": i, "query": b["query"], "media": b["media"]})
    write_json(pj, beats)
    write_json(job / "work" / f"{slug}_punch_alts.json", [{k: v for k, v in it.items() if k != "_alts"} for it in items])
    pl = planche(job, items) if items else None
    out(ok=True, medias=rep, planche=str(pl) if pl else None, suite="regarde la planche ; build_punch.py pick <job> <slug> <n> a-f|none")


def pick(job_name, slug, n, choice):
    import argparse as _a

    from broll import download
    job = job_dir(job_name)
    pj, aj = job / "work" / f"{slug}_punch.json", job / "work" / f"{slug}_punch_alts.json"
    beats, alts = read_json(pj), read_json(aj)
    it = alts[int(n) - 1]
    b = beats[it["beat"]]
    if choice == "none":
        b.pop("media", None)
    else:
        b["media"], _ = download(job, _a.Namespace(id=it["alts"]["abcdef".index(choice)] if len(choice) == 1 else choice))
    write_json(pj, beats)
    out(ok=True, temps_fort=it["beat"], media=b.get("media"))


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == "fetch":
        return fetch(sys.argv[2], sys.argv[3])
    if len(sys.argv) >= 6 and sys.argv[1] == "pick":
        return pick(*sys.argv[2:6])
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--size")
    ap.add_argument("--no-captions", action="store_true")
    ap.add_argument("--lang", help="sous-titres traduits (translate.py apply) : nl, en…")
    build(ap.parse_args())


if __name__ == "__main__":
    main()
