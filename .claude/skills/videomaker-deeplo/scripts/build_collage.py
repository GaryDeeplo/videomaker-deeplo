"""COLLAGE ÉDITORIAL (motion design pur, sur musique, sans voix) -> <job>/index.html

Style « premium motion graphics » : papier crème vignetté (ou noir), titres en serif Didone (Bodoni Moda, OFL), UNE couleur
d'accent rouge-orange, objets photo détourés (Pixabay ou photos du client, détourage local), toutes petites silhouettes
pour l'échelle, mot surligné dans une étiquette (et échangé), formes d'accent (rayon, flèches, bande, disque), décor
éditorial (code-barres, trame, paragraphe minuscule). Une idée par écran ; écrans calés sur les temps de la musique.

  python build_collage.py <job> <slug> [--size 9:16]

work/<slug>_collage.json :
  {"accent": "#e2512f",
   "scenes": [
     {"dur": 2.6, "fond": "papier | creme | noir",
      "kicker": "too many", "titre": "*Time*", "titre2": "RETURNS", "anim": "mots | lettres", "pos": "haut | centre | bas",
      "etiquette": "Silent [Relentless]"  |  "Some [SPEND|WASTE] it"     ([A|B] : le mot change à mi-écran),
      "objet": {"query": "hourglass" | "image": "inbox/x.jpg", "x": 70, "y": 25, "w": 40, "rot": -10, "anim": "zoom | chute | glisse",
                "pieces": ["MEETINGS", "TASK", "DEADLINES"], "nb": false},
      "forme": "rayon | fleches | bande | disque", "gens": 3, "deco": ["codebarre", "trame", "texte"]}]}
x / y / w en % de l'image (centre de l'objet, largeur). "pieces" : l'objet se fend en morceaux reliés à leurs étiquettes.
Musique : add_music.py (même slug) ; sans musique, chaque écran dure "dur". Objets Pixabay : crédits dans renders/credits.txt.
"""
import argparse
import hashlib
import html
import json
import re
import shutil
import urllib.request
from pathlib import Path

from common import ROOT, add_credit, config, fail, job_dir, music_beats, out, read_json, size_of, snap_beat

esc = lambda s: html.escape(str(s), quote=True)
VENDOR = Path(__file__).resolve().parent.parent / "vendor" / "fonts"
FIG = {  # silhouettes (viewBox 0 0 20 56) : debout, qui marche
    "debout": "M6 11 Q10 9 14 11 L15 30 L13 30 L12.5 54 L10.8 54 L10 33 L9.2 54 L7.5 54 L7 30 L5 30 Z",
    "marche": "M6.5 11 Q10 9 13.5 11 L15 29 L13 29 L15.5 53 L13.6 54 L10 35 L7.2 54 L5.4 53 L7.2 29 L5 29 Z",
}
FONDS = {"papier": ("#e7dcc8", "#c9b99c", "#1a1714"), "creme": ("#ecead2", "#d2cfb0", "#1a1714"), "noir": ("#141210", "#050505", "#f2ece2")}


