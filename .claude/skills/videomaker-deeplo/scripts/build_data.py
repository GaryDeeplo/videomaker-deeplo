"""PACK « INFOGRAPHIE CHIFFRÉE » -> <job>/index.html : vidéo sans visage façon page de journal de données. Fond papier,
rubrique en haut (« VUES PAR REEL · JOUR 03 ») sous un double filet, un graphique par idée, la phrase dite en bas qui se
colore au fil des mots (mot fort dans une boîte), frise des jours avec drapeau en bas.

  python build_data.py <job> <slug> [--size 9:16] [--no-outro]

Avant : storyboard (voix off) -> voice.py -> build_text.py -> add_music.py ; puis work/<slug>_data.json :
  {"days": {"count": 14, "label": "Reels d'essai"},          (facultatif : frise J1…J14 et « JOUR 03 » en haut)
   "beats": [ chaque temps fort posé sur un MOT dit, visible jusqu'au suivant ; "head" (rubrique) et "day" restent
              acquis tant qu'un temps fort suivant ne les change pas :
     {"word": "…", "head": "Vues par reel", "day": 1, "type": "bars", "unit": "vues",
      "items": [{"label": "…", "value": 1612, "sub": "…", "icon": "smartphone"}, …], "highlight": 1}
     {"type": "grid",   "value": "×10", "sub": "par jour", "count": 10, "icon": "smartphone"}
     {"type": "people", "count": 72, "dark": 18, "pill": "votre produit", "icon": "heart"}
     {"type": "flip",   "to": 100000, "label": "vues", "stamp": "Conseil de pro"}
     {"type": "line",   "points": [120, 150, 900, 1100, 1818], "steps": true, "label": "1 818 vues / jour",
      "xlabels": ["J1", "J4", "J7", "J10", "J12"], "notes": [[2, "version 2"], [3, "version 3"]]}
     {"type": "pct",    "items": [{"label": "…", "value": 18, "icon": "…"}, …], "highlight": 1}
     {"type": "days",   "count": 7, "stamp": "7 jours d'essai gratuit"}
     {"type": "title",  "text": "Ce que ça *change* vraiment"}
     {"type": "end",    "name": "Martin", "url": "boulangerie-martin.be", "sub": "Voici le lien :", "logo": true}
   ]}
Chiffres, pourcentages, courbes : uniquement des données réelles du client (ou présentées comme un exemple, dit à
l'oral). Accent : visual.dataAccent (sinon l'accent de la charte s'il est vif, sinon rouge).
"""
import argparse
import html
import json
import re
import shutil
from pathlib import Path

import panel as pn
from build_punch import vivid
from common import ROOT, block_file, brand_info, config, fail, job_dir, mount, out, read_json, size_of, word_hit

esc = lambda s: html.escape(str(s), quote=True)
TYPES = ("bars", "grid", "people", "flip", "line", "pct", "days", "title", "end")


def fmt(v):
    v = float(v)
    s = f"{v:,.0f}" if v == int(v) else f"{v:,.1f}"
    return s.replace(",", " ").replace(".", ",")


