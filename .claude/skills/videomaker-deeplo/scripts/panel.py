"""PANNEAU D'ANIMATION de la mise en page « écran partagé » (layout split) : animation en haut, visage en bas,
sous-titres sur la jointure.

Temps forts (work/<slug>_panels.json), chacun posé sur un MOT dit (jamais un timecode), visible jusqu'au suivant :
  {"type": "title",  "word": "…", "text": "Vos photos ne *vendent* pas", "tag": "LE PROBLÈME", "flash": false, "mark": true}
  {"type": "check",  "word": "…", "title": "Ce qu'on vérifie", "items": ["…", "…", "…"], "stamp": "VALIDÉ", "tag": "…"}
  {"type": "stat",   "word": "…", "value": 1200, "prefix": "+", "suffix": "", "label": "clientes servies", "tag": "…"}
  {"type": "search", "word": "…", "query": "fleuriste lyon", "results": ["Fleurs & Co · 4,9 ★", "…"], "tag": "…"}
  {"type": "image",  "word": "…", "image": "inbox/x.jpg | assets/broll/…", "caption": "…", "tag": "…"}
  {"type": "steps",  "word": "…", "items": ["Réservez", "Venez", "Repartez"], "tag": "…"}
  {"type": "icons",  "word": "…", "title": "…", "items": [{"icon": "clock", "label": "1 h"}, {"icon": "heart", "label": "…"}]}
Visuels en plus :
  - pictos Lucide (licence ISC, lucide.dev/icons) : "icon" sur un titre, items {"text": "…", "icon": "nom"} dans check / steps ;
  - "image" : photo OU vidéo (client, site, Pixabay) dans un cadre ; "query": "1-2 mots anglais" sans "image" ->
    panel.py fetch la cherche sur Pixabay (planche de choix, panel.py pick) ;
  - "lottie": {"name": "valide", "x": 78, "y": 72, "size": 26} sur n'importe quel temps fort : emoji animé (library/lottie)
    posé dans la scène (x / y en % de la scène, taille en % de sa largeur).
*mot* = mot fort en italique serif. Chiffres, avis, résultats : uniquement des données réelles du client.
Sans fichier : un temps fort « title » par phrase forte (overlays gardés de text.json).

  python panel.py suggest <job> <slug>     # squelette work/<slug>_panels_suggested.json (une entrée par phrase)
  python panel.py fetch   <job> <slug>     # temps forts "image" avec "query" : Pixabay -> planche work/broll/planche.jpg
  python panel.py pick    <job> <slug> <n> <a-f|none>
"""
import html
import json
import re
import shutil
import sys
from pathlib import Path

from common import ROOT, job_dir, out, read_json, word_hit, write_json

VENDOR = ROOT / ".claude" / "skills" / "videomaker-deeplo" / "vendor" / "fonts"
LUCIDE = ROOT / ".claude" / "skills" / "videomaker-deeplo" / "vendor" / "lucide"


def icon(name):
    """Picto Lucide en SVG inline (téléchargé une fois depuis le paquet npm lucide-static, gardé dans vendor/lucide)."""
    name = re.sub(r"[^a-z0-9-]", "", str(name).lower())
    if not name:
        return ""
    f = LUCIDE / f"{name}.svg"
    if not f.exists():
        import urllib.request
        try:
            with urllib.request.urlopen(f"https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/{name}.svg", timeout=20) as r:
                LUCIDE.mkdir(parents=True, exist_ok=True)
                f.write_bytes(r.read())
        except Exception:  # noqa: BLE001 — picto inconnu : on s'en passe
            return ""
    svg = re.sub(r"<!--.*?-->", "", f.read_text(encoding="utf-8"), flags=re.S).strip()
    return re.sub(r'\swidth="24"\s+height="24"', ' width="100%" height="100%"', svg, count=1)


def item_text(it):
    return it.get("text") or it.get("label") or "" if isinstance(it, dict) else str(it)


def item_icon(it):
    return icon(it.get("icon")) if isinstance(it, dict) and it.get("icon") else ""


def media_box(W, ph, theme):
    """Intérieur du cadre « image » (mêmes valeurs que le CSS), pour poser une vidéo hors du temps fort minuté."""
    u = W / 1080
    if theme == "paper":
        l, t, b, bw, rad = round(110 * u), round(ph * 0.12), round(ph * 0.16), max(2, round(3 * u)), round(10 * u)
    else:
        l, t, b, bw, rad = round(110 * u), round(120 * u), round(ph * 0.14), 2, round(24 * u)
    return l + bw, t + bw, W - 2 * l - 2 * bw, ph - t - b - 2 * bw, max(0, rad - bw)


def esc(s):
    return html.escape(str(s), quote=True)


def _hex(c):
    c = c.lstrip("#")
    return [int(c[i:i + 2], 16) for i in (0, 2, 4)] if len(c) == 6 else [128, 128, 128]


def _mix(a, b, t):
    pa, pb = _hex(a), _hex(b)
    return "#" + "".join(f"{round(pa[i] * (1 - t) + pb[i] * t):02x}" for i in range(3))


def _lum(c):
    r, g, b = _hex(c)
    return 0.299 * r + 0.587 * g + 0.114 * b