def fonts_css(job):
    (job / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    css = []
    for f, w, st in (("BodoniModa-700-normal.woff2", 700, "normal"), ("BodoniModa-700-italic.woff2", 700, "italic"), ("BodoniModa-400-italic.woff2", 400, "italic")):
        shutil.copy2(VENDOR / f, job / "assets" / "fonts" / f)
        css.append(f"@font-face {{ font-family: 'Bodoni Moda'; src: url('assets/fonts/{f}') format('woff2'); font-weight: {w}; font-style: {st}; }}")
    return " ".join(css)


def cutout_png(job, spec):
    """Objet détouré (PNG transparent) : photo du client ou première photo Pixabay de la recherche ; mis en cache."""
    from PIL import Image
    d = job / "assets" / "collage"
    d.mkdir(parents=True, exist_ok=True)
    key = hashlib.md5(json.dumps({k: spec.get(k) for k in ("image", "query", "n")}, sort_keys=True).encode()).hexdigest()[:10]
    dst = d / f"obj-{key}.png"
    if dst.exists():
        return f"assets/collage/{dst.name}"
    if spec.get("image"):
        src = next((b / spec["image"] for b in (job, job / "inbox", ROOT) if (b / spec["image"]).exists()), None)
        if not src:
            fail(f"image introuvable : {spec['image']}")
        img = Image.open(src)
    else:
        from broll import pixabay
        hits = pixabay("", {"q": spec["query"][:100], "image_type": "photo", "per_page": "10", "safesearch": "true"}).get("hits", [])
        if not hits:
            fail(f"Pixabay : rien pour « {spec['query']} »")
        h = hits[min(int(spec.get("n", 0)), len(hits) - 1)]
        tmp = d / f"src-{key}.jpg"
        req = urllib.request.Request(h.get("largeImageURL") or h["webformatURL"], headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            tmp.write_bytes(r.read())
        img = Image.open(tmp)
        add_credit(job, f"Image par {h.get('user') or 'auteur inconnu'} sur Pixabay — {h.get('pageURL', '')}")
    img = img.convert("RGBA")
    img.thumbnail((1400, 1400))
    if not (spec.get("image", "").lower().endswith(".png") and img.getextrema()[3][0] < 250):  # déjà transparent : gardé tel quel
        from rembg import new_session, remove
        img = remove(img, session=new_session(spec.get("model", "isnet-general-use")))
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    img.save(dst)
    return f"assets/collage/{dst.name}"


def barcode(seed, w, h):
    x, bars, k = 0, [], seed
    while x < w:
        k = (k * 1103515245 + 12345) & 0x7FFFFFFF
        bw = 2 + k % 6
        if (k >> 7) % 3:
            bars.append(f'<rect x="{x}" y="0" width="{bw}" height="{h}" />')
        x += bw + 2 + (k >> 3) % 4
    return f'<svg class="bc" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(bars)}</svg>'


def title_html(text, anim):
    """*mot* en italique ; anim lettres : chaque lettre dans son span (elles tombent en décalé)."""
    out_ = []
    for k, part in enumerate(re.split(r"(\*[^*]+\*)", text)):
        if not part:
            continue
        it = part.startswith("*")
        pre, post = (" " if part[:1] == " " else ""), (" " if part[-1:] == " " else "")
        part = part.strip("*").strip()
        if anim == "lettres":
            inner = "".join(f'<span class="ch">{esc(c) if c != " " else "&nbsp;"}</span>' for c in part)
        else:
            inner = " ".join(f'<span class="wd">{esc(w)}</span>' for w in part.split())
        out_.append(f'{pre}<span class="{"it" if it else "rm"}">{inner}</span>{post}')
    return "".join(out_)


def scene(job, sc, k, t0, d, W, H, acc):
    u = W / 1080
    bg, edge, ink = FONDS.get(sc.get("fond", "papier"), FONDS["papier"])
    sid, html_, js = f"sc{k}", [], []
    J = lambda s: js.append(s)
    pos = {"haut": 0.12, "centre": 0.4, "bas": 0.66}.get(sc.get("pos", "haut"), 0.12)
    # forme d'accent (derrière l'objet)
    forme = sc.get("forme")
    if forme == "rayon":
        cx, cy = W * 0.28, H * 0.82
        html_.append(f'<svg class="fm" width="{W}" height="{H}"><polygon class="ray" points="{cx - 90*u:.0f},{cy:.0f} {cx + 90*u:.0f},{cy:.0f} {W + 40},{H * 0.18:.0f} {W + 40},{H * 0.48:.0f}" />'
                     f'<ellipse class="dsk" cx="{cx:.0f}" cy="{cy:.0f}" rx="{150*u:.0f}" ry="{150*u:.0f}" /></svg>')
        J(f'  tl.fromTo("#{sid} .ray", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4, ease: "power2.out", immediateRender: false }}, {t0 + 0.15});')
        J(f'  tl.fromTo("#{sid} .dsk", {{ scale: 0, transformOrigin: "50% 50%" }}, {{ scale: 1, duration: 0.4, ease: "back.out(2)", immediateRender: false }}, {t0 + 0.05});')
        sc.setdefault("_fig", (cx, cy - 6 * u, 1.8))
    elif forme == "fleches":
        cx, cy = W / 2, H * 0.9
        a = 60 * u
        pts = (f"{cx - a:.0f},{H + 10} {cx - a * 0.45:.0f},{cy - 60*u:.0f} {cx - 210*u:.0f},{cy - 40*u:.0f} {cx - 210*u:.0f},{cy - 85*u:.0f} {cx - 300*u:.0f},{cy - 55*u:.0f} "
               f"{cx - 210*u:.0f},{cy - 25*u:.0f} {cx - 210*u:.0f},{cy - 10*u:.0f} {cx - a * 0.55:.0f},{cy - 30*u:.0f} "
               f"{cx + a * 0.55:.0f},{cy - 30*u:.0f} {cx + 210*u:.0f},{cy - 10*u:.0f} {cx + 210*u:.0f},{cy - 25*u:.0f} {cx + 300*u:.0f},{cy - 55*u:.0f} "
               f"{cx + 210*u:.0f},{cy - 85*u:.0f} {cx + 210*u:.0f},{cy - 40*u:.0f} {cx + a * 0.45:.0f},{cy - 60*u:.0f} {cx + a:.0f},{H + 10}")
        html_.append(f'<svg class="fm" width="{W}" height="{H}"><polygon class="arw" points="{pts}" /></svg>')
        J(f'  tl.fromTo("#{sid} .arw", {{ opacity: 0, scaleY: 0.3, transformOrigin: "50% 100%" }}, {{ opacity: 1, scaleY: 1, duration: 0.45, ease: "power3.out", immediateRender: false }}, {t0 + 0.1});')
        sc.setdefault("_fig", (cx, cy - 60 * u, 1.6))
    # objet détouré
    ob = sc.get("objet")
    if ob:
        src = cutout_png(job, ob)
        ow = W * float(ob.get("w", 50)) / 100
        ox, oy = W * float(ob.get("x", 50)) / 100, H * float(ob.get("y", 45)) / 100
        rot = float(ob.get("rot", 0))
        filt = "grayscale(1) contrast(1.1)" if ob.get("nb") else "none"
        st = f"left:{ox - ow / 2:.0f}px;top:{oy:.0f}px;width:{ow:.0f}px;transform:translateY(-50%) rotate({rot}deg);filter:{filt}"
        if forme == "disque":
            html_.append(f'<i class="disc" style="left:{ox - ow * 0.45:.0f}px;top:{oy - ow * 0.45:.0f}px;width:{ow * 0.9:.0f}px;height:{ow * 0.9:.0f}px"></i>')
            J(f'  tl.fromTo("#{sid} .disc", {{ scale: 0 }}, {{ scale: 1, duration: 0.45, ease: "back.out(1.8)", immediateRender: false }}, {t0 + 0.05});')
        pieces = ob.get("pieces") or []
        if pieces:  # l'objet se fend : 3 morceaux (haut-gauche, haut-droite, bas) qui s'écartent, reliés à leurs étiquettes
            clips = ["inset(0 50% 50% 0)", "inset(0 0 50% 50%)", "inset(50% 0 0 0)"]
            moves = [(-0.07, -0.05), (0.07, -0.05), (0, 0.07)]
            for j, (cp, (mx, my)) in enumerate(zip(clips, moves)):
                html_.append(f'<div class="obw" style="{st}"><div class="obi"><img class="ob pc{j}" src="{src}" style="clip-path:{cp}" alt=""></div></div>')
                J(f'  tl.fromTo("#{sid} .pc{j}", {{ x: 0, y: 0 }}, {{ x: {ow * mx:.0f}, y: {ow * my:.0f}, duration: 0.5, ease: "power3.out", immediateRender: false }}, {t0 + 0.45});')
            labs = [(ox - ow * 0.55, oy - ow * 0.45, "end"), (ox + ow * 0.55, oy - ow * 0.45, "start"), (ox, oy + ow * 0.62, "middle")]
            anchors = [(ox - ow * 0.25, oy - ow * 0.2), (ox + ow * 0.25, oy - ow * 0.2), (ox, oy + ow * 0.3)]
            svg = []
            for j, (name, (lx, ly, an), (ax, ay)) in enumerate(zip(pieces[:3], labs, anchors)):
                svg.append(f'<line class="pl pl{j}" x1="{ax:.0f}" y1="{ay:.0f}" x2="{lx:.0f}" y2="{ly + (14*u if j < 2 else -40*u):.0f}" pathLength="100" />'
                           f'<text class="plt plt{j}" x="{lx:.0f}" y="{ly:.0f}" text-anchor="{an}">{esc(name)}</text>')
                tj = round(t0 + 0.7 + j * min(0.35, d * 0.15), 3)
                J(f'  tl.fromTo("#{sid} .pl{j}", {{ attr: {{ "stroke-dashoffset": 100 }} }}, {{ attr: {{ "stroke-dashoffset": 0 }}, duration: 0.3, immediateRender: true }}, {tj});')
                J(f'  tl.fromTo("#{sid} .plt{j}", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.25, immediateRender: false }}, {round(tj + 0.15, 3)});')
            html_.append(f'<svg class="fm top" width="{W}" height="{H}">{"".join(svg)}</svg>')
        else:
            html_.append(f'<div class="obw" style="{st}"><div class="obi"><img class="ob" src="{src}" alt=""></div></div>')
            if forme == "bande":  # une bande d'accent coupe l'objet, l'objet y passe en rouge
                html_.append(f'<div class="obw band" style="{st.replace(filt, "none")}"><div class="obi"><img class="ob" src="{src}" alt=""></div></div>')
                J(f'  tl.fromTo("#{sid} .band", {{ clipPath: "polygon(38% -10%, 38% -10%, 22% 110%, 22% 110%)" }}, '
                  f'{{ clipPath: "polygon(38% -10%, 62% -10%, 46% 110%, 22% 110%)", duration: 0.45, ease: "power3.inOut", immediateRender: false }}, {t0 + 0.5});')
        an = ob.get("anim", "zoom")
        frm = {"zoom": "scale: 1.25, opacity: 0", "chute": "y: -260, rotation: -14, opacity: 0", "glisse": "x: 260, opacity: 0"}.get(an, "scale: 1.25, opacity: 0")
        J(f'  tl.fromTo("#{sid} .obi", {{ {frm} }}, {{ scale: 1, x: 0, y: 0, rotation: 0, opacity: 1, duration: 0.55, ease: "power3.out", immediateRender: false }}, {t0 + 0.05});')
        if not pieces:  # lent travelling avant pendant l'écran
            J(f'  tl.fromTo("#{sid} .ob", {{ scale: 1 }}, {{ scale: 1.05, duration: {round(d, 3)}, ease: "none", immediateRender: false }}, {t0});')
    # silhouettes : une sur la forme (rayon / flèches), d'autres éparpillées
    figs = []
    if sc.get("_fig"):
        figs.append(sc["_fig"])
    zone = (0.62, 0.9) if pos < 0.3 else (0.1, 0.3)  # les silhouettes évitent le titre
    for j in range(int(sc.get("gens", 0))):
        figs.append((W * (0.14 + ((j * 37) % 72) / 100), H * (zone[0] + (zone[1] - zone[0]) * ((j * 23) % 30) / 30), 1.0 + (j % 3) * 0.15))
    for j, (fx, fy, sc_) in enumerate(figs):
        hh = 56 * u * sc_
        kind = "marche" if j % 2 else "debout"
        html_.append(f'<svg class="fig f{j}" width="{hh * 20 / 56:.0f}" height="{hh:.0f}" viewBox="0 0 20 56" style="left:{fx - hh * 10 / 56:.0f}px;top:{fy - hh:.0f}px">'
                     f'<ellipse cx="13" cy="54.5" rx="7" ry="1.6" class="sh" /><circle cx="10" cy="5" r="3.6" /><path d="{FIG[kind]}" /></svg>')
    if figs:
        J(f'  tl.fromTo("#{sid} .fig", {{ opacity: 0, y: 8 }}, {{ opacity: 1, y: 0, duration: 0.3, stagger: 0.08, ease: "power2.out", immediateRender: false }}, {t0 + 0.3});')
    # décor éditorial
    for dd in sc.get("deco", []):
        if dd == "codebarre":
            html_.append(f'<div class="dc bcw">{barcode(k * 97 + 13, round(150*u), round(46*u))}</div>')
        elif dd == "trame":
            html_.append('<div class="dc trame"></div>')
        elif dd == "texte":
            html_.append('<div class="dc para">Time is primarily measured in linear spans or periods, ordered from shortest to longest. '
                         'Practical, human-scale measurements are performed using clocks and calendars.</div>' if sc.get("lang") == "en" else
                         '<div class="dc para">Le temps se mesure en durées ordonnées de la plus courte à la plus longue. À l\'échelle humaine, '
                         'on le compte avec des horloges et des calendriers, jour après jour.</div>')
    if sc.get("deco"):
        J(f'  tl.fromTo("#{sid} .dc", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4, stagger: 0.1, immediateRender: false }}, {t0 + 0.2});')
    # texte
    anim = sc.get("anim", "mots")
    txt = []
    if sc.get("kicker"):
        txt.append(f'<div class="kk">{esc(sc["kicker"])}</div>')
    if sc.get("titre") and anim != "lettres" or sc.get("titre"):
        txt.append(f'<div class="tt">{title_html(sc["titre"], anim)}</div>')
    if sc.get("titre2"):
        txt.append(f'<div class="tt t2">{title_html(sc["titre2"], "mots")}</div>')
    et = sc.get("etiquette")
    if et:
        m = re.match(r"(.*)\[([^\]]+)\](.*)", et)
        if m:
            words = m.group(2).split("|")
            tags = "".join(f'<b class="tg g{j}">{esc(w)}</b>' for j, w in enumerate(words))
            txt.append(f'<div class="et">{esc(m.group(1))}<span class="tgw">{tags}<b class="tg sz">{esc(max(words, key=len))}</b></span>{esc(m.group(3))}</div>')
        else:
            txt.append(f'<div class="et">{esc(et)}</div>')
    if txt:
        html_.append(f'<div class="tx" style="top:{H * pos:.0f}px">{"".join(txt)}</div>')
        if sc.get("kicker"):
            J(f'  tl.fromTo("#{sid} .kk", {{ opacity: 0, y: 10 }}, {{ opacity: 1, y: 0, duration: 0.3, immediateRender: false }}, {t0 + 0.1});')
        if anim == "lettres" and sc.get("titre"):
            J(f'  tl.fromTo("#{sid} .tt:not(.t2) .ch", {{ opacity: 0, y: -90, rotation: -12 }}, {{ opacity: 1, y: 0, rotation: 0, duration: 0.45, stagger: 0.07, '
              f'ease: "bounce.out", immediateRender: false }}, {t0 + 0.15});')
        elif sc.get("titre"):
            J(f'  tl.fromTo("#{sid} .tt:not(.t2) .wd", {{ opacity: 0, y: 30, filter: "blur(8px)" }}, {{ opacity: 1, y: 0, filter: "blur(0px)", duration: 0.4, '
              f'stagger: 0.16, ease: "power3.out", immediateRender: false }}, {t0 + 0.15});')
        if sc.get("titre2"):
            J(f'  tl.fromTo("#{sid} .t2 .wd", {{ opacity: 0, y: 24 }}, {{ opacity: 1, y: 0, duration: 0.35, stagger: 0.12, ease: "power3.out", immediateRender: false }}, '
              f'{round(t0 + d * 0.45, 3)});')
        if et:
            J(f'  tl.fromTo("#{sid} .et", {{ opacity: 0, x: -20 }}, {{ opacity: 1, x: 0, duration: 0.35, ease: "power2.out", immediateRender: false }}, {t0 + 0.45});')
        if et and "[" in et:
            J(f'  tl.fromTo("#{sid} .g0", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.3, ease: "power3.out", immediateRender: false }}, {t0 + 0.55});')
        if et and "|" in et:  # le mot de l'étiquette change à mi-écran
            ts = round(t0 + d * 0.55, 3)
            J(f'  tl.to("#{sid} .g0", {{ y: -40, opacity: 0, duration: 0.2, ease: "power2.in" }}, {ts});')
            J(f'  tl.fromTo("#{sid} .g1", {{ y: 40, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.25, ease: "back.out(2)", immediateRender: false }}, {round(ts + 0.15, 3)});')
    return (f'    <div class="clip sc" id="{sid}" data-start="{round(t0, 3)}" data-duration="{round(d, 3)}" data-track-index="{2 + k % 2}" '
            f'style="--bg:{bg};--edge:{edge};--ink:{ink}"><div class="pp"></div>' + "".join(html_) + '</div>'), js


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("slug")
    ap.add_argument("--size")
    a = ap.parse_args()
    job = job_dir(a.job)
    c = config(job)
    W, H = size_of(a.size, c["visual"])
    u = W / 1080
    cj = job / "work" / f"{a.slug}_collage.json"
    if not cj.exists():
        fail(f"{cj} absent (voir l'en-tête de build_collage.py)")
    spec = read_json(cj)
    acc = spec.get("accent", "#e2512f")
    scenes = spec.get("scenes", [])
    if not scenes:
        fail("aucune scène")
    beats = music_beats(job, a.slug)
    starts, t = [], 0.0
    for sc in scenes:
        starts.append(round(t, 3))
        t += float(sc.get("dur", 2.6))
        if beats:
            t = snap_beat(t, beats, 0.3, lo=starts[-1] + 1.0)
    total = round(t, 3)
    nodes, js = [], []
    for k, (sc, t0) in enumerate(zip(scenes, starts)):
        d = (starts[k + 1] if k + 1 < len(starts) else total) - t0
        n_, j_ = scene(job, dict(sc), k, t0, d, W, H, acc)
        nodes.append(n_)
        js += j_
    audio = ""
    mj = job / "work" / f"{a.slug}_music.json"
    if mj.exists():
        audio = f'    <audio id="music" class="clip" src="{read_json(mj)["file"]}" data-start="0" data-duration="{total}" data-track-index="9" data-volume="1"></audio>'
    noise = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'>"
             "<feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2' stitchTiles='stitch'/></filter>"
             "<rect width='100%' height='100%' filter='url(%23n)' opacity='.5'/></svg>")
    doc = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<title>{esc(a.slug)}</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
<style>
  {fonts_css(job)}
  html, body {{ margin: 0; width: {W}px; height: {H}px; overflow: hidden; background: #000; }}
  #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; font-family: 'Inter', sans-serif; }}
  .sc {{ position: absolute; inset: 0; overflow: hidden; color: var(--ink); }}
  .pp {{ position: absolute; inset: 0; background: radial-gradient(ellipse 75% 65% at 50% 45%, var(--bg) 0%, var(--bg) 45%, var(--edge) 100%); }}
  .pp::after {{ content: ""; position: absolute; inset: 0; background-image: url("{noise}"); opacity: .16; mix-blend-mode: multiply; }}
  .fm {{ position: absolute; left: 0; top: 0; overflow: visible; }}
  .fm.top {{ z-index: 6; }}
  .ray, .arw, .dsk {{ fill: {acc}; }}
  .disc {{ position: absolute; border-radius: 50%; background: {acc}; }}
  .obw {{ position: absolute; z-index: 3; }}
  .ob {{ display: block; width: 100%; filter: drop-shadow(0 {round(24*u)}px {round(30*u)}px rgba(0,0,0,.35)); }}
  .band {{ z-index: 4; clip-path: polygon(38% -10%, 62% -10%, 46% 110%, 22% 110%); }}
  .band .ob {{ filter: grayscale(1) sepia(1) saturate(7) hue-rotate(-18deg) brightness(.95); }}
  .pl {{ stroke: {acc}; stroke-width: {max(2, round(2.5*u))}; stroke-dasharray: 100; }}
  .plt {{ font: 700 {round(40*u)}px 'Bodoni Moda', Georgia, serif; fill: var(--ink); letter-spacing: .02em; }}
  .fig {{ position: absolute; z-index: 5; fill: #0d0c0b; overflow: visible; }}
  .fig .sh {{ fill: rgba(0,0,0,.28); }}
  .dc {{ position: absolute; z-index: 2; opacity: 0; }}
  .bcw {{ left: {round(50*u)}px; top: {round(40*u)}px; }}
  .bc rect {{ fill: var(--ink); }}
  .trame {{ left: {round(W * 0.22)}px; top: {round(H * 0.3)}px; width: {round(W * 0.56)}px; height: {round(H * 0.2)}px;
           background-image: radial-gradient(circle, rgba(0,0,0,.22) 1.4px, transparent 1.6px); background-size: {round(34*u)}px {round(34*u)}px; }}
  .para {{ left: {round(W * 0.2)}px; right: {round(W * 0.2)}px; bottom: {round(H * 0.18)}px; font-size: {round(17*u)}px; line-height: 1.35; font-weight: 600; opacity: .75; }}
  .tx {{ position: absolute; left: {round(60*u)}px; right: {round(60*u)}px; z-index: 7; text-align: center; }}
  .kk {{ font: italic 400 {round(54*u)}px 'Bodoni Moda', Georgia, serif; opacity: 0; }}
  .tt {{ font: 700 {round(160*u)}px 'Bodoni Moda', Georgia, serif; line-height: .95; letter-spacing: -.01em; }}
  .tt .it {{ font-style: italic; }}
  .tt .wd, .tt .ch {{ display: inline-block; }}
  .tt.t2 {{ margin-top: {round(8*u)}px; font-size: {round(96*u)}px; color: {acc}; letter-spacing: .08em; }}
  .et {{ margin-top: {round(18*u)}px; font: 600 {round(44*u)}px 'Bodoni Moda', Georgia, serif; opacity: 0; }}
  .tgw {{ position: relative; display: inline-grid; margin: 0 .25em; vertical-align: middle; }}
  .tg {{ grid-area: 1 / 1; padding: .02em .35em .08em; background: {acc}; color: #fff; font: 600 {round(38*u)}px 'IBM Plex Mono', monospace; letter-spacing: .04em;
        transform-origin: 0 50%; }}
  .tg.g1 {{ opacity: 0; }}
  .tg.sz {{ visibility: hidden; }}
</style>
</head>
<body>
  <div id="root" data-composition-id="collage" data-start="0" data-width="{W}" data-height="{H}" data-duration="{total}">
{chr(10).join(nodes)}
{audio}
  </div>
<script>
  window.__timelines = window.__timelines || {{}};
  const tl = gsap.timeline({{ paused: true }});
{chr(10).join(js)}
  window.__timelines["collage"] = tl;
</script>
</body>
</html>
"""
    import panel as pn
    doc = doc.replace("<style>\n", "<style>\n  " + pn.fonts(job) + "\n", 1)
    (job / "index.html").write_text(doc, encoding="utf-8")
    out(ok=True, format=f"{W}x{H}", duree=total, ecrans=len(scenes), musique=bool(audio), sur_les_temps=bool(beats),
        suite="npx hyperframes check, puis snapshot (un par écran) ; objets Pixabay : crédits dans renders/credits.txt")


if __name__ == "__main__":
    main()