def beat_html(job, b, sid, s0, d, sw, sh, u, C, vis):
    """-> (html, js) d'un temps fort ; coordonnées de la scène (sw × sh)."""
    typ = b.get("type", "title")
    js = []
    T = lambda x: round(s0 + x, 3)
    if typ == "bars":
        items = b.get("items", [])[:5]
        hi = b.get("highlight")
        mx = max([float(it.get("value", 0)) for it in items] or [1]) or 1
        rh = min(round(170 * u), round(sh * 0.9 / max(1, len(items))))
        shades = [C["ink"], C["grey"], C["ink"], C["grey2"], C["ink"]]
        rows = []
        for j, it in enumerate(items):
            col = C["acc"] if j == hi else shades[j % len(shades)]
            wpx = round(sw * 0.46 * float(it.get("value", 0)) / mx)
            ic = pn.icon(it["icon"]) if it.get("icon") else ""
            rows.append(f'<div class="brow b{j}" style="top:{round(sh * 0.06) + j * rh}px;height:{rh}px">'
                        f'<i class="bbar" style="width:{max(8, wpx)}px;background:{col}"></i>'
                        + (f'<span class="bic">{ic}</span>' if ic else "")
                        + f'<span class="bval"><b class="n{j}">0</b> <small>{esc(b.get("unit", ""))}</small>'
                        f'<em>{esc(pn.glue(it.get("label", "")))}</em>' + (f'<em class="s">{esc(pn.glue(it["sub"]))}</em>' if it.get("sub") else "")
                        + '</span></div>')
            tj = T(0.15 + j * 0.16)
            js.append(f'  tl.fromTo("#{sid} .b{j} .bbar", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.7, ease: "power3.out", immediateRender: false }}, {tj});')
            js.append(f'  tl.fromTo("#{sid} .b{j} .bval", {{ opacity: 0, x: -20 }}, {{ opacity: 1, x: 0, duration: 0.4, ease: "power2.out", immediateRender: false }}, {round(tj + 0.2, 3)});')
            js.append(count_js(f"#{sid} .n{j}", float(it.get("value", 0)), round(tj + 0.15, 3), 0.9))
        return "".join(rows), js
    if typ == "grid":
        n = max(1, min(15, int(b.get("count", 10))))
        cols = 5
        ic = pn.icon(b.get("icon", "smartphone"))
        tiles = "".join(f'<i class="tile t{j}">{ic}</i>' for j in range(n))
        h = (f'<div class="gbig"><span>{esc(b.get("value", ""))}</span>' + (f'<small>{esc(b["sub"])}</small>' if b.get("sub") else "") + '</div>'
             f'<div class="tiles" style="grid-template-columns:repeat({cols},1fr)">{tiles}</div>')
        js.append(f'  tl.fromTo("#{sid} .gbig", {{ opacity: 0, scale: 0.6 }}, {{ opacity: 1, scale: 1, duration: 0.5, ease: "back.out(2.2)", immediateRender: false }}, {T(0.05)});')
        js.append(f'  tl.fromTo("#{sid} .tile", {{ opacity: 0, y: -40, scale: 0.6 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.4, ease: "back.out(2.4)", '
                  f'stagger: {round(min(0.12, (d * 0.5) / n), 3)}, immediateRender: false }}, {T(0.35)});')
        return h, js
    if typ == "people":
        n = max(12, min(120, int(b.get("count", 72))))
        dark = set(range(0, n, max(1, round(n / max(1, int(b.get("dark", 0)) or 1))))) if b.get("dark") else set()
        ppl = "".join(f'<i class="pp{" dk" if j in dark else ""}"></i>' for j in range(n))
        pill = (f'<div class="pill">' + (f'<span class="pic">{pn.icon(b["icon"])}</span>' if b.get("icon") else "")
                + f'{esc(b["pill"])}</div>') if b.get("pill") else ""
        h = f'<div class="crowd">{ppl}</div>{pill}'
        js.append(f'  tl.fromTo("#{sid} .pp", {{ opacity: 0, y: 14 }}, {{ opacity: 1, y: 0, duration: 0.3, ease: "power2.out", '
                  f'stagger: {round(min(0.02, (d * 0.4) / n), 4)}, immediateRender: false }}, {T(0.1)});')
        if dark:
            js.append(f'  tl.fromTo("#{sid} .pp.dk", {{ backgroundColor: "{C["grey2"]}" }}, {{ backgroundColor: "{C["ink"]}", duration: 0.3, stagger: 0.03, '
                      f'immediateRender: false }}, {T(min(d * 0.45, 1.6))});')
        if pill:
            js.append(f'  tl.fromTo("#{sid} .pill", {{ opacity: 0, scale: 0.5 }}, {{ opacity: 1, scale: 1, duration: 0.45, ease: "back.out(2.4)", '
                      f'immediateRender: false }}, {T(min(d * 0.55, 2.0))});')
        return h, js
    if typ == "flip":
        to = int(float(b.get("to", 0)))
        digits = f"{to:,}".replace(",", " ")
        cells = "".join('<i class="gap"></i>' if ch == " " else f'<i class="dg d{k}">0</i>' for k, ch in enumerate(digits))
        h = ((f'<div class="stampx">{esc(b["stamp"])}</div>' if b.get("stamp") else "")
             + f'<div class="flip">{cells}</div>' + (f'<div class="flbl">{esc(pn.glue(b["label"]))}</div>' if b.get("label") else ""))
        ndig = len(digits.replace(" ", ""))
        tf = round(max(0.8, min(2.0, d * 0.5)), 2)
        js.append(f'  tl.fromTo("#{sid} .flip", {{ opacity: 0, y: 30 }}, {{ opacity: 1, y: 0, duration: 0.4, ease: "power3.out", immediateRender: false }}, {T(0.05)});')
        js.append(f'  (function () {{ const ds = document.querySelectorAll("#{sid} .dg"), o = {{ v: 0 }};'
                  f' tl.fromTo(o, {{ v: 0 }}, {{ v: {to}, duration: {tf}, ease: "power2.inOut", immediateRender: false, onUpdate: function () {{'
                  f' const s = String(Math.round(o.v)).padStart({ndig}, "0"); ds.forEach(function (e, i) {{ e.textContent = s[i]; }}); }} }}, {T(0.35)}); }})();')
        js.append(f'  tl.to("#{sid} .dg", {{ backgroundColor: "{C["acc"]}", duration: 0.25, stagger: 0.04 }}, {T(0.4 + tf)});')
        if b.get("stamp"):
            js.append(f'  tl.fromTo("#{sid} .stampx", {{ opacity: 0, scale: 2, rotation: -14 }}, {{ opacity: 1, scale: 1, rotation: -4, duration: 0.35, '
                      f'ease: "back.out(2)", immediateRender: false }}, {T(0.15)});')
        if b.get("label"):
            js.append(f'  tl.fromTo("#{sid} .flbl", {{ opacity: 0, y: 16 }}, {{ opacity: 1, y: 0, duration: 0.4, immediateRender: false }}, {T(0.6)});')
        return h, js
    if typ == "line":
        pts = [float(x) for x in b.get("points", [])][:12] or [0, 1]
        top_v = max(pts) * 1.15 or 1
        cw, ch = sw - round(110 * u), round(sh * 0.66)
        x0, y0 = round(100 * u), round(sh * 0.12)
        X = lambda i: x0 + cw * i / max(1, len(pts) - 1)
        Y = lambda v: y0 + ch - ch * v / top_v
        if b.get("steps"):
            path = f"M {X(0):.0f} {Y(pts[0]):.0f}" + "".join(f" H {X(i):.0f} V {Y(v):.0f}" for i, v in enumerate(pts) if i)
        else:
            path = "M " + " L ".join(f"{X(i):.0f} {Y(v):.0f}" for i, v in enumerate(pts))
        grid = "".join(f'<line x1="{x0}" x2="{x0 + cw}" y1="{Y(top_v * k / 3):.0f}" y2="{Y(top_v * k / 3):.0f}" class="gl" />'
                       f'<text x="{x0 - round(14*u)}" y="{Y(top_v * k / 3) + round(8*u):.0f}" class="gt" text-anchor="end">{fmt(round(top_v * k / 3, -1) if top_v > 50 else top_v * k / 3)}</text>'
                       for k in range(0, 4))
        xl = "".join(f'<text x="{X(i * (len(pts) - 1) / max(1, len(b["xlabels"]) - 1)):.0f}" y="{y0 + ch + round(44*u)}" class="gt" text-anchor="middle">{esc(t)}</text>'
                     for i, t in enumerate(b.get("xlabels", [])))
        notes = "".join(f'<g class="note2 m{k}"><rect x="{X(i) - round(70*u):.0f}" y="{Y(pts[i]) - round(66*u):.0f}" width="{round(140*u)}" height="{round(40*u)}" rx="{round(8*u)}" />'
                        f'<text x="{X(i):.0f}" y="{Y(pts[i]) - round(38*u):.0f}" text-anchor="middle">{esc(t)}</text></g>'
                        for k, (i, t) in enumerate(b.get("notes", [])) if 0 <= int(i) < len(pts))
        ex, ey = X(len(pts) - 1), Y(pts[-1])
        h = (f'<svg class="chart" width="{sw}" height="{sh}" viewBox="0 0 {sw} {sh}">{grid}{xl}'
             f'<path class="ln" d="{path}" pathLength="1000" />{notes}<circle class="dot" cx="{ex:.0f}" cy="{ey:.0f}" r="{round(14*u)}" /></svg>'
             + (f'<div class="lbl2" style="right:{round(30*u)}px;top:{max(0, round(ey - 130 * u))}px">{esc(pn.glue(b["label"]))}</div>' if b.get("label") else ""))
        tl_ = round(max(1.0, min(2.4, d * 0.6)), 2)
        js.append(f'  tl.fromTo("#{sid} .ln", {{ attr: {{ "stroke-dashoffset": 1000 }} }}, {{ attr: {{ "stroke-dashoffset": 0 }}, duration: {tl_}, ease: "power1.inOut", '
                  f'immediateRender: true }}, {T(0.2)});')
        js.append(f'  tl.fromTo("#{sid} .dot", {{ opacity: 0, scale: 0 }}, {{ opacity: 1, scale: 1, transformOrigin: "50% 50%", duration: 0.3, ease: "back.out(3)", '
                  f'immediateRender: false }}, {T(0.2 + tl_)});')
        for k, (i, t) in enumerate(b.get("notes", [])):
            js.append(f'  tl.fromTo("#{sid} .m{k}", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.25, immediateRender: false }}, '
                      f'{T(0.2 + tl_ * int(i) / max(1, len(pts) - 1))});')
        if b.get("label"):
            js.append(f'  tl.fromTo("#{sid} .lbl2", {{ opacity: 0, y: 16 }}, {{ opacity: 1, y: 0, duration: 0.4, ease: "back.out(2)", immediateRender: false }}, {T(0.3 + tl_)});')
        return h, js
    if typ == "pct":
        items = b.get("items", [])[:5]
        hi = b.get("highlight")
        rh = min(round(170 * u), round(sh * 0.9 / max(1, len(items))))
        rows = []
        for j, it in enumerate(items):
            v = float(it.get("value", 0))
            col = C["acc"] if j == hi else C["ink"]
            ic = pn.icon(it["icon"]) if it.get("icon") else ""
            rows.append(f'<div class="prow r{j}" style="top:{round(sh * 0.06) + j * rh}px">'
                        + (f'<span class="bic">{ic}</span>' if ic else "")
                        + f'<div class="pin"><em>{esc(pn.glue(it.get("label", "")))}</em><div class="pl"><i class="pb" style="width:{round(sw * 0.42 * v / 100)}px;background:{col}"></i>'
                        f'<b class="pv{" hi" if j == hi else ""}"><span class="n{j}">0</span> %</b></div></div></div>')
            tj = T(0.15 + j * 0.15)
            js.append(f'  tl.fromTo("#{sid} .r{j}", {{ opacity: 0, x: -24 }}, {{ opacity: 1, x: 0, duration: 0.35, ease: "power2.out", immediateRender: false }}, {tj});')
            js.append(f'  tl.fromTo("#{sid} .r{j} .pb", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.6, ease: "power3.out", immediateRender: false }}, {round(tj + 0.1, 3)});')
            js.append(count_js(f"#{sid} .n{j}", v, round(tj + 0.1, 3), 0.6))
        h = "".join(rows)
        if hi is not None and 0 <= int(hi) < len(items):
            js.append(f'  tl.fromTo("#{sid} .pv.hi", {{ "--ring": 0 }}, {{ "--ring": 1, duration: 0.4, ease: "power2.out", immediateRender: false }}, {T(min(d * 0.55, 1.8))});')
            js.append(f'  tl.fromTo("#{sid} .pv.hi", {{ scale: 1 }}, {{ scale: 1.15, duration: 0.18, yoyo: true, repeat: 1, immediateRender: false }}, {T(min(d * 0.55, 1.8))});')
        return h, js
    if typ == "days":
        n = max(1, min(7, int(b.get("count", 7))))
        boxes = "".join(f'<div class="dbx x{j}"><i>✓</i><span>J{j + 1}</span></div>' for j in range(n))
        h = (f'<div class="drow">{boxes}</div>' + (f'<div class="stampx s2">{esc(b["stamp"])}</div>' if b.get("stamp") else ""))
        js.append(f'  tl.fromTo("#{sid} .dbx", {{ opacity: 0, y: 20 }}, {{ opacity: 1, y: 0, duration: 0.3, stagger: 0.06, immediateRender: false }}, {T(0.1)});')
        span = max(0.06, min(0.25, (d * 0.55 - 0.6) / n))
        js.append(f'  tl.fromTo("#{sid} .dbx i", {{ scale: 0 }}, {{ scale: 1, duration: 0.25, ease: "back.out(3)", stagger: {round(span, 3)}, immediateRender: false }}, {T(0.6)});')
        if b.get("stamp"):
            js.append(f'  tl.fromTo("#{sid} .stampx", {{ opacity: 0, scale: 2, rotation: -14 }}, {{ opacity: 1, scale: 1, rotation: -3, duration: 0.35, '
                      f'ease: "back.out(2)", immediateRender: false }}, {T(0.6 + span * n)});')
        return h, js
    if typ == "end":
        logo = ""
        if b.get("logo") and vis.get("logo"):
            lp = ROOT / vis["logo"]
            (job / "assets" / "img").mkdir(parents=True, exist_ok=True)
            shutil.copy2(lp, job / "assets" / "img" / lp.name)
            logo = f'<img class="elogo" src="assets/img/{lp.name}" alt="">'
        h = (f'<div class="endb">{logo}<div class="ename">{esc(b.get("name", ""))}</div>'
             + (f'<div class="ebub">' + (f'<small>{esc(b["sub"])}</small>' if b.get("sub") else "") + f'<b>{esc(b["url"])}</b></div>' if b.get("url") else "")
             + '</div>')
        js.append(f'  tl.fromTo("#{sid} .elogo", {{ opacity: 0, y: -30 }}, {{ opacity: 1, y: 0, duration: 0.5, ease: "back.out(2)", immediateRender: false }}, {T(0.05)});')
        js.append(f'  tl.fromTo("#{sid} .ename", {{ opacity: 0, scale: 0.7 }}, {{ opacity: 1, scale: 1, duration: 0.5, ease: "back.out(2.2)", immediateRender: false }}, {T(0.2)});')
        js.append(f'  tl.fromTo("#{sid} .ebub", {{ opacity: 0, y: 30, scale: 0.9 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.45, ease: "back.out(2)", immediateRender: false }}, {T(0.6)});')
        return h, js
    # title
    parts = re.split(r"(\*[^*]+\*)", pn.glue(b.get("text", "")))
    inner = "".join(f'<span class="hlw">{esc(p.strip("*"))}</span>' if p.startswith("*") else esc(p) for p in parts)
    js.append(f'  tl.fromTo("#{sid} .tt", {{ opacity: 0, y: 30 }}, {{ opacity: 1, y: 0, duration: 0.5, ease: "power3.out", immediateRender: false }}, {T(0.05)});')
    js.append(f'  tl.fromTo("#{sid} .hlw", {{ backgroundSize: "0% 100%" }}, {{ backgroundSize: "100% 100%", duration: 0.45, ease: "power2.out", immediateRender: false }}, {T(0.45)});')
    return f'<div class="tt">{inner}</div>', js