def _contrast(a, b):
    def rl(c):
        v = [x / 255 for x in _hex(c)]
        v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
        return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]
    la, lb = sorted((rl(a), rl(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def colors(vis):
    """Fond sombre teinté par la charte ; accent assez lumineux pour se lire sur ce fond."""
    acc = vis.get("panelAccent") or vis.get("accentColor", "#7CE3A1")
    if _lum(acc) < 110:  # accent sombre (espresso, marine) : on l'éclaircit pour le panneau
        acc = _mix(acc, "#ffffff", 0.45)
    base = vis.get("panelBg") or _mix("#0b0c0e", acc, 0.035)  # presque noir : l'accent ne vit que dans la lueur
    return base, _mix(base, acc, 0.16), acc, ("#111111" if _lum(acc) > 160 else "#ffffff")


def fonts(job):
    d = job / "assets" / "fonts"
    d.mkdir(parents=True, exist_ok=True)
    for f in ("InstrumentSerif-Italic.ttf", "IBMPlexMono-Medium.ttf"):
        shutil.copy2(VENDOR / f, d / f)
    return ("@font-face { font-family: 'Instrument Serif'; src: url('assets/fonts/InstrumentSerif-Italic.ttf'); font-style: italic; font-weight: 400; } "
            "@font-face { font-family: 'IBM Plex Mono'; src: url('assets/fonts/IBMPlexMono-Medium.ttf'); font-weight: 500; }")


def css(W, ph, fam, vis):
    base, tint, acc, on_acc = colors(vis)
    u = W / 1080
    noise = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'>"
             "<feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/></filter>"
             "<rect width='100%' height='100%' filter='url(%23n)' opacity='.55'/></svg>")
    return f"""
  #panel {{ position: absolute; left: 0; top: 0; width: {W}px; height: {ph}px; overflow: hidden; z-index: 20; background: {base};
           font-family: '{fam}', 'Inter', sans-serif; color: #f4f4f2; }}
  #panel .pbg {{ position: absolute; inset: 0; background: radial-gradient(ellipse 80% 70% at 50% 38%, {tint} 0%, {base} 72%); }}
  #panel .floor {{ position: absolute; left: -{round(W*0.5)}px; width: {round(W*2)}px; height: {round(ph*1.6)}px; top: {round(ph*0.52)}px;
           transform-origin: 50% 0; transform: perspective({round(900*u)}px) rotateX(64deg); overflow: hidden; opacity: .55;
           -webkit-mask-image: linear-gradient(to bottom, transparent 0%, #000 30%, #000 60%, transparent 100%); }}
  #panel .floor .fl {{ position: absolute; left: 0; right: 0; top: 0; height: 600%;
           background-image: linear-gradient({acc}26 2px, transparent 2px), linear-gradient(90deg, {acc}26 2px, transparent 2px);
           background-size: {round(120*u)}px {round(120*u)}px; }}
  #panel .sweep {{ position: absolute; top: -20%; left: -60%; width: 45%; height: 140%; transform: rotate(18deg);
           background: linear-gradient(90deg, transparent, rgba(255,255,255,.06), transparent); }}
  #panel .grain {{ position: absolute; inset: 0; background-image: url("{noise}"); opacity: .10; mix-blend-mode: overlay; }}
  #panel .vig {{ position: absolute; inset: 0; background: radial-gradient(ellipse 90% 85% at 50% 45%, transparent 55%, rgba(0,0,0,.55) 100%); }}
  #panel .flash {{ position: absolute; left: 50%; top: 45%; width: {round(900*u)}px; height: {round(900*u)}px; margin: -{round(450*u)}px 0 0 -{round(450*u)}px;
           border-radius: 50%; background: radial-gradient(circle, rgba(255,255,255,.9) 0%, {acc}55 35%, transparent 70%); opacity: 0; z-index: 9; }}
  .beat {{ position: absolute; inset: 0; z-index: 5; }}
  .beat .bi {{ position: absolute; inset: 0; opacity: 0; }}
  .tag {{ position: absolute; right: {round(56*u)}px; top: {round(52*u)}px; font: 500 {round(24*u)}px 'IBM Plex Mono', monospace; letter-spacing: .14em;
         text-transform: uppercase; color: rgba(244,244,242,.6); display: flex; align-items: center; gap: {round(12*u)}px; }}
  .tag::before {{ content: ""; width: {round(10*u)}px; height: {round(10*u)}px; border-radius: 50%; background: {acc}; box-shadow: 0 0 {round(14*u)}px {acc}; }}
  .ttl {{ position: absolute; left: {round(70*u)}px; right: {round(70*u)}px; top: {round(ph*0.15)}px; font-weight: 800; font-size: {round(112*u)}px;
         line-height: 1.02; letter-spacing: -.025em; text-wrap: balance; }}
  .ttl .w {{ display: inline-block; opacity: 0; margin-right: .22em; }}
  .ttl .it {{ font-family: 'Instrument Serif', Georgia, serif; font-style: italic; font-weight: 400; letter-spacing: 0; color: {acc};
             font-size: 1.12em; }}
  .mark {{ position: absolute; left: 50%; top: {round(ph*0.62)}px; width: {round(150*u)}px; height: {round(150*u)}px; margin-left: -{round(75*u)}px;
          background: {acc}; clip-path: polygon(50% 0%, 61% 39%, 100% 50%, 61% 61%, 50% 100%, 39% 61%, 0% 50%, 39% 39%);
          filter: drop-shadow(0 0 {round(30*u)}px {acc}); opacity: 0; }}
  .card {{ position: absolute; left: {round(70*u)}px; right: {round(70*u)}px; top: {round(ph*0.17)}px; border-radius: {round(26*u)}px;
          background: linear-gradient(180deg, rgba(255,255,255,.085), rgba(255,255,255,.035)); border: 1px solid rgba(255,255,255,.14);
          box-shadow: 0 {round(30*u)}px {round(80*u)}px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.12); padding: {round(34*u)}px {round(38*u)}px; }}
  .chead {{ font: 500 {round(24*u)}px 'IBM Plex Mono', monospace; letter-spacing: .12em; text-transform: uppercase; color: rgba(244,244,242,.55);
           margin-bottom: {round(22*u)}px; }}
  .row {{ display: flex; align-items: center; gap: {round(22*u)}px; padding: {round(22*u)}px 0; font-size: {round(56*u)}px; font-weight: 600;
         border-top: 1px solid rgba(255,255,255,.08); opacity: 0; }}
  .box {{ flex: 0 0 auto; width: {round(56*u)}px; height: {round(56*u)}px; border-radius: {round(12*u)}px; border: 2px solid rgba(255,255,255,.35);
         position: relative; }}
  .box i {{ position: absolute; inset: -2px; border-radius: {round(10*u)}px; background: {acc}; display: flex; align-items: center;
           justify-content: center; color: {on_acc}; font-style: normal; font-weight: 900; font-size: {round(32*u)}px; transform: scale(0); }}
  .stamp {{ position: absolute; right: {round(150*u)}px; bottom: {round(ph*0.15)}px; padding: .1em .4em; border: {round(6*u)}px solid {acc}; color: {acc};
           font-weight: 900; font-size: {round(62*u)}px; letter-spacing: .04em; text-transform: uppercase; border-radius: {round(10*u)}px;
           transform: rotate(-8deg); opacity: 0; background: rgba(0,0,0,.25); box-shadow: 0 0 {round(40*u)}px {acc}55; }}
  .big {{ position: absolute; left: 0; right: 0; top: {round(ph*0.22)}px; text-align: center; font-weight: 800; font-size: {round(230*u)}px;
         letter-spacing: -.04em; line-height: 1; font-variant-numeric: tabular-nums; }}
  .big .px {{ color: {acc}; }}
  .lbl {{ position: absolute; left: 0; right: 0; top: {round(ph*0.22 + 250*u)}px; text-align: center; font-family: 'Instrument Serif', Georgia, serif;
         font-style: italic; font-size: {round(70*u)}px; color: rgba(244,244,242,.85); opacity: 0; }}
  .bar {{ position: absolute; left: {round(W*0.3)}px; right: {round(W*0.3)}px; top: {round(ph*0.22 + 236*u)}px; height: {round(6*u)}px;
         background: {acc}; transform-origin: 0 50%; transform: scaleX(0); box-shadow: 0 0 {round(20*u)}px {acc}; }}
  .win {{ padding: 0; overflow: hidden; }}
  .wbar {{ display: flex; align-items: center; gap: {round(12*u)}px; padding: {round(20*u)}px {round(26*u)}px; background: rgba(255,255,255,.05);
          border-bottom: 1px solid rgba(255,255,255,.08); }}
  .wbar b {{ width: {round(16*u)}px; height: {round(16*u)}px; border-radius: 50%; background: rgba(255,255,255,.25); }}
  .field {{ margin: {round(28*u)}px {round(30*u)}px {round(10*u)}px; padding: {round(20*u)}px {round(26*u)}px; border-radius: {round(16*u)}px;
           border: 2px solid {acc}; font-size: {round(50*u)}px; font-weight: 600; min-height: {round(56*u)}px; box-shadow: 0 0 {round(26*u)}px {acc}40; }}
  .field .q::after {{ content: ""; display: inline-block; width: {round(4*u)}px; height: .9em; background: {acc}; margin-left: 4px; vertical-align: -.1em; }}
  .res {{ margin: {round(14*u)}px {round(30*u)}px; padding: {round(18*u)}px {round(24*u)}px; border-radius: {round(14*u)}px;
         background: rgba(255,255,255,.04); font-size: {round(44*u)}px; font-weight: 600; opacity: 0; }}
  .res small {{ display: block; height: {round(10*u)}px; width: 60%; margin-top: {round(12*u)}px; border-radius: 6px; background: rgba(255,255,255,.12); }}
  .res.top {{ border: 1px solid {acc}; box-shadow: 0 0 {round(30*u)}px {acc}40; }}
  .ph {{ position: absolute; left: {round(110*u)}px; right: {round(110*u)}px; top: {round(120*u)}px; bottom: {round(ph*0.14)}px; border-radius: {round(24*u)}px;
        overflow: hidden; border: 2px solid {acc}; box-shadow: 0 0 {round(50*u)}px {acc}44, 0 {round(30*u)}px {round(70*u)}px rgba(0,0,0,.5); }}
  .ph img, .ph video {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
  .cap2 {{ position: absolute; left: 0; right: 0; bottom: {round(ph*0.045)}px; text-align: center; font: 500 {round(26*u)}px 'IBM Plex Mono', monospace;
          letter-spacing: .12em; text-transform: uppercase; color: rgba(244,244,242,.65); }}
  .stp {{ display: flex; align-items: center; gap: {round(26*u)}px; margin: 0 0 {round(22*u)}px; padding: {round(28*u)}px {round(32*u)}px;
         border-radius: {round(22*u)}px; background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.10); font-size: {round(60*u)}px;
         font-weight: 700; opacity: 0; }}
  .stp .n {{ flex: 0 0 auto; width: {round(70*u)}px; height: {round(70*u)}px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
            font: 500 {round(32*u)}px 'IBM Plex Mono', monospace; border: 2px solid rgba(255,255,255,.3); }}
  .stp.on {{ background: {acc}22; border-color: {acc}; }}
  .stp.on .n {{ background: {acc}; color: {on_acc}; border-color: {acc}; }}
  .stps {{ position: absolute; left: {round(80*u)}px; right: {round(80*u)}px; top: {round(ph*0.2)}px; }}
  .ico {{ display: inline-flex; flex: 0 0 auto; width: 1.05em; height: 1.05em; color: {acc}; }}
  .ico svg {{ stroke-width: 2.2; }}
  .stp .n svg {{ width: 62%; height: 62%; }}
  .bigico {{ position: absolute; left: 50%; top: {round(ph*0.58)}px; width: {round(190*u)}px; height: {round(190*u)}px; margin-left: -{round(95*u)}px;
            color: {acc}; opacity: 0; filter: drop-shadow(0 0 {round(24*u)}px {acc}66); }}
  .igrid {{ position: absolute; left: {round(60*u)}px; right: {round(60*u)}px; top: {round(ph*0.2)}px; display: grid; gap: {round(46*u)}px {round(30*u)}px; }}
  .ic {{ text-align: center; opacity: 0; }}
  .ic .cir {{ width: {round(200*u)}px; height: {round(200*u)}px; border-radius: 50%; margin: 0 auto; background: {acc}; color: {on_acc};
             display: flex; align-items: center; justify-content: center; box-shadow: 0 {round(14*u)}px {round(40*u)}px {acc}55; }}
  .ic .cir svg {{ width: 50%; height: 50%; stroke-width: 2; }}
  .ic .lab {{ margin-top: {round(22*u)}px; font-size: {round(46*u)}px; font-weight: 700; line-height: 1.1; }}
  .ihead {{ position: absolute; left: 0; right: 0; top: {round(ph*0.08)}px; text-align: center; font: 500 {round(26*u)}px 'IBM Plex Mono', monospace;
           letter-spacing: .12em; text-transform: uppercase; opacity: .65; }}"""


def title_words(text):
    """*mot* -> italique serif ; renvoie le HTML des mots."""
    out_ = []
    for m in re.finditer(r"\*([^*]+)\*|(\S+)", text):
        if m.group(1):
            out_ += [f'<span class="w it">{esc(w)}</span>' for w in m.group(1).split()]
        else:
            out_.append(f'<span class="w">{esc(m.group(2))}</span>')
    # un petit mot (de, le, à, ça…) ne finit jamais une ligne : il reste collé au mot suivant
    from build_text import WEAK, deac
    raw = re.findall(r"\*[^*]+\*|\S+", text)
    flat = [w for tok in raw for w in (tok.strip("*").split() if tok.startswith("*") else [tok])]
    glued, k = [], 0
    while k < len(out_):
        j = k
        while j + 1 < len(out_) and deac(re.sub(r"[^\w'’]", "", flat[j] if j < len(flat) else "").lower()) in WEAK:
            j += 1
        glued.append(out_[k] if j == k else '<span class="u" style="white-space:nowrap">' + " ".join(out_[k:j + 1]) + "</span>")
        k = j + 1
    out_ = glued
    h = " ".join(out_)
    # ponctuation jamais seule en début de ligne : collée au mot d'avant (espace insécable devant ? ! : ; à la française)
    h = re.sub(r'</span> <span class="w">([?!:;»]+)</span>', lambda m_: "&nbsp;" + m_.group(1) + "</span>", h)
    return re.sub(r'</span> <span class="w">([,.…]+)</span>', lambda m_: m_.group(1) + "</span>", h)


def background_js(dur, T0):
    """Le sol en perspective avance lentement, un reflet traverse le panneau toutes les 7 s."""
    total = round(dur + T0, 2)
    return (f'  tl.fromTo("#panel .floor .fl", {{ y: 0 }}, {{ y: -{round(total * 40)}, duration: {total}, ease: "none", immediateRender: false }}, 0);\n'
            f'  tl.fromTo("#panel .sweep", {{ x: 0 }}, {{ x: 2400, duration: 7, ease: "power1.inOut", repeat: {max(0, int(total // 7))}, '
            f'immediateRender: false }}, 0.5);')


def paper_colors(vis):
    """Thème papier : fond de la charte, encre, accent assez soutenu pour porter du texte blanc."""
    bg, ink = vis.get("bgColor", "#f4efe6"), vis.get("inkColor", "#1d1b19")
    if _lum(bg) < 150:  # charte sombre : le papier reste clair
        bg = "#f4efe6"
    acc = vis.get("paperAccent") or vis.get("accentColor", "#9b1b30")
    if _lum(acc) > 165:
        acc = _mix(acc, ink, 0.45)
    base = acc
    for t in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6):  # texte blanc lisible (WCAG 4,5:1) sur l'accent
        if _contrast(acc, "#ffffff") >= 4.6:
            break
        acc = _mix(base, ink if _lum(ink) < 90 else "#000000", t)
    return bg, ink, acc, _mix(bg, "#ffffff", 0.65)


def css_paper(W, ph, fam, vis):
    """Thème « explainer papier » : mêmes temps forts, rendu carte papier, encre, ombres franches (surcharge du thème sombre)."""
    bg, ink, acc, paper = paper_colors(vis)
    u = W / 1080
    sh = f"{round(8*u)}px {round(8*u)}px 0 {ink}"
    return css(W, ph, fam, {**vis, "panelAccent": acc}) + f"""
  #panel.paper {{ position: absolute; inset: 0; width: auto; height: auto; background: transparent; color: {ink}; z-index: 5; }}
  #panel.paper .tag {{ display: none; }}
  #panel.paper .flash {{ background: radial-gradient(circle, {acc}66 0%, transparent 65%); }}
  #panel.paper .ttl {{ color: {ink}; }}
  #panel.paper .ttl .it {{ color: {acc}; }}
  #panel.paper .mark {{ background: {acc}; filter: none; }}
  #panel.paper .card {{ background: #fff; border: {max(2, round(3*u))}px solid {ink}; border-radius: {round(10*u)}px; box-shadow: {sh}; color: {ink}; }}
  #panel.paper .chead {{ color: {ink}; opacity: .6; }}
  #panel.paper .row {{ border-top: 1px solid {ink}22; }}
  #panel.paper .box {{ border-color: {ink}; }}
  #panel.paper .box i {{ background: {acc}; color: #fff; }}
  #panel.paper .stamp {{ background: #fff; color: {acc}; border-color: {acc}; box-shadow: {sh}; }}
  #panel.paper .big, #panel.paper .lbl {{ color: {ink}; }}
  #panel.paper .big .px {{ color: {acc}; }}
  #panel.paper .bar {{ background: {acc}; box-shadow: none; }}
  #panel.paper .wbar {{ background: {ink}0d; border-bottom: 2px solid {ink}; }}
  #panel.paper .wbar b {{ background: {ink}55; }}
  #panel.paper .field {{ border-color: {ink}; box-shadow: none; }}
  #panel.paper .field .q::after {{ background: {acc}; }}
  #panel.paper .res {{ background: {ink}08; }}
  #panel.paper .res small {{ background: {ink}22; }}
  #panel.paper .res.top {{ border: 2px solid {acc}; box-shadow: none; }}
  #panel.paper .ph {{ border: {max(2, round(3*u))}px solid {ink}; box-shadow: {sh}; border-radius: {round(10*u)}px; }}
  #panel.paper .cap2 {{ color: {ink}; opacity: .7; }}
  #panel.paper .stp {{ background: #fff; border: {max(2, round(3*u))}px solid {ink}; box-shadow: {sh}; color: {ink}; }}
  #panel.paper .stp .n {{ border-color: {ink}; }}
  #panel.paper .stp.on {{ background: {acc}; color: #fff; border-color: {ink}; }}
  #panel.paper .stp.on .n {{ background: #fff; color: {acc}; border-color: #fff; }}
  #panel.paper .ttl {{ top: {round(ph*0.24)}px; font-size: {round(118*u)}px; }}
  #panel.paper .mark {{ top: {round(ph*0.66)}px; }}
  #panel.paper .card {{ top: {round(ph*0.22)}px; }}
  #panel.paper .row {{ font-size: {round(62*u)}px; padding: {round(26*u)}px 0; }}
  #panel.paper .chead {{ font-size: {round(28*u)}px; }}
  #panel.paper .big {{ top: {round(ph*0.24)}px; font-size: {round(300*u)}px; }}
  #panel.paper .bar {{ top: {round(ph*0.24 + 320*u)}px; }}
  #panel.paper .lbl {{ top: {round(ph*0.24 + 345*u)}px; font-size: {round(84*u)}px; }}
  #panel.paper .stps {{ top: {round(ph*0.2)}px; }}
  #panel.paper .stp {{ font-size: {round(64*u)}px; padding: {round(32*u)}px {round(34*u)}px; margin-bottom: {round(28*u)}px; }}
  #panel.paper .ph {{ top: {round(ph*0.12)}px; bottom: {round(ph*0.16)}px; }}
  #panel.paper .ic .cir {{ border: {max(2, round(3*u))}px solid {ink}; box-shadow: {sh}; color: #fff; }}
  #panel.paper .ic .lab {{ color: {ink}; }}
  #panel.paper .bigico {{ filter: none; top: {round(ph*0.68)}px; }}
  #panel.paper .igrid {{ top: {round(ph*0.24)}px; }}
  #panel.paper .ic .cir {{ width: {round(270*u)}px; height: {round(270*u)}px; }}
  #panel.paper .ic .lab {{ font-size: {round(58*u)}px; margin-top: {round(28*u)}px; }}
  #panel.paper .ihead {{ top: {round(ph*0.1)}px; font-size: {round(30*u)}px; }}
  #panel.paper .ihead {{ color: {ink}; }}"""


def nodes(job, beats, words, dur, T0, W, ph, vis, theme="dark", origin=(0, 0)):
    """-> (html du panneau, lignes JS, rapport, calques). Temps : contenu (avant intro) ; T0 ajouté aux data-start.
    Calques : vidéos et emojis animés posés HORS du panneau (une vidéo minutée ne s'imbrique pas dans un temps fort),
    positionnés par rapport à la racine grâce à origin = coin haut-gauche de la scène."""
    u = W / 1080
    ox, oy = origin
    layers = []
    placed = []
    for b in beats or []:
        hit = word_hit(words, b.get("word", ""), b.get("occurrence", 1)) if b.get("word") else None
        t = (hit["start"] - 0.12) if hit else (b.get("_t") if b.get("_t") is not None else None)
        if t is None:
            continue
        placed.append((max(0.0, t), b))
    placed.sort(key=lambda x: x[0])
    if placed:
        placed[0] = (0.0, placed[0][1])  # le panneau n'est jamais vide au début
    html_, js, rep = [], ([background_js(dur, T0)] if theme == "dark" else []), []
    for k, (t0, b) in enumerate(placed):
        t1 = placed[k + 1][0] if k + 1 < len(placed) else dur
        if t1 - t0 < 0.5:
            continue
        d, s0 = round(t1 - t0, 3), round(t0, 3)
        sid, typ = f"bt{k}", b.get("type", "title")
        tag = f'<div class="tag">{esc(b["tag"])}</div>' if b.get("tag") else ""
        inner, bj = "", []
        if typ == "title":
            big = icon(b["icon"]) if b.get("icon") else ""
            inner = (f'<div class="ttl">{title_words(b.get("text", ""))}</div>'
                     + (f'<div class="bigico">{big}</div>' if big else ('<div class="mark"></div>' if b.get("mark") else "")))
            if big:
                bj.append(f'  tl.fromTo("#{sid} .bigico", {{ opacity: 0, scale: 0.3, rotation: -25 }}, {{ opacity: 1, scale: 1, rotation: 0, '
                          f'duration: 0.65, ease: "back.out(2.4)", immediateRender: false }}, {s0 + 0.45});')
                bj.append(f'  tl.to("#{sid} .bigico", {{ y: -{round(14*u)}, duration: 1.2, ease: "sine.inOut", yoyo: true, repeat: {max(0, int((d - 1.2) // 1.2))} }}, {s0 + 1.1});')
            bj.append(f'  tl.fromTo("#{sid} .ttl .w", {{ opacity: 0, y: 34, filter: "blur(10px)" }}, {{ opacity: 1, y: 0, filter: "blur(0px)", '
                      f'duration: 0.42, stagger: 0.11, ease: "power3.out", immediateRender: false }}, {s0 + 0.08});')
            bj.append(f'  tl.fromTo("#{sid} .ttl .it", {{ scale: 1.25, rotation: -5 }}, {{ scale: 1, rotation: 0, duration: 0.6, '
                      f'ease: "back.out(2.4)", immediateRender: false }}, {s0 + 0.2});')
            if b.get("mark"):
                bj.append(f'  tl.fromTo("#{sid} .mark", {{ opacity: 0, scale: 0.2, rotation: -90 }}, {{ opacity: 1, scale: 1, rotation: 0, '
                          f'duration: 0.7, ease: "back.out(2.2)", immediateRender: false }}, {s0 + 0.45});')
                bj.append(f'  tl.to("#{sid} .mark", {{ rotation: 45, duration: {max(0.5, d - 1.2)}, ease: "none" }}, {s0 + 1.15});')
        elif typ == "check":
            items = b.get("items", [])[:5]
            rows = "".join(f'<div class="row r{j}"><span class="box"><i>✓</i></span>'
                           + (f'<span class="ico">{item_icon(it)}</span>' if item_icon(it) else "")
                           + f'<span>{esc(item_text(it))}</span></div>' for j, it in enumerate(items))
            inner = (f'<div class="card"><div class="chead">{esc(b.get("title", ""))}</div>{rows}</div>'
                     + (f'<div class="stamp">{esc(b["stamp"])}</div>' if b.get("stamp") else ""))
            bj.append(f'  tl.fromTo("#{sid} .card", {{ opacity: 0, y: 50, rotationX: 14, transformPerspective: 900 }}, {{ opacity: 1, y: 0, '
                      f'rotationX: 0, duration: 0.55, ease: "power3.out", immediateRender: false }}, {s0 + 0.05});')
            span = max(0.35, (d * 0.7 - 0.5) / max(1, len(items)))
            for j in range(len(items)):
                tj = round(s0 + 0.35 + j * span, 3)
                bj.append(f'  tl.fromTo("#{sid} .r{j}", {{ opacity: 0, x: -24 }}, {{ opacity: 1, x: 0, duration: 0.3, ease: "power2.out", immediateRender: false }}, {tj});')
                bj.append(f'  tl.fromTo("#{sid} .r{j} .box i", {{ scale: 0 }}, {{ scale: 1, duration: 0.32, ease: "back.out(3)", immediateRender: false }}, {round(tj + 0.18, 3)});')
            if b.get("stamp"):
                ts = round(s0 + 0.35 + len(items) * span + 0.1, 3)
                bj.append(f'  tl.fromTo("#{sid} .stamp", {{ opacity: 0, scale: 2.4, rotation: -20 }}, {{ opacity: 1, scale: 1, rotation: -8, '
                          f'duration: 0.38, ease: "back.out(2)", immediateRender: false }}, {ts});')
                bj.append(f'  tl.fromTo("#panel .flash", {{ opacity: 0.7, scale: 0.3 }}, {{ opacity: 0, scale: 1.3, duration: 0.5, ease: "power2.out", '
                          f'immediateRender: false }}, {ts});')
        elif typ == "stat":
            v = float(str(b.get("value", 0)).replace(" ", "").replace(",", "."))
            dec = 1 if (v % 1) else 0
            inner = (f'<div class="big"><span class="px">{esc(b.get("prefix", ""))}</span><span class="num">0</span>'
                     f'<span class="px">{esc(b.get("suffix", ""))}</span></div><div class="bar"></div><div class="lbl">{esc(b.get("label", ""))}</div>')
            bj.append(f'  tl.fromTo("#{sid} .big", {{ opacity: 0, scale: 0.85 }}, {{ opacity: 1, scale: 1, duration: 0.5, ease: "back.out(1.8)", immediateRender: false }}, {s0 + 0.05});')
            bj.append(f'  (function () {{ const el = document.querySelector("#{sid} .num"), o = {{ v: 0 }};'
                      f' tl.fromTo(o, {{ v: 0 }}, {{ v: {v}, duration: {round(min(1.6, d * 0.5), 2)}, ease: "power2.out", immediateRender: false,'
                      f' onUpdate: function () {{ el.textContent = o.v.toLocaleString("fr-FR", {{ minimumFractionDigits: {dec}, maximumFractionDigits: {dec} }}); }} }}, {s0 + 0.1}); }})();')
            bj.append(f'  tl.fromTo("#{sid} .bar", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.7, ease: "power3.inOut", immediateRender: false }}, {s0 + 0.4});')
            bj.append(f'  tl.fromTo("#{sid} .lbl", {{ opacity: 0, y: 20 }}, {{ opacity: 1, y: 0, duration: 0.45, ease: "power2.out", immediateRender: false }}, {s0 + 0.7});')
        elif typ == "search":
            q, res = b.get("query", ""), b.get("results", [])[:3]
            rows = "".join(f'<div class="res{" top" if j == 0 else ""} s{j}">{esc(r)}<small></small></div>' for j, r in enumerate(res))
            inner = (f'<div class="card win"><div class="wbar"><b></b><b></b><b></b></div><div class="field"><span class="q"></span></div>{rows}</div>')
            bj.append(f'  tl.fromTo("#{sid} .card", {{ opacity: 0, y: 40, scale: 0.96 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.5, ease: "power3.out", immediateRender: false }}, {s0 + 0.05});')
            tq = round(min(1.4, 0.06 * len(q) + 0.2), 2)
            bj.append(f'  (function () {{ const el = document.querySelector("#{sid} .q"), q = {json.dumps(q, ensure_ascii=False)}, o = {{ n: 0 }};'
                      f' tl.fromTo(o, {{ n: 0 }}, {{ n: q.length, duration: {tq}, ease: "none", immediateRender: false,'
                      f' onUpdate: function () {{ el.textContent = q.slice(0, Math.round(o.n)); }} }}, {s0 + 0.4}); }})();')
            for j in range(len(res)):
                bj.append(f'  tl.fromTo("#{sid} .s{j}", {{ opacity: 0, y: 26 }}, {{ opacity: 1, y: 0, duration: 0.35, ease: "power2.out", immediateRender: false }}, {round(s0 + 0.5 + tq + j * 0.18, 3)});')
        elif typ == "image":
            src = b.get("image", "")
            p = Path(src)
            if not (job / p).exists():
                for base in (job / "inbox", ROOT):
                    if (base / p).exists():
                        (job / "assets" / "img").mkdir(parents=True, exist_ok=True)
                        shutil.copy2(base / p, job / "assets" / "img" / p.name)
                        src = f"assets/img/{p.name}"
                        break
            if not src:
                rep.append({"type": typ, "pose": False, "raison": "pas d'image (panel.py fetch pour une query)"})
                continue
            is_vid = src.lower().endswith((".mp4", ".webm", ".mov"))
            med = "" if is_vid else f'<img src="{esc(src)}" alt="">'
            inner = f'<div class="ph">{med}</div>' + (f'<div class="cap2">{esc(b["caption"])}</div>' if b.get("caption") else "")
            if is_vid:  # le cadre est dans le temps fort, la vidéo dans un calque à la même place
                x, y, w, h, rad = media_box(W, ph, theme)
                lid = f"lv{k}"
                layers.append(f'    <div class="mlayer" id="{lid}" style="position:absolute;left:{ox + x}px;top:{oy + y}px;width:{w}px;height:{h}px;'
                              f'border-radius:{rad}px;overflow:hidden;z-index:30;opacity:0"><video id="{lid}v" class="clip" src="{esc(src)}" '
                              f'data-start="{round(s0 + T0, 3)}" data-duration="{d}" data-track-index="{80 + k}" muted playsinline '
                              f'style="width:100%;height:100%;object-fit:cover;display:block"></video></div>')
                bj.append(f'  tl.fromTo("#{sid} .ph", {{ opacity: 0, y: 60 }}, {{ opacity: 1, y: 0, duration: 0.6, ease: "power3.out", immediateRender: false }}, {s0 + 0.05});')
                bj.append(f'  tl.fromTo("#{lid}", {{ opacity: 0, y: 60 }}, {{ opacity: 1, y: 0, duration: 0.6, ease: "power3.out", immediateRender: false }}, {s0 + 0.05});')
                if k + 1 < len(placed):
                    bj.append(f'  tl.to("#{lid}", {{ opacity: 0, y: -16, duration: 0.22, ease: "power2.in" }}, {round(t1 - 0.22, 3)});')
            else:
                bj.append(f'  tl.fromTo("#{sid} .ph", {{ opacity: 0, y: 60, rotationX: 16, transformPerspective: 1000 }}, {{ opacity: 1, y: 0, rotationX: 0, '
                          f'duration: 0.6, ease: "power3.out", immediateRender: false }}, {s0 + 0.05});')
                bj.append(f'  tl.fromTo("#{sid} .ph img", {{ scale: 1.0 }}, {{ scale: 1.1, duration: {d}, ease: "none", immediateRender: false }}, {s0});')
        elif typ == "steps":
            items = b.get("items", [])[:4]
            rows = "".join(f'<div class="stp p{j}"><span class="n">{item_icon(it) or j + 1}</span><span>{esc(item_text(it))}</span></div>'
                           for j, it in enumerate(items))
            inner = f'<div class="stps">{rows}</div>'
            span = max(0.4, (d - 0.6) / max(1, len(items)))
            for j in range(len(items)):
                tj = round(s0 + 0.15 + j * span, 3)
                bj.append(f'  tl.fromTo("#{sid} .p{j}", {{ opacity: 0, x: 40 }}, {{ opacity: 1, x: 0, duration: 0.4, ease: "power3.out", immediateRender: false }}, {tj});')
                bj.append(f'  tl.call(function () {{ document.querySelectorAll("#{sid} .stp").forEach(function (e, i) {{ e.classList.toggle("on", i === {j}); }}); }}, null, {tj});')
        elif typ == "icons":
            items = b.get("items", [])[:6]
            cols = 2 if len(items) == 4 else min(3, max(1, len(items)))
            cells = "".join(f'<div class="ic c{j}"><div class="cir">{item_icon(it)}</div><div class="lab">{esc(item_text(it))}</div></div>'
                            for j, it in enumerate(items))
            inner = ((f'<div class="ihead">{esc(b["title"])}</div>' if b.get("title") else "")
                     + f'<div class="igrid" style="grid-template-columns:repeat({cols},1fr)">{cells}</div>')
            span = max(0.25, min(0.6, (d * 0.6) / max(1, len(items))))
            for j in range(len(items)):
                tj = round(s0 + 0.15 + j * span, 3)
                bj.append(f'  tl.fromTo("#{sid} .c{j}", {{ opacity: 0, y: -{round(120*u)}, rotation: {(-12, 10, -6, 8, -10, 6)[j]} }}, {{ opacity: 1, y: 0, rotation: 0, '
                          f'duration: 0.7, ease: "bounce.out", immediateRender: false }}, {tj});')
        else:
            rep.append({"type": typ, "pose": False, "raison": "type inconnu"})
            continue
        lo = b.get("lottie")
        if lo:  # emoji animé (library/lottie) posé dans la scène, rejoué en boucle pendant le temps fort
            import math
            lm = ROOT / "library" / "lottie" / str(lo.get("name", "")) / "lottie.json"
            if lm.exists() and "webm" in read_json(lm):
                meta = read_json(lm)
                (job / "assets" / "lottie").mkdir(parents=True, exist_ok=True)
                shutil.copy2(lm.parent / meta["webm"], job / "assets" / "lottie" / meta["webm"])
                from common import add_credit
                add_credit(job, meta["credit"])
                size = round(W * float(lo.get("size", 26)) / 100)
                lx = ox + round(W * float(lo.get("x", 78)) / 100) - size // 2
                ly = oy + round(ph * float(lo.get("y", 72)) / 100) - size // 2
                one = float(meta.get("rendered_duration") or meta.get("duration") or 1.5)
                start = s0 + 0.4
                n = max(1, math.ceil((t1 - start - 0.25) / one - 0.05))
                for r_ in range(n):
                    layers.append(f'    <video id="lo{k}_{r_}" class="clip" src="assets/lottie/{meta["webm"]}" data-start="{round(start + T0 + r_ * one, 3)}" '
                                  f'data-duration="{round(min(one, t1 - start - r_ * one), 3)}" data-track-index="{90 + k}" muted playsinline '
                                  f'style="position:absolute;left:{lx}px;top:{ly}px;width:{size}px;height:{size}px;z-index:35"></video>')
        html_.append(f'      <div class="clip beat" id="{sid}" data-start="{round(s0 + T0, 3)}" data-duration="{d}" data-track-index="{70 + k % 2}">'
                     f'<div class="bi">{tag}{inner}</div></div>')
        js.append(f'  tl.fromTo("#{sid} .bi", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.25, ease: "power1.out", immediateRender: false }}, {s0});')
        if b.get("tag"):
            js.append(f'  tl.fromTo("#{sid} .tag", {{ opacity: 0, x: 20 }}, {{ opacity: 1, x: 0, duration: 0.4, ease: "power2.out", immediateRender: false }}, {s0 + 0.05});')
        if b.get("flash") and typ != "check":
            js.append(f'  tl.fromTo("#panel .flash", {{ opacity: 0.8, scale: 0.3 }}, {{ opacity: 0, scale: 1.4, duration: 0.55, ease: "power2.out", immediateRender: false }}, {s0 + 0.15});')
        js += bj
        if k + 1 < len(placed):
            js.append(f'  tl.to("#{sid} .bi", {{ opacity: 0, y: -16, duration: 0.22, ease: "power2.in" }}, {round(t1 - 0.22, 3)});')
        rep.append({"type": typ, "a": s0, "duree": d, "mot": b.get("word")})
    panel = (f'    <div id="panel"><div class="pbg"></div><div class="floor"><div class="fl"></div></div><div class="sweep"></div>'
             f'\n{chr(10).join(html_)}\n      <div class="flash"></div><div class="grain"></div><div class="vig"></div></div>')
    if theme == "paper":  # pas de décor sombre : le papier et le motif sont dessinés par build_explainer
        panel = f'    <div id="panel" class="paper">\n{chr(10).join(html_)}\n      <div class="flash"></div></div>'
    return panel, js, rep, layers


def default_beats(text_json):
    """Sans panels.json : un titre par phrase forte gardée (overlays de text.json), mot fort = le plus long."""
    beats = []
    for o in (text_json.get("overlays") or []):
        if not o.get("keep") or not o.get("words"):
            continue
        ws = [w["w"].strip(".,!?…;:") for w in o["words"]]
        j = max(range(len(ws)), key=lambda i: len(ws[i]))
        txt = " ".join(f"*{w}*" if i == j else w for i, w in enumerate(ws))
        beats.append({"type": "title", "_t": float(o["start"]), "text": txt})
    return beats


def fetch(job_name, slug):
    """Temps forts "image" avec "query" et sans "image" : Pixabay (vidéos assez longues puis photos), 1re posée, planche."""
    import argparse as _a

    from broll import candidates, download, planche
    from common import config, size_of
    job = job_dir(job_name)
    pj = job / "work" / f"{slug}_panels.json"
    beats = read_json(pj)
    items, rep_ = [], []
    for i, b in enumerate(beats):
        if b.get("type") != "image" or b.get("image") or not b.get("query"):
            continue
        alts = [x for x in candidates(job, b["query"], True, None, "wide") if float(x.get("duree") or 0) >= 4][:3]
        alts += candidates(job, b["query"], False, None, "wide")[:3]
        if not alts:
            rep_.append({"temps_fort": i, "query": b["query"], "raison": "aucun résultat"})
            continue
        b["image"], _ = download(job, _a.Namespace(id=alts[0]["id"]))
        items.append({"beat": i, "query": b["query"], "phrase": b.get("text") or b.get("caption") or b.get("word", ""),
                      "alts": [x["id"] for x in alts], "_alts": alts})
        rep_.append({"temps_fort": i, "query": b["query"], "image": b["image"]})
    from common import write_json as _w
    _w(pj, beats)
    _w(job / "work" / f"{slug}_panels_alts.json", [{k: v for k, v in it.items() if k != "_alts"} for it in items])
    pl = planche(job, items) if items else None
    out(ok=True, images=rep_, planche=str(pl) if pl else None, suite="regarde la planche ; panel.py pick <job> <slug> <n> a-f|none")


def pick(job_name, slug, n, choice):
    import argparse as _a

    from broll import download
    job = job_dir(job_name)
    pj, aj = job / "work" / f"{slug}_panels.json", job / "work" / f"{slug}_panels_alts.json"
    beats, alts = read_json(pj), read_json(aj)
    it = alts[int(n) - 1]
    b = beats[it["beat"]]
    if choice == "none":
        b.pop("image", None)
        b["type"] = "title" if b.get("text") else b["type"]
    else:
        b["image"], _ = download(job, _a.Namespace(id=it["alts"]["abcdef".index(choice)] if len(choice) == 1 else choice))
    write_json(pj, beats)
    out(ok=True, temps_fort=it["beat"], image=b.get("image"))


def suggest(job_name, slug):
    from broll import find_moments
    job = job_dir(job_name)
    rows, _ = find_moments(job, slug, 3.0)
    sk = [{"type": "title", "word": r["word"], "occurrence": r["occurrence"], "text": r["phrase"][:60], "tag": "",
           "phrase": r["phrase"]} for r in rows]
    dst = job / "work" / f"{slug}_panels_suggested.json"
    write_json(dst, sk)
    out(ok=True, temps_forts=len(sk), fichier=str(dst),
        suite="réécris chaque temps fort (type, texte court avec *mot fort*, tag de chapitre), puis enregistre work/<slug>_panels.json")


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "suggest":
        suggest(sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 4 and sys.argv[1] == "fetch":
        fetch(sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 6 and sys.argv[1] == "pick":
        pick(*sys.argv[2:6])
    else:
        print(__doc__)