def count_js(sel, v, at, dur):
    dec = 1 if v % 1 else 0
    return (f'  (function () {{ const el = document.querySelector("{sel}"), o = {{ v: 0 }};'
            f' tl.fromTo(o, {{ v: 0 }}, {{ v: {v}, duration: {dur}, ease: "power2.out", immediateRender: false,'
            f' onUpdate: function () {{ el.textContent = o.v.toLocaleString("fr-FR", {{ minimumFractionDigits: {dec}, maximumFractionDigits: {dec} }}); }} }}, {at}); }})();')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--size")
    ap.add_argument("--no-outro", action="store_true")
    a = ap.parse_args()
    job = job_dir(a.job)
    c = config(job)
    vis = c["visual"]
    W, H = size_of(a.size, vis)
    u = W / 1080
    mj, tj, dj = (job / "work" / f"{a.slug}_{x}.json" for x in ("map", "text", "data"))
    for p in (mj, tj, dj):
        if not p.exists():
            fail(f"{p.name} absent (voice.py, build_text.py, puis work/<slug>_data.json : voir l'aide de build_data.py)")
    m, t, data = read_json(mj), read_json(tj), read_json(dj)
    dur = float(m["out_duration"])
    voice = Path(m["cut"]).name
    fam = vis["fontFamily"]

    bg = vis.get("bgColor", "#f2ede4")
    if pn._lum(bg) < 170:
        bg = "#f2ede4"
    ink = vis.get("inkColor", "#151515")
    if pn._lum(ink) > 90:
        ink = "#151515"
    acc = vis.get("dataAccent") or (vis.get("accentColor") if vivid(vis.get("accentColor", "#000000")) else "#d62f2f")
    if pn._contrast(acc, "#ffffff") < 3.2:
        acc = pn._mix(acc, ink, 0.3)
    C = {"ink": ink, "acc": acc, "bg": bg, "grey": pn._mix(ink, bg, 0.5), "grey2": pn._mix(ink, bg, 0.72), "mute": pn._mix(ink, bg, 0.32)}

    faces = []
    for f in vis.get("fonts", []):
        ff = ROOT / f["file"] if not Path(f["file"]).is_absolute() else Path(f["file"])
        (job / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
        shutil.copy2(ff, job / "assets" / "fonts" / ff.name)
        faces.append(f"@font-face {{ font-family: '{fam}'; src: url('assets/fonts/{ff.name}'); font-weight: {f.get('weight', 400)}; }}")
    if vis.get("fontFile"):
        ff = ROOT / vis["fontFile"] if not Path(vis["fontFile"]).is_absolute() else Path(vis["fontFile"])
        (job / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
        shutil.copy2(ff, job / "assets" / "fonts" / ff.name)
        faces.append(f"@font-face {{ font-family: '{fam}'; src: url('assets/fonts/{ff.name}'); font-weight: 100 900; }}")
    faces.append(pn.fonts(job))

    # géométrie
    mx = round(72 * u)
    sw = W - 2 * mx
    rule_y, head_y = round(H * 0.105), round(H * 0.118)
    st_y, st_h = round(H * 0.17), round(H * 0.50)
    cap_y = round(H * 0.69)
    days = data.get("days") or {}
    nd = int(days.get("count", 0))
    tl_y = round(H * 0.86)

    words = [w for g in t.get("captions", []) for w in g["words"]]
    placed = []
    for b in data.get("beats", []):
        hit = word_hit(words, b.get("word", ""), b.get("occurrence", 1)) if b.get("word") else None
        if hit is None and b.get("word"):
            continue
        placed.append((max(0.0, hit["start"] - 0.12) if hit else 0.0, b))
    placed.sort(key=lambda x: x[0])
    if not placed:
        fail("aucun temps fort posé (mots introuvables ?)")
    placed[0] = (0.0, placed[0][1])

    stage, js, rep = [], [], []
    head, day = "", None
    heads = []
    for k, (t0, b) in enumerate(placed):
        t1 = placed[k + 1][0] if k + 1 < len(placed) else dur
        if t1 - t0 < 0.4:
            continue
        typ = b.get("type", "title")
        if typ not in TYPES:
            rep.append({"type": typ, "pose": False, "raison": "type inconnu"})
            continue
        s0, d = round(t0, 3), round(t1 - t0, 3)
        sid = f"db{k}"
        inner, bj = beat_html(job, b, sid, s0, d, sw, st_h, u, C, vis)
        stage.append(f'      <div class="clip beat t-{typ}" id="{sid}" data-start="{s0}" data-duration="{d}" data-track-index="{20 + k % 2}">{inner}</div>')
        js.append(f'  tl.fromTo("#{sid}", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.2, immediateRender: false }}, {s0});')
        js += bj
        if k + 1 < len(placed):
            js.append(f'  tl.to("#{sid}", {{ opacity: 0, y: -14, duration: 0.2, ease: "power2.in" }}, {round(t1 - 0.2, 3)});')
        if b.get("head"):
            head = b["head"]
        if b.get("day") is not None:
            day = int(b["day"])
        if not heads or heads[-1]["head"] != head or heads[-1]["day"] != day:
            heads.append({"head": head, "day": day, "t0": s0, "t1": t1})
        else:
            heads[-1]["t1"] = t1
        rep.append({"type": typ, "a": s0, "duree": d, "mot": b.get("word")})

    # rubrique + jour (un élément par changement)
    hh = []
    for i, h_ in enumerate(heads):
        hd = round(h_["t1"] - h_["t0"], 3)
        dtxt = f'{days.get("word", "Jour").upper()} {h_["day"]:02d}' if (h_["day"] is not None and nd) else ""
        hh.append(f'      <div class="clip hd" id="hd{i}" data-start="{h_["t0"]}" data-duration="{hd}" data-track-index="{10 + i % 2}">'
                  f'<span class="hl">{esc(h_["head"])}</span><span class="hr">{esc(dtxt)}</span></div>')
        js.append(f'  tl.fromTo("#hd{i} span", {{ opacity: 0, y: 10 }}, {{ opacity: 1, y: 0, duration: 0.3, stagger: 0.06, immediateRender: false }}, {h_["t0"]});')
        if i + 1 < len(heads):
            js.append(f'  tl.to("#hd{i} span", {{ opacity: 0, duration: 0.15 }}, {round(h_["t1"] - 0.15, 3)});')

    # frise des jours : graduations, trait de progression, drapeau au jour en cours
    frise = ""
    if nd:
        fw = W - 2 * mx
        ticks = "".join(f'<i class="tk" style="left:{round(fw * j / max(1, nd - 1))}px"></i>'
                        + (f'<span class="tkl" style="left:{round(fw * j / max(1, nd - 1))}px">J{j + 1}</span>' if j % max(1, nd // 7) == 0 or j == nd - 1 else "")
                        for j in range(nd))
        frise = (f'<div class="frise"><i class="fl0"></i><i class="fl1"></i>{ticks}<i class="flag"></i>'
                 f'<span class="fll">{esc(days.get("label", ""))}</span><span class="flr"></span></div>')
        prev = None
        for h_ in heads:
            if h_["day"] is None or h_["day"] == prev:
                continue
            x = round(fw * (h_["day"] - 1) / max(1, nd - 1))
            js.append(f'  tl.to(".frise .flag", {{ x: {x}, duration: 0.5, ease: "power2.inOut" }}, {h_["t0"]});')
            js.append(f'  tl.to(".frise .fl1", {{ scaleX: {round((h_["day"] - 1) / max(1, nd - 1), 4)}, duration: 0.5, ease: "power2.inOut" }}, {h_["t0"]});')
            js.append(f'  (function () {{ const el = document.querySelector(".frise .flr"), o = {{ v: 0 }}; tl.fromTo(o, {{ v: 0 }}, {{ v: 1, duration: 0.01, '
                      f'immediateRender: false, onUpdate: function () {{ el.textContent = "{days.get("word", "Jour")} {h_["day"]} sur {nd}"; }} }}, {h_["t0"]}); }})();')
            prev = h_["day"]

    # phrase dite : morceau de phrase entier, mots qui passent du gris à l'encre, mot fort en boîte
    caps, capjs = [], []
    groups = [o for o in t.get("overlays", []) if o.get("words")] or [{"words": g["words"], "start": g["start"], "end": g["end"]} for g in t.get("captions", [])]
    for i, g in enumerate(groups):
        ws = g["words"]
        st = round(max(0.0, ws[0]["start"] - 0.08), 3)
        nxt = groups[i + 1]["words"][0]["start"] - 0.08 if i + 1 < len(groups) else dur
        en = round(min(dur, nxt), 3)
        if en - st < 0.2:
            continue
        keys = [j for j, w in enumerate(ws) if re.search(r"\d", w["w"])]
        if not keys:
            from pack import strong
            keys = [strong(ws)]
        spans = " ".join(f'<span class="cw{" ck" if j in keys else ""}">{esc(pn.glue(w["w"]))}</span>' for j, w in enumerate(ws))
        caps.append(f'      <div class="clip cp" id="cp{i}" data-start="{st}" data-duration="{round(en - st, 3)}" data-track-index="30">{spans}</div>')
        times = [round(max(st, w.get("start", st)), 3) for w in ws]
        capjs.append(f'  say("cp{i}", {st}, {json.dumps(times)});')

    audio = [f'    <audio id="voice" class="clip" src="assets/{esc(voice)}" data-start="0" data-duration="{dur}" data-track-index="8" data-volume="1"></audio>']
    mu = job / "work" / f"{a.slug}_music.json"
    if mu.exists():
        audio.append(f'    <audio id="music" class="clip" src="{read_json(mu)["file"]}" data-start="0" data-duration="{dur}" '
                     f'data-track-index="9" data-volume="1"></audio>')
    total, outro = dur, ""
    br = c.get("branding", {})
    if br.get("outro") and not a.no_outro:
        block_file(job, br["outro"])
        od = float(br.get("outroDuration", 3.4))
        brand = brand_info(job)
        logo = ""
        if vis.get("logo"):
            lp = ROOT / vis["logo"]
            (job / "assets" / "img").mkdir(parents=True, exist_ok=True)
            shutil.copy2(lp, job / "assets" / "img" / lp.name)
            logo = f"assets/img/{lp.name}"
        outro = mount(br["outro"], "brand-outro", dur, od, W, H, 22,
                      {"logo": logo, "bg": vis.get("bgColor", "#f6f4f0"), "ink": vis.get("inkColor", "#1a1a1a"), "accent": vis["accentColor"],
                       "font": fam, "blend": vis.get("logoBlend", "normal"), "tagline": brand.get("tagline", ""),
                       "info": (brand.get("contact") or {}).get("site", "")}, z=200)
        total = round(dur + od, 3)

    mono = "'IBM Plex Mono', monospace"
    noise = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'>"
             "<feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2' stitchTiles='stitch'/></filter>"
             "<rect width='100%' height='100%' filter='url(%23n)' opacity='.5'/></svg>")
    G = lambda x: round(x * u)
    doc = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<title>{esc(a.slug)}</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
<style>
  {' '.join(faces)}
  html, body {{ margin: 0; padding: 0; width: {W}px; height: {H}px; overflow: hidden; background: {bg}; }}
  #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; font-family: '{fam}', 'Inter', sans-serif; color: {ink};
          background: radial-gradient(ellipse 90% 70% at 50% 40%, {pn._mix(bg, '#ffffff', 0.35)} 0%, {bg} 70%); }}
  .grain {{ position: absolute; inset: 0; background-image: url("{noise}"); opacity: .07; mix-blend-mode: multiply; }}
  .rule {{ position: absolute; left: {mx}px; right: {mx}px; top: {rule_y}px; height: {G(5)}px; background: {ink}; }}
  .rule::after {{ content: ""; position: absolute; left: 0; right: 0; top: {G(11)}px; height: {max(1, G(2))}px; background: {ink}; }}
  .hd {{ position: absolute; left: {mx}px; right: {mx}px; top: {head_y + G(14)}px; display: flex; justify-content: space-between;
        font: 700 {G(28)}px {mono}; letter-spacing: .1em; text-transform: uppercase; }}
  .hd .hl {{ color: {acc}; }}
  .stage {{ position: absolute; left: {mx}px; top: {st_y}px; width: {sw}px; height: {st_h}px; }}
  .beat {{ position: absolute; inset: 0; opacity: 0; }}
  .brow {{ position: absolute; left: 0; right: 0; display: flex; align-items: center; gap: {G(20)}px; }}
  .bbar {{ display: block; height: {G(74)}px; transform-origin: 0 50%; flex: 0 0 auto; }}
  .bic {{ flex: 0 0 auto; width: {G(64)}px; height: {G(84)}px; border-radius: {G(12)}px; background: {ink}; color: {bg}; display: flex;
         align-items: center; justify-content: center; }}
  .bic svg {{ width: 55%; height: 55%; }}
  .bval {{ display: flex; flex-direction: column; line-height: 1.05; }}
  .bval b {{ font-size: {G(58)}px; font-weight: 800; font-variant-numeric: tabular-nums; }}
  .bval small {{ display: none; }}
  .bval em {{ font-style: normal; font-size: {G(30)}px; font-weight: 700; }}
  .bval em.s {{ font: 500 {G(24)}px {mono}; color: {C["mute"]}; }}
  .gbig {{ text-align: left; margin-top: {G(10)}px; color: {acc}; font-weight: 800; font-size: {G(170)}px; line-height: 1; }}
  .gbig small {{ display: inline-block; margin-left: {G(16)}px; vertical-align: middle; font-size: {G(40)}px; color: {ink}; padding: {G(6)}px {G(16)}px;
               border: {G(3)}px solid {ink}; border-radius: {G(10)}px; background: #fff; }}
  .tiles {{ display: grid; gap: {G(26)}px {G(30)}px; margin-top: {G(50)}px; }}
  .tile {{ display: flex; align-items: center; justify-content: center; height: {G(150)}px; border-radius: {G(16)}px; background: {ink}; color: {bg};
          box-shadow: 0 {G(6)}px 0 {acc}; }}
  .tile svg {{ width: 46%; height: 46%; }}
  .crowd {{ display: grid; grid-template-columns: repeat(12, 1fr); gap: {G(18)}px {G(10)}px; margin-top: {G(40)}px; }}
  .pp {{ position: relative; height: {G(62)}px; display: block; background: {C["grey2"]}; border-radius: {G(30)}px {G(30)}px {G(8)}px {G(8)}px;
        -webkit-mask: radial-gradient(circle at 50% {G(14)}px, #000 {G(12)}px, transparent {G(13)}px) top / 100% {G(28)}px no-repeat,
                      linear-gradient(#000, #000) bottom / 100% {G(30)}px no-repeat; }}
  .pp.dk {{ background: {C["grey2"]}; }}
  .pill {{ position: absolute; left: 50%; top: 42%; transform: translate(-50%, -50%); display: flex; align-items: center; gap: {G(14)}px; padding: {G(16)}px {G(30)}px;
          border: {G(4)}px solid {acc}; border-radius: 99px; background: #fff; font-size: {G(46)}px; font-weight: 800; white-space: nowrap;
          box-shadow: 0 {G(16)}px {G(40)}px rgba(0,0,0,.15); }}
  .pill .pic {{ width: {G(44)}px; height: {G(44)}px; color: {acc}; display: inline-flex; }}
  .flip {{ display: flex; justify-content: center; gap: {G(14)}px; margin-top: {G(150)}px; }}
  .dg {{ display: flex; align-items: center; justify-content: center; width: {G(120)}px; height: {G(170)}px; border-radius: {G(14)}px; background: {ink};
        color: #fff; font: 700 {G(120)}px {mono}; font-style: normal; box-shadow: inset 0 -{G(85)}px 0 rgba(255,255,255,.06); }}
  .gap {{ width: {G(26)}px; }}
  .flbl {{ text-align: center; margin-top: {G(40)}px; font-size: {G(56)}px; font-weight: 800; }}
  .stampx {{ position: absolute; left: 0; top: {G(20)}px; padding: {G(6)}px {G(20)}px; border: {G(5)}px solid {acc}; color: {acc}; border-radius: {G(8)}px;
            font-weight: 900; font-size: {G(50)}px; text-transform: uppercase; background: #fff; }}
  .stampx.s2 {{ top: auto; bottom: {G(160)}px; left: {G(20)}px; }}
  .chart {{ position: absolute; left: 0; top: 0; overflow: visible; }}
  .chart .gl {{ stroke: {ink}22; stroke-width: {max(1, G(2))}; }}
  .chart .gt {{ font: 500 {G(24)}px {mono}; fill: {C["mute"]}; }}
  .chart .ln {{ fill: none; stroke: {ink}; stroke-width: {G(7)}; stroke-linejoin: round; stroke-linecap: round; stroke-dasharray: 1000; }}
  .chart .dot {{ fill: {acc}; }}
  .note2 rect {{ fill: #fff; stroke: {ink}; stroke-width: {max(1, G(2))}; }}
  .note2 text {{ font: 600 {G(22)}px {mono}; fill: {ink}; }}
  .lbl2 {{ position: absolute; font-size: {G(60)}px; font-weight: 800; color: {acc}; white-space: nowrap; }}
  .prow {{ position: absolute; left: 0; right: 0; display: flex; align-items: center; gap: {G(20)}px; }}
  .pin em {{ display: block; font-style: normal; font-size: {G(28)}px; font-weight: 700; margin-bottom: {G(8)}px; }}
  .pl {{ display: flex; align-items: center; gap: {G(18)}px; }}
  .pb {{ display: block; height: {G(46)}px; transform-origin: 0 50%; }}
  .pv {{ position: relative; font-size: {G(56)}px; font-weight: 800; font-variant-numeric: tabular-nums; --ring: 0; }}
  .pv.hi {{ color: {acc}; }}
  .pv.hi::after {{ content: ""; position: absolute; left: -22%; right: -22%; top: -30%; bottom: -30%; border: {G(5)}px solid {acc}; border-radius: 50%;
                  opacity: var(--ring); transform: rotate(-6deg) scale(calc(.6 + var(--ring) * .4)); }}
  .drow {{ display: flex; justify-content: center; gap: {G(16)}px; margin-top: {G(260)}px; }}
  .dbx {{ position: relative; width: {G(112)}px; height: {G(112)}px; border: {G(4)}px solid {ink}; border-radius: {G(10)}px; background: #fff; }}
  .dbx i {{ position: absolute; inset: -{G(4)}px; border-radius: {G(10)}px; background: #1f9d55; color: #fff; display: flex; align-items: center;
           justify-content: center; font-style: normal; font-size: {G(64)}px; font-weight: 900; transform: scale(0); }}
  .dbx span {{ position: absolute; left: 0; right: 0; top: 112%; text-align: center; font: 500 {G(22)}px {mono}; color: {C["mute"]}; }}
  .tt {{ position: absolute; left: 0; right: 0; top: 30%; font-size: {G(104)}px; font-weight: 800; line-height: 1.05; letter-spacing: -.02em; text-wrap: balance; }}
  .hlw {{ color: #fff; padding: 0 .12em; background: linear-gradient({acc}, {acc}) no-repeat 0 0 / 0% 100%; box-decoration-break: clone;
         -webkit-box-decoration-break: clone; }}
  .endb {{ position: absolute; left: 0; right: 0; top: 10%; text-align: center; }}
  .elogo {{ max-width: {G(360)}px; max-height: {G(200)}px; object-fit: contain; mix-blend-mode: {vis.get("logoBlend", "normal")}; }}
  .ename {{ margin-top: {G(20)}px; font-size: {G(170)}px; font-weight: 900; color: {acc}; letter-spacing: -.02em; line-height: 1; text-transform: uppercase; }}
  .ebub {{ display: inline-block; margin-top: {G(70)}px; padding: {G(24)}px {G(40)}px; border: {G(4)}px solid {ink}; border-radius: {G(36)}px {G(36)}px {G(36)}px {G(8)}px;
          background: #fff; text-align: left; box-shadow: 0 {G(18)}px {G(40)}px rgba(0,0,0,.12); }}
  .ebub small {{ display: block; font-size: {G(30)}px; color: {C["mute"]}; }}
  .ebub b {{ font-size: {G(56)}px; }}
  .cp {{ position: absolute; left: {mx}px; right: {mx}px; top: {cap_y}px; font-size: {G(58)}px; font-weight: 800; line-height: 1.22; letter-spacing: -.01em;
        z-index: 40; opacity: 0; }}
  .cw {{ color: {C["grey2"]}; }}
  .cw.on {{ color: {ink}; }}
  .cw.ck.on {{ color: #fff; background: {ink}; padding: 0 .14em; }}
  .frise {{ position: absolute; left: {mx}px; right: {mx}px; top: {tl_y}px; height: {G(120)}px; }}
  .frise .fl0 {{ position: absolute; left: 0; right: 0; top: {G(40)}px; height: {max(1, G(3))}px; background: {ink}55; }}
  .frise .fl1 {{ position: absolute; left: 0; right: 0; top: {G(39)}px; height: {G(5)}px; background: {acc}; transform-origin: 0 50%; }}
  .frise .tk {{ position: absolute; top: {G(32)}px; width: {max(1, G(3))}px; height: {G(20)}px; background: {ink}88; }}
  .frise .tkl {{ position: absolute; top: {G(62)}px; transform: translateX(-50%); font: 500 {G(20)}px {mono}; color: {C["mute"]}; }}
  .frise .flag {{ position: absolute; left: 0; top: -{G(6)}px; width: {max(2, G(4))}px; height: {G(50)}px; background: {acc}; }}
  .frise .flag::after {{ content: ""; position: absolute; left: {max(2, G(4))}px; top: 0; border-left: {G(30)}px solid {acc}; border-top: {G(11)}px solid transparent;
                        border-bottom: {G(11)}px solid transparent; }}
  .frise .fll, .frise .flr {{ position: absolute; top: {G(100)}px; font: 500 {G(20)}px {mono}; color: {C["mute"]}; }}
  .frise .flr {{ right: 0; }}
</style>
</head>
<body>
  <div id="root" data-composition-id="data" data-start="0" data-width="{W}" data-height="{H}" data-duration="{total}">
    <div class="grain"></div>
    <div class="rule"></div>
{chr(10).join(hh)}
    <div class="stage">
{chr(10).join(stage)}
    </div>
{chr(10).join(caps)}
    {frise}
{chr(10).join(audio)}
{outro}
  </div>
<script>
  window.__timelines = window.__timelines || {{}};
  const tl = gsap.timeline({{ paused: true }});
  function say(id, st, ts) {{
    const g = "#" + id, ws = document.querySelectorAll(g + " .cw");
    tl.fromTo(g, {{ opacity: 0, y: 12 }}, {{ opacity: 1, y: 0, duration: 0.2, ease: "power2.out", immediateRender: false }}, st);
    ts.forEach(function (t, i) {{
      const o = {{ v: 0 }};
      tl.fromTo(o, {{ v: 0 }}, {{ v: 1, duration: 0.01, immediateRender: false, onUpdate: function () {{ ws[i].classList.toggle("on", o.v > 0.5); }} }}, t);
    }});
  }}
{chr(10).join(capjs)}
{chr(10).join(js)}
  gsap.set(".frise .fl1", {{ scaleX: 0 }});
  tl.fromTo(".rule", {{ scaleX: 0 }}, {{ scaleX: 1, transformOrigin: "0 50%", duration: 0.6, ease: "power3.out", immediateRender: false }}, 0);
  window.__timelines["data"] = tl;
</script>
</body>
</html>
"""
    (job / "index.html").write_text(doc, encoding="utf-8")
    out(ok=True, format=f"{W}x{H}", duree=total, temps_forts=rep, rubriques=len(heads), phrases=len(caps),
        suite="npx hyperframes check, puis snapshot")


if __name__ == "__main__":
    main()
